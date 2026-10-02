"""Helpers shared by module loaders."""
import re
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ImportBatch, RawRow

_REF = re.compile(r"^\s*(\d+)\s*/\s*(\d{4})\s*$")


def parse_number_year(text: object) -> tuple[str, int] | None:
    """'35/2026' -> ('35', 2026). None if the text is not in n/yyyy form (never guessed)."""
    m = _REF.match(str(text)) if text is not None else None
    return (str(int(m.group(1))), int(m.group(2))) if m else None


def date_from_json(value) -> date | None:
    return date.fromisoformat(value) if value else None


def rows_with_status(session: Session, batch: ImportBatch, statuses: tuple[str, ...]) -> list[RawRow]:
    return list(session.scalars(select(RawRow).where(
        RawRow.batch_id == batch.id, RawRow.status.in_(statuses)).order_by(RawRow.row_number)))


def raw_value(batch: ImportBatch, row: RawRow, field: str):
    """The untouched source cell behind a canonical field (audit trail)."""
    for header, fname in (batch.column_map or {}).items():
        if fname == field:
            return row.payload.get(header)
    return None


def flag_for(row: RawRow, field: str) -> dict | None:
    return next((f for f in (row.cleaned or {}).get("_flags", []) if f["field"] == field), None)
