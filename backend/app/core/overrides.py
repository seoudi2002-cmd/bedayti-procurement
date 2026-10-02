"""Correction (override) layer.

Rules: the source value is never overwritten and never lost. A correction records original value, corrected value,
reason, proposer, timestamp and review status; only an *approved* correction changes the working value of the
target record, and it is re-applied automatically whenever the record is re-loaded from source.

Targets are whitelisted (entity type → resolvable record + editable fields); anything else is refused.
"""
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.cleaning.normalizers import parse_date, parse_number
from app.core.exceptions import auto_resolve, reopen_system_resolved
from app.core.periods import ensure_period
from app.core.po_costs import sync_po_cost
from app.models import (
    DataOverride, DimBranch, DimSupplier, ExtractedLine, FactPoLine, FinanceHandover, ImportBatch, PoHeader, RawRow,
    Requisition,
)


class OverrideError(ValueError):
    pass


@dataclass(frozen=True)
class FieldRule:
    column: str
    type: str  # text | number | integer | date
    nullable: bool = True


@dataclass(frozen=True)
class Target:
    fields: dict[str, FieldRule]
    resolve: Callable[[Session, str], object | None]
    after_apply: Callable[[Session, object, str, str], None] | None = None  # (session, obj, field, key)
    original_hook: Callable[[object, str], str | None] | None = None  # source value when the column is NULL


def _split(key: str, sep: str = "/") -> tuple[int, str]:
    fy, _, num = key.partition(sep)
    return int(fy), num


def _po_header(session: Session, key: str):
    fy, num = _split(key)
    return session.scalar(select(PoHeader).where(PoHeader.fiscal_year == fy, PoHeader.po_number == num))


def _po_line(session: Session, key: str):
    head, _, line = key.partition("#")
    header = _po_header(session, head)
    return None if header is None else session.scalar(select(FactPoLine).where(
        FactPoLine.po_header_id == header.id, FactPoLine.line_number == int(line)))


def _requisition(session: Session, key: str):
    fy, num = _split(key)
    return session.scalar(select(Requisition).where(Requisition.fiscal_year == fy, Requisition.req_number == num))


def _handover(session: Session, key: str):
    return session.scalar(select(FinanceHandover).where(FinanceHandover.memo_no == int(key)))


def _extracted_line(session: Session, key: str):
    return session.get(ExtractedLine, int(key))


def _after_po_header(session: Session, header: PoHeader, field: str, key: str) -> None:
    """Refresh everything derived from the corrected value and close exceptions the correction answers."""
    note = "Resolved by an approved correction"
    if field == "po_date":
        header.period = ensure_period(session, header.po_date) if header.po_date is not None else None
        if header.po_date is not None:
            auto_resolve(session, "po_date_invalid", "po_header", key, note)
            auto_resolve(session, "po_date_missing", "po_header", key, note)
    if field == "supplier_id" and header.supplier_id is not None:
        for code in ("po_supplier_missing", "po_supplier_unresolved", "po_supplier_ambiguous_register_no",
                     "po_supplier_register_no_not_found"):
            auto_resolve(session, code, "po_header", key, note)
    if field == "total_amount" and header.total_amount is not None:
        auto_resolve(session, "po_total_missing", "po_header", key, note)
        auto_resolve(session, "po_total_invalid", "po_header", key, note)
    if field == "branch_id" and header.branch_id is not None:
        header.branch_attribution_status, header.branch_attribution_method = "confirmed", "manual_override"
        header.branch_source_text = "approved correction"
        auto_resolve(session, "po_branch_not_identified", "po_header", key, note)
        auto_resolve(session, "po_branch_evidence_conflict", "po_header", key, note)
    handed, total = header.finance_handover_amount_register, header.total_amount
    if field in ("total_amount", "finance_handover_amount_register") and handed is not None and total is not None \
            and Decimal(str(handed)) <= Decimal(str(total)) + Decimal("0.5"):
        auto_resolve(session, "finance_handover_amount_exceeds_total", "po_header", key, note)
    sync_po_cost(session, header)


