#!/usr/bin/env python3
"""Local admin panel: shows the state of every meeting and runs pipeline.py jobs one at a time."""
import argparse, datetime as dt, json, os, pathlib, posixpath, re, signal, subprocess, sys, threading, urllib.parse, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import pipeline as p

PORT = 8750
JOBS_DIR = p.STATE / "jobs"
JOBS_FILE = p.STATE / "jobs.json"
lock = threading.Lock()
wake = threading.Condition(lock)
jobs = []        # newest last
current = None   # (job, Popen)
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def now():
    return dt.datetime.now().isoformat(timespec="seconds")


def save_jobs():
    p.write_json(JOBS_FILE, jobs[-60:])


def describe(body):
    """Turn a request from the page into a job. Only these fixed commands can ever run."""
    action = body.get("action")
    if action == "check":
        return "Check for new meetings", ["calendar"], []
    if action == "new":
        return "Download + process new meetings", ["process", "--new"], []
    if action == "latest":
        n = int(body.get("count", 5))
        if not 1 <= n <= 50:
            raise ValueError("Pick between 1 and 50 meetings")
        return f"Download + process latest {n} missing", ["process", "--latest", str(n)], []
    if action == "range":
        a, b = body.get("from", ""), body.get("to", "")
        if not (DATE.fullmatch(a) and DATE.fullmatch(b)) or a > b:
            raise ValueError("Pick a valid from and to date")
        return f"Download + process {a} to {b}", ["process", "--from", a, "--to", b], []
    if action == "build":
        return "Update website", ["build"], []
    if action == "deploy":
        return "Deploy to citycouncil.akwiat.com", ["deploy"], []
    if action == "meeting":
        key, mode = body.get("key", ""), body.get("mode")
        if not DATE.fullmatch(key):
            raise ValueError("Bad meeting date")
        modes = {"all": ("Process", []),
                 "docs": ("Re-download documents", ["--steps", "docs,parse", "--force"]),
                 "captions": ("Redo transcript", ["--steps", "transcribe", "--force"]),
                 "whisper": ("Transcribe with Whisper", ["--steps", "transcribe", "--whisper"]),
                 "summarize": ("Redo summary", ["--steps", "summarize", "--force"])}
        if mode not in modes:
            raise ValueError("Unknown action")
        label, extra = modes[mode]
        return f"{label}: {key}", ["process", "--dates", key] + extra, [key]
    raise ValueError("Unknown action")


def meetings_in(args):
    """Which meetings a job will touch, so the table can show them as queued or running."""
    if args[0] != "process" or "--dates" in args:
        return []
    get = lambda flag: args[args.index(flag) + 1] if flag in args else None
    ns = argparse.Namespace(dates=None, latest=int(get("--latest") or 0), new="--new" in args, from_=get("--from"), to=get("--to"))
    return [p.key_of(m) for m in p.select(ns)]


def add_job(body):
    title, args, keys = describe(body)
    keys = keys or meetings_in(args)
    with lock:
        job = {"id": (max((j["id"] for j in jobs), default=0)) + 1, "title": title, "args": args, "keys": keys,
               "status": "queued", "created": now(), "started": None, "finished": None, "exit": None}
        jobs.append(job)
        save_jobs()
        wake.notify_all()
    return job


def worker():
    global current
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    while True:
        with lock:
            job = next((j for j in jobs if j["status"] == "queued"), None)
            while job is None:
                wake.wait()
                job = next((j for j in jobs if j["status"] == "queued"), None)
            job.update(status="running", started=now())
            save_jobs()
        env = {**os.environ, "PYTHONUNBUFFERED": "1", "PATH": f"{pathlib.Path.home()}/.local/bin:{os.environ.get('PATH', '')}"}
        with open(JOBS_DIR / f"{job['id']}.log", "wb") as out:
            proc = subprocess.Popen([sys.executable, str(p.ROOT / "pipeline.py")] + job["args"], cwd=p.ROOT, env=env,
                                    stdout=out, stderr=subprocess.STDOUT, start_new_session=True)
            with lock:
                current = (job, proc)
            code = proc.wait()
        with lock:
            current = None
            if job["status"] == "cancelling":
                job["status"] = "cancelled"
            else:
                job["status"] = "done" if code == 0 else "failed"
            job.update(finished=now(), exit=code)
            save_jobs()


