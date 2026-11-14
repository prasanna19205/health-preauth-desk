"""Chunk a text-based day-care procedure list for clause-level retrieval.

The source list is not bundled with this project. This parser is deliberately
format tolerant: it preserves page numbers and groups wrapped PDF lines around
numbered/bulleted procedure entries, while keeping a page intact when no entry
markers can be identified.
"""
import hashlib
import re

from parse_pdf import extract_pages


ITEM_RE = re.compile(r"^(?:(?:\d{1,4}|[A-Z])(?:[.)]|\s+-)\s+|[•▪●*-]\s+)(\S.*)$")
HEADING_RE = re.compile(r"^(?:annexure|day[ -]?care|list of|contents|page\s+\d+)\b", re.I)
MIN_CHARS = 12
MAX_CHARS = 1200


def _id(doc_id, version, clause_id, text):
    raw = f"{doc_id}|{version}|{clause_id}|{text}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _split(text):
    if len(text) <= MAX_CHARS:
        return [text]
    parts, current = [], ""
    for sentence in re.split(r"(?<=[.;])\s+", text):
        if current and len(current) + len(sentence) + 1 > MAX_CHARS:
            parts.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        parts.append(current)
    return parts


def build_daycare_chunks(pdf_path, doc_id="daycare", doc_version="unknown"):
    chunks = []
    for page, raw_text in extract_pages(pdf_path):
        groups = []
        current = []
        for raw_line in raw_text.splitlines():
            line = " ".join(raw_line.split())
            if not line or line.isdigit() or line.lower().startswith("care health"):
                continue
            if HEADING_RE.match(line):
                if current:
                    groups.append(" ".join(current))
                    current = []
                continue
            item = ITEM_RE.match(line)
            if item:
                if current:
                    groups.append(" ".join(current))
                current = [item.group(1).strip()]
            elif current:
                current.append(line)
            elif len(line) >= MIN_CHARS:
                # Some lists are laid out in columns and have no numbering.
                # Preserve the line so it remains searchable instead of
                # silently dropping it.
                groups.append(line)
        if current:
            groups.append(" ".join(current))

        for item_no, text in enumerate(groups, start=1):
            text = text.strip()
            if len(text) < MIN_CHARS:
                continue
            clause_id = f"{doc_id}:p{page}:item{item_no}"
            for part_no, part in enumerate(_split(text), start=1):
                part_id = clause_id if part_no == 1 else f"{clause_id}#{part_no}"
                chunks.append({
                    "id": _id(doc_id, doc_version, part_id, part),
                    "clause_id": part_id,
                    "doc_id": doc_id,
                    "doc_version": doc_version,
                    "section_type": "daycare_procedure",
                    "page": page,
                    "heading": "Day-care procedures",
                    "text": part,
                })
    return chunks
