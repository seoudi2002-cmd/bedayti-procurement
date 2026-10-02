"""One cost source per PO (kept consistent whichever import supplied the data)."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import FactCost, FactPoLine, PoHeader

MODULE = "purchase_orders"


def sync_po_cost(session: Session, header: PoHeader) -> None:
    """A PO's spend comes from its lines if it has any, else from one header-level row (when total and period are
    known). Prevents double counting when a PO appears in both the register and a line-level import."""
    ref = f"po:{header.id}"
    has_lines = session.scalar(select(func.count()).select_from(FactPoLine).where(FactPoLine.po_header_id == header.id))
    cost = session.scalar(select(FactCost).where(FactCost.module_id == MODULE, FactCost.source_ref == ref))
    if has_lines or header.total_amount is None or header.period is None:
        if cost is not None:
            session.delete(cost)
        return
    if cost is None:
        cost = FactCost(module_id=MODULE, source_ref=ref)
        session.add(cost)
    cost.period, cost.branch_id, cost.supplier_id = header.period, header.branch_id, header.supplier_id
    cost.cost_center_id, cost.amount, cost.currency = header.cost_center_id, header.total_amount, header.currency
    cost.batch_id = header.batch_id
    cost.attrs = {"po_number": header.po_number, "fiscal_year": header.fiscal_year, "granularity": "header_only"}
