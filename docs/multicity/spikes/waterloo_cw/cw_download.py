import re, os, sys, datetime, polite
W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
n = 0
for line in open(f"{W}/dl/cw_folders.txt"):
    m = re.match(r"/document/(\d+) \| (.+?) ?- (\d{2} [A-Z][a-z]{2} \d{4}) - Minutes - Pdf", line)
    if not m: continue
    did, name, d = m.groups()
    iso = datetime.datetime.strptime(d, "%d %b %Y").date().isoformat()
    if iso < "2022-11-15": continue
    slug = f"{iso}_{re.sub(r'[^A-Za-z0-9]+','-',name.strip()).strip('-')}_{did}"
    p = f"{W}/dl/cw_pdf/{slug}.pdf"
    if os.path.exists(p): continue
    b = polite.get(f"https://centrewellington.civicweb.net/document/{did}", binary=True, cache=False)
    assert b[:4] == b"%PDF", slug
    open(p, "wb").write(b); n += 1
print("downloaded", n)
