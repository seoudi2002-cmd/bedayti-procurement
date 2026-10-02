"""Table → line items, shared by every source (scanned grid via OCR, Word tables, native-PDF tables).

Two layers:
  1. Readers produce a `RawTable`: a column role per column and the cell texts as read (with confidence/location).
  2. `lines_from_table` parses and VALIDATES it identically for all sources (arithmetic, row sequence, table total).

Nothing is guessed: an unreadable cell stays empty and flags the line; a value is only "derived" if explicitly
labelled so (it never is, at the moment).
"""
import re
import tempfile
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path

from app.core.cleaning.normalizers import normalize_text

ROLE_KEYWORDS: dict[str, tuple[tuple[str, int], ...]] = {
    "unit_price": (("سعر الوحده", 10), ("سعر", 6), ("unit price", 10), ("price", 6), ("u p", 8), ("up", 5), ("unit cost", 8)),
    "total": (("الثمن الاجمالي", 10), ("الاجمالي", 8), ("اجمالي", 8), ("total", 8), ("t p", 8), ("tp", 5), ("amount", 5),
              ("المبلغ", 5), ("القيمه", 4), ("الثمن", 6)),
    "qty": (("عدد الوحدات", 9), ("عدد", 7), ("الكميه", 9), ("كميه", 8), ("qty", 9), ("quantity", 9)),
    "unit": (("الوحده", 4), ("uom", 8), ("unit", 3)),
    "description": (("وصف الوحده", 9), ("وصف", 6), ("البيان", 9), ("بيان", 8), ("description", 9), ("item", 5), ("الصنف", 8), ("اسم البند", 8), ("المواصفات", 6),
                    ("اسم الصنف", 8)),
    "seq": (("م", 6), ("no", 3), ("مسلسل", 8), ("#", 5)),
}
SUBCOLUMN = {"pound": ("جنيه", "egp", "ج م", "le"), "piaster": ("قرش", "pt", "pts")}
TOTAL_ROW_WORDS = tuple(normalize_text(w) for w in ("الاجمالي", "اجمالي", "total", "subtotal", "المجموع", "الإجمالي"))
NUMERIC_ROLES = ("seq", "qty", "unit_price", "total")


@dataclass
class Cell:
    text: str = ""
    conf: float | None = None  # 0-1
    page: int | None = None
    bbox: tuple[int, int, int, int] | None = None  # x, y, w, h in page pixels (upright)
    note: str | None = None  # e.g. "alternate_reading" when another OCR pass was needed to satisfy arithmetic


@dataclass
class RawTable:
    roles: list[str | None]  # e.g. ["total_pound", "total_piaster", "unit_price_pound", ..., "description", "unit", "qty", "seq"]
    rows: list[list[Cell]]
    page: int | None = None
    source: str = "ocr_grid"  # ocr_grid | docx | pdf_native
    stated_total_raw: str | None = None
    stated_total_conf: float | None = None
    price_basis_text: str | None = None  # wording such as "شامل ضريبة القيمة المضافة" found near the table
    notes: list[str] = field(default_factory=list)


@dataclass
class ParsedLine:
    line_no: int
    page: int | None
    bbox: dict | None
    description_raw: str | None = None
    quantity_raw: str | None = None
    unit_price_raw: str | None = None
    line_total_raw: str | None = None
    description: str | None = None
    unit_description: str | None = None
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    line_total: Decimal | None = None
    field_confidence: dict = field(default_factory=dict)
    confidence: float = 0.0
    flags: list[str] = field(default_factory=list)
    seq_raw: str | None = None
    kind: str = "item"  # item | adjustment (a row with an amount but no item, quantity or price: VAT, shipping, breakdown ...)


@dataclass
class ParsedTable:
    lines: list[ParsedLine]
    stated_total: Decimal | None
    stated_total_raw: str | None
    sum_of_lines: Decimal | None
    flags: list[str]
    price_basis: str | None


def role_scores(text: str) -> dict[str, int]:
    norm = normalize_text(text)
    if not norm:
        return {}
    tokens = set(norm.split())
    scores: dict[str, int] = {}
    for role, kws in ROLE_KEYWORDS.items():
        score = 0
        for kw, weight in kws:
            k = normalize_text(kw) or kw
            if " " in k or len(k) > 2:
                hit = k in norm
            elif role == "seq":  # a lone letter inside noisy OCR text is not evidence; only a header that IS the marker is
                hit = norm == k
            else:  # short keywords must be whole tokens ("tp", "up")
                hit = k in tokens
            if hit:
                score = max(score, weight)
        if score:
            scores[role] = score
    return scores


def role_of_header(text: str) -> str | None:
    scores = role_scores(text)
    if scores:
        return max(scores, key=scores.get)
    norm = normalize_text(text)
    if not norm:
        return None
    # OCR damage: accept a close spelling of a long keyword
    from difflib import SequenceMatcher
    tokens = set(norm.split())
    best, best_score = None, 0
    for role, kws in ROLE_KEYWORDS.items():
        for kw, weight in kws:
            k = normalize_text(kw)
            if len(k) >= 4 and " " not in k and any(len(t) >= 4 and SequenceMatcher(None, t, k).ratio() >= 0.8 for t in tokens):
                if weight > best_score:
                    best, best_score = role, weight
    return best


