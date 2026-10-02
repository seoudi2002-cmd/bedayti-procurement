import io
from pathlib import Path

import pytest
from openpyxl import Workbook
from sqlalchemy import select

from app.core.ingestion.pipeline import DuplicateUploadError, stage_file, validate_batch
from app.core.ingestion.readers import UnsupportedFileError, read_table
from app.core.mapping.engine import suggest_mapping
from app.models import RawRow, ValidationIssue

FIXTURE = Path(__file__).parent / "fixtures" / "po_sample.csv"


def _xlsx_with_title_rows() -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Data"
    ws.append(["Monthly PO report"])
    ws.append([])
    ws.append(["رقم أمر الشراء", "التاريخ", "الفرع", "المورد", "الكمية", "السعر"])
    ws.append(["PO-9", "01/02/2025", "فرع المعادي", "مورد", "٣", "١٠٫٥"])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_xlsx_header_detected_below_title_rows():
    t = read_table("r.xlsx", _xlsx_with_title_rows())
    assert t.header_row == 3 and t.headers[0] == "رقم أمر الشراء" and len(t.rows) == 1


def test_arabic_cp1256_csv():
    data = "الفرع,المورد\nالمعادي,مورد\n".encode("cp1256")
    t = read_table("a.csv", data)
    assert t.headers == ["الفرع", "المورد"] and t.rows[0][1]["الفرع"] == "المعادي"


def test_unsupported_extension():
    with pytest.raises(UnsupportedFileError):
        read_table("a.pdf", b"x")


def test_arabic_headers_map_to_fields(po_spec):
    t = read_table("r.xlsx", _xlsx_with_title_rows())
    m = suggest_mapping(t.headers, po_spec.schema_)
    assert m["رقم أمر الشراء"]["field"] == "po_number"
    assert m["الفرع"]["field"] == "branch" and m["السعر"]["field"] == "unit_price"


def test_csv_pipeline_validates_and_flags_bad_rows(session, po_spec):
    batch, table = stage_file(session, po_spec, "po_sample.csv", FIXTURE.read_bytes())
    assert batch.rows_total == 5 and batch.status == "staged"
    validate_batch(session, po_spec, batch, headers=table.headers)
    assert (batch.rows_valid, batch.rows_rejected) == (3, 2)
    rows = {r.row_number: r for r in session.scalars(select(RawRow).where(RawRow.batch_id == batch.id))}
    assert rows[3].cleaned["line_amount"] == "450.00" or rows[3].cleaned["line_amount"].startswith("450")  # derived
    codes = {(i.code, i.field) for i in session.scalars(select(ValidationIssue))}
    assert ("bad_value", "po_date") in codes and ("missing_required", "branch") in codes


def test_duplicate_upload_blocked(session, po_spec):
    stage_file(session, po_spec, "po_sample.csv", FIXTURE.read_bytes())
    with pytest.raises(DuplicateUploadError):
        stage_file(session, po_spec, "again.csv", FIXTURE.read_bytes())


def test_missing_required_column_rejects_all_rows(session, po_spec):
    batch, table = stage_file(session, po_spec, "x.csv", b"PO No,Qty\nP1,2\n")
    validate_batch(session, po_spec, batch, headers=table.headers)
    assert batch.rows_valid == 0
    assert any(i.code == "missing_column" for i in session.scalars(select(ValidationIssue)))


def test_revalidate_with_corrected_mapping_replaces_issues(session, po_spec):
    batch, table = stage_file(session, po_spec, "po_sample.csv", FIXTURE.read_bytes())
    validate_batch(session, po_spec, batch, headers=table.headers)
    first = len(session.scalars(select(ValidationIssue)).all())
    validate_batch(session, po_spec, batch, headers=table.headers)
    assert len(session.scalars(select(ValidationIssue)).all()) == first
