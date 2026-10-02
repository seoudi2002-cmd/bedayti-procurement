"""stage → validate. Loading into facts is a per-module step (see core/modules/loader.py).

Principles: the source is never modified (raw_row.payload is immutable); every transformation is recorded
(cleaned values, fill-downs, flags, skipped rows); bad cells either reject the row or are flagged with NULL,
never silently "fixed".
"""
import hashlib
import re
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.cleaning.normalizers import (
    clean_text, excel_error, normalize_text, parse_bool, parse_date, parse_number, text_from_cell,
)
from app.core.ingestion.readers import TableData, read_table
from app.core.mapping.engine import missing_required, suggest_mapping
from app.core.modules.spec import FieldSpec, ModuleSchema, ReportModuleSpec
from app.core.periods import fiscal_year
from app.models.meta import ImportBatch, RawRow, ValidationIssue


class DuplicateUploadError(Exception):
    def __init__(self, batch_id: int):
        super().__init__(f"This exact file was already imported (batch {batch_id})")
        self.batch_id = batch_id


def _jsonable(v):
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, Decimal):
        return str(v)
    if isinstance(v, list):
        return [_jsonable(x) for x in v]
    if isinstance(v, dict):
        return {k: _jsonable(x) for k, x in v.items()}
    return v


def stage_file(
    session: Session, spec: ReportModuleSpec, filename: str, content: bytes,
    sheet: str | None = None, header_row: int | None = None, created_by: str | None = None,
    profile: str = "default",
) -> tuple[ImportBatch, TableData]:
    """Store the file and its untouched rows. Nothing is cleaned or loaded yet."""
    schema = spec.schema_for(profile)
    module_id = spec.manifest.id
    file_hash = hashlib.sha256(content).hexdigest()
    dup = session.scalar(select(ImportBatch).where(
        ImportBatch.module_id == module_id, ImportBatch.file_hash == file_hash,
        ImportBatch.profile == profile, ImportBatch.status != "rolled_back"))
    if dup:
        raise DuplicateUploadError(dup.id)
    table = read_table(filename, content, sheet, header_row or schema.header_row, sheet_hint=schema.sheet)

    upload_dir = Path(get_settings().upload_dir) / module_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    storage = upload_dir / f"{file_hash[:16]}{Path(filename).suffix.lower()}"
    storage.write_bytes(content)

    batch = ImportBatch(
        module_id=module_id, profile=profile, file_name=Path(filename).name, file_hash=file_hash,
        storage_path=str(storage), sheet_name=table.sheet_name, status="staged", rows_total=len(table.rows),
        created_by=created_by)
    session.add(batch)
    session.flush()
    session.add_all(
        RawRow(batch_id=batch.id, sheet_name=table.sheet_name, row_number=n,
               payload={k: _jsonable(v) for k, v in row.items()})
        for n, row in table.rows)
    session.commit()
    return batch, table


def _in_bounds(d: date, schema: ModuleSchema) -> bool:
    low = date.fromisoformat(schema.plausible_from)
    return low <= d <= date.today() + timedelta(days=schema.plausible_days_ahead)


def _clean_value(f: FieldSpec, raw, schema: ModuleSchema):
    """Return the cleaned value, or raise ValueError(message)."""
    if raw is None or (isinstance(raw, str) and raw.strip() == ""):
        return f.default
    if f.value_map:
        text = clean_text(raw)
        by_norm = {normalize_text(k): v for k, v in f.value_map.items()}
        if normalize_text(text) not in by_norm:
            raise ValueError(f"'{text}' is not a known value for {f.label} {sorted(f.value_map)}")
        return by_norm[normalize_text(text)]
    if f.type == "text":
        return text_from_cell(raw)
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
        d = parse_date(raw, schema.dayfirst)
        if d is not None and not _in_bounds(d, schema):
            raise ValueError(f"implausible date {d.isoformat()} (outside {schema.plausible_from} .. today+{schema.plausible_days_ahead}d)")
        return d
    if f.type == "bool":
        return parse_bool(raw)
    if f.type == "enum":
        text = clean_text(raw)
        by_norm = {normalize_text(v): v for v in f.allowed_values}
        if normalize_text(text) not in by_norm:
            raise ValueError(f"'{text}' is not one of {f.allowed_values}")
        return by_norm[normalize_text(text)]
    return raw


def _blank(v) -> bool:
    return v is None or (isinstance(v, str) and v.strip() == "")


