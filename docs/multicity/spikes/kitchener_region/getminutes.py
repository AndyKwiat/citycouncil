import json, sys, threading
from common import *
from scope import SCOPE, body_of
def run(c):
    ms = json.load(open(CACHE / f"cal_{c}.json"))
    n = 0
    for m in sorted(ms, key=lambda m: m["StartDate"]):
        if not body_of(c, m["MeetingName"]): continue
        if not ("2022/03/01" <= m["StartDate"][:10] <= "2026/11/09"): continue
        if c == "kitchener" and m["StartDate"][:10] < "2022/11/15": continue
        docs = {d["Title"]: d for d in m["MeetingDocumentLink"]}
        if "Minutes (HTML)" not in docs: continue
        try:
            fetch(BASES[c] + docs["Minutes (HTML)"]["Url"], cache_name=f"min/{c}/{m['ID']}.html")
        except Exception as e:
            print(c, m["ID"], "ERR", e, flush=True)
        n += 1
        if n % 25 == 0: print(c, n, flush=True)
    print(c, "done", n, flush=True)
ts = [threading.Thread(target=run, args=(c,)) for c in BASES]
[t.start() for t in ts]; [t.join() for t in ts]
