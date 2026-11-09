#!/usr/bin/env python3
"""Every data step for the council sites: meeting list, documents, minutes parsing, transcription (captions
first, Whisper fallback), summaries and deploy. Each council's settings live in cities/<slug>/city.json and its
data in data/<slug>/; the source adapters are in sources/, the shared steps in core/.

The admin panel runs this file as a subprocess, but it also works by hand:
  pipeline.py calendar --from 2025-01-01
  pipeline.py process --latest 5
  pipeline.py process --city guelph --dates 2026-09-15 --steps summarize --force
  pipeline.py build            (every council plus the landing page)
"""
import argparse, datetime as dt, hashlib, os, pathlib, re, shutil, signal, subprocess, sys

from core.common import ROOT, STATE, SITE, UA, file_hash, get, log, read_json, write_json  # noqa: F401 (re-exported)
from core import city as cities
from core.summarize import SUMMARY_MODEL, check_summary, closed_only, formatted_start, transcript_text  # noqa: F401
from core.transcribe import GAP_SECONDS, clean_segments, find_gaps, parse_vtt  # noqa: F401
from core.votes import export_votes, meeting_dirs  # noqa: F401
from core import summarize as summarize_step, transcribe as transcribe_step
from sources import escribe
from sources.escribe import audit_votes, parse_result, split_names, surname, vote_side  # noqa: F401

APP = "citycouncil"
RADIFY = pathlib.Path.home() / "radify/bin/radify"
OWNER = "you@example.com"
STEPS = ["docs", "parse", "transcribe", "summarize"]
ADAPTERS = {"escribe": escribe}


def adapter(city):
    return ADAPTERS[city.adapter]


def load(slug=None):
    return cities.load(slug or cities.DEFAULT)


# ---------------------------------------------------------------- meeting list

def refresh_calendar(city, start=None, end=None):
    adapter(city).refresh_calendar(city, start, end)


def key_of(m):
    return m["key"]


def council_meetings(city=None):
    """In-scope meetings in the cached meeting list, newest first (normalized, meeting.json v2)."""
    city = city or load()
    return adapter(city).list_meetings(city)


def is_past(m):
    return dt.datetime.fromisoformat(m["start"]) < dt.datetime.now()


# ---------------------------------------------------------------- steps

def step_docs(city, m, force=False):
    adapter(city).fetch_documents(city, m, force)


def step_parse(city, m, force=False):
    return adapter(city).parse_minutes(city, city.raw / m["key"]) is not None


def step_transcribe(city, m, force=False, whisper=False):
    return transcribe_step.transcribe(city, m, force, whisper)


def step_summarize(city, m, force=False):
    return summarize_step.summarize(city, m, force)


# ---------------------------------------------------------------- status (read by the admin panel)

def site_fingerprint(root=None):
    root = root or SITE
    if not (root / "index.html").exists():
        return None
    h = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_file():
            h.update(str(path.relative_to(root)).encode())
            h.update(path.read_bytes())
    return h.hexdigest()


def content_stamp(d):
    """Changes whenever anything the site shows for a meeting changes."""
    files = [d / n for n in ("summary.json", "minutes.json", "transcript.json")]
    return max((f.stat().st_mtime for f in files if f.exists()), default=0)


def built_meetings(built, city):
    return ((built or {}).get("cities", {}).get(city.slug) or {}).get("meetings", {})


def meeting_status(m, built=None, city=None):
    city = city or load(m.get("city"))
    key = m["key"]
    d = city.raw / key
    meta = read_json(d / "transcript_meta.json")
    summary = read_json(d / "summary.json")
    minutes = read_json(d / "minutes.json")
    has_minutes = (d / "minutes.html").exists()
    on = built_meetings(built, city)
    on_site = key in on
    stale = on_site and on[key] != content_stamp(d)
    when = formatted_start(m) + ("" if m["type"] == city.get("main_type") else f" · {m['body_name']}")
    return {
        "key": key, "id": m["id"], "when": when, "body": m["body"], "body_name": m["body_name"], "past": is_past(m),
        "minutes_posted": m["minutes_posted"], "video_listed": bool(m.get("video")),
        "downloaded": has_minutes or (d / "agenda.html").exists(),
        "has_minutes": has_minutes, "has_captions": (d / "captions.vtt").exists(),
        "parsed": bool(minutes), "closed_only": bool(minutes and closed_only(minutes)),
        "motions": len(minutes["motions"]) if minutes else 0,
        "votes": sum(1 for x in minutes["motions"] if x["result"]["for"] is not None and (not x["inherited"] or x.get("consent_source"))) if minutes else 0,
        "vote_problems": minutes.get("vote_problems", []) if minutes else [],
        "transcript": {"method": meta["method"], "words": meta["words"], "wpm": meta["caption_wpm"],
                       "gaps": len(meta["gaps"]), "gaps_filled": sum(1 for g in meta["gaps"] if g["filled"])} if meta else None,
        "summary": {"title": summary["title"], "model": summary.get("model")} if summary else None,
        "on_site": on_site, "stale": stale,
        "complete": bool(minutes and summary and (meta or not m.get("video"))),
    }


