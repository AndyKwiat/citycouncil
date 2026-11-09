import json, re, sys, collections, pathlib
from bs4 import BeautifulSoup
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from scope import body_of
out = []
for c in ["kitchener", "region"]:
    cal = {m["ID"]: m for m in json.load(open(ROOT / f"cache/cal_{c}.json"))}
    for p in sorted((ROOT / f"cache/min/{c}").glob("*.html")):
        mid = p.stem; m = cal[mid]
        raw = p.read_text(encoding="utf8", errors="ignore")
        s = BeautifulSoup(raw, "html.parser")
        text = s.get_text("\n", strip=True)
        cut = text.find("Call to Order"); head = text[:cut if cut > 0 else 2500]
        heads = re.findall(r"^([A-Z][A-Za-z ,/&()-]{2,40}:)$", head, re.M)
        motions = s.select(".AgendaItemMotion")
        rec = split = 0; labels = collections.Counter(); results = collections.Counter(); splits = []
        unrecorded_results = collections.Counter(); voters = collections.Counter()
        for li in motions:
            rows = [r for r in li.select(".MotionVoters tr") if r.select_one(".VoterVote") and r.select_one(".VoterVote").get_text(strip=True)]
            res = " ".join(li.select_one(".MotionResult").get_text(" ", strip=True).split()) if li.select_one(".MotionResult") else ""
            if not rows:
                unrecorded_results[re.sub(r"\d+", "n", res)[:60]] += 1
                continue
            rec += 1
            against = 0
            for r in rows:
                lab = r.select_one(".VoterVote")
                lab = " ".join(lab.get_text(" ", strip=True).split()) if lab else ""
                if not lab: continue
                users = r.select_one(".VotesUsers")
                for nm in re.split(r",|\band\b", users.get_text(" ", strip=True) if users else ""):
                    if nm.strip(): voters[" ".join(nm.split())] += 1
                w = re.sub(r"\s*\(\d+\)", "", lab)
                labels[w] += 1
                n = re.search(r"\((\d+)\)", lab)
                if w.lower() in ("contra", "opposed", "against", "voted in opposition", "nay", "no"):
                    against += int(n.group(1)) if n else len([x for x in re.split(r",|\band\b", r.get_text()) if x.strip()])
            results[re.sub(r"\d+", "n", res)[:60]] += 1
            if against > 0: split += 1
        out.append(dict(council=c, id=mid, name=m["MeetingName"], body=body_of(c, m["MeetingName"]), date=m["StartDate"][:10],
                        motions=len(motions), recorded=rec, split=split, labels=dict(labels), heads=heads,
                        bookmarks=bool(re.search(r"Bookmarks\s*:\s*\[\s*\{", raw)), results=dict(results),
                        unrec=dict(unrecorded_results), has_video=m.get("HasVideo"), voters=dict(voters), head=" ".join(head.split())[:1500]))
(ROOT / "analysis.json").write_text(json.dumps(out, indent=1))
print(len(out))
