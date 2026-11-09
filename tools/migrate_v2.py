#!/usr/bin/env python3
"""One-off (Phase 1): move Guelph's eSCRIBE meeting records to meeting.json v2 and councillors.json to terms.

- data/guelph/raw/<key>/meeting.json (eSCRIBE's record) moves to source/meeting_source.json (git mv, history kept)
- a normalized meeting.json v2 takes its place; video_file.txt is folded into video.parts and removed
- cities/guelph/councillors.json becomes {"_source", "terms": {"2022-2026": {...}, "2026-2030": {}}}
Safe to re-run: meetings already at v2 are skipped.
"""
import hashlib, subprocess, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from core.common import ROOT, read_json, write_json
from core import city as cities
from sources import escribe
from video import isilive


def git(*args):
    subprocess.run(["git", "-C", str(ROOT), *args], check=True)


def migrate_meetings(city):
    expected = {m["id"]: m["key"] for m in escribe.list_meetings(city)}
    for d in sorted(x for x in city.raw.iterdir() if x.is_dir()):
        old = read_json(d / "meeting.json")
        if not old or old.get("version") == 2:
            continue
        key = expected.get(old["ID"])
        if key != d.name:
            raise SystemExit(f"{d.name}: the new key rule gives {key!r}; refusing to move it")
        (d / "source").mkdir(exist_ok=True)
        git("mv", str(d / "meeting.json"), str(d / "source" / "meeting_source.json"))
        m = escribe.normalize(city, old, d.name)
        vf = d / "video_file.txt"
        if m["video"] and vf.exists():
            m["video"]["parts"] = [isilive.part(escribe.base(city), city.cfg["escribe"]["isi_client"], old["ID"], vf.read_text())]
        if (d / "minutes.html").exists():
            m["source_hashes"]["minutes.html"] = hashlib.sha256((d / "minutes.html").read_bytes()).hexdigest()
        write_json(d / "meeting.json", {k: v for k, v in m.items() if k != "_source"})
        if vf.exists():
            git("rm", "-qf", str(vf))
        print("migrated", d.name)


def migrate_councillors(city):
    path = city.dir / "councillors.json"
    old = read_json(path)
    if "terms" in old:
        return
    members = {k: v for k, v in old.items() if not k.startswith("_")}
    write_json(path, {"_source": old.get("_source", ""), "terms": {"2022-2026": members, "2026-2030": {}}})
    print("councillors.json now per term")


if __name__ == "__main__":
    c = cities.load("guelph")
    migrate_meetings(c)
    migrate_councillors(c)
