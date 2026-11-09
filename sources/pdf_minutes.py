"""Text from a council's minutes PDF, with running headers and footers removed, keeping each line's page number.

Waterloo and Centre Wellington publish digitally made PDFs, so the text extracts cleanly; what breaks parsing is the
page furniture ("September 8, 2025 Page 150 Council Meeting", "Page 3 of 17") landing inside a vote list.
"""
import re

FOOTER = re.compile(r"^Page \d+ of \d+$")


def extract(pdf_path, header=None):
    """[(page number, line)] for every non-empty line, minus headers matching `header` and "Page N of M" footers."""
    import pdfplumber
    head = re.compile(header) if header else None
    out = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for n, page in enumerate(pdf.pages, 1):
            for line in (page.extract_text() or "").split("\n"):
                line = " ".join(line.split())
                if not line or FOOTER.match(line) or (head and head.match(line)):
                    continue
                out.append((n, line))
    return out


def save_text(lines, path):
    """minutes.txt: one line per text line, prefixed with its page, so a re-parse needs no PDF."""
    path.write_text("".join(f"{p}\t{l}\n" for p, l in lines))


def load_text(path):
    return [(int(p), l) for p, l in (row.split("\t", 1) for row in path.read_text().splitlines() if "\t" in row)]


def paragraphs(lines):
    """Join wrapped PDF lines back into paragraphs: a line ending a sentence, or a short line, ends one."""
    paras, cur = [], []
    for line in lines:
        cur.append(line)
        if re.search(r"[.:;]$", line) or len(line) < 55:
            paras.append(" ".join(cur))
            cur = []
    if cur:
        paras.append(" ".join(cur))
    return paras
