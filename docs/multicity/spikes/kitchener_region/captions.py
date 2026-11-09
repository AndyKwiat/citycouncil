import json, re, html, urllib.parse
from common import *
CLIENT = {"kitchener": "kitchener", "region": "waterloo"}
SAMPLE = {
 "region": [("Council Meeting", y) for y in ["2022/11", "2022/12", "2023/03", "2023/10", "2024/04", "2024/11", "2025/05", "2025/10", "2026/09"]] +
           [("Administration and Finance", "2023/0"), ("Planning and Works", "2023/1"), ("Community and Health Services", "2024/0"),
            ("Sustainability, Infrastructure, and Development", "2025/0"), ("Strategic Planning and Budget Committee", "2025/0"),
            ("Community and Health Services", "2026/0"), ("Planning and Works", "2022/0")],
 "kitchener": [("Council Meeting", y) for y in ["2022/12", "2023/03", "2023/10", "2024/04", "2024/11", "2025/06"]] +
              [("Finance and Corporate Services Committee", "2023/0"), ("Planning and Strategic Initiatives Committee", "2024/0"),
               ("Community and Infrastructure Services Committee", "2023/1"), ("Special Council Meeting", "2024/0")],
}
rows = []
for c, picks in SAMPLE.items():
    cal = sorted(json.load(open(CACHE / f"cal_{c}.json")), key=lambda m: m["StartDate"])
    for name, pfx in picks:
        m = next((m for m in cal if m["MeetingName"] == name and m["StartDate"].startswith(pfx) and m.get("HasVideo")), None)
        if not m: rows.append((c, name, pfx, "no meeting with video")); continue
        p = fetch(BASES[c] + f"/Players/ISIStandAlonePlayer.aspx?Id={m['ID']}", cache_name=f"player/{c}/{m['ID']}.html").decode("utf8", "ignore")
        f = re.search(r'data-file_name="([^"]+)"', p); cl = re.search(r'data-client_id="([^"]+)"', p)
        if not f: rows.append((c, name, m["StartDate"], "player has no file")); continue
        fn = html.unescape(f.group(1))
        st, b = fetch(f"https://video.isilive.ca/{CLIENT[c]}/{urllib.parse.quote(fn)}.vtt", cache_name=f"vtt/{c}/{m['ID']}.vtt", allow_status=True)
        mp = CACHE / f"min/{c}/{m['ID']}.html"
        bm = None
        if mp.exists():
            raw = mp.read_text(errors="ignore"); bm = len(re.findall(r'"AgendaItemId"', raw))
        rows.append((c, name, m["StartDate"][:10], cl.group(1) if cl else None, fn, st, len(b), "bookmarks=%s" % bm))
for r in rows: print(r)
(ROOT / "captions.json").write_text(json.dumps(rows, indent=1))
