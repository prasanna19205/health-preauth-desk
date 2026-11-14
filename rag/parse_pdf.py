import sys
from pathlib import Path
import pymupdf


def extract_pages(pdf_path):
    doc = pymupdf.open(pdf_path)
    return [(i, page.get_text("text")) for i, page in enumerate(doc, start=1)]


if __name__ == "__main__":
    src = Path(sys.argv[1])
    out = Path("data/processed") / (src.stem + "_pages.txt")
    with open(out, "w", encoding="utf-8") as f:
        for n, text in extract_pages(src):
            f.write(f"\n===== PAGE {n} =====\n{text}")
    print("wrote", out)