def validate_batch(
    session: Session, spec: ReportModuleSpec, batch: ImportBatch, column_map: dict[str, str] | None = None,
    headers: list[str] | None = None,
) -> ImportBatch:
    """Clean every staged row with the mapping, record issues, and set batch counts.

    column_map is {source_header: canonical_field}; when omitted the module's alias-based suggestion is used.
    Re-running replaces earlier results, so users can fix the mapping and retry.
    """
    schema = spec.schema_for(batch.profile)
    rows = session.scalars(select(RawRow).where(RawRow.batch_id == batch.id).order_by(RawRow.row_number)).all()
    if column_map is None:
        hdrs = headers or (list(rows[0].payload.keys()) if rows else [])
        column_map = {h: m["field"] for h, m in suggest_mapping(hdrs, schema).items()}
    session.execute(delete(ValidationIssue).where(ValidationIssue.batch_id == batch.id))
    batch.column_map = column_map

    def issue(row, severity, code, fld, msg):
        session.add(ValidationIssue(
            batch_id=batch.id, raw_row_id=row.id if row else None, severity=severity, code=code, field=fld, message=msg))

    unknown = sorted(set(column_map.values()) - {f.name for f in schema.fields})
    if unknown:
        raise ValueError(f"Mapping targets unknown fields: {unknown}")
    mapped = set(column_map.values())
    header_of: dict[str, str] = {}
    for h, fname in column_map.items():
        header_of.setdefault(fname, h)
    absent = missing_required(mapped, schema)
    if absent:
        issue(None, "error", "missing_column", None, f"Required columns not mapped: {', '.join(absent)}")

    keep_re = re.compile(schema.row_filter.regex) if schema.row_filter else None
    last: dict[str, object] = {}
    valid = rejected = skipped = 0
    seen_keys: set = set()
    for row in rows:
        values = dict(row.payload)
        if keep_re is not None:
            cell = values.get(header_of.get(schema.row_filter.field, ""))
            if _blank(cell) or not keep_re.fullmatch(str(cell).strip()):
                row.status, row.cleaned = "skipped", None
                issue(row, "info", "skipped_non_data_row", schema.row_filter.field,
                      "Row does not look like a data row (e.g. subtotal/heading)")
                skipped += 1
                continue
        filled: list[str] = []
        for fd in schema.fill_down:  # merged cells: carry the group's value down, never across groups
            h = header_of.get(fd.field)
            if h is None:
                continue
            if fd.reset_on and not _blank(row.payload.get(header_of.get(fd.reset_on, ""))):  # a NEW group starts only on a real source value
                last[fd.field] = None
            if _blank(values.get(h)):
                if last.get(fd.field) is not None:
                    values[h] = last[fd.field]
                    filled.append(fd.field)
            else:
                last[fd.field] = values[h]

        cleaned: dict = {}
        flags: list[dict] = []
        errors = 0
        for header, fname in column_map.items():
            f = schema.field(fname)
            raw = values.get(header)
            err = excel_error(raw)
            try:
                if err:
                    flags.append({"field": fname, "code": "source_error", "message": f"cell holds {err}", "raw": err})
                    issue(row, "warning", "source_error", fname, f"Source cell holds an Excel error value {err}")
                    cleaned[fname] = None
                    continue
                cleaned[fname] = _clean_value(f, raw, schema)
            except ValueError as exc:
                if f.on_invalid == "flag":
                    cleaned[fname] = None
                    flags.append({"field": fname, "code": "invalid_value", "message": str(exc), "raw": _jsonable(raw)})
                    issue(row, "warning", "flagged_value", fname, str(exc))
                else:
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
        fy_field = schema.fiscal_year_field
        if fy_field and cleaned.get(fy_field) is None and schema.date_field and cleaned.get(schema.date_field):
            cleaned[fy_field] = fiscal_year(cleaned[schema.date_field])
        key = tuple(cleaned.get(n) for n in schema.unique_key)
        if key and all(k is not None for k in key):
            if key in seen_keys:
                issue(row, "warning", "duplicate_key", None, f"Duplicate row key {key}")
            seen_keys.add(key)
        if flags:
            cleaned["_flags"] = flags
        if filled:
            cleaned["_filled_down"] = filled
        row.cleaned = _jsonable(cleaned)
        row.status = "rejected" if errors or absent else "valid"
        valid += row.status == "valid"
        rejected += row.status == "rejected"

    batch.rows_valid, batch.rows_rejected, batch.rows_skipped = valid, rejected, skipped
    batch.status = "validated"
    session.commit()
    return batch
