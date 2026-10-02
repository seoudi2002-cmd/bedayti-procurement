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
from app.core.po_costs import sync_po_cost
from app.core.entities import EntityResolver
from app.core.modules.registry import get_registry
from app.core.periods import ensure_period
from app.models import (
    FactCost, FactPoLine, ImportBatch, PoHeader, ProcurementCase, ProcurementDocument, RawRow, ValidationIssue,
)

MODULE = "purchase_orders"
LOAD_ISSUE_CODES = ("unresolved_entity", "inconsistent_header")
HEADER_TEXT = ("requisition_no", "purchase_method", "payment_terms", "status")
HEADER_INT = ("delivery_days", "payment_days")


def _d(v) -> date | None:
    return date.fromisoformat(v) if v else None


def _n(v) -> Decimal | None:
    return Decimal(str(v)) if v not in (None, "") else None


def _first(cleaned_rows: list[dict], key: str):
    return next((c[key] for c in cleaned_rows if c.get(key) not in (None, "")), None)


def load_lines(session: Session, batch: ImportBatch) -> int:
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
        header.granularity = "lines"
        sync_po_cost(session, header)  # line-level cost rows supersede any header-level one
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
    register_headers = {h for (h,) in session.execute(select(PoHeader.id).where(
        PoHeader.batch_id == batch.id, PoHeader.granularity == "header_only")).all()}
    line_headers = {h for (h,) in session.execute(select(FactPoLine.po_header_id).where(
        FactPoLine.batch_id == batch.id)).all()}
    session.execute(delete(FactPoLine).where(FactPoLine.batch_id == batch.id))
    session.flush()
    line_headers |= register_headers
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


# --------------------------------------------------------------------------------------------------
# Dispatcher and header-level (register) profile
# --------------------------------------------------------------------------------------------------
def load(session: Session, batch: ImportBatch) -> int:
    return load_register(session, batch) if batch.profile == "register" else load_lines(session, batch)


