import json, os, sys, datetime
import polite
W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = json.load(open(f"{W}/dl/wl_meetings.json"))
n = 0
for r in R:
    if not r["calendar"].startswith("Council") or "Minutes" not in r["docs"]:
        continue
    slug = r["href"].rsplit("/", 1)[1]
    if slug[:10] < "2022-11-15":
        continue
    p = f"{W}/dl/wl_pdf/{slug}.pdf"
    if os.path.exists(p):
        continue
    b = polite.get("https://events.waterloo.ca" + r["docs"]["Minutes"], binary=True, cache=False)
    open(p, "wb").write(b); n += 1
    print(slug, len(b), file=sys.stderr)
print("downloaded", n)
