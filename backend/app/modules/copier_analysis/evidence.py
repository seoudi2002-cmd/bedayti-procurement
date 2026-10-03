"""Scanned printer status pages = SUPPORTING EVIDENCE ONLY.

Each page carries the printer's 'Printed Pages' counter. The counter is read by OCR and compared with the statement's
current readings: a match supports a reading, a non-match is reported for review. These values are never used for KPIs,
costs, totals or decisions; the statement and the invoice always take precedence."""
import re
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

COUNTER_RE = re.compile(r"Printed\s*Pages\s*[:;|]?\s*([0-9][0-9 ,.]{2,9})", re.I)
STAMP_RE = re.compile(r"(\d{2}/\d{2}/20\d{2})\s+(\d{2}[:.]\d{2})")


@dataclass
class EvidencePage:
    page_no: int
    counter_value: int | None
    counter_raw: str | None
    printed_at_text: str | None
    confidence: float | None


def read_counter(text: str) -> tuple[int | None, str | None]:
    m = COUNTER_RE.search(text)
    if not m:
        return None, None
    raw = m.group(1).strip()
    digits = re.sub(r"\D", "", raw)
    return (int(digits) if len(digits) >= 3 else None), raw


def printed_at(text: str, top_lines: int = 12) -> str | None:
    """The page's own print timestamp sits in the first lines; later timestamps (e.g. a data-sanitisation date) are other events."""
    head = "\n".join(text.splitlines()[:top_lines])
    m = STAMP_RE.search(head)
    return f"{m.group(1)} {m.group(2).replace('.', ':')}" if m else None


def _read_page(pdf: Path, page: int, workdir: Path, dpi: int) -> EvidencePage:
    from app.core.extraction.ocr import default_engine
    from app.core.extraction.pdfio import render_page
    img = render_page(pdf, page, workdir, dpi=dpi)
    pg = default_engine().ocr_image(img, psm=6, lang="eng")
    text = pg.text()
    value, raw = read_counter(text)
    return EvidencePage(page, value, raw, printed_at(text), round(pg.mean_conf, 1))


def read_pdf(pdf: Path, workers: int = 4, dpi: int = 200) -> list[EvidencePage]:
    from app.core.extraction.pdfio import page_count, require_poppler
    require_poppler()
    n = page_count(pdf)
    with tempfile.TemporaryDirectory(prefix="evid_") as tmp, ThreadPoolExecutor(max_workers=workers) as pool:
        work = Path(tmp)
        return list(pool.map(lambda p: _read_page(pdf, p, work, dpi), range(1, n + 1)))


def match_pages(pages: list[dict], machines: list[dict]) -> list[dict]:
    """Status per page against the statement's current readings. `pages`: {page_no, counter_value}; `machines`:
    {source_ref, cur}. Returns [{page_no, status, matched_machine_ref, note}]."""
    by_cur: dict[int, list[dict]] = {}
    for m in machines:
        if m.get("cur") is not None:
            by_cur.setdefault(m["cur"], []).append(m)
    seen: dict[int, int] = {}
    out = []
    for p in pages:
        v = p["counter_value"]
        if v is None:
            out.append({"page_no": p["page_no"], "status": "unreadable", "matched_machine_ref": None, "note": "no counter could be read"})
            continue
        if v in seen:
            out.append({"page_no": p["page_no"], "status": "duplicate", "matched_machine_ref": None, "note": f"same counter as page {seen[v]}"})
            continue
        seen[v] = p["page_no"]
        cands = by_cur.get(v, [])
        if len(cands) == 1:
            out.append({"page_no": p["page_no"], "status": "matched", "matched_machine_ref": cands[0]["source_ref"], "note": None})
        elif len(cands) > 1:
            out.append({"page_no": p["page_no"], "status": "ambiguous", "matched_machine_ref": None, "note": f"{len(cands)} machines share this reading"})
        else:
            out.append({"page_no": p["page_no"], "status": "no_match", "matched_machine_ref": None,
                        "note": "no machine in the statement has this current reading (misread counter or a conflict: review)"})
    return out
