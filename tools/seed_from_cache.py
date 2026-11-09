#!/usr/bin/env python3
"""One-off: start a council's data from a Phase 0 spike cache (calendar records and minutes pages keyed by meeting id),
so the council's site isn't asked for the same pages twice.

  tools/seed_from_cache.py <slug> <calendar.json> <folder of <id>.html minutes>
"""
import hashlib, json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from core import city as cities
from core.common import read_json, write_json
from sources import escribe

slug, cal, folder = sys.argv[1], pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])
city = cities.load(slug)
recs = json.loads(cal.read_text())
known = {m["ID"]: m for m in (read_json(city.calendar) or {"d": []})["d"]}
known.update({m["ID"]: m for m in recs})
write_json(city.calendar, {"d": list(known.values()), "checked_at": None})
seeded = 0
for m in escribe.list_meetings(city):
    page = folder / f"{m['id']}.html"
    status = folder / f"{m['id']}.html.status"
    if not page.exists() or (status.exists() and status.read_text().strip() != "200") or page.stat().st_size < 2000:
        continue
    d = city.raw / m["key"]
    if (d / "minutes.html").exists():
        continue
    d.mkdir(parents=True, exist_ok=True)
    body = page.read_bytes()
    (d / "minutes.html").write_bytes(body)
    m["source_hashes"]["minutes.html"] = hashlib.sha256(body).hexdigest()
    escribe.save_meeting(city, m)
    seeded += 1
print(f"{slug}: {len(escribe.list_meetings(city))} meetings in scope, {seeded} minutes seeded from the cache")