def sub_role(text: str) -> str | None:
    """pound/piaster marker in a sub-header; tolerates one or two damaged letters ("جنيك" for "جنيه")."""
    from difflib import SequenceMatcher
    norm = normalize_text(text)
    toks = norm.split()
    for sub, kws in SUBCOLUMN.items():
        for k in kws:
            nk = normalize_text(k)
            if nk in toks or nk == norm:
                return sub
            if len(nk) >= 3 and any(len(t) >= 3 and SequenceMatcher(None, t, nk).ratio() >= 0.74 for t in toks):
                return sub
    return None


_NUM = re.compile(r"-?\d[\d,]*(?:\.\d+)?")


_NON_EGP = re.compile(r"دولار|usd|\$|يورو|eur|ريال|sar|جنيه استرليني|gbp")


def parse_ocr_number(text: str | None, dash_zero: bool = False) -> Decimal | None:
    """Digits as OCR'd ('1,870', '9350', '677,950', '1,640.35088'). A lone dash is zero ONLY where the caller says so
    (an empty piaster cell); in a quantity or price cell it means "not applicable" and parses to None."""
    if text is None:
        return None
    t = text.strip().translate(str.maketrans("٠١٢٣٤٥٦٧٨٩٫٬", "0123456789.,"))
    if t in {"-", "—", "–", "_"}:
        return Decimal(0) if dash_zero else None
    t = t.replace(" ", "")
    if re.fullmatch(r"[1-9]\d{0,2}[.,]\d{3}", t):
        t = t.replace(".", ",")  # OCR often turns the thousands comma into a dot ("677.950" is 677,950, not 677.95)
    m = _NUM.fullmatch(t)
    if not m:
        m2 = _NUM.search(t)
        if not m2 or len(m2.group(0)) < len(re.sub(r"[^\d]", "", t)):
            return None
        t = m2.group(0)
    t = t.replace(",", "")
    try:
        return Decimal(t)
    except InvalidOperation:
        return None


def _money(pound: Cell | None, piaster: Cell | None) -> tuple[Decimal | None, str | None, float | None]:
    if pound is None:
        return None, None, None
    p = parse_ocr_number(pound.text)
    if p is None:
        return None, pound.text or None, pound.conf
    raw = pound.text
    conf = pound.conf
    if piaster is not None:
        q = parse_ocr_number(piaster.text, dash_zero=True)
        if q is not None and q != 0:
            p = p + q / Decimal(100)
            raw = f"{pound.text} / {piaster.text}"
            conf = min(conf or 1.0, piaster.conf or 1.0)
    return p, raw, conf


def _cells_by_role(roles: list[str | None], row: list[Cell]) -> dict[str, Cell]:
    return {r: c for r, c in zip(roles, row) if r}