def load_register(session: Session, batch: ImportBatch) -> int:
    """PO register (one row per PO, no lines) → po_header (+ one header-level cost row when priced and dated).

    Principle: load what the source says and flag what is uncertain; never invent. Only conflicting PO numbers
    (same number on several rows) are held. Every flag is a data_exception for manual review.
    """
    from app.core.attribution import BranchAttributor
    from app.core.procurement_attribution import reattribute_po
    from app.core.documents import link_po_to_requisition
    from app.core.entities import EntityResolver, compact
    from app.core.exceptions import raise_exception
    from app.core.loader_utils import date_from_json, flag_for, parse_number_year, raw_value, rows_with_status
    from app.core.periods import fiscal_year as fy_of
    from app.models import DimSupplier, Requisition

    spec = get_registry().get(MODULE)
    resolver = EntityResolver(session, spec.manifest.entity_policy)
    attributor = BranchAttributor(session)
    rows = rows_with_status(session, batch, ("valid", "held", "loaded"))
    suppliers: dict[int, list[DimSupplier]] = {}
    for s_ in session.scalars(select(DimSupplier).where(DimSupplier.register_no.is_not(None))):
        suppliers.setdefault(s_.register_no, []).append(s_)
    requisitions = {(r_.fiscal_year, r_.req_number): r_ for r_ in session.scalars(select(Requisition))}
    parsed = {r.id: parse_number_year(r.cleaned["po_ref"]) for r in rows}
    groups: dict[tuple[str, int], list[RawRow]] = {}
    for r in rows:
        if parsed[r.id]:
            groups.setdefault(parsed[r.id], []).append(r)

    def exc(code, severity, key, message, details=None, entity="po_header"):
        raise_exception(session, code, severity, entity, key, message, details or {}, MODULE, batch.id)

    loaded = held = 0
    for r in rows:
        c = r.cleaned
        key = parsed[r.id]
        if key is None:
            r.status = "held"
            held += 1
            exc("po_number_format", "error", f"{batch.id}:{r.row_number}",
                f"PO number '{c['po_ref']}' is not in n/yyyy form; row held", {"row": r.row_number}, "po_row")
            continue
        number, fy = key
        label = f"{fy}/{number}"
        if len(groups[key]) > 1:
            r.status = "held"
            held += 1
            exc("po_number_conflict", "error", label,
                "The same PO number appears on several rows (different suppliers/requisitions?): all rows held for "
                "manual review; the source is not modified",
                {"rows": [x.row_number for x in groups[key]],
                 "suppliers": [x.cleaned.get("supplier_name") for x in groups[key]],
                 "requisitions": [x.cleaned.get("requisition_ref") for x in groups[key]],
                 "totals": [x.cleaned.get("total_amount") for x in groups[key]]})
            continue

        header = session.scalar(select(PoHeader).where(PoHeader.fiscal_year == fy, PoHeader.po_number == number))
        if header is None:
            header = PoHeader(fiscal_year=fy, po_number=number, po_date=None, currency=get_settings().default_currency,
                              granularity="header_only")
            session.add(header)
        header.number_source = c["po_ref"]
        header.batch_id = batch.id
        # --- date: NULL when missing/invalid, raw text kept
        header.po_date = date_from_json(c.get("po_date"))
        raw_date = raw_value(batch, r, "po_date")
        header.po_date_source = None if raw_date is None else str(raw_date)
        flag = flag_for(r, "po_date")
        if header.po_date is None:
            header.period = None
            if flag:
                exc("po_date_invalid", "error", label, f"PO date is invalid: {flag['message']}",
                    {"raw": flag["raw"]})
            else:
                exc("po_date_missing", "warning", label, "PO has no date in the source")
        else:
            header.period = ensure_period(session, header.po_date)
            if fy_of(header.po_date) != fy:
                exc("po_fiscal_year_vs_date", "warning", label, "Fiscal year in the PO number differs from the PO date's year",
                    {"po_date": header.po_date.isoformat()})
        # --- supplier: by register number (an ID), name only as cross-check / fallback
        header.supplier_name_source = c.get("supplier_name")
        header.supplier_register_no_source = c.get("supplier_register_no")
        header.supplier_category_source = c.get("supplier_category_source")
        regno, sname = c.get("supplier_register_no"), c.get("supplier_name")
        supplier = None
        if regno is not None:
            all_cands = suppliers.get(regno, [])
            cands = all_cands
            if sname and len(all_cands) > 1:  # shared register number: the name decides, if it can
                cands = [x for x in all_cands if compact(x.name) == compact(sname)]
            if len(cands) == 1:
                supplier = cands[0]
                if sname and compact(supplier.name) != compact(sname):
                    exc("po_supplier_name_mismatch", "warning", label,
                        "Supplier name on the PO differs from the register entry for that register number",
                        {"po_name": sname, "register_name": supplier.name, "register_no": regno})
            elif not all_cands:
                exc("po_supplier_register_no_not_found", "warning", label,
                    "Supplier register number is not in the supplier register", {"register_no": regno})
            else:
                exc("po_supplier_ambiguous_register_no", "warning", label,
                    "Several suppliers share this register number and the name does not decide", {"register_no": regno})
        elif sname:
            res = resolver.resolve("supplier", sname)
            if res and res.status == "resolved":
                supplier = session.get(DimSupplier, res.entity_id)
            else:
                exc("po_supplier_unresolved", "warning", label, "Supplier name matches no register entry", {"name": sname})
        else:
            exc("po_supplier_missing", "info", label, "PO has no supplier in the source",
                {"order_status": c.get("order_status")})
        header.supplier_id = supplier.id if supplier else None
        # --- amounts (NULL = not stated, never zero)
        total = Decimal(c["total_amount"]) if c.get("total_amount") not in (None, "") else None
        header.total_amount = total
        tflag = flag_for(r, "total_amount")
        if total is None:
            exc("po_total_invalid" if tflag else "po_total_missing", "warning" if tflag else "info", label,
                "PO total is invalid in the source" if tflag else "PO has no total in the source (excluded from spend)",
                {"order_status": c.get("order_status"), "raw": tflag["raw"] if tflag else None})
        handed = Decimal(c["finance_handover_amount"]) if c.get("finance_handover_amount") not in (None, "") else None
        header.finance_handover_amount_register = handed
        header.remaining_register = Decimal(c["remaining_register"]) if c.get("remaining_register") not in (None, "") else None
        if handed is not None and total is not None and handed > total + Decimal("0.5"):
            exc("finance_handover_amount_exceeds_total", "warning", label,
                "Finance handover amount in the register is greater than the PO total (not treated as a confirmed payment)",
                {"po_total": str(total), "handover_amount": str(handed)})
        elif handed is not None and total is None:
            exc("po_handover_without_total", "warning", label, "Handover amount present but no PO total", {"handover_amount": str(handed)})
        # --- descriptive source fields
        header.description_source = c.get("description")
        header.po_category_source = c.get("po_category_source")
        header.issuance_status_source, header.order_status_source = c.get("issuance_status"), c.get("order_status")
        # --- requisition link (by stated number only)
        header.requisition_no = c.get("requisition_ref")
        rkey = parse_number_year(c.get("requisition_ref"))
        if c.get("requisition_ref") and rkey is None:
            exc("po_requisition_format", "warning", label, "Requisition number is not in n/yyyy form",
                {"requisition_ref": c.get("requisition_ref")})
        elif rkey is not None:
            if rkey != (number, fy):
                exc("po_requisition_number_differs", "warning", label,
                    "PO number differs from the requisition number it references: review the cross-reference",
                    {"po": label, "requisition": c["requisition_ref"]})
            req = requisitions.get((rkey[1], rkey[0]))
            if req is not None:
                link_po_to_requisition(session, header, req)
            else:
                exc("po_requisition_not_found", "warning", label,
                    "Referenced requisition is not in the loaded requisition register", {"requisition_ref": c["requisition_ref"]})
        session.flush()
        reattribute_po(session, header, attributor, batch.id)  # after the requisition link: it is evidence too
        sync_po_cost(session, header)
        ensure_po_anchor(session, header)
        r.status = "loaded"
        loaded += 1
    batch.rows_loaded, batch.rows_held = loaded, held
    batch.rows_valid = batch.rows_total - batch.rows_rejected - batch.rows_skipped
    batch.status = "partially_loaded" if held else "loaded"
    batch.loaded_at = func.now()
    session.commit()
    return loaded
