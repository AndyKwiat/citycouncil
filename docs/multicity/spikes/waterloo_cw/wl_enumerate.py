"""Enumerate City of Waterloo GovStack meetings via the /meetings/Index search POST.
Recipe: GET /meetings (session cookie + __RequestVerificationToken), then POST form fields
StartDate/EndDate (MM/DD/YYYY), Calendar ('' | 'Council Calendar' | 'Committee Calendar'), Keywords, Page (0-based).
"""
import json, re, sys, os
import polite
from bs4 import BeautifulSoup

BASE = "https://events.waterloo.ca"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dl", "wl_meetings.json")


def token():
    h = polite.get(BASE + "/meetings", cache=False)
    return re.findall(r'name="__RequestVerificationToken" type="hidden" value="([^"]+)"', h)[0]


def search(tok, start, end, cal="", page=0):
    d = {"__RequestVerificationToken": tok, "StartDate": start, "EndDate": end, "Calendar": cal,
         "Keywords": "", "Page": str(page)}
    r = polite.post(BASE + "/meetings/Index", d, cache=False, headers={"Referer": BASE + "/meetings"})
    s = BeautifulSoup(r, "html.parser")
    rn = s.select_one(".resultsNumber")
    total = int(re.search(r"(\d+)", rn.get_text()).group(1)) if rn else None
    heads = {th.get("id"): th.get_text(strip=True) for th in s.select("thead th")}
    rows = []
    for tr in s.select("tbody tr"):
        tds = tr.select("td")
        if not tds:
            continue
        a = tr.select_one("td[headers=c2] a")
        docs = {}
        for td in tds[2:]:
            for da in td.select("a[href]"):
                docs[heads.get(" ".join(td.get("headers") or []), " ".join(td.get("headers") or []))] = da["href"]
        rows.append({"when": tds[0].get_text(" ", strip=True), "name": a.get_text(" ", strip=True) if a else None,
                     "href": a["href"] if a else None, "docs": docs, "calendar": cal})
    pages = sorted({int(x) for x in re.findall(r'data-page="?(\d+)', r)} | {int(x) for x in re.findall(r"totalPages[\"']?\s*[:=]\s*(\d+)", r)})
    return total, rows, pages, r


if __name__ == "__main__":
    tok = token()
    allrows = []
    for cal in ["Council Calendar", "Committee Calendar"]:
        for y in range(2022, 2027):
            page = 0
            while True:
                total, rows, _, _ = search(tok, f"01/01/{y}", f"12/31/{y}", cal, page)
                for r in rows:
                    r["year"] = y
                allrows += rows
                print(cal, y, "page", page, "total", total, "rows", len(rows), file=sys.stderr)
                if not rows or (page + 1) * 25 >= (total or 0):
                    break
                page += 1
    json.dump(allrows, open(OUT, "w"), indent=1)
    print(len(allrows))