def _after_po_line(session: Session, line: FactPoLine, field: str, key: str) -> None:
    if field in ("quantity", "unit_price") and field and line.quantity is not None and line.unit_price is not None \
            and field != "line_amount":
        pass  # the amount is a separate, explicit field: never recomputed silently
    header = session.get(PoHeader, line.po_header_id) if line.po_header_id else None
    if header is not None:
        from sqlalchemy import func
        header.lines_total = session.scalar(select(func.sum(FactPoLine.line_amount)).where(FactPoLine.po_header_id == header.id))
        from app.models import FactCost
        cost = session.scalar(select(FactCost).where(FactCost.module_id == "purchase_orders",
                                                     FactCost.source_ref == f"po_line:{line.id}"))
        if cost is not None:
            cost.amount, cost.branch_id = line.line_amount, line.branch_id
    if field == "branch_id" and line.branch_id is not None:
        line.branch_attribution_status, line.branch_attribution_method = "confirmed", "manual_override"


def _original_po_date(header: PoHeader, field: str) -> str | None:
    return header.po_date_source if field == "po_date" else None


TARGETS: dict[str, Target] = {
    "po_header": Target(
        fields={"po_date": FieldRule("po_date", "date"), "total_amount": FieldRule("total_amount", "number"),
                "supplier_id": FieldRule("supplier_id", "integer"), "branch_id": FieldRule("branch_id", "integer"),
                "finance_handover_amount_register": FieldRule("finance_handover_amount_register", "number"),
                "remaining_register": FieldRule("remaining_register", "number"),
                "requisition_no": FieldRule("requisition_no", "text")},
        resolve=_po_header, after_apply=_after_po_header, original_hook=_original_po_date),
    "po_line": Target(
        fields={"quantity": FieldRule("quantity", "number", False), "unit_price": FieldRule("unit_price", "number", False),
                "line_amount": FieldRule("line_amount", "number", False), "item_description": FieldRule("item_description", "text"),
                "branch_id": FieldRule("branch_id", "integer")},
        resolve=_po_line, after_apply=_after_po_line),
    "requisition": Target(fields={"request_date": FieldRule("request_date", "date")}, resolve=_requisition),
    "finance_handover": Target(
        fields={"amount": FieldRule("amount", "number"), "sent_date": FieldRule("sent_date", "date"),
                "po_number_source": FieldRule("po_number_source", "text")}, resolve=_handover),
    "extracted_line": Target(
        fields={"quantity": FieldRule("quantity", "number"), "unit_price": FieldRule("unit_price", "number"),
                "line_total": FieldRule("line_total", "number"), "description": FieldRule("description", "text")},
        resolve=_extracted_line),
}
REFERENCES = {"branch_id": DimBranch, "supplier_id": DimSupplier}  # corrected ids must exist


def parse_value(rule: FieldRule, text: str | None):
    if text is None or str(text).strip() == "":
        if not rule.nullable:
            raise OverrideError("a value is required for this field")
        return None
    try:
        if rule.type == "number":
            return parse_number(text)
        if rule.type == "integer":
            n = parse_number(text)
            if n != n.to_integral_value():
                raise OverrideError("a whole number is required")
            return int(n)
        if rule.type == "date":
            d = parse_date(text)
            if d is None or not (date(2015, 1, 1) <= d <= date.today().replace(year=date.today().year + 1)):
                raise OverrideError("date is empty or implausible")
            return d
    except (ValueError, InvalidOperation) as exc:
        raise OverrideError(str(exc)) from exc
    return str(text).strip()


def _text(value) -> str | None:
    if value is None:
        return None
    return value.isoformat() if isinstance(value, (date, datetime)) else str(value)


def _target(entity_type: str) -> Target:
    if entity_type not in TARGETS:
        raise OverrideError(f"Corrections are not available for '{entity_type}'. Allowed: {sorted(TARGETS)}")
    return TARGETS[entity_type]


def propose(session: Session, entity_type: str, entity_key: str, field: str, corrected: str | None, reason: str,
            user: str, auto_approve: bool = False) -> DataOverride:
    target = _target(entity_type)
    if field not in target.fields:
        raise OverrideError(f"Field '{field}' of {entity_type} cannot be corrected. Allowed: {sorted(target.fields)}")
    if not reason or not reason.strip():
        raise OverrideError("A reason is required")
    obj = target.resolve(session, entity_key)
    if obj is None:
        raise OverrideError(f"{entity_type} '{entity_key}' not found")
    rule = target.fields[field]
    value = parse_value(rule, corrected)
    if field in REFERENCES and value is not None and session.get(REFERENCES[field], value) is None:
        raise OverrideError(f"{field} {value} does not exist")
    first = session.scalar(select(DataOverride).where(
        DataOverride.entity_type == entity_type, DataOverride.entity_key == entity_key, DataOverride.field == field,
        DataOverride.status.in_(("approved", "superseded", "reverted"))).order_by(DataOverride.id))
    if first is not None:
        original = first.original_value  # the true source value, not the previous correction
    else:
        original = _text(getattr(obj, rule.column))
        if original is None and target.original_hook:
            original = target.original_hook(obj, field)
    row = DataOverride(entity_type=entity_type, entity_key=entity_key, field=field, value_type=rule.type,
                       original_value=original, corrected_value=_text(value), reason=reason.strip(), proposed_by=user)
    session.add(row)
    session.flush()
    if auto_approve:
        return approve(session, row.id, user, "auto-approved by proposer")
    session.commit()
    return row


