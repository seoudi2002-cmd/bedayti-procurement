"""Finance handover memo loader.

A memo is an amount handed to Finance, NOT a confirmed bank payment. Two types share the register but stay
distinct: 'po' (against a PO) and 'service' (no PO: recurring administrative/service payments).
Key: memo_no (running number in the source sheet) - it must stay stable across re-exports.
Supplier is linked only by exact/compact name via the supplier register; unmatched stays NULL (+ review alias).
Anything doubtful becomes a data_exception; no source value is altered.
"""
from collections import defaultdict
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.cleaning.normalizers import normalize_text
from app.core.attribution import BranchAttributor
from app.core.entities import EntityResolver
from app.core.overrides import reapply_approved
from app.core.po_costs import sync_po_cost
from app.core.procurement_attribution import reattribute_po
from app.core.exceptions import raise_exception
from app.core.loader_utils import date_from_json, parse_number_year, raw_value, rows_with_status
from app.core.modules.registry import get_registry
from app.core.periods import ensure_period
from app.models import FinanceHandover, ImportBatch, PoHeader

MODULE = "finance_handover"
TOLERANCE = Decimal("0.5")


def load(session: Session, batch: ImportBatch) -> int:
    spec = get_registry().get(MODULE)
    resolver = EntityResolver(session, spec.manifest.entity_policy)
    rows = rows_with_status(session, batch, ("valid", "loaded"))
    po_lookup = {(h.fiscal_year, h.po_number): h for h in session.scalars(select(PoHeader))}
    memos: list[FinanceHandover] = []
    unresolved_sup: dict[str, int] = defaultdict(int)
    po_not_found: set[str] = set()
    anomalies: list[str] = []

    for r in rows:
        c = r.cleaned
        memo = session.scalar(select(FinanceHandover).where(FinanceHandover.memo_no == int(c["memo_no"])))
        if memo is None:
            memo = FinanceHandover(memo_no=int(c["memo_no"]), memo_type=c["memo_type"], memo_type_source=str(raw_value(batch, r, "memo_type")).strip())
            session.add(memo)
        memo.memo_type, memo.memo_type_source = c["memo_type"], str(raw_value(batch, r, "memo_type")).strip()
        memo.sent_date = date_from_json(c.get("sent_date"))
        memo.period = ensure_period(session, memo.sent_date) if memo.sent_date else None
        memo.po_number_source = c.get("po_ref")
        memo.supplier_name_source = c.get("supplier_name")
        memo.supplier_category_source = c.get("supplier_category_source")
        memo.subject_source, memo.purchase_category_source = c.get("subject_source"), c.get("purchase_category_source")
        memo.amount = Decimal(c["amount"]) if c.get("amount") not in (None, "") else None
        memo.batch_id, memo.raw_row_id = batch.id, r.id
        res = resolver.resolve("supplier", c.get("supplier_name"))
        if res and res.status == "resolved":
            memo.supplier_id = res.entity_id
        else:
            memo.supplier_id = None
            if c.get("supplier_name"):
                unresolved_sup[c["supplier_name"]] += 1
        memo.po_header_id = None
        if c.get("po_ref"):
            key = parse_number_year(c["po_ref"])
            header = po_lookup.get((key[1], key[0])) if key else None
            if header is not None:
                memo.po_header_id = header.id
            else:
                po_not_found.add(c["po_ref"])
        if memo.memo_type == "po" and not c.get("po_ref"):
            anomalies.append(f"memo {memo.memo_no}: PO-type memo without PO number")
            raise_exception(session, "handover_po_memo_without_po", "warning", "finance_handover", str(memo.memo_no),
                            "Memo is typed as a PO memo but has no PO number", {}, MODULE, batch.id)
        if memo.memo_type == "service" and c.get("po_ref"):
            raise_exception(session, "handover_service_memo_with_po", "warning", "finance_handover", str(memo.memo_no),
                            "Memo is typed as a service memo but carries a PO number", {"po": c["po_ref"]}, MODULE, batch.id)
        if memo.amount is None:
            raise_exception(session, "handover_amount_missing", "warning", "finance_handover", str(memo.memo_no),
                            "Memo has no amount", {}, MODULE, batch.id)
        session.flush()
        reapply_approved(session, "finance_handover", str(memo.memo_no), memo)
        r.status = "loaded"
        memos.append(memo)
    session.flush()
    attributor = BranchAttributor(session)
    for header_id in {m.po_header_id for m in memos if m.po_header_id}:
        header = session.get(PoHeader, header_id)
        reattribute_po(session, header, attributor, batch.id)  # memo subjects are supporting evidence
        sync_po_cost(session, header)

    # possible duplicates: same PO, same supplier text, same amount (different memo numbers/dates)
    dup_groups: dict[tuple, list[FinanceHandover]] = defaultdict(list)
    per_po: dict[str, list[FinanceHandover]] = defaultdict(list)
    for m in session.scalars(select(FinanceHandover).where(FinanceHandover.po_number_source.is_not(None))):
        if m.amount is not None:
            dup_groups[(m.po_number_source, normalize_text(m.supplier_name_source), m.amount)].append(m)
        per_po[m.po_number_source].append(m)
    for (po, _sup, amount), group in dup_groups.items():
        if len(group) > 1:
            raise_exception(session, "handover_possible_duplicate", "warning", "po", po,
                            "Several memos for the same PO, supplier and amount: possible duplicate",
                            {"memo_nos": sorted(m.memo_no for m in group), "amount": str(amount),
                             "dates": [m.sent_date.isoformat() if m.sent_date else None for m in group]}, MODULE, batch.id)
    for po, group in per_po.items():
        key = parse_number_year(po)
        header = po_lookup.get((key[1], key[0])) if key else None
        if header is not None and header.total_amount is not None:
            total = sum((m.amount for m in group if m.amount is not None), Decimal(0))
            if total > Decimal(header.total_amount) + TOLERANCE:
                raise_exception(session, "handover_exceeds_po_total", "warning", "po", po,
                                "Memos handed to Finance for this PO add up to more than the PO total",
                                {"handover_total": str(total), "po_total": str(header.total_amount),
                                 "memo_nos": sorted(m.memo_no for m in group)}, MODULE, batch.id)

    if unresolved_sup:
        raise_exception(session, "handover_supplier_unresolved", "warning", "import_batch", str(batch.id),
                        f"{len(unresolved_sup)} supplier names in the memos match no supplier in the register "
                        "(left unlinked, see /api/aliases)", {"names": dict(unresolved_sup)}, MODULE, batch.id)
    if po_not_found:
        raise_exception(session, "handover_po_not_in_register", "info", "import_batch", str(batch.id),
                        f"{len(po_not_found)} PO numbers on memos are not in the loaded PO register "
                        "(e.g. POs of a period the register does not cover)", {"po_numbers": sorted(po_not_found)}, MODULE, batch.id)
    batch.rows_loaded, batch.rows_held, batch.status = len(rows), 0, "loaded"
    batch.loaded_at = func.now()
    session.commit()
    return batch.rows_loaded


def rollback(session: Session, batch: ImportBatch) -> None:
    from sqlalchemy import delete
    session.execute(delete(FinanceHandover).where(FinanceHandover.batch_id == batch.id))
    batch.status, batch.rows_loaded = "rolled_back", 0
    session.commit()
