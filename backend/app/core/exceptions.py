"""Raise and track business data exceptions (see models/quality.py).

raise_exception is an upsert on (code, entity_type, entity_key): re-running a load refreshes message/details
and last_seen_at but keeps a person's decision (accepted/dismissed/resolved) intact.
"""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DataException


def raise_exception(session: Session, code: str, severity: str, entity_type: str, entity_key: str, message: str,
                    details: dict | None = None, module_id: str | None = None, batch_id: int | None = None) -> DataException:
    row = session.scalar(select(DataException).where(
        DataException.code == code, DataException.entity_type == entity_type, DataException.entity_key == str(entity_key)))
    now = datetime.now(timezone.utc)
    if row is None:
        row = DataException(code=code, severity=severity, entity_type=entity_type, entity_key=str(entity_key),
                            message=message, details=details or {}, module_id=module_id, batch_id=batch_id,
                            status="open", last_seen_at=now)
        session.add(row)
    else:
        row.message, row.details, row.severity, row.last_seen_at = message, details or {}, severity, now
        row.batch_id = batch_id or row.batch_id
    return row


def decide_exception(session: Session, exception_id: int, status: str, decided_by: str | None, note: str | None) -> DataException:
    if status not in ("accepted", "resolved", "dismissed", "open"):
        raise ValueError("status must be accepted, resolved, dismissed or open")
    row = session.get(DataException, exception_id)
    if row is None:
        raise KeyError(exception_id)
    row.status, row.decided_by, row.decision_note = status, decided_by, note
    session.commit()
    return row


def auto_resolve(session: Session, code: str, entity_type: str, entity_key: str, note: str) -> None:
    """Close an exception the platform itself has seen disappear (e.g. a missing link now exists).
    Only open ones are touched; a person's earlier decision is left alone."""
    row = session.scalar(select(DataException).where(
        DataException.code == code, DataException.entity_type == entity_type,
        DataException.entity_key == str(entity_key), DataException.status == "open"))
    if row is not None:
        row.status, row.decided_by, row.decision_note = "resolved", "system", note