def lines_from_table(table: RawTable, tol_abs: Decimal = Decimal("0.5"), tol_rel: Decimal = Decimal("0.0002")) -> ParsedTable:
    flags: list[str] = []
    for needed in ("description",):
        if needed not in table.roles:
            flags.append(f"no_{needed}_column")
    lines: list[ParsedLine] = []
    for idx, row in enumerate(table.rows, start=1):
        c = _cells_by_role(table.roles, row)
        if not any((cell.text or "").strip() for cell in row):
            continue
        cells = [x for x in row if x.bbox]
        bbox = None
        if cells:
            x0 = min(x.bbox[0] for x in cells); y0 = min(x.bbox[1] for x in cells)
            x1 = max(x.bbox[0] + x.bbox[2] for x in cells); y1 = max(x.bbox[1] + x.bbox[3] for x in cells)
            bbox = {"x": x0, "y": y0, "w": x1 - x0, "h": y1 - y0}
        ln = ParsedLine(line_no=len(lines) + 1, page=next((x.page for x in row if x.page), table.page), bbox=bbox)
        desc = c.get("description")
        ln.description_raw = desc.text.strip() if desc and desc.text.strip() else None
        ln.description = re.sub(r"\s+", " ", ln.description_raw) if ln.description_raw else None
        if ln.description:
            ln.field_confidence["description"] = desc.conf
        unit = c.get("unit")
        ln.unit_description = re.sub(r"\s+", " ", unit.text).strip() or None if unit else None
        seq = c.get("seq")
        ln.seq_raw = seq.text.strip() if seq else None
        qty = c.get("qty")
        if qty:
            ln.quantity_raw = qty.text.strip() or None
            ln.quantity = parse_ocr_number(qty.text)
            ln.field_confidence["quantity"] = qty.conf
        pr, raw, conf = _money(c.get("unit_price") or c.get("unit_price_pound"), c.get("unit_price_piaster"))
        ln.unit_price, ln.unit_price_raw, ln.field_confidence["unit_price"] = pr, raw, conf
        tt, raw, conf = _money(c.get("total") or c.get("total_pound"), c.get("total_piaster"))
        ln.line_total, ln.line_total_raw, ln.field_confidence["line_total"] = tt, raw, conf
        ln.flags.extend(f"cell_{n}" for n in (c[r].note for r in ("qty", "unit_price", "unit_price_pound", "total", "total_pound") if r in c and c[r].note) if n)
        raw_blob = " ".join((x.text or "") for x in row)
        if _NON_EGP.search(normalize_text(raw_blob)):
            ln.flags.append("non_egp_currency")
        if not ln.description and ln.quantity is None and ln.unit_price is None and ln.line_total is not None:
            ln.kind = "adjustment"
            ln.flags.append("adjustment_row")
        lines.append(ln)

    sum_total = Decimal(0)
    have_sum = False
    for ln in lines:
        if ln.kind == "adjustment":
            ln.confidence = round(min([v for v in ln.field_confidence.values() if v is not None] or [0.5]), 3)
            if ln.line_total is not None:
                sum_total += ln.line_total
                have_sum = True
            continue
        missing = [n for n, v in (("quantity", ln.quantity), ("unit_price", ln.unit_price), ("line_total", ln.line_total)) if v is None]
        if ln.description is None:
            missing.append("description")
        for m in missing:
            ln.flags.append(f"unreadable_{m}")
        if ln.quantity is not None and ln.unit_price is not None and ln.line_total is not None:
            expected = ln.quantity * ln.unit_price
            diff = abs(expected - ln.line_total)
            if diff <= max(tol_abs, tol_rel * abs(ln.line_total)):
                ln.flags.append("arithmetic_verified")
            else:
                ln.flags.append("arithmetic_mismatch")
        else:
            ln.flags.append("arithmetic_not_checkable")
        if ln.line_total is not None:
            sum_total += ln.line_total
            have_sum = True
        confs = [v for v in ln.field_confidence.values() if v is not None]
        base = min(confs) if confs else 0.0
        if "arithmetic_verified" in ln.flags:  # three independent numbers agreeing is strong evidence
            base = max(base, min(0.95, (sum(confs) / len(confs)) + 0.1)) if confs else base
        if "arithmetic_mismatch" in ln.flags:
            base = min(base, 0.4)
        if any(f.startswith("unreadable_") for f in ln.flags):
            base = min(base, 0.35)
        ln.confidence = round(base, 3)

    stated = parse_ocr_number(table.stated_total_raw) if table.stated_total_raw else None
    seqs = [parse_ocr_number(ln.seq_raw) for ln in lines if ln.seq_raw]
    ints = [int(s) for s in seqs if s is not None]
    if ints and ints != list(range(ints[0], ints[0] + len(ints))):
        flags.append("row_sequence_gap")  # a row may have been missed or misread
    if stated is not None and have_sum:
        if abs(sum_total - stated) <= max(tol_abs, tol_rel * abs(stated)):
            flags.append("table_total_verified")
        else:
            flags.append("table_total_mismatch")
    elif stated is None:
        flags.append("table_total_unreadable")
    basis = None
    if table.price_basis_text:
        n = normalize_text(table.price_basis_text)
        if ("غير شامل" in n or "excl" in n or "قبل" in n) and ("ضريب" in n or "vat" in n):
            basis = "excl_vat"  # check first: "غير شامل" contains "شامل"
        elif "شامل" in n and ("ضريب" in n or "vat" in n):
            basis = "incl_vat"
    return ParsedTable(lines=lines, stated_total=stated, stated_total_raw=table.stated_total_raw,
                       sum_of_lines=sum_total if have_sum else None, flags=flags, price_basis=basis)


# ======================================================================================================
# Scanned pages: grid detection + per-cell OCR
# ======================================================================================================
@dataclass
class Grid:
    xs: list[int]  # reference vertical borders, ascending
    ys: list[int]  # horizontal borders, ascending
    bbox: tuple[int, int, int, int]  # x0, y0, x1, y1
    band_xs: list[list[int]] | None = None  # per band: the borders as actually found (scans drift/skew)

    def xs_for(self, band: int) -> list[int]:
        return self.band_xs[band] if self.band_xs else self.xs


def _merge_positions(values: list[float], gap: int) -> list[int]:
    out: list[int] = []
    cur: list[float] = []
    for v in sorted(values):
        if cur and v - cur[-1] > gap:
            out.append(int(round(sum(cur) / len(cur))))
            cur = []
        cur.append(v)
    if cur:
        out.append(int(round(sum(cur) / len(cur))))
    return out


def deskew(gray, max_angle: float = 4.0):
    """Straighten a slightly rotated scan using its long horizontal rulings. Returns (image, angle_degrees)."""
    import cv2
    import numpy as np
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    h, w = bw.shape
    hor = cv2.morphologyEx(bw, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (max(40, int(w * 0.04)), 1)))
    lines = cv2.HoughLinesP(hor, 1, np.pi / 3600, threshold=150, minLineLength=int(w * 0.25), maxLineGap=25)
    if lines is None:
        return gray, 0.0
    angles = []
    for x1, y1, x2, y2 in lines.reshape(-1, 4):
        a = np.degrees(np.arctan2(y2 - y1, x2 - x1))
        if abs(a) <= max_angle:
            angles.append(a)
    if len(angles) < 2:
        return gray, 0.0
    angle = float(np.median(angles))
    if abs(angle) < 0.05:
        return gray, 0.0
    m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.warpAffine(gray, m, (w, h), flags=cv2.INTER_CUBIC, borderValue=255), angle


