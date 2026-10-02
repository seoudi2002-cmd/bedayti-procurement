from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import Principal, require
from app.core.documents import case_overview
from app.core.entities import resolve_alias
from app.core.modules.registry import get_registry
from app.db import get_session
from app.models import EntityAlias, FactPoLine, PoHeader

router = APIRouter()
MODULE = "purchase_orders"


class AliasDecision(BaseModel):
    entity_id: int | None = None
    create_new: bool = False
    branch_kind: str | None = None  # for new branches: branch | regional_office
    region_id: int | None = None


@router.get("/aliases")
def list_aliases(status: str = "pending", entity_type: str | None = None, session: Session = Depends(get_session),
                 _: Principal = Depends(require("analyst"))):
    q = select(EntityAlias).where(EntityAlias.status == status).order_by(EntityAlias.entity_type, EntityAlias.alias_raw)
    if entity_type:
        q = q.where(EntityAlias.entity_type == entity_type)
    return [{"id": a.id, "entity_type": a.entity_type, "raw": a.alias_raw, "suggested_entity_id": a.entity_id,
             "confidence": float(a.confidence) if a.confidence is not None else None, "status": a.status}
            for a in session.scalars(q)]


@router.post("/aliases/{alias_id}/resolve")
def decide_alias(alias_id: int, body: AliasDecision, session: Session = Depends(get_session),
                 _: Principal = Depends(require("analyst"))):
    alias = session.get(EntityAlias, alias_id)
    if alias is None:
        raise HTTPException(404, "Alias not found")
    try:
        alias = resolve_alias(session, alias, body.entity_id, body.create_new, body.branch_kind, body.region_id)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"id": alias.id, "status": alias.status, "entity_id": alias.entity_id}


@router.get("/purchase-orders")
def list_pos(fiscal_year: int | None = None, supplier_id: int | None = None, branch_attribution_status: str | None = None,
             limit: int = 100, session: Session = Depends(get_session), _: Principal = Depends(require("viewer"))):
    q = select(PoHeader).order_by(PoHeader.po_date.desc(), PoHeader.id.desc()).limit(min(limit, 500))
    if fiscal_year:
        q = q.where(PoHeader.fiscal_year == fiscal_year)
    if supplier_id:
        q = q.where(PoHeader.supplier_id == supplier_id)
    if branch_attribution_status:
        q = q.where(PoHeader.branch_attribution_status == branch_attribution_status)
    return [{"id": h.id, "fiscal_year": h.fiscal_year, "po_number": h.po_number, "number_source": h.number_source,
             "po_date": h.po_date, "supplier_id": h.supplier_id,
             "total_amount": None if h.total_amount is None else float(h.total_amount),
             "finance_handover_amount_register": None if h.finance_handover_amount_register is None
             else float(h.finance_handover_amount_register),
             "branch_id": h.branch_id, "branch_attribution_status": h.branch_attribution_status,
             "order_status_source": h.order_status_source, "granularity": h.granularity}
            for h in session.scalars(q)]


@router.get("/purchase-orders/{po_id}")
def get_po(po_id: int, session: Session = Depends(get_session), _: Principal = Depends(require("viewer"))):
    h = session.get(PoHeader, po_id)
    if h is None:
        raise HTTPException(404, "PO not found")
    lines = session.scalars(select(FactPoLine).where(FactPoLine.po_header_id == po_id).order_by(FactPoLine.line_number))
    overview = case_overview(session, get_registry().get(MODULE), h.case_id) if h.case_id else None
    return {
        "id": h.id, "fiscal_year": h.fiscal_year, "po_number": h.po_number, "po_date": h.po_date,
        "approval_date": h.approval_date, "supplier_id": h.supplier_id, "requisition_no": h.requisition_no,
        "purchase_method": h.purchase_method, "payment_days": h.payment_days, "delivery_days": h.delivery_days,
        "total_amount": None if h.total_amount is None else float(h.total_amount), "currency": h.currency,
        "status": h.status, "granularity": h.granularity, "po_date_source": h.po_date_source,
        "description_source": h.description_source, "po_category_source": h.po_category_source,
        "supplier_category_source": h.supplier_category_source, "order_status_source": h.order_status_source,
        "finance_handover_amount_register": None if h.finance_handover_amount_register is None
        else float(h.finance_handover_amount_register),
        "remaining_register": None if h.remaining_register is None else float(h.remaining_register),
        "branch": {"id": h.branch_id, "method": h.branch_attribution_method, "status": h.branch_attribution_status,
                   "source_text": h.branch_source_text},
        "lines": [{"line_number": ln.line_number, "item": ln.item_description, "quantity": float(ln.quantity),
                   "unit_price": float(ln.unit_price), "line_amount": float(ln.line_amount),
                   "branch_id": ln.branch_id, "category_id": ln.category_id} for ln in lines],
        "documents": [{"type": d.doc_type, "number": d.doc_number, "date": d.doc_date, "amount": d.amount and float(d.amount)}
                      for d in overview["documents"]] if overview else [],
        "current_stage": overview["current_stage"] if overview else None,
        "missing_required_documents": overview["missing_required"] if overview else [],
    }
