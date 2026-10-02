"""stage → validate. Loading into facts is a per-module step (see core/modules/loader.py)."""
import hashlib
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.cleaning.normalizers import (
    clean_text, normalize_text, parse_bool, parse_date, parse_number,
)
from app.core.ingestion.readers import TableData, read_table
from app.core.mapping.engine import missing_required, suggest_mapping
from app.core.modules.spec import FieldSpec, ReportModuleSpec
from app.models.meta import ImportBatch, RawRow, ValidationIssue


class DuplicateUploadError(Exception):
    def __init__(self, batch_id: int):
        super().__init__(f"This exact file was already imported (batch {batch_id})")
        self.batch_id = batch_id


def _jsonable(v):
    if isinstance(v, (datetime,)) or hasattr(v, "isoformat"):
        return v.isoformat()
    if isinstance(v, Decimal):
        return str(v)
    return v


def stage_file(
    session: Session, spec: ReportModuleSpec, filename: str, content: bytes,
    sheet: str | None = None, header_row: int | None = None, created_by: str | None = None,
) -> tuple[ImportBatch, TableData]:
    """Store the file and its untouched rows. Nothing is cleaned or loaded yet."""
    module_id = spec.manifest.id
    file_hash = hashlib.sha256(content).hexdigest()
    dup = session.scalar(select(ImportBatch).where(
        ImportBatch.module_id == module_id, ImportBatch.file_hash == file_hash,
        ImportBatch.status != "rolled_back"))
    if dup:
        raise DuplicateUploadError(dup.id)
    table = read_table(filename, content, sheet, header_row)

    upload_dir = Path(get_settings().upload_dir) / module_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    storage = upload_dir / f"{file_hash[:16]}{Path(filename).suffix.lower()}"
    storage.write_bytes(content)

    batch = ImportBatch(
        module_id=module_id, file_name=Path(filename).name, file_hash=file_hash, storage_path=str(storage),
        sheet_name=table.sheet_name, status="staged", rows_total=len(table.rows), created_by=created_by)
    session.add(batch)
    session.flush()
    session.add_all(
        RawRow(batch_id=batch.id, sheet_name=table.sheet_name, row_number=n,
               payload={k: _jsonable(v) for k, v in row.items()})
        for n, row in table.rows)
    session.commit()
    return batch, table


def _clean_value(f: FieldSpec, raw, dayfirst: bool):
    """Return the cleaned value, or raise ValueError(code, message)."""
    if raw is None or (isinstance(raw, str) and raw.strip() == ""):
        return f.default
    if f.type == "text":
        return clean_text(raw)
    if f.type in ("number", "integer"):
        num = parse_number(raw)
        if num is None:
            return f.default
        if f.type == "integer":
            if num != num.to_integral_value():
                raise ValueError(f"expected a whole number, got {raw!r}")
            return int(num)
        if f.min is not None and float(num) < f.min:
            raise ValueError(f"{f.label} below minimum {f.min}: {num}")
        return num
    if f.type == "date":
        return parse_date(raw, dayfirst)
    if f.type == "bool":
        return parse_bool(raw)
    if f.type == "enum":
        text = clean_text(raw)
        by_norm = {normalize_text(v): v for v in f.allowed_values}
        if normalize_text(text) not in by_norm:
            raise ValueError(f"'{text}' is not one of {f.allowed_values}")
        return by_norm[normalize_text(text)]
    return raw


def validate_batch(
    session: Session, spec: ReportModuleSpec, batch: ImportBatch, column_map: dict[str, str] | None = None,
    headers: list[str] | None = None,
) -> ImportBatch:
    """Clean every staged row with the mapping, record issues, and set batch counts.

    column_map is {source_header: canonical_field}; when omitted the module's alias-based suggestion is used.
    Re-running replaces earlier results, so users can fix the mapping and retry.
    """
    schema = spec.schema_
    rows = session.scalars(select(RawRow).where(RawRow.batch_id == batch.id).order_by(RawRow.row_number)).all()
    if column_map is None:
        hdrs = headers or (list(rows[0].payload.keys()) if rows else [])
        column_map = {h: m["field"] for h, m in suggest_mapping(hdrs, schema).items()}
    session.execute(delete(ValidationIssue).where(ValidationIssue.batch_id == batch.id))

    def issue(row, severity, code, fld, msg):
        session.add(ValidationIssue(
            batch_id=batch.id, raw_row_id=row.id if row else None, severity=severity, code=code, field=fld, message=msg))

    unknown = sorted(set(column_map.values()) - {f.name for f in schema.fields})
    if unknown:
        raise ValueError(f"Mapping targets unknown fields: {unknown}")
    mapped = set(column_map.values())
    absent = missing_required(mapped, schema)
    if absent:
        issue(None, "error", "missing_column", None, f"Required columns not mapped: {', '.join(absent)}")

    valid = rejected = 0
    seen_keys: set = set()
    for row in rows:
        cleaned: dict = {}
        errors = 0
        for header, fname in column_map.items():
            f = schema.field(fname)
            try:
                cleaned[fname] = _clean_value(f, row.payload.get(header), schema.dayfirst)
            except ValueError as exc:
                errors += 1
                issue(row, "error", "bad_value", fname, str(exc))
        for f in schema.fields:
            if f.derive and cleaned.get(f.name) is None:
                parts = [cleaned.get(n) for n in f.derive["of"]]
                if all(p is not None for p in parts):
                    product = Decimal(1)
                    for p in parts:
                        product *= Decimal(p)
                    cleaned[f.name] = product
            if f.required and cleaned.get(f.name) is None:
                if f.name not in mapped and f.derive is None:
                    continue  # already reported once as a missing_column
                errors += 1
                issue(row, "error", "missing_required", f.name, f"{f.label} is required")
        key = tuple(cleaned.get(n) for n in schema.unique_key)
        if key and all(k is not None for k in key):
            if key in seen_keys:
                issue(row, "warning", "duplicate_key", None, f"Duplicate row key {key}")
            seen_keys.add(key)
        row.cleaned = {k: _jsonable(v) for k, v in cleaned.items()}
        row.status = "rejected" if errors or absent else "valid"
        valid += row.status == "valid"
        rejected += row.status == "rejected"

    batch.rows_valid, batch.rows_rejected = valid, rejected
    batch.status = "validated"
    session.commit()
    return batch
