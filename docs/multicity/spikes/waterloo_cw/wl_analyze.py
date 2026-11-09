"""Count motions / tallies / named votes in City of Waterloo council minutes text."""
import os, re, sys, collections, json

D = sys.argv[1]
HDR = re.compile(r"^[A-Z][a-z]+ \d{1,2}, \d{4} Page \d+ .*$")
OUT = re.compile(r"^(Carried Unanimously|Carried|Motion Failed|Motion Defeated|Motion failed|Motion defeated|Defeated|Lost|Tied)\s*\.?$")
TAL = re.compile(r"^(\d+) Vot(?:ed|ing) in (Favou?r|Opposition)\s*$")
NAME = re.compile(r"^\((MAYOR|COUNCILLOR|Mayor|Councillor) ([^)]+)\)\s*$")

per_year = collections.defaultdict(collections.Counter)
examples = collections.defaultdict(list)
splits = []
for f in sorted(os.listdir(D)):
    y = f[:4]
    if f[:10] >= "2026-11-15":
        continue
    term = "2022-26"
    lines = [l.strip() for l in open(os.path.join(D, f)).read().split("\n")]
    lines = [l for l in lines if l and l != "\f" and not HDR.match(l)]
    c = per_year[y]
    c["meetings"] += 1
    for i, l in enumerate(lines):
        if l.startswith("Moved by"):
            c["moved_by"] += 1
        if "requested a recorded vote" in l:
            c["recorded_requested"] += 1
        if re.search(r"\b(left|joined) the meeting", l):
            c["left_joined"] += 1
        if "abstain" in l.lower():
            c["abstain_mentions"] += 1
        m = OUT.match(l)
        if not m:
            continue
        outcome = m.group(1).lower()
        c["outcomes"] += 1
        c["out:" + outcome] += 1
        tally = {}; names = {"Favour": [], "Opposition": []}; cur = None
        j = i + 1
        while j < len(lines):
            t = TAL.match(lines[j]); n = NAME.match(lines[j])
            if t:
                cur = t.group(2).replace("Favor","Favour"); tally[cur] = int(t.group(1))
            elif n and cur:
                names[cur].append(n.group(2).title())
            else:
                break
            j += 1
        rec = any("requested a recorded vote" in lines[k] for k in range(max(0, i - 3), i))
        if tally:
            c["with_tally"] += 1
            opp = tally.get("Opposition", 0)
            if opp:
                c["split_tally"] += 1
                named_fav = bool(names["Favour"])
                c["split_named_both" if named_fav else "split_named_opp_only"] += 1
                if len(names["Opposition"]) != opp:
                    c["opp_name_count_mismatch"] += 1
                    examples["mismatch"].append((f, i, tally, names))
                splits.append({"file": f, "outcome": outcome, "tally": tally, "names": names, "recorded": rec})
            else:
                c["unanimous_with_tally"] += 1
        else:
            if outcome == "carried":
                c["plain_carried_no_tally"] += 1
                examples["plain_carried"].append((f, lines[max(0, i - 2):i + 3]))
            if outcome.startswith("motion"):
                c["failed_no_tally"] += 1
                examples["failed_no_tally"].append((f, lines[max(0, i - 2):i + 3]))
        if outcome == "carried unanimously" and opp_free(tally) if False else False:
            pass

keys = ["meetings", "moved_by", "outcomes", "out:carried unanimously", "out:carried", "out:motion failed",
        "out:motion defeated", "with_tally", "split_tally", "split_named_opp_only", "split_named_both",
        "unanimous_with_tally", "recorded_requested", "plain_carried_no_tally", "failed_no_tally",
        "opp_name_count_mismatch", "left_joined", "abstain_mentions"]
tot = collections.Counter()
print("year | " + " | ".join(keys))
for y in sorted(per_year):
    tot.update(per_year[y])
    print(y, "|", " | ".join(str(per_year[y][k]) for k in keys))
print("total |", " | ".join(str(tot[k]) for k in keys))
for k, v in examples.items():
    print("\n##", k, len(v))
    for e in v[:8]:
        print(e)
json.dump(splits, open(os.path.join(os.path.dirname(D.rstrip("/")), "wl_splits.json"), "w"), indent=1)
# per-person dissent count
dis = collections.Counter(n for s in splits for n in s["names"]["Opposition"])
print("\nnamed in opposition:", dis.most_common())