def detect_grids(gray, min_cols: int = 3, min_rows: int = 3):
    """Find ruled tables on an upright grayscale page (numpy array).

    Row separators are long horizontal rulings. Within each band between two separators we look for vertical rulings
    spanning most of the band; consecutive bands that share their vertical rulings form one table (so a signature
    block under the main table is not mixed into it, and merged header cells just have fewer rulings)."""
    import cv2
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    h, w = bw.shape
    hor = cv2.morphologyEx(bw, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (max(30, int(w * 0.02)), 1)))
    hor = cv2.morphologyEx(hor, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (max(40, int(w * 0.036)), 1)))  # re-join broken rulings
    ver = cv2.morphologyEx(bw, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(25, int(h * 0.009)))))
    _, _, st, _ = cv2.connectedComponentsWithStats(hor)
    ys = _merge_positions([y + hh / 2 for x, y, wd, hh, _ in st[1:] if wd >= 0.35 * w], 8)
    bands = []  # (y0, y1, xs)
    for y0, y1 in zip(ys, ys[1:]):
        bh = y1 - y0
        if bh < 50:
            continue
        seg = ver[y0 + 6:y1 - 6]
        col = seg.sum(axis=0) / 255
        # tall rows: faded rulings are broken, so accept 45% coverage but never less than 70 px (text strokes are shorter)
        need = max(70.0, 0.45 * (bh - 12)) if bh >= 150 else 0.8 * (bh - 12)
        xs = _merge_positions([x for x in range(w) if col[x] >= need], 14)
        bands.append((y0, y1, xs))

    def same(a, b, need=0.6):
        if not a or not b:
            return False
        hit = sum(any(abs(x - y) <= 32 for y in b) for x in a)
        return hit >= need * min(len(a), len(b))

    tables: list[list[tuple[int, int, list[int]]]] = []
    cur: list = []
    for band in bands:
        y0, y1, xs = band
        if len(xs) < 2:
            if cur:
                tables.append(cur)
                cur = []
            continue
        ref = max((b[2] for b in cur), key=len) if cur else []
        if cur and same(xs, ref) and abs(y0 - cur[-1][1]) <= 12:
            cur.append(band)
        else:
            if cur:
                tables.append(cur)
            cur = [band]
    if cur:
        tables.append(cur)
    grids: list[Grid] = []
    for t in tables:
        if len(t) < min_rows - 1:
            continue
        allx = sorted(x for _, _, xs in t for x in xs)
        xs = _merge_positions(allx, 30)
        # keep rulings seen in at least half the bands (drops one-off marks)
        keep = [x for x in xs if sum(any(abs(x - y) <= 32 for y in b[2]) for b in t) >= max(1, len(t) // 2)]
        if len(keep) < min_cols:
            continue
        band_xs = []
        for _, _, bx in t:
            offs = [min((y - x for y in bx), key=abs) for x in keep if any(abs(y - x) <= 32 for y in bx)]
            drift = int(sorted(offs)[len(offs) // 2]) if offs else 0
            aligned = []
            for x in keep:
                near = [y for y in bx if abs(y - x) <= 32]
                aligned.append(min(near, key=lambda y: abs(y - x)) if near else x + drift)
            band_xs.append(aligned)
        tys = [t[0][0]] + [b[1] for b in t]
        grids.append(Grid(xs=keep, ys=tys, bbox=(keep[0], tys[0], keep[-1], tys[-1]), band_xs=band_xs))
    grids.sort(key=lambda g: -(g.bbox[2] - g.bbox[0]) * (g.bbox[3] - g.bbox[1]))
    return grids


def remove_rulings(gray):
    """Erase table rulings so OCR reads the text, not the grid (ruled lines make Tesseract's layout analysis fail)."""
    import cv2
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    h, w = bw.shape
    hor = cv2.morphologyEx(bw, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (max(30, int(w * 0.02)), 1)))
    ver = cv2.morphologyEx(bw, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(30, int(h * 0.012)))))
    mask = cv2.dilate(cv2.bitwise_or(hor, ver), cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)))
    out = gray.copy()
    out[mask > 0] = 255
    return out


def _crop_to_file(gray, box: tuple[int, int, int, int], workdir: Path, name: str, scale: float = 1.0) -> Path:
    import cv2
    x0, y0, x1, y1 = box
    crop = gray[max(0, y0):y1, max(0, x0):x1]
    if scale != 1.0:
        crop = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    path = workdir / f"{name}.png"
    cv2.imwrite(str(path), crop)
    return path


def _ink(gray, box) -> float:
    x0, y0, x1, y1 = box
    crop = gray[y0:y1, x0:x1]
    return float((crop < 140).mean()) if crop.size else 0.0


