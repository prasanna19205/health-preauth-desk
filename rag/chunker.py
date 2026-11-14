import re
import hashlib
from parse_pdf import extract_pages

# "4.1. Standard Exclusions:", "3.2.20 Health Management Program", "4. Exclusions"
HEADING_RE = re.compile(r"^(\d{1,2}(?:\.\d{1,2}){0,3})\.?\s+([A-Z][^\n]{2,80})$")
# "(i) Pre-Existing Diseases: Code- Excl01"  /  "30-day waiting period- Code- Excl03"
EXCL_RE = re.compile(
    r"^(?:\([ivxl]+\)\s*)?([^()]{3,80}?)[\s:\-–]*\(?Code\s*-?\s*(Excl\s*\d+)\)?\s*$",
    re.IGNORECASE)
PERM_RE = re.compile(r"^\(b\)\s+Permanent Exclusions", re.IGNORECASE)
ITEM_RE = re.compile(r"^(\d{1,2})\.\s+(\S.*)$")
ANNEX_RE = re.compile(r"^Annexure\s+([IVX]+)\b")
CODE_IN_TEXT = re.compile(r"Code\s*-?\s*(Excl\s*\d+)", re.IGNORECASE)
CODE_PAREN = re.compile(r"\(\s*Code\s*-?\s*Excl\s*\d+\s*\)", re.IGNORECASE)

WAITING_CODES = {"excl01", "excl02", "excl03"}
MAX_CHARS = 1500
MIN_BODY = 40

# Only these plain numbered lines count as real top-level headings.
# Everything else like "5. Any Claim paid..." or "10 Leggings" is a list item.
TOP_TITLES = ("preamble", "definitions", "benefits covered", "exclusions",
              "general terms", "other terms")

HEADING_RULES = [
    ("waiting_period", ["waiting period", "wait period"]),
    ("exclusion", ["exclusion"]),
    ("sublimit", ["sub-limit", "sublimit", "sub limit"]),
    ("definition", ["definition"]),
]


def type_from_heading(heading):
    h = heading.lower()
    for label, words in HEADING_RULES:
        if any(w in h for w in words):
            return label
    return None


def norm_code(raw):
    """'Excl 3' / 'excl03' -> 'Excl03'"""
    digits = re.sub(r"\D", "", raw)
    return "Excl" + digits.zfill(2)


def clean_lines(text):
    """Skip blanks, lone page numbers, page headers, lone bullets, lone '(iii)' markers."""
    for line in text.splitlines():
        line = line.strip()
        if not line or line.isdigit() or line == "•":
            continue
        if line.startswith("Care Supreme"):
            continue
        if re.fullmatch(r"\([ivxl]+\)", line):
            continue
        yield line


def split_long(text, limit=MAX_CHARS):
    if len(text) <= limit:
        return [text]
    parts, cur = [], ""
    for sent in re.split(r"(?<=[.;])\s+", text):
        if cur and len(cur) + len(sent) > limit:
            parts.append(cur)
            cur = sent
        else:
            cur = (cur + " " + sent).strip()
    if cur:
        parts.append(cur)
    return parts


def make_id(doc_id, doc_version, clause_id, text):
    raw = f"{doc_id}|{doc_version}|{clause_id}|{text}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def new_section(number, heading, page, code=None, perm=False):
    return {"number": number, "heading": heading, "page": page,
            "code": code, "perm": perm, "lines": []}


