"""YouTube, for councils that stream there (Waterloo, Centre Wellington): find a meeting's videos by the date in their
titles, and fetch YouTube's automatic captions.

Politeness: one channel listing a day, and one caption track per video (asking for a second track got HTTP 429 in
Phase 0), with yt-dlp's own sleep between subtitle requests.
"""
import datetime as dt, json, re, subprocess, sys, time
from core.common import log, read_json, write_json

MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def yt_dlp():
    return [sys.executable, "-m", "yt_dlp", "--quiet", "--no-warnings"]


def listing(city, max_age_hours=20):
    """Every stream on the council's channel: [{id, title, duration}], cached in data/<slug>/youtube.json."""
    cfg = city.cfg["youtube"]
    path = city.data / "youtube.json"
    cached = read_json(path)
    if cached and time.time() - cached.get("fetched", 0) < max_age_hours * 3600:
        return cached["videos"]
    videos = []
    for tab in cfg.get("tabs", ["streams"]):
        r = subprocess.run(yt_dlp() + ["--flat-playlist", "-J", f"https://www.youtube.com/channel/{cfg['channel']}/{tab}"],
                           capture_output=True, text=True, timeout=600)
        if r.returncode:
            raise RuntimeError(f"YouTube listing failed: {r.stderr[:300]}")
        videos += [{"id": e["id"], "title": e.get("title") or "", "duration": e.get("duration")}
                   for e in json.loads(r.stdout).get("entries", []) if e.get("id")]
    seen, unique = set(), []
    for v in videos:
        if v["id"] not in seen:
            seen.add(v["id"])
            unique.append(v)
    write_json(path, {"fetched": time.time(), "videos": unique})
    log(f"  YouTube: {len(unique)} videos listed for {city.slug}")
    return unique


def title_date(title):
    """The meeting date written in a title: "September 8, 2025" or "24 Aug 2026"."""
    t = title.lower()
    m = re.search(r"\b([a-z]{3})[a-z]*\.?\s+(\d{1,2}),?\s+(\d{4})", t)
    if m and m.group(1) in MONTHS:
        return dt.date(int(m.group(3)), MONTHS[m.group(1)], int(m.group(2)))
    m = re.search(r"\b(\d{1,2})\s+([a-z]{3})[a-z]*\.?\s+(\d{4})", t)
    if m and m.group(2) in MONTHS:
        return dt.date(int(m.group(3)), MONTHS[m.group(2)], int(m.group(1)))
    return None


def order_key(title):
    """Parts in order: "(Part 2)" after "(Part 1)", and a 6:30 PM stream after the 3:00 PM one."""
    part = re.search(r"part\s*(\d+)|pt\.?\s*(\d+)", title, re.I)
    clock = re.search(r"@\s*(\d{1,2}):(\d{2})\s*([ap])m", title, re.I)
    minutes = (int(clock.group(1)) % 12 + (12 if clock.group(3).lower() == "p" else 0)) * 60 + int(clock.group(2)) if clock else 0
    return (int(next(g for g in part.groups() if g)) if part else 0, minutes, title)


def find(city, date, meeting_type):
    """Videos whose title has this date and the words city.json lists for the meeting type, in part order."""
    rule = city.cfg["youtube"]["types"].get(meeting_type, {})
    words, never = [w.lower() for w in rule.get("words", [])], [w.lower() for w in rule.get("not", [])]
    hits = [v for v in listing(city) if title_date(v["title"]) == date and all(w in v["title"].lower() for w in words)
            and not any(w in v["title"].lower() for w in never)]
    return sorted(hits, key=lambda v: order_key(v["title"]))


def part(video):
    return {"url": f"https://www.youtube.com/watch?v={video['id']}", "youtube_id": video["id"], "title": video["title"],
            "duration": video.get("duration")}


def captions(video_id, out_dir):
    """Download YouTube's automatic captions (json3) for one video; returns the file, or None if there are none."""
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"{video_id}.en-orig.json3"
    if target.exists():
        return target
    r = subprocess.run(yt_dlp() + ["--skip-download", "--write-auto-subs", "--sub-langs", "en-orig", "--sub-format", "json3",
                                   "--sleep-subtitles", "5", "-o", str(out_dir / "%(id)s.%(ext)s"),
                                   f"https://www.youtube.com/watch?v={video_id}"], capture_output=True, text=True, timeout=600)
    if r.returncode and "429" in r.stderr:
        raise RuntimeError("YouTube rate limit (HTTP 429) on captions; try again later")
    return target if target.exists() else None


def parse_json3(path, offset=0.0):
    """Caption events as transcript segments, shifted by `offset` seconds (for the second part of a meeting)."""
    data = json.loads(path.read_text())
    segs = []
    for ev in data.get("events", []):
        text = "".join(s.get("utf8", "") for s in ev.get("segs") or []).replace("\n", " ").replace(">>", " ").strip()
        if not text or "tStartMs" not in ev:
            continue
        start = ev["tStartMs"] / 1000 + offset
        segs.append({"start": round(start, 1), "end": round(start + ev.get("dDurationMs", 0) / 1000, 1),
                     "text": " ".join(text.split()), "source": "youtube-auto"})
    return segs
