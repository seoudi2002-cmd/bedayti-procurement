"""Purchase Orders loader: validated raw rows → po_header + fact_po_line + fact_cost (+ case anchor).

Rules
- Natural key is (fiscal_year, po_number[, line_number]); loading is an upsert, so cumulative re-exports are safe.
- A PO is loaded all-or-nothing: if any line has an unresolved entity (or the lines disagree on supplier/date)
  the whole PO is held, so header totals never reflect half a PO.
- Unresolved names create `entity_alias` review items; after they are resolved, call load again.
"""
from datetime import date
from decimal import Decimal

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.cleaning.normalizers import normalize_text
from app.core.documents import ensure_po_anchor
from app.core.entities import EntityResolver
from app.core.modules.registry import get_registry
from app.core.periods import ensure_period
from app.models import (
    FactCost, FactPoLine, ImportBatch, PoHeader, ProcurementCase, ProcurementDocument, RawRow, ValidationIssue,
)

LOAD_ISSUE_CODES = ("unresolved_entity", "inconsistent_header")
HEADER_TEXT = ("requisition_no", "purchase_method", "payment_terms", "status")
HEADER_INT = ("delivery_days", "payment_days")


def _d(v) -> date | None:
    return date.fromisoformat(v) if v else None


def _n(v) -> Decimal | None:
    return Decimal(str(v)) if v not in (None, "") else None


def _first(cleaned_rows: list[dict], key: str):
    return next((c[key] for c in cleaned_rows if c.get(key) not in (None, "")), None)


def load(session: Session, batch: ImportBatch) -> int:
    spec = get_registry().get(batch.module_id)
    resolver = EntityResolver(session, spec.manifest.entity_policy)
    session.execute(delete(ValidationIssue).where(
        ValidationIssue.batch_id == batch.id, ValidationIssue.code.in_(LOAD_ISSUE_CODES)))

    rows = session.scalars(select(RawRow).where(
        RawRow.batch_id == batch.id, RawRow.status.in_(("valid", "held", "loaded"))).order_by(RawRow.row_number)).all()
    groups: dict[tuple[int, str], list[RawRow]] = {}
    for r in rows:
        groups.setdefault((int(r.cleaned["fiscal_year"]), str(r.cleaned["po_number"])), []).append(r)

    def issue(row, severity, code, field, message):
        session.add(ValidationIssue(batch_id=batch.id, raw_row_id=row.id, severity=severity, code=code,
                                    field=field, message=message))

    for (fy, po_number), group in groups.items():
        cleaned = [r.cleaned for r in group]

        # 1. one PO = one supplier and one date
        suppliers = {normalize_text(c.get("supplier")) for c in cleaned}
        dates = {c.get("po_date") for c in cleaned}
        if len(suppliers) > 1 or len(dates) > 1:
            for r in group:
                r.status = "rejected"
                issue(r, "error", "inconsistent_header", "supplier" if len(suppliers) > 1 else "po_date",
                      f"Lines of PO {po_number}/{fy} disagree on supplier or PO date")
            continue

        # 2. resolve every entity; any "review" holds the whole PO
        held = False
        header_sup = resolver.resolve("supplier", cleaned[0].get("supplier"))
        header_cc = resolver.resolve("cost_center", _first(cleaned, "requesting_unit"))
        resolved_lines = []
        for r in group:
            c = r.cleaned
            br = resolver.resolve("branch", c.get("branch"))
            cat = resolver.resolve("category", c.get("category"))
            item = resolver.resolve("item", c.get("item_code"), name=c.get("item_description"))
            resolved_lines.append((r, br, cat, item))
            for fld, res, value in (("branch", br, c.get("branch")), ("category", cat, c.get("category")),
                                    ("item_code", item, c.get("item_code"))):
                if res and res.status == "review":
                    held = True
                    issue(r, "warning", "unresolved_entity", fld, f"'{value}' needs review (see /api/aliases)")
        for res, fld in ((header_sup, "supplier"), (header_cc, "requesting_unit")):
            if res and res.status == "review":
                held = True
                for r in group:
                    issue(r, "warning", "unresolved_entity", fld, f"'{r.cleaned.get(fld)}' needs review")
        if held:
            for r in group:
                r.status = "held"
            continue

        # 3. header upsert
        po_date = _d(cleaned[0]["po_date"])
        period = ensure_period(session, po_date)
        header = session.scalar(select(PoHeader).where(PoHeader.fiscal_year == fy, PoHeader.po_number == po_number))
        if header is None:
            header = PoHeader(fiscal_year=fy, po_number=po_number, po_date=po_date, period=period,
                              supplier_id=header_sup.entity_id, currency=get_settings().default_currency)
            session.add(header)
        header.po_date, header.period, header.supplier_id, header.batch_id = po_date, period, header_sup.entity_id, batch.id
        if header_cc:
            header.cost_center_id = header_cc.entity_id
        for f in HEADER_TEXT:
            if (v := _first(cleaned, f)) is not None:
                setattr(header, f, v)
        for f in HEADER_INT:
            if (v := _first(cleaned, f)) is not None:
                setattr(header, f, int(v))
        if (v := _first(cleaned, "approval_date")):
            header.approval_date = _d(v)
        if (v := _first(cleaned, "currency")):
            header.currency = str(v)[:3].upper()
        branch_ids = {br.entity_id for _, br, _, _ in resolved_lines if br}
        header.branch_id = branch_ids.pop() if len(branch_ids) == 1 else None
        session.flush()

        # 4. lines + conformed cost rows (upsert)
        for r, br, cat, item in resolved_lines:
            c = r.cleaned
            line_no = int(c.get("line_number") or 1)
            line = session.scalar(select(FactPoLine).where(
                FactPoLine.po_header_id == header.id, FactPoLine.line_number == line_no))
            if line is None:
                line = FactPoLine(po_header_id=header.id, line_number=line_no)
                session.add(line)
            line.fiscal_year, line.po_number, line.po_date, line.period = fy, po_number, po_date, period
            line.branch_id = br.entity_id if br else None
            line.supplier_id = header.supplier_id
            line.category_id = cat.entity_id if cat else None
            line.item_id = item.entity_id if item else None
            line.item_description = c.get("item_description")
            line.quantity, line.unit_price, line.line_amount = _n(c["quantity"]), _n(c["unit_price"]), _n(c["line_amount"])
            line.uom = c.get("uom")
            line.vat_rate, line.vat_amount = _n(c.get("vat_rate")), _n(c.get("vat_amount"))
            line.currency = header.currency
            line.requested_by, line.status = c.get("requested_by"), c.get("status")
            line.required_date, line.received_date = _d(c.get("required_date")), _d(c.get("received_date"))
            line.batch_id, line.raw_row_id = batch.id, r.id
            session.flush()

            ref = f"po_line:{line.id}"
            cost = session.scalar(select(FactCost).where(FactCost.module_id == batch.module_id, FactCost.source_ref == ref))
            if cost is None:
                cost = FactCost(module_id=batch.module_id, source_ref=ref)
                session.add(cost)
            cost.period, cost.branch_id, cost.supplier_id, cost.category_id = period, line.branch_id, line.supplier_id, line.category_id
            cost.cost_center_id = header.cost_center_id
            cost.amount, cost.currency = line.line_amount, line.currency
            cost.batch_id, cost.raw_row_id = batch.id, r.id
            cost.attrs = {"po_number": po_number, "fiscal_year": fy, "line_number": line_no}
            r.status = "loaded"

        session.flush()
        header.total_amount = session.scalar(select(func.sum(FactPoLine.line_amount)).where(
            FactPoLine.po_header_id == header.id)) or 0
        ensure_po_anchor(session, header)

    _refresh_counts(session, batch)
    session.commit()
    return batch.rows_loaded