# ---------------------------------------------------------------- orchestration

def process(city, meetings, steps, force=False, whisper=False):
    failed = []
    for n, m in enumerate(meetings, 1):
        log(f"\n[{n}/{len(meetings)}] {city.slug} {m['key']}  {formatted_start(m)}")
        try:
            if "docs" in steps:
                step_docs(city, m, force)
            if "parse" in steps:
                step_parse(city, m, force)
            if "transcribe" in steps:
                step_transcribe(city, m, force, whisper)
            if "summarize" in steps:
                step_summarize(city, m, force)
        except Exception as e:
            log(f"  FAILED: {e}")
            failed.append(m["key"])
    if "parse" in steps:
        export_votes(city)
    log(f"\nDone: {len(meetings) - len(failed)} of {len(meetings)} meetings OK." + (f" Failed: {', '.join(failed)}" if failed else ""))
    if failed:
        sys.exit(1)


def select(args, city=None):
    city = city or load(getattr(args, "city", None))
    ms = council_meetings(city)
    bodies = set((getattr(args, "bodies", None) or "").split(",")) - {""}
    if bodies:
        ms = [m for m in ms if m["body"] in bodies]
    past = [m for m in ms if is_past(m)]
    raw = city.raw
    if args.dates:
        wanted = set(args.dates.split(","))
        return [m for m in ms if m["key"] in wanted]
    if args.latest:
        def closed(m):
            minutes = read_json(raw / m["key"] / "minutes.json")
            return bool(minutes and closed_only(minutes))
        missing = [m for m in past if not (raw / m["key"] / "summary.json").exists() and m["minutes_posted"] and not closed(m)]
        return missing[:args.latest]
    if args.new:
        newest = max((m["start"] for m in past if (raw / m["key"] / "summary.json").exists()), default="")
        return [m for m in past if m["start"] > newest or
                ((raw / m["key"]).exists() and not (raw / m["key"] / "summary.json").exists())]
    if getattr(args, "from_") or args.to:
        lo, hi = getattr(args, "from_") or "0000", args.to or "9999"
        return [m for m in past if lo <= m["start"][:10] <= hi]
    return []


# ---------------------------------------------------------------- deploy

SITE_DOMAIN = "cityhallvotes.ca"
SITE_PATH = ""   # every council lives under cityhallvotes.ca/<slug>/; the root is the landing page
CF = ROOT / "cf"
CF_DIST = STATE / "cf" / "dist"
SECRETS = pathlib.Path.home() / ".config/akwiat/secrets.env"