def _apply(session: Session, row: DataOverride, obj, target: Target) -> None:
    rule = target.fields[row.field]
    setattr(obj, rule.column, parse_value(rule, row.corrected_value))
    if target.after_apply:
        target.after_apply(session, obj, row.field, row.entity_key)


def approve(session: Session, override_id: int, reviewer: str, note: str | None = None) -> DataOverride:
    row = session.get(DataOverride, override_id)
    if row is None:
        raise OverrideError("Correction not found")
    if row.status != "proposed":
        raise OverrideError(f"Only proposed corrections can be approved (status is {row.status})")
    if reviewer == row.proposed_by and not get_settings().allow_self_approval:
        raise OverrideError("A different user must approve this correction")
    if row.entity_type == "source_row":  # applied to the cleaned copy at the next (re)load of the batch
        row.status, row.reviewed_by, row.review_note = "approved", reviewer, note
        row.reviewed_at = row.applied_at = datetime.now(timezone.utc)
        session.commit()
        return row
    target = _target(row.entity_type)
    obj = target.resolve(session, row.entity_key)
    if obj is None:
        raise OverrideError("Target record no longer exists")
    for prev in session.scalars(select(DataOverride).where(
            DataOverride.entity_type == row.entity_type, DataOverride.entity_key == row.entity_key,
            DataOverride.field == row.field, DataOverride.status == "approved")):
        prev.status = "superseded"
    row.status, row.reviewed_by, row.review_note = "approved", reviewer, note
    row.reviewed_at = row.applied_at = datetime.now(timezone.utc)
    _apply(session, row, obj, target)
    session.commit()
    return row


def reject(session: Session, override_id: int, reviewer: str, note: str | None = None) -> DataOverride:
    row = session.get(DataOverride, override_id)
    if row is None or row.status != "proposed":
        raise OverrideError("Only proposed corrections can be rejected")
    row.status, row.reviewed_by, row.review_note = "rejected", reviewer, note
    row.reviewed_at = datetime.now(timezone.utc)
    session.commit()
    return row


def revert(session: Session, override_id: int, user: str, note: str | None = None) -> DataOverride:
    """Undo an approved correction: the original source value becomes the working value again."""
    row = session.get(DataOverride, override_id)
    if row is None or row.status != "approved":
        raise OverrideError("Only approved corrections can be reverted")
    if row.entity_type == "source_row":
        _restore_source_row(session, row)
        row.status, row.reviewed_by, row.review_note = "reverted", user, note
        row.reviewed_at = datetime.now(timezone.utc)
        session.commit()
        return row
    target = _target(row.entity_type)
    obj = target.resolve(session, row.entity_key)
    if obj is not None:
        rule = target.fields[row.field]
        try:
            restored = parse_value(rule, row.original_value)
        except OverrideError:
            restored = None  # the source value was itself invalid/empty (e.g. an implausible date): back to NULL
        setattr(obj, rule.column, restored)
        if target.after_apply:
            target.after_apply(session, obj, row.field, row.entity_key)
        reopen_system_resolved(session, "po_header" if row.entity_type == "po_header" else row.entity_type, row.entity_key)
    row.status, row.reviewed_by, row.review_note = "reverted", user, note
    row.reviewed_at = datetime.now(timezone.utc)
    session.commit()
    return row


