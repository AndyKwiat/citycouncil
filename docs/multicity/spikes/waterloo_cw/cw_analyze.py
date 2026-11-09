"""Count motions and recorded votes in Centre Wellington minutes text (files named YYYY-MM-DD_Type_docid.txt)."""
import os, re, sys, collections

D = sys.argv[1]
FOOT = re.compile(r"^Page \d+ of \d+$")
HEAD = re.compile(r"^(Council|Committee of the Whole|Special Council|Budget Committee of the Whole|.*) Minutes [A-Z][a-z]+ \d{1,2}, \d{4}$")
OUT = re.compile(r"^(CARRIED|DEFEATED|LOST|TIED|WITHDRAWN|Carried|Defeated)\b(.*)$")
MEM = re.compile(r"^(Mayor|Deputy Mayor|Councillor) ([A-Z][A-Za-z.'\- ]+?)(?: (For|Against|Abstained|Opposed))?$")
REQ = re.compile(r"(requested|asked for|called for) a recorded vote", re.I)

stats = collections.defaultdict(collections.Counter)
blocks = []
for f in sorted(os.listdir(D)):
    date, typ = f.split("_")[0], f.split("_")[1]
    body = "council" if typ.startswith(("Council", "Special")) else "cow"
    if date >= "2026-11-15":
        continue
    raw = [l.strip() for l in open(os.path.join(D, f)).read().split("\n")]
    hf = sum(1 for l in raw if FOOT.match(l) or HEAD.match(l))
    lines = [l for l in raw if l and l != "\f" and not FOOT.match(l) and not HEAD.match(l)]
    k = (date[:4], body)
    c = stats[k]
    c["meetings"] += 1
    c["header_footer_lines"] += hf
    for i, l in enumerate(lines):
        if l.startswith("Moved by") or re.match(r"^\d+(\.\d+)* Moved by", l):
            c["moved_by"] += 1
        m = OUT.match(l)
        if m:
            c["outcomes"] += 1
            c["out:" + m.group(1).upper() + ("" if not m.group(2) else (" as amended" if "amended" in m.group(2) else " other"))] += 1
        if re.search(r"\b(left|joined|rejoin(ed|s)?) the meeting", l):
            c["left_joined"] += 1
        if REQ.search(l) and "omitted" not in l:
            c["recorded_requests"] += 1
            # find member run within next 40 lines
            run = []
            j = i + 1
            while j < min(len(lines), i + 45):
                mm = MEM.match(lines[j])
                if mm:
                    if " the " in lines[j] or " requested" in lines[j] or " asked" in lines[j]:
                        if run: break
                    else:
                        run.append((mm.group(2), mm.group(3)))
                        j += 1
                        continue
                elif run and lines[j] in ("Evoy",):
                    j += 1; continue
                elif run:
                    break
                j += 1
            votes = collections.Counter(v for _, v in run)
            split = votes.get("Against", 0) + votes.get("Opposed", 0) > 0
            blocks.append((f, len(run), dict(votes), split))
            if len(run) >= 3:
                c["recorded_blocks"] += 1
                c["recorded_split"] += split
                if None in votes:
                    c["recorded_with_missing_vote_word"] += 1
            else:
                c["recorded_request_no_block"] += 1

keys = ["meetings", "moved_by", "outcomes", "out:CARRIED", "out:CARRIED as amended", "out:CARRIED other", "out:DEFEATED",
        "out:WITHDRAWN", "recorded_requests", "recorded_blocks", "recorded_split", "recorded_request_no_block",
        "recorded_with_missing_vote_word", "left_joined", "header_footer_lines"]
print("year,body | " + " | ".join(keys))
tot = collections.defaultdict(collections.Counter)
for k in sorted(stats):
    tot[k[1]].update(stats[k])
    print(k, "|", " | ".join(str(stats[k][x]) for x in keys))
for b, c in tot.items():
    print("TOTAL", b, "|", " | ".join(str(c[x]) for x in keys))
print()
for b in blocks:
    print(b)
