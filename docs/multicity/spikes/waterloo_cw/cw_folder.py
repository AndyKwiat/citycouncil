import re, sys, polite
def folder(fid):
    h = polite.get(f"https://centrewellington.civicweb.net/filepro/documents/{fid}")
    out = []
    for m in re.finditer(r'href="(/(?:filepro/documents|document)/(\d+)[^"]*)"[^>]*>', h):
        s = h[m.end():m.end() + 500]
        t = " ".join(re.sub(r"<[^>]+>", " ", s).split())
        out.append((m.group(1), t[:120]))
    seen = set(); res = []
    for u, t in out:
        if u in seen: continue
        seen.add(u); res.append((u, t))
    return h, res
if __name__ == "__main__":
    for fid in sys.argv[1:]:
        h, res = folder(fid)
        print("##", fid, len(res))
        for u, t in res: print(u, "|", t)
