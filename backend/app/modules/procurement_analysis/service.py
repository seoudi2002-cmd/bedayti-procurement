"""Upload -> validate -> load for the procurement registers, by reusing the existing register loaders (suppliers, requisitions,
purchase orders [register profile], finance handover, branch master), then read what they hold. Source files are stored untouched
by the loaders' own staging; nothing is invented: a missing PO total stays missing (never 0)."""
import hashlib
from decimal import Decimal
from io import BytesIO

from openpyxl import load_workbook
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.analysis import AnalysisError, UploadResult
from app.core.cleaning.normalizers import normalize_text
from app.core.ingestion.pipeline import DuplicateUploadError, stage_file, validate_batch
from app.core.modules.loader import get_loader
from app.core.modules.registry import get_registry
from app.core.system_seed import ensure_system_branches
from app.models import (
    DataException,
    DimBranch,
    DimSupplier,
    FinanceHandover,
    ImportBatch,
    PoHeader,
    Requisition,
)

# normalised sheet title -> (loader module, profile). Loading order matters: master data first.
SHEETS = {
    "فروع بدايتي": ("branches", "default", 0), "سجل الموردين": ("suppliers", "default", 1), "اشعارات الاحتياج": ("requisitions", "default", 2),
    "اوامر الشراء": ("purchase_orders", "register", 3), "استلامات المالية": ("finance_handover", "default", 4),
}
MODULES = ("branches", "suppliers", "requisitions", "purchase_orders", "finance_handover")
ZERO = Decimal(0)


def _sheets(content: bytes) -> list[str]:
    wb = load_workbook(BytesIO(content), read_only=True)
    return [ws.title for ws in wb.worksheets]


def recognise(content: bytes) -> list[tuple[str, str, str]]:
    """[(sheet title, loader module, profile)] in load order."""
    found = []
    for t in _sheets(content):
        key = normalize_text(t)
        for name, (mod, prof, order) in SHEETS.items():
            if normalize_text(name) == key:
                found.append((order, t, mod, prof))
    return [(t, m, p) for _o, t, m, p in sorted(found)]


def ingest(session: Session, content: bytes, filename: str, user: str | None, options: dict) -> UploadResult:
    if not filename.lower().endswith((".xlsx", ".xlsm")):
        raise AnalysisError(400, "Upload the procurement register workbook (Excel)")
    try:
        todo = recognise(content)
    except Exception as exc:
        raise AnalysisError(400, "The file is not a readable Excel workbook") from exc
    if not todo:
        raise AnalysisError(422, "No procurement register sheet recognised (expected: suppliers, requisitions, purchase orders, finance handover, or the branch master)")
    reg = get_registry()
    ensure_system_branches(session)
    done, dup = [], 0
    for sheet, module, profile in todo:
        spec = reg.get(module)
        try:
            batch, _t = stage_file(session, spec, filename, content, sheet=sheet, created_by=user, profile=profile)
        except DuplicateUploadError:
            dup += 1
            continue
        validate_batch(session, spec, batch)
        get_loader(module).load(session, batch)
        session.refresh(batch)
        done.append({"sheet": sheet, "module": module, "rows": batch.rows_total, "valid": batch.rows_valid, "loaded": batch.rows_loaded, "held": batch.rows_held,
                     "status": batch.status})
    if not done:
        raise AnalysisError(409, {"message": "This exact file was already loaded", "dataset_id": "all"})
    return UploadResult("all", {"id": "all", "module": "procurement", "label": filename, "loaded": done, "already_loaded_sheets": dup,
                                "sha256": hashlib.sha256(content).hexdigest()[:16]})


# ------------------------------------------------------------------------------------------------ queries
def has_data(session: Session) -> bool:
    return session.scalar(select(PoHeader.id).limit(1)) is not None or session.scalar(select(Requisition.id).limit(1)) is not None


def load(session: Session) -> dict:
    sup = {s.id: s for s in session.scalars(select(DimSupplier))}
    branches = {b.id: b for b in session.scalars(select(DimBranch))}
    reqs = list(session.scalars(select(Requisition)))
    rq = {r.id: r for r in reqs}
    cancelled = {e.entity_key for e in session.scalars(select(DataException).where(DataException.code == "po_status_indicates_cancellation"))}
    pos = []
    for p in session.scalars(select(PoHeader)):
        r = rq.get(p.requisition_id)
        b = branches.get(p.branch_id)
        s = sup.get(p.supplier_id)
        pos.append({"id": p.id, "fy": p.fiscal_year, "number": p.number_source or f"{p.po_number}/{p.fiscal_year}", "date": p.po_date,
                    "supplier_id": p.supplier_id, "supplier": (s.name if s else p.supplier_name_source) or None, "total": p.total_amount and Decimal(str(p.total_amount)),
                    "po_category": p.po_category_source, "supplier_category": p.supplier_category_source or (s and getattr(s, "category_source", None)),
                    "order_status": p.order_status_source, "issuance_status": p.issuance_status_source,
                    "handed": Decimal(str(p.finance_handover_amount_register)) if p.finance_handover_amount_register is not None else None,
                    "remaining": Decimal(str(p.remaining_register)) if p.remaining_register is not None else None,
                    "requisition_id": p.requisition_id, "req_date": r.request_date if r else None, "department": r.department_source if r else None,
                    "branch_status": p.branch_attribution_status, "branch": (b.name_ar or b.name_en) if b and b.branch_type == "branch" else None,
                    "branch_type": b.branch_type if b else None, "cancelled": f"{p.fiscal_year}/{p.po_number}" in cancelled})
    memos = [{"id": m.id, "no": m.memo_no, "type": m.memo_type, "date": m.sent_date, "po_id": m.po_header_id, "po_ref": m.po_number_source,
              "supplier": m.supplier_name_source, "supplier_id": m.supplier_id, "category": m.purchase_category_source,
              "amount": Decimal(str(m.amount)) if m.amount is not None else None} for m in session.scalars(select(FinanceHandover))]
    requisitions = [{"id": r.id, "fy": r.fiscal_year, "number": r.number_source, "date": r.request_date, "department": r.department_source, "priority": r.priority_source,
                     "status": r.status_source} for r in reqs]
    batches = [{"module": b.module_id, "file": b.file_name, "sheet": b.sheet_name, "rows": b.rows_total, "valid": b.rows_valid, "loaded": b.rows_loaded, "held": b.rows_held,
                "status": b.status} for b in session.scalars(select(ImportBatch).where(ImportBatch.module_id.in_(MODULES), ImportBatch.status != "rolled_back").order_by(ImportBatch.id))]
    exc = [{"code": e.code, "severity": e.severity, "key": e.entity_key, "status": e.status} for e in session.scalars(select(DataException))]
    return {"pos": pos, "requisitions": requisitions, "memos": memos, "batches": batches, "exceptions": exc, "suppliers": len(sup)}