def state():
    built = p.read_json(p.STATE / "build.json") or {}
    deployed = p.read_json(p.STATE / "deploy.json") or {}
    meetings = [p.meeting_status(m, built) for m in p.council_meetings()]
    with lock:
        active = {k: j["status"] for j in jobs if j["status"] in ("queued", "running") for k in j["keys"]}
        recent = list(reversed(jobs[-25:]))
    for m in meetings:
        m["job"] = active.get(m["key"])
    ready = {m["key"] for m in meetings if m["summary"]}
    built_keys = set(built.get("meetings", {}))
    fingerprint = built.get("fingerprint")
    return {"meetings": meetings, "checked_at": (p.read_json(p.CALENDAR) or {}).get("checked_at"), "jobs": recent,
            "build": {"at": built.get("built_at"), "count": len(built_keys),
                      "stale": sorted((ready - built_keys) | {m["key"] for m in meetings if m["stale"]}),
                      "removed": sorted(built_keys - ready)},
            "deploy": {"at": deployed.get("deployed_at"), "current": bool(fingerprint and deployed.get("fingerprint") == fingerprint)}}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, body, ctype="application/json"):
        if not isinstance(body, bytes):
            body = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def local_only(self):
        # Stops other websites in the browser from driving this panel.
        allowed = {f"127.0.0.1:{PORT}", f"localhost:{PORT}"}
        if self.headers.get("Host") not in allowed:
            return False
        origin = self.headers.get("Origin")
        return not origin or urllib.parse.urlparse(origin).netloc in allowed

    def do_GET(self):
        if not self.local_only():
            return self.send(403, {"error": "forbidden"})
        url = urllib.parse.urlparse(self.path)
        path = url.path
        if path == "/":
            return self.send(200, (p.ROOT / "admin.html").read_bytes(), "text/html; charset=utf-8")
        if path == "/api/state":
            return self.send(200, state())
        found = re.fullmatch(r"/api/jobs/(\d+)/log", path)
        if found:
            log = JOBS_DIR / f"{int(found.group(1))}.log"
            return self.send(200, log.read_bytes() if log.exists() else b"", "text/plain; charset=utf-8")
        if path == "/site" or path.startswith("/site/"):
            rel = posixpath.normpath(urllib.parse.unquote(path[len("/site"):]).lstrip("/")) if path != "/site" else "."
            target = (p.SITE / rel).resolve()
            if target.is_dir():
                target = target / "index.html"
            if p.SITE.resolve() in target.parents and target.is_file():
                return self.send(200, target.read_bytes(), "text/html; charset=utf-8")
        self.send(404, {"error": "not found"})

    def do_POST(self):
        if not self.local_only() or self.headers.get("Content-Type") != "application/json":
            return self.send(403, {"error": "forbidden"})
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            found = re.fullmatch(r"/api/jobs/(\d+)/cancel", self.path)
            if found:
                return self.send(200, cancel(int(found.group(1))))
            if self.path == "/api/jobs":
                return self.send(200, add_job(body))
            self.send(404, {"error": "not found"})
        except ValueError as e:
            self.send(400, {"error": str(e)})


def cancel(job_id):
    with lock:
        job = next((j for j in jobs if j["id"] == job_id), None)
        if not job:
            raise ValueError("No such job")
        if job["status"] == "queued":
            job.update(status="cancelled", finished=now())
        elif job["status"] == "running" and current and current[0] is job:
            job["status"] = "cancelling"
            os.killpg(current[1].pid, signal.SIGTERM)
        save_jobs()
        return job


def main():
    global jobs
    jobs = p.read_json(JOBS_FILE) or []
    for j in jobs:  # anything mid-flight when the panel last stopped is gone
        if j["status"] in ("queued", "running", "cancelling"):
            j.update(status="interrupted", finished=now())
    threading.Thread(target=worker, daemon=True).start()
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://127.0.0.1:{PORT}/"
    print(f"Admin panel: {url}  (Ctrl-C to stop)", flush=True)
    if "--no-open" not in sys.argv:
        threading.Timer(0.4, webbrowser.open, [url]).start()
    server.serve_forever()


if __name__ == "__main__":
    main()