def build_policy_chunks(pdf_path, doc_id, doc_version):
    # 1) cut the document into sections
    sections = []
    cur = new_section("0", "Preamble", 1)
    in_perm = False   # True after the line "(b) Permanent Exclusions:"
    for page_no, text in extract_pages(pdf_path):
        for line in clean_lines(text):
            hm = HEADING_RE.match(line)
            dotted = bool(hm) and "." in hm.group(1)
            im = ITEM_RE.match(line)
            em = EXCL_RE.match(line)
            an = ANNEX_RE.match(line)
            if an:                                         # "Annexure I - List of ..."
                sections.append(cur)
                cur = new_section("Annex" + an.group(1), line[:80], page_no)
                in_perm = False
            elif PERM_RE.match(line):
                sections.append(cur)
                cur = new_section("4.1b", "Permanent Exclusions", page_no)
                in_perm = True
            elif dotted:                                   # e.g. "4.2. Specific Exclusions:"
                sections.append(cur)
                cur = new_section(hm.group(1), hm.group(2).strip(), page_no)
                in_perm = False
            elif in_perm and im:                           # permanent exclusion item
                sections.append(cur)
                first = im.group(2).strip()
                head = CODE_PAREN.sub("", first)[:80].strip(" :")
                cur = new_section(f"Perm{im.group(1)}", head, page_no, perm=True)
                cur["lines"].append(first)
            elif (not in_perm) and em:                     # Excl01, Excl02, Excl03
                sections.append(cur)
                code = norm_code(em.group(2))
                cur = new_section(code, em.group(1).strip().rstrip(":-– ").strip(),
                                  page_no, code=code.lower())
            elif (hm and (not in_perm) and (not cur["code"])
                  and hm.group(2).lower().startswith(TOP_TITLES)):   # plain "4. Exclusions"
                sections.append(cur)
                cur = new_section(hm.group(1), hm.group(2).strip(), page_no)
            else:
                cur["lines"].append(line)   # includes list items like "4. Cataract"
    sections.append(cur)

    # permanent-exclusion items: read the code from anywhere in the item's text
    for s in sections:
        if s["perm"]:
            m = CODE_IN_TEXT.search(s["heading"] + " " + " ".join(s["lines"]))
            if m:
                s["number"] = norm_code(m.group(1))
                s["code"] = s["number"].lower()

    # 2) turn sections into chunks
    chunks, seen = [], {}
    parent_type, parent_num = "cover", "0"
    for s in sections:
        own = type_from_heading(s["heading"])
        if s["code"]:
            stype = "waiting_period" if s["code"] in WAITING_CODES else "exclusion"
        elif s["perm"]:
            stype = "exclusion"
        elif s["number"].startswith("Annex"):
            stype = "annexure"
        elif "." not in s["number"]:
            parent_type, parent_num = own or "cover", s["number"]
            stype = parent_type
        else:
            top = s["number"].split(".")[0]
            if top != parent_num:
                parent_type, parent_num = "cover", top
            stype = own or parent_type

        body = " ".join(s["lines"]).strip()
        if len(body) < MIN_BODY:
            continue

        lead = body[:300].rstrip() + "..."
        for idx, piece in enumerate(split_long(body)):
            base = f"{doc_id}:{s['number']}"
            if idx > 0:
                base += f"#{idx + 1}"
            seen[base] = seen.get(base, 0) + 1
            clause_id = base if seen[base] == 1 else f"{base}-dup{seen[base]}"
            if idx == 0:
                full_text = f"[{s['number']}] {s['heading']}\n{piece}"
            else:
                # carry the start of the clause (e.g. "24 months") into later pieces
                full_text = (f"[{s['number']}] {s['heading']} (continued)\n"
                             f"Clause begins: {lead}\n{piece}")
            chunks.append({
                "id": make_id(doc_id, doc_version, clause_id, full_text),
                "clause_id": clause_id,
                "doc_id": doc_id,
                "doc_version": doc_version,
                "section_type": stype,
                "page": s["page"],
                "heading": s["heading"],
                "text": full_text,
            })
    return chunks


if __name__ == "__main__":
    from collections import Counter
    cs = build_policy_chunks("data/raw/policy.pdf", "policy", "test")
    print("total chunks:", len(cs))
    print(Counter(c["section_type"] for c in cs))
    print("\n--- Excl clause ids ---")
    print(sorted(c["clause_id"] for c in cs if c["clause_id"].startswith("policy:Excl")))
    print("\n--- annexure ids ---")
    print([c["clause_id"] for c in cs if c["section_type"] == "annexure"])
    print("\n--- chunks that mention cataract ---")
    for c in cs:
        if "cataract" in c["text"].lower():
            print(c["clause_id"], "|", c["section_type"], "| page", c["page"])
            print(c["text"][:300].replace("\n", " "))
            print()