def _refresh_counts(session: Session, batch: ImportBatch) -> None:
    counts = dict(session.execute(select(RawRow.status, func.count()).where(
        RawRow.batch_id == batch.id).group_by(RawRow.status)).all())
    batch.rows_loaded, batch.rows_held = counts.get("loaded", 0), counts.get("held", 0)
    batch.rows_rejected = counts.get("rejected", 0)
    batch.rows_valid = batch.rows_total - batch.rows_rejected
    batch.status = "partially_loaded" if batch.rows_held else "loaded"
    batch.loaded_at = func.now()


def rollback(session: Session, batch: ImportBatch) -> None:
    """Remove what this batch last wrote. Lines first upserted by an earlier batch and refreshed by this one
    are removed too (lineage points to the latest batch) — re-load the earlier file to restore them."""
    session.execute(delete(FactCost).where(FactCost.batch_id == batch.id))
    line_headers = {h for (h,) in session.execute(select(FactPoLine.po_header_id).where(
        FactPoLine.batch_id == batch.id)).all()}
    session.execute(delete(FactPoLine).where(FactPoLine.batch_id == batch.id))
    session.flush()
    for hid in line_headers:
        if hid and not session.scalar(select(func.count()).select_from(FactPoLine).where(FactPoLine.po_header_id == hid)):
            header = session.get(PoHeader, hid)
            case_id = header.case_id
            session.execute(delete(ProcurementDocument).where(
                ProcurementDocument.po_header_id == hid, ProcurementDocument.doc_type == "purchase_order"))
            if session.scalar(select(func.count()).select_from(ProcurementDocument).where(
                    ProcurementDocument.po_header_id == hid)):
                header.total_amount = 0  # other documents still reference it: keep the header, empty
                continue
            session.delete(header)
            session.flush()
            if case_id and not session.scalar(select(func.count()).select_from(ProcurementDocument).where(
                    ProcurementDocument.case_id == case_id)):
                session.execute(delete(ProcurementCase).where(ProcurementCase.id == case_id))
        elif hid:
            header = session.get(PoHeader, hid)
            header.total_amount = session.scalar(select(func.sum(FactPoLine.line_amount)).where(
                FactPoLine.po_header_id == hid)) or 0
    for r in session.scalars(select(RawRow).where(RawRow.batch_id == batch.id, RawRow.status == "loaded")):
        r.status = "valid"
    batch.status, batch.rows_loaded, batch.rows_held = "rolled_back", 0, 0
    session.commit()