def cloudflare_env():
    """wrangler needs the API token (kept with radify's secrets) and the account that owns the domain."""
    import json, urllib.request
    env = dict(os.environ)
    found = dict(line.split("=", 1) for line in SECRETS.read_text().splitlines() if "=" in line and not line.startswith("#"))
    # A separate token with Workers permissions; radify's own token only manages DNS.
    token = (found.get("CLOUDFLARE_WORKERS_TOKEN") or "").strip().strip('"')
    if not token:
        raise SystemExit(f"Add CLOUDFLARE_WORKERS_TOKEN to {SECRETS} (see README: Hosting on Cloudflare)")
    env["CLOUDFLARE_API_TOKEN"] = token
    req = urllib.request.Request(f"https://api.cloudflare.com/client/v4/zones?name={SITE_DOMAIN}",
                                 headers={"Authorization": f"Bearer {env['CLOUDFLARE_API_TOKEN']}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        zones = json.load(r)["result"]
    if not zones:
        raise SystemExit(f"The Cloudflare token can't see {SITE_DOMAIN}")
    env["CLOUDFLARE_ACCOUNT_ID"] = zones[0]["account"]["id"]
    return env


def wrangler(args, env, **kw):
    return subprocess.run(["npx", "--yes", "wrangler@4", *args, "--config", str(CF / "wrangler.jsonc")], env=env, **kw)


def deploy():
    """Publish every built council and the landing page to Cloudflare at https://cityhallvotes.ca/ (public)."""
    if not (SITE / "index.html").exists():
        raise SystemExit("Nothing to deploy: build the website first.")
    shutil.rmtree(CF_DIST, ignore_errors=True)
    shutil.copytree(SITE, CF_DIST)  # site/ already holds /index.html, /search.html, /_redirects and /<slug>/
    (CF_DIST / "robots.txt").write_text("User-agent: *\nAllow: /\n")
    log(f"Deploying {SITE} to https://{SITE_DOMAIN}/")
    wrangler(["deploy"], cloudflare_env(), check=True)
    write_json(STATE / "deploy.json", {"deployed_at": dt.datetime.now().isoformat(timespec="seconds"), "fingerprint": site_fingerprint()})
    log(f"Deployed: https://{SITE_DOMAIN}/ (public)")


SEARCH_APP = "api-citycouncil"
SEARCH_MEMORY = "900M"  # the embedding model alone needs about 450 MB, over radify's 512 MB default


def deploy_search():
    """Build the Linux search server and ship it, with the current index, to api-citycouncil.akwiat.com."""
    import search_index
    if not search_index.DB.exists():
        raise SystemExit("No search index yet: update the search index first.")
    log("Building the search server for Linux...")
    subprocess.run(["cargo", "build", "--release", "--target", "x86_64-unknown-linux-musl"], cwd=search_index.SEARCH, check=True)
    dist = search_index.OUT / "dist"
    shutil.rmtree(dist, ignore_errors=True)
    (dist / "bin").mkdir(parents=True)
    (dist / "static").mkdir()
    shutil.copy(search_index.SEARCH / "target/x86_64-unknown-linux-musl/release/app", dist / "bin/app")
    shutil.copy(search_index.DB, dist / "static/search.sqlite")
    apps = subprocess.run([str(RADIFY), "apps"], capture_output=True, text=True, check=True).stdout
    if not re.search(rf"^{SEARCH_APP}\s", apps, re.M):
        log(f"Creating app {SEARCH_APP}; it answers only requests carrying the site's key")
        subprocess.run([str(RADIFY), "create", SEARCH_APP, "--policy", "public"], check=True)
    limit = subprocess.run(["ssh", "step1-deploy", f"systemctl show app@{SEARCH_APP} -p MemoryMax --value"], capture_output=True, text=True).stdout.strip()
    if limit.isdigit() and int(limit) < 800 * 2 ** 20:
        log(f"WARNING: app@{SEARCH_APP} may run out of memory (limit {int(limit) // 2 ** 20} MB). See README: Search.")
    log(f"Deploying to {SEARCH_APP}.akwiat.com")
    subprocess.run([str(RADIFY), "deploy", SEARCH_APP, str(dist)], check=True)
    write_json(STATE / "search_deploy.json", {"deployed_at": dt.datetime.now().isoformat(timespec="seconds"), "db": file_hash(search_index.DB)})
    log(f"Search API live at https://{SEARCH_APP}.akwiat.com (answers only the site's Worker)")


def search_status():
    import search_index
    info, live = read_json(STATE / "search.json") or {}, read_json(STATE / "search_deploy.json") or {}
    newest = max((content_stamp(d) for slug in cities.all_slugs() for d in meeting_dirs(load(slug))
                  if (d / "summary.json").exists()), default=0)
    built = search_index.DB.stat().st_mtime if search_index.DB.exists() else 0
    return {"indexed_at": info.get("indexed_at"), "chunks": info.get("chunks"), "stale": bool(built and newest > built),
            "deployed_at": live.get("deployed_at"), "current": bool(built and live.get("db") == file_hash(search_index.DB))}


def chosen(slug):
    return [load(s) for s in cities.all_slugs()] if slug == "all" else [load(slug)]


def main():
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))  # so a cancelled job still removes its temp audio
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("calendar")
    c.add_argument("--city", default=cities.DEFAULT)
    c.add_argument("--from", dest="from_")
    c.add_argument("--to")
    w = sub.add_parser("process")
    w.add_argument("--city", default=cities.DEFAULT)
    w.add_argument("--dates", help="meeting keys, comma-separated (YYYY-MM-DD or YYYY-MM-DD-<type>)")
    w.add_argument("--latest", type=int)
    w.add_argument("--new", action="store_true")
    w.add_argument("--from", dest="from_")
    w.add_argument("--to")
    w.add_argument("--bodies", help="council, committee, or both comma-separated (default: both)")
    w.add_argument("--steps", default=",".join(STEPS))
    w.add_argument("--force", action="store_true")
    w.add_argument("--whisper", action="store_true")
    b = sub.add_parser("build")
    b.add_argument("--city", default="all")
    sub.add_parser("deploy")
    sub.add_parser("search-index")
    sub.add_parser("search-deploy")
    sub.add_parser("export-votes").add_argument("--city", default=cities.DEFAULT)
    a = p.parse_args()
    if a.cmd == "calendar":
        for city in chosen(a.city):
            refresh_calendar(city, a.from_, a.to)
    elif a.cmd == "process":
        for city in chosen(a.city):
            if a.new or a.latest or a.from_ or a.to:
                refresh_calendar(city)
            meetings = select(a, city)
            if not meetings:
                log(f"{city.slug}: no meetings to process.")
                continue
            process(city, meetings, a.steps.split(","), a.force, a.whisper)
    elif a.cmd == "build":
        import build
        build.main(None if a.city == "all" else [a.city])
    elif a.cmd == "deploy":
        deploy()
    elif a.cmd == "search-index":
        import search_index
        search_index.index()
    elif a.cmd == "search-deploy":
        deploy_search()
    elif a.cmd == "export-votes":
        for city in chosen(a.city):
            export_votes(city)


if __name__ == "__main__":
    main()
