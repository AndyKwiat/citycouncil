import sys, os, pdfplumber
src, dst = sys.argv[1], sys.argv[2]
os.makedirs(dst, exist_ok=True)
for f in sorted(os.listdir(src)):
    if not f.endswith(".pdf"): continue
    o = os.path.join(dst, f[:-4] + ".txt")
    if os.path.exists(o): continue
    try:
        with pdfplumber.open(os.path.join(src, f)) as pdf:
            pages = [(p.extract_text() or "") for p in pdf.pages]
        open(o, "w").write("\n\f\n".join(pages))
    except Exception as e:
        print("ERR", f, e)