def _restore_source_row(session: Session, ov: DataOverride) -> None:
    """Re-derive the cleaned value of the corrected cell from the untouched raw cell."""
    from app.core.ingestion.pipeline import _clean_value, _jsonable
    from app.core.modules.registry import get_registry
    module_id, file_prefix, number = ov.entity_key.split(":")
    batch = session.scalar(select(ImportBatch).where(ImportBatch.module_id == module_id,
                                                      ImportBatch.file_hash.like(file_prefix + "%")))
    row = session.scalar(select(RawRow).where(RawRow.batch_id == batch.id, RawRow.row_number == int(number))) if batch else None
    if row is None or row.cleaned is None:
        return
    schema = get_registry().get(module_id).schema_for(batch.profile)
    raw = next((row.payload.get(h) for h, f in (batch.column_map or {}).items() if f == ov.field), None)
    cleaned = dict(row.cleaned)
    try:
        cleaned[ov.field] = _jsonable(_clean_value(schema.field(ov.field), raw, schema))
    except ValueError:
        cleaned[ov.field] = None
    cleaned["_overrides"] = [o for o in cleaned.get("_overrides", []) if o.get("override_id") != ov.id]
    row.cleaned = cleaned


def reapply_approved(session: Session, entity_type: str, entity_key: str, obj) -> int:
    """Called by loaders after (re)writing a record from source so approved corrections are not lost."""
    target = TARGETS.get(entity_type)
    if target is None:
        return 0
    n = 0
    for row in session.scalars(select(DataOverride).where(
            DataOverride.entity_type == entity_type, DataOverride.entity_key == entity_key,
            DataOverride.status == "approved").order_by(DataOverride.id)):
        _apply(session, row, obj, target)
        n += 1
    return n


def history(session: Session, entity_type: str, entity_key: str) -> list[DataOverride]:
    return list(session.scalars(select(DataOverride).where(
        DataOverride.entity_type == entity_type, DataOverride.entity_key == entity_key).order_by(DataOverride.id)))


# ---------------------------------------------------------------- source-row corrections (held / rejected rows)
def row_key(batch: ImportBatch, row_number: int) -> str:
    return f"{batch.module_id}:{batch.file_hash[:12]}:{row_number}"


def propose_row_correction(session: Session, batch: ImportBatch, row_number: int, field: str, corrected: str,
                           reason: str, user: str) -> DataOverride:
    """Correct one cell of one staged source row (e.g. the PO number of a conflicting row). The raw row is untouched;
    the correction is applied to the *cleaned* copy when the batch is (re)loaded."""
    from app.core.ingestion.pipeline import _clean_value
    from app.core.modules.registry import get_registry
    spec = get_registry().get(batch.module_id)
    schema = spec.schema_for(batch.profile)
    if field not in {f.name for f in schema.fields}:
        raise OverrideError(f"Unknown field '{field}' for module {batch.module_id}")
    row = session.scalar(select(RawRow).where(RawRow.batch_id == batch.id, RawRow.row_number == row_number))
    if row is None:
        raise OverrideError("Row not found")
    if not reason.strip():
        raise OverrideError("A reason is required")
    try:
        _clean_value(schema.field(field), corrected, schema)
    except ValueError as exc:
        raise OverrideError(str(exc)) from exc
    original = next((row.payload.get(h) for h, f in (batch.column_map or {}).items() if f == field), None)
    ov = DataOverride(entity_type="source_row", entity_key=row_key(batch, row_number), field=field, value_type="text",
                      original_value=_text(original), corrected_value=str(corrected).strip(), reason=reason.strip(),
                      proposed_by=user)
    session.add(ov)
    session.commit()
    return ov


def apply_row_overrides(session: Session, batch: ImportBatch, rows: list[RawRow]) -> int:
    """Apply approved source-row corrections to the cleaned copies (raw payload is never touched)."""
    from app.core.ingestion.pipeline import _clean_value, _jsonable
    from app.core.modules.registry import get_registry
    schema = get_registry().get(batch.module_id).schema_for(batch.profile)
    prefix = f"{batch.module_id}:{batch.file_hash[:12]}:"
    ovs = list(session.scalars(select(DataOverride).where(
        DataOverride.entity_type == "source_row", DataOverride.entity_key.like(prefix + "%"),
        DataOverride.status == "approved").order_by(DataOverride.id)))
    n = 0
    for ov in ovs:
        number = int(ov.entity_key.rsplit(":", 1)[1])
        row = next((r for r in rows if r.row_number == number), None)
        if row is None or row.cleaned is None:
            continue
        cleaned = dict(row.cleaned)
        cleaned[ov.field] = _jsonable(_clean_value(schema.field(ov.field), ov.corrected_value, schema))
        cleaned["_overrides"] = [*cleaned.get("_overrides", []), {"field": ov.field, "override_id": ov.id}]
        row.cleaned = cleaned
        if row.status in ("held", "rejected"):
            row.status = "valid"  # the correction answers what held/rejected it; the loader re-checks everything
        n += 1
    return n
