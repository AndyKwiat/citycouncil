#!/usr/bin/env python3
"""Cuts summaries, votes, minutes and transcripts into searchable chunks, then has the Rust indexer embed them.

Every council goes into one index. Chunks carry their council (`city`), meeting date and body, and link to pages with
URLs relative to the council's folder (site/<city>/), so the search pages can link from anywhere on the site.
"""
import datetime as dt, html, json, re, subprocess
import build
import pipeline as p
from core import city as cities

SEARCH = p.ROOT / "search"
OUT = p.STATE / "search"
CHUNKS = OUT / "chunks.jsonl"
DB = OUT / "search.sqlite"
MODEL = SEARCH / "model"
NATIVE = SEARCH / "target" / "release" / "app"
TRANSCRIPT_WORDS = 170
KIND_NAMES = {"summary": "Meeting summary", "vote": "Council vote", "minutes": "Minutes", "transcript": "Meeting transcript"}


def strip(text):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", text or "")).split())


def chunk(m, kind, title, text, url, label="", context="", embed_text=None):
    """m: the meeting, with its council: {city, key, date, body, who}, where who is e.g. "Guelph City Council"."""
    day = dt.date.fromisoformat(m["date"])
    when = f"{day:%B} {day.day}, {day.year}"
    return {"kind": kind, "city": m["city"], "meeting": m["key"], "date": m["date"], "body": m["body"], "title": title,
            "text": text, "url": url, "label": label,
            "embed": f"{KIND_NAMES[kind]}, {m['who']}, {when}. {context}{title}. {embed_text or text}"}


def meeting_info(city, m):
    """What a chunk needs to know about its meeting. Guelph's council meetings keep their old embedded prefix, so
    their vectors are reused."""
    return {"city": city.slug, "key": m["key"], "date": m["start"][:10], "body": m.get("body", "council"), "who": build.body_title(city, m)}


def vote_text(text, motions):
    """Summaries carry {{vote:m3}} tokens; spell them out for search."""
    def sub(found):
        x = motions.get(found.group(1))
        return f"({x['result']['label']})" if x and x["result"]["label"] else ""
    return re.sub(r"\s*\{\{vote:(m\d+)\}\}", lambda m: " " + sub(m) if sub(m) else "", text)


def meeting_chunks(m, summary, minutes, transcript):
    key = m["key"]
    out = []
    motions = {x["id"]: x for x in minutes["motions"]} if minutes else {}
    if summary:
        overview = " ".join(vote_text(t, motions) for t in summary["overview"])
        out.append(chunk(m, "summary", summary["title"], f"{summary['subtitle']} {overview}", f"index.html#m-{key}"))
        for d in summary["decisions"]:
            x = motions.get(d["motion"])
            label = x["result"]["label"] if x else ""
            out.append(chunk(m, "summary", d["item"], vote_text(d["detail"], motions), f"index.html#m-{key}", label, "Key decision: "))
        if summary.get("debate"):
            out.append(chunk(m, "summary", "What the debate was about", " ".join(vote_text(b, motions) for b in summary["debate"]),
                             f"index.html#m-{key}"))
    if minutes:
        for x in minutes["motions"]:
            if not (x["text"] or x["result"]["label"]):
                continue
            v = x["votes"]
            result = f"Result: {x['result']['text'] or x['result']['label']}." if x["result"]["text"] or x["result"]["label"] else ""
            parts = [x["text"], result]
            if v["for"]:
                parts.append(f"For: {', '.join(v['for'])}.")
            if v["against"]:
                parts.append(f"Against: {', '.join(v['against'])}.")
            if x["moved_by"]:
                parts.append(f"Moved by {x['moved_by']}" + (f", seconded by {x['seconded_by']}." if x["seconded_by"] else "."))
            title = x["item_title"] + (f": {x['name']}" if x["name"] and x["name"].lower() not in x["item_title"].lower() else "")
            # Long motions are split so nothing falls past the model's limit; names stay out of the embedding,
            # where they'd only add noise, but keyword search still finds them.
            for piece in split_words(x["text"], 280):
                out.append(chunk(m, "vote", title, " ".join(filter(None, [piece] + parts[1:])), f"minutes/{key}.html#{x['id']}",
                                 x["result"]["label"] or "", embed_text=" ".join(filter(None, [piece, result]))))
        for item in minutes["items"]:
            notes = strip(" ".join(item["notes"]))
            if len(notes.split()) < 15:
                continue
            anchor = f"#i-{item['id']}" if item["id"] else ""
            for n, piece in enumerate(split_words(notes, 250)):
                out.append(chunk(m, "minutes", f"{item['number']} {item['title']}".strip(), piece, f"minutes/{key}.html{anchor}"))
    if transcript:
        spans = sorted((i["video_start"], i["video_end"] or i["video_start"], i["title"]) for i in (minutes or {}).get("items", [])
                       if i.get("video_start") is not None)
        buffer, start = [], None
        for para in build.paragraphs(transcript):
            if start is None:
                start = int(para["start"])
            buffer.append(" ".join(para["text"]))
            if sum(len(b.split()) for b in buffer) >= TRANSCRIPT_WORDS:
                out.append(transcript_chunk(m, start, " ".join(buffer), spans))
                buffer, start = [], None
        if buffer:
            out.append(transcript_chunk(m, start, " ".join(buffer), spans))
    return out


def transcript_chunk(m, start, text, spans):
    topic = next((t for a, b, t in reversed(spans) if a <= start), "")
    title = f"{topic} ({build.hms(start)})" if topic else f"At {build.hms(start)}"
    return chunk(m, "transcript", title, text, f"transcripts/{m['key']}.html#t-{start}", context="Discussion of ")


def split_words(text, size):
    words = text.split()
    return [" ".join(words[i:i + size]) for i in range(0, len(words), size)] or [text]


def export():
    rows = []
    for slug in cities.all_slugs():
        city = cities.load(slug)
        for d in p.meeting_dirs(city):
            m, summary, minutes = p.read_json(d / "meeting.json"), p.read_json(d / "summary.json"), p.read_json(d / "minutes.json")
            if not (m and summary and minutes):
                continue  # only meetings that are on the website
            rows += meeting_chunks(meeting_info(city, m), summary, minutes, p.read_json(d / "transcript.json"))
    OUT.mkdir(parents=True, exist_ok=True)
    with open(CHUNKS, "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    counts = {k: sum(1 for r in rows if r["kind"] == k) for k in KIND_NAMES}
    p.log(f"Exported {len(rows)} chunks: " + ", ".join(f"{v} {k}" for k, v in counts.items()))
    return rows


def ensure_indexer():
    if not NATIVE.exists():
        p.log("Building the search indexer (first time only)...")
        subprocess.run(["cargo", "build", "--release"], cwd=SEARCH, check=True)
    if not (MODEL / "model.safetensors").exists():
        subprocess.run([str(NATIVE), "fetch-model", str(MODEL)], check=True)


def index():
    export()
    ensure_indexer()
    subprocess.run([str(NATIVE), "index", str(CHUNKS), str(DB), str(MODEL)], check=True)
    p.write_json(p.STATE / "search.json", {"indexed_at": dt.datetime.now().isoformat(timespec="seconds"),
                                           "chunks": sum(1 for _ in open(CHUNKS)), "db": str(DB)})
    p.log(f"Search index ready: {DB}")


if __name__ == "__main__":
    index()
