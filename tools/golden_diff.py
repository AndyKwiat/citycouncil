#!/usr/bin/env python3
"""Phase 1 check: compare site/guelph/ with the golden copy of the old site (state/golden/site/), ignoring the
intended changes (stylesheet, theme header and favicon, footer disclaimer, page scripts), and print what's left.

  tools/golden_diff.py [golden dir] [site dir]
"""
import difflib, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
INTENDED = [
    (r"(<style>.*?</style>)+", "<style/>"),
    (r'<link rel="icon"[^>]*>', ""),
    (r'<div class="hero"[^>]*></div>', ""),
    (r'<footer class="site">.*?</footer>', ""),
    (r"<script>.*?</script>", "<script/>"),
]


def normalize(text):
    for pattern, repl in INTENDED:
        text = re.sub(pattern, repl, text, flags=re.S)
    return re.sub(r">\s*<", ">\n<", text)


def main(golden, site):
    gold = {p.relative_to(golden) for p in golden.rglob("*") if p.is_file()}
    new = {p.relative_to(site) for p in site.rglob("*") if p.is_file()}
    print(f"golden {len(gold)} files, new {len(new)} files")
    for p in sorted(gold - new):
        print("MISSING", p)
    for p in sorted(new - gold):
        print("ADDED  ", p)
    same = changed = 0
    for p in sorted(gold & new):
        a, b = (golden / p).read_bytes(), (site / p).read_bytes()
        if a == b:
            same += 1
            continue
        if p.suffix != ".html":
            print("BINARY CHANGED", p)
            changed += 1
            continue
        x, y = normalize(a.decode()), normalize(b.decode())
        if x == y:
            same += 1
            continue
        changed += 1
        print(f"--- {p}")
        for line in list(difflib.unified_diff(x.splitlines(), y.splitlines(), lineterm="", n=0))[2:40]:
            print("   ", line[:220])
    print(f"{same} files identical apart from intended changes, {changed} with other differences")
    return changed


if __name__ == "__main__":
    g = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "state/golden/site"
    s = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "site/guelph"
    sys.exit(1 if main(g, s) else 0)
