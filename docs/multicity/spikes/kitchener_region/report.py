import json, collections, sys
a = json.load(open(sys.argv[1]))
T0, T1 = "2022/11/15", "2026/11/09"
for c in ["kitchener", "region"]:
    print("=====", c)
    by = collections.defaultdict(lambda: collections.Counter())
    for x in a:
        if x["council"] != c or not (T0 <= x["date"] <= T1): continue
        k = (x["body"], x["name"])
        b = by[k]; b["meetings"] += 1; b["motions"] += x["motions"]; b["recorded"] += x["recorded"]; b["split"] += x["split"]
        b["mtg_with_motions"] += x["motions"] > 0; b["mtg_with_rec"] += x["recorded"] > 0; b["mtg_with_split"] += x["split"] > 0
        b["bookmarks"] += x["bookmarks"]
    tot = collections.defaultdict(collections.Counter)
    for k in sorted(by):
        print(k, dict(by[k]))
        if k[0] in ("council", "committee"): tot[k[0]].update(by[k])
    for b in tot: print("TOTAL", b, dict(tot[b]))
    yr = collections.defaultdict(collections.Counter)
    for x in a:
        if x["council"] == c and x["body"] in ("council", "committee") and T0 <= x["date"] <= T1:
            y = yr[(x["date"][:4], x["body"])]; y["m"] += x["motions"]; y["rec"] += x["recorded"]; y["split"] += x["split"]; y["mtg"] += 1
    for k in sorted(yr): print("  year", k, dict(yr[k]))
    lab = collections.Counter(); heads = collections.Counter(); res = collections.Counter(); unrec = collections.Counter()
    for x in a:
        if x["council"] == c and T0 <= x["date"] <= T1:
            lab.update(x["labels"]); heads.update(set(x["heads"])); res.update(x["results"]); unrec.update(x["unrec"])
    print("labels", lab.most_common()); print("heads", heads.most_common(30))
    print("recorded results", res.most_common(15)); print("unrecorded results", unrec.most_common(15))