def _is_alpha_text(text: str) -> bool:
    letters = sum(ch.isalpha() for ch in text)
    return letters >= max(2, 0.5 * len(text.replace(" ", "")))


def infer_numeric_roles(columns: dict[int, list[Decimal | None]], tol_rel: Decimal = Decimal("0.0002")) -> dict[int, str]:
    """When headers cannot be read: find (quantity, unit price, total) among numeric columns by arithmetic —
    the triple with qty × price = total on most rows — and the running-number column. Evidence is numeric, so the
    result is verifiable; lines are still flagged `roles_inferred`."""
    from itertools import permutations
    cols = [c for c, vals in columns.items() if sum(v is not None for v in vals) >= 2]
    best: tuple[float, tuple[int, int, int]] | None = None
    for q, p_, t in permutations(cols, 3):
        n = hits = 0
        for vq, vp, vt in zip(columns[q], columns[p_], columns[t]):
            if vq is None or vp is None or vt is None or vt == 0:
                continue
            n += 1
            if abs(vq * vp - vt) <= max(Decimal(1), tol_rel * abs(vt)):
                hits += 1
        if n >= 2 and (best is None or hits / n > best[0] or (hits / n == best[0] and hits > 0)):
            if hits / n >= 0.6:
                best = (hits / n, (q, p_, t))
    roles: dict[int, str] = {}
    if best:
        q, p_, t = best[1]
        # quantity × price = total cannot tell the two factors apart; the quantity is the smaller one (it is
        # then still flagged `roles_inferred` for review)
        def med(c):
            v = sorted(x for x in columns[c] if x is not None)
            return v[len(v) // 2]
        if med(q) > med(p_):
            q, p_ = p_, q
        roles[q], roles[p_], roles[t] = "qty", "unit_price", "total"
        for c in cols:
            if c in roles:
                continue
            ints = [int(v) for v in columns[c] if v is not None and v == v.to_integral_value()]
            if ints and ints == list(range(ints[0], ints[0] + len(ints))) and ints[0] in (0, 1):
                roles[c] = "seq"
    return roles


def _variant_readings(engine, gray, box, work: Path, tag: str) -> list[str]:
    """Several OCR passes over one numeric cell (different scale/binarisation/page-segmentation)."""
    import cv2
    x0, y0, x1, y1 = box
    crop = gray[y0:y1, x0:x1]
    out: list[str] = []
    variants = []
    for scale, psm in ((2.4, 7), (1.0, 7), (2.0, 8), (3.0, 13)):
        img = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC) if scale != 1.0 else crop
        variants.append((img, psm))
    _, otsu = cv2.threshold(cv2.resize(crop, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    variants.append((otsu, 7))
    for k, (img, psm) in enumerate(variants):
        path = work / f"{tag}_v{k}.png"
        cv2.imwrite(str(path), img)
        pg = engine.ocr_image(path, psm=psm, lang="eng", whitelist="0123456789.,-")
        t = "".join(w.text for w in sorted(pg.words, key=lambda w: w.left))
        if t and t not in out:
            out.append(t)
    return out


def _resolve_with_alternate_readings(engine, gray, work: Path, page: int, roles, cells, body, box_of) -> None:
    """For a row whose quantity × unit price ≠ total (or has an unreadable number), re-read the three numeric cells
    with other OCR settings and accept a combination ONLY if it satisfies the arithmetic. The first reading is kept
    in the cell note; every such line still goes to human review."""
    from itertools import product
    idx = {r: i for i, r in enumerate(roles) if r}
    qty_i = idx.get("qty")
    price_i = idx.get("unit_price") if "unit_price" in idx else idx.get("unit_price_pound")
    total_i = idx.get("total") if "total" in idx else idx.get("total_pound")
    if None in (qty_i, price_i, total_i):
        return

    def val(c: Cell) -> Decimal | None:
        return parse_ocr_number(c.text) if c.text else None

    for j in body:
        cq, cp, ct = cells[(j, qty_i)], cells[(j, price_i)], cells[(j, total_i)]
        q, p_, t = val(cq), val(cp), val(ct)
        if q is not None and p_ is not None and t is not None and abs(q * p_ - t) <= max(Decimal("0.5"), Decimal("0.0002") * abs(t)):
            continue
        if not any((c.text or "").strip() for c in (cq, cp, ct)):
            continue
        reads = []
        for cell, i in ((cq, qty_i), (cp, price_i), (ct, total_i)):
            alts = [cell.text] if cell.text else []
            alts += [a for a in _variant_readings(engine, gray, box_of(j, i), work, f"p{page}_alt{j}_{i}") if a not in alts]
            reads.append(alts)
        good = []
        for a, b, c in product(*reads):
            va, vb, vc = parse_ocr_number(a), parse_ocr_number(b), parse_ocr_number(c)
            if va is None or vb is None or vc is None or vc == 0 or va == 0:
                continue
            if abs(va * vb - vc) <= max(Decimal("0.5"), Decimal("0.0002") * abs(vc)):
                good.append((a, b, c))
        if len({tuple(g) for g in good}) == 1:  # one consistent reading: take it, but mark it
            for cell, new in zip((cq, cp, ct), good[0]):
                if new != cell.text:
                    cell.note = f"alternate_reading(first_read={cell.text or 'empty'})"
                    cell.text = new
                    cell.conf = min(cell.conf or 0.7, 0.7)


def read_scanned_table(engine, gray, grid: Grid, page: int, workdir: Path | None = None, lang: str = "ara+eng") -> RawTable | None:
    """Read one ruled table from an upright page image. Returns None when it does not look like a line-item table.

    Rulings are erased first (Tesseract's layout analysis fails on ruled grids). The header strip is read as sparse
    text to find column roles; every body cell is then read on its own (digits-only for numeric columns), which is far
    more reliable than reading the whole table in one pass."""
    work = workdir or Path(tempfile.mkdtemp(prefix="tbl_"))
    ruled = gray
    gray = remove_rulings(gray)  # text-only copy for all OCR/ink measurements; `ruled` is only used for geometry
    ys = grid.ys
    ncols = len(grid.xs) - 1
    nb = len(ys) - 1
    m = 6  # margin inside the rulings, px
    tx0, ty0, tx1, ty1 = grid.bbox

    # --- 0. where does the line-item table start? A ruled grid can also cover info boxes above it: the table begins at
    # the first band whose text names at least two column roles (e.g. description + unit price).
    probe = min(nb, 8)
    pstrip = _crop_to_file(gray, (tx0, ys[0], tx1, ys[probe]), work, f"p{page}_probe")
    pw = engine.ocr_image(pstrip, psm=11, lang=lang)
    band_text: dict[int, list[str]] = {}
    for w in pw.words:
        cy = w.cy + ys[0]
        jj = next((k for k in range(probe) if ys[k] <= cy < ys[k + 1]), -1)
        if jj >= 0:
            band_text.setdefault(jj, []).append(w.text)
    start = next((j for j in range(probe) if sum(1 for v in role_scores(" ".join(band_text.get(j, []))).values() if v >= 4) >= 2), 0)
    if start:
        grid = Grid(xs=grid.xs, ys=grid.ys[start:], bbox=(tx0, ys[start], tx1, ty1),
                    band_xs=grid.band_xs[start:] if grid.band_xs else None)
        ys, nb, (tx0, _, tx1, ty1) = grid.ys, len(grid.ys) - 1, grid.bbox

    def col_of(cx: float, j: int) -> int:
        bx = grid.xs_for(j)
        for i in range(ncols):
            if bx[i] - tx0 <= cx < bx[i + 1] - tx0:
                return i
        return -1

    # --- 1. header strip: sparse-text OCR over the first bands → words per (band, column)
    strip_bands = min(4, nb)
    strip = _crop_to_file(gray, (tx0, ys[0], tx1, ys[strip_bands]), work, f"p{page}_header")
    sw = engine.ocr_image(strip, psm=11, lang=lang)
    texts: dict[tuple[int, int], list] = {}
    for w in sw.words:
        cy = w.cy + ys[0]
        j = next((k for k in range(strip_bands) if ys[k] <= cy < ys[k + 1]), -1)
        if j < 0:
            continue
        i = col_of(w.cx, j)
        if i >= 0:
            texts.setdefault((j, i), []).append(w)

    def htext(j: int, i: int) -> str:
        return " ".join(w.text for w in sorted(texts.get((j, i), []), key=lambda w: (w.cy // 30, w.left if lang == "eng" else -w.left)))

    def band_digit_words(j: int) -> int:
        return sum(1 for i in range(ncols) for w in texts.get((j, i), []) if re.fullmatch(r"[\d.,]{2,}", w.text))

    # --- 2. header bands = the leading bands before the first band that looks like data
    header_bands = 0
    for j in range(strip_bands):
        band_text = " ".join(htext(j, i) for i in range(ncols))
        looks_header = any(role_of_header(htext(j, i)) for i in range(ncols)) or any(sub_role(w) for w in band_text.split())
        if band_digit_words(j) >= 2 and not looks_header:
            break
        header_bands = j + 1
    if header_bands == 0 or header_bands >= nb:
        return None

    # --- 3. header groups (a missing header ruling merges columns) and keyword roles
    import cv2
    _, bw = cv2.threshold(ruled, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    y0, y1 = ys[0], ys[1]
    groups: list[list[int]] = [[0]]
    for i in range(1, ncols):
        x = grid.xs_for(0)[i]
        ink = (bw[y0 + 4:y1 - 4, max(0, x - 3):x + 4] > 0).mean() if y1 - y0 > 12 else 1.0
        if ink >= 0.45:
            groups.append([i])
        else:
            groups[-1].append(i)
    roles: list[str | None] = [None] * ncols
    subs: dict[int, str | None] = {}
    for i in range(ncols):
        subs[i] = next((sub_role(htext(j, i)) for j in range(header_bands) if sub_role(htext(j, i))), None)
    # money pairs: a "جنيه" (pound) column followed by its "قرش" (piaster) column (the latter's header is often garbled)
    in_pair: set[int] = set()
    unnamed_pairs: list[int] = []
    for i in range(ncols - 1):
        if i in in_pair:
            continue
        if (subs[i] == "pound" and subs[i + 1] in ("piaster", None)) or (subs[i] is None and subs[i + 1] == "piaster" and i not in in_pair):
            text = " ".join(htext(j, k) for j in range(header_bands) for k in (i, i + 1))
            norm = normalize_text(text)
            if any(k in norm for k in ("الثمن", "الاجمالي", "اجمالي", "total")):
                base = "total"
            elif any(k in norm for k in ("سعر", "الوحده", "price", "unit")):
                base = "unit_price"
            else:
                base = None
            if base:
                roles[i], roles[i + 1] = f"{base}_pound", f"{base}_piaster"
            else:
                unnamed_pairs.append(i)
            in_pair.update({i, i + 1})
    for g in groups:
        free = [i for i in g if i not in in_pair]
        if not free:
            continue
        header_text = " ".join(htext(j, i) for j in range(header_bands) for i in g)
        base = role_of_header(header_text)
        for i in free:
            roles[i] = base if i == free[0] else (None if len(g) > 1 else base)
    # a money pair whose heading was lost is the other one of (unit price, total) — only when exactly one is named
    named = {r.rsplit("_", 1)[0] for r in roles if r and r.endswith(("_pound", "_piaster"))}
    other = {"total": "unit_price", "unit_price": "total"}
    single = {r for r in roles if r in other}
    for i in unnamed_pairs:
        known = (named | single) & set(other)
        if len(known) == 1:
            base = other[next(iter(known))]
            roles[i], roles[i + 1] = f"{base}_pound", f"{base}_piaster"

    # --- 4. body bands; the table-total band (a labelled row, e.g. "Total ...") ends the line items
    table = RawTable(roles=roles, rows=[], page=page, source="ocr_grid")
    body: list[int] = []

    def box_of(j: int, i: int) -> tuple[int, int, int, int]:
        bx = grid.xs_for(j)
        return (bx[i] + m, ys[j] + m, bx[i + 1] - m, ys[j + 1] - m)

    def read_text(j: int, i: int, psm: int = 6, scale: float = 1.3):
        box = box_of(j, i)
        path = _crop_to_file(gray, box, work, f"p{page}_r{j}_c{i}t", scale=scale)
        pg = engine.ocr_image(path, psm=psm, lang=lang)
        text = " ".join(w.text for w in pg.words)
        conf = (sum(w.conf for w in pg.words) / len(pg.words) / 100) if pg.words else None
        return text, conf

    def read_digits(j: int, i: int):
        box = box_of(j, i)
        path = _crop_to_file(gray, box, work, f"p{page}_r{j}_c{i}", scale=1.6)
        pg = engine.ocr_image(path, psm=7, lang="eng", whitelist="0123456789.,-")
        text = "".join(w.text for w in sorted(pg.words, key=lambda w: w.left))
        conf = (sum(w.conf for w in pg.words) / len(pg.words) / 100) if pg.words else None
        return text, conf

    for j in range(header_bands, nb):
        if ys[j + 1] - ys[j] < 40:
            continue
        # a total row has a label in its first/widest cell: read the whole band as text once
        band_path = _crop_to_file(gray, (tx0 + m, ys[j] + m, tx1 - m, ys[j + 1] - m), work, f"p{page}_r{j}_band")
        bpg = engine.ocr_image(band_path, psm=6, lang=lang)
        btxt = normalize_text(" ".join(w.text for w in bpg.words))
        if any(wd in btxt for wd in TOTAL_ROW_WORDS if len(wd) > 3) and sum(1 for w in bpg.words if re.fullmatch(r"[\d.,]{4,}", w.text)) <= 2:
            nums = [w for w in bpg.words if parse_ocr_number(w.text) is not None and len(re.sub(r"\D", "", w.text)) >= 3]
            if nums:
                best = max(nums, key=lambda w: parse_ocr_number(w.text))
                table.stated_total_raw, table.stated_total_conf = best.text, best.conf / 100
            table.price_basis_text = " ".join(w.text for w in bpg.words)
            break
        body.append(j)
    if not body:
        return None

    # --- 5. column kinds: keyword role; unnamed columns are probed with digit OCR on the first body rows
    numeric_cols: set[int] = set()
    text_cols: set[int] = {i for i, r in enumerate(roles) if r in ("description", "unit")}
    for i in range(ncols):
        if i in text_cols:
            continue
        r = roles[i]
        if r and (r in NUMERIC_ROLES or r.endswith(("_pound", "_piaster"))):
            numeric_cols.add(i)
            continue
        probes = [read_digits(j, i)[0] for j in body[:3] if _ink(gray, box_of(j, i)) >= 0.004]
        ok = sum(parse_ocr_number(t) is not None and bool(re.sub(r"\D", "", t)) for t in probes)
        letters = sum(ch.isalpha() for j in body[:2] for ch in read_text(j, i)[0])
        if probes and ok >= max(1, len(probes) - 1) and letters < 6:  # prose with digits in it is a text column
            numeric_cols.add(i)
        else:
            text_cols.add(i)

    # --- 6. per-cell reading
    cells: dict[tuple[int, int], Cell] = {}
    for j in body:
        for i in range(ncols):
            box = box_of(j, i)
            if box[2] <= box[0] or box[3] <= box[1]:
                cells[(j, i)] = Cell()
                continue
            geo = (box[0], box[1], box[2] - box[0], box[3] - box[1])
            if _ink(gray, box) < 0.004:
                cells[(j, i)] = Cell("", None, page, geo)
            elif i in numeric_cols:
                t, c = read_digits(j, i)
                cells[(j, i)] = Cell(t, c, page, geo)
            else:
                t, c = read_text(j, i)
                if (not t or (c is not None and c < 0.5)) and _ink(gray, box) >= 0.006:
                    t2, c2 = read_text(j, i, psm=7, scale=1.0)
                    if t2 and (not t or (c2 or 0) > (c or 0)):
                        t, c = t2, c2
                cells[(j, i)] = Cell(t, c, page, geo)

    # --- 6b. a header spanning two columns names the first, but the figures can sit in the neighbour (an empty margin
    # column left of a merged header): move the role to the adjacent unnamed numeric column that holds the data.
    def _col_empty(i: int) -> bool:
        return all(not (cells[(j, i)].text or "").strip() for j in body)
    for i in range(ncols):
        r = roles[i]
        if r and (r in NUMERIC_ROLES) and i not in text_cols and _col_empty(i):
            for k in (i + 1, i - 1):
                if 0 <= k < ncols and roles[k] is None and k in numeric_cols and not _col_empty(k):
                    roles[k], roles[i] = r, None
                    break

    # --- 7. roles for numeric columns the headers did not name
    vals = {i: [parse_ocr_number(cells[(j, i)].text, dash_zero=True) if cells[(j, i)].text else None for j in body] for i in numeric_cols}
    inferred = False
    unnamed = [i for i in sorted(numeric_cols) if roles[i] is None]

    def money_vec(base: str):
        main = next((i for i, r in enumerate(roles) if r in (base, f"{base}_pound")), None)
        if main is None:
            return None
        pia = next((i for i, r in enumerate(roles) if r == f"{base}_piaster"), None)
        out = []
        for k in range(len(body)):
            v = vals[main][k] if main in vals else None
            if v is not None and pia is not None and pia in vals and vals[pia][k]:
                v = v + vals[pia][k] / Decimal(100)
            out.append(v)
        return out

    price_vec, total_vec = money_vec("unit_price"), money_vec("total")
    if unnamed and "qty" not in roles and price_vec is not None and total_vec is not None:
        # headers named the money columns: the quantity is the free column that makes qty × price = total
        best_c, best_hits = None, 0
        for c in unnamed:
            hits = sum(1 for q, p_, t in zip(vals[c], price_vec, total_vec)
                       if q and p_ is not None and t and abs(q * p_ - t) <= max(Decimal("0.5"), Decimal("0.0002") * abs(t)))
            if hits > best_hits:
                best_c, best_hits = c, hits
        usable = sum(1 for p_, t in zip(price_vec, total_vec) if p_ is not None and t)
        if best_c is not None and usable and best_hits / usable >= 0.6:
            roles[best_c] = "qty"
            inferred = True
            unnamed = [i for i in unnamed if i != best_c]
    if unnamed and not ({"qty", "unit_price", "total"} <= {r for r in roles if r} or "qty" in roles and price_vec is not None):
        piaster: dict[int, int] = {}
        for i in unnamed:
            col = [v for v in vals[i] if v is not None]
            if col and all(v == 0 for v in col) and (i - 1) in numeric_cols and (i - 1) not in piaster.values():
                piaster[i] = i - 1  # an all-dash column right after a number column: its piasters
        mainvals = {i: vals[i] for i in unnamed if i not in piaster}
        for i, r in infer_numeric_roles(mainvals).items():
            roles[i] = r
            inferred = True
        for pi, base in piaster.items():
            if roles[base] in ("unit_price", "total"):
                roles[pi] = f"{roles[base]}_piaster"
                roles[base] = f"{roles[base]}_pound"
    rest = [i for i in unnamed if roles[i] is None]
    if "seq" not in roles:
        for i in rest:
            ints = [int(v) for v in vals[i] if v is not None and v == v.to_integral_value()]
            if ints and ints[0] in (0, 1) and all(b - a == 1 for a, b in zip(ints, ints[1:])):
                roles[i] = "seq"
                break
    if "description" not in roles:
        widths = [(grid.xs[i + 1] - grid.xs[i], i) for i in text_cols if roles[i] is None]
        if widths:
            roles[max(widths)[1]] = "description"
    if "unit" not in roles:
        rest = [i for i in sorted(text_cols) if roles[i] is None]
        if rest:
            roles[rest[0]] = "unit"
    table.roles = roles
    if inferred:
        table.notes.append("roles_inferred")
    _resolve_with_alternate_readings(engine, gray, work, page, roles, cells, body, box_of)
    for j in body:
        row = [cells[(j, i)] for i in range(ncols)]
        if any((c.text or "").strip() for c in row):
            table.rows.append(row)
    return table
