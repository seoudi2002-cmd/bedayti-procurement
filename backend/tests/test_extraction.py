from decimal import Decimal

import pytest
from docx import Document
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core import overrides as ov
from app.core.extraction import classify, docx_reader, headers, service
from app.core.extraction import table as tbl
from app.core.extraction.table import Cell, RawTable
from app.db import get_session
from app.main import app
from app.models import (
    DataException, ExtractedDocument, ExtractedLine, FactPoLine, PoHeader,
    ProcurementDocument,
)
from tests.helpers import xlsx  # noqa: F401
from tests.scan_helpers import ROWS, fonts_available, make_po_scan
from tests.test_procurement_registers import base, headers as po_headers, po_book, po_row  # noqa: F401
from tests.test_master_data import run
from datetime import datetime

needs_ocr = pytest.mark.skipif(not fonts_available(), reason="tesseract/poppler/fonts not installed")


def C(text, conf=0.95):
    return Cell(text, conf)


def table_of(rows, roles=("seq", "description", "qty", "unit_price", "total"), total=None, basis=None):
    return RawTable(roles=list(roles), rows=[[C(x) for x in r] for r in rows], stated_total_raw=total, price_basis_text=basis)


# ---------------------------------------------------------------- parsing & validation
def test_header_roles_arabic_and_english():
    assert tbl.role_of_header("البيـان") == "description" or tbl.role_of_header("البيان") == "description"
    assert tbl.role_of_header("سعر الوحدة شامل الضريبة") == "unit_price"
    assert tbl.role_of_header("الإجمالي شامل الضريبة") == "total"
    assert tbl.role_of_header("وصف الوحدة") == "description"  # the item-description column on real POs
    assert tbl.role_of_header("الوحدة") == "unit"
    assert tbl.role_of_header("عدد الوحدات") == "qty"
    assert tbl.role_of_header("Qty") == "qty" and tbl.role_of_header("Unit Price") == "unit_price"
    assert tbl.role_of_header("م") == "seq" and tbl.role_of_header("Description") == "description"
    assert tbl.role_of_header("something else") is None


def test_parse_ocr_number_rules():
    p = tbl.parse_ocr_number
    assert p("1,870") == 1870 and p("677.950") == 677950 and p("1,640.35088") == Decimal("1640.35088")
    assert p("0.319") == Decimal("0.319")  # leading zero: a real decimal, not thousands
    assert p("-") is None and p("-", dash_zero=True) == 0  # a dash is zero only in a piaster cell
    assert p("٣٥٠") == 350 and p("abc") is None and p(None) is None


def test_lines_are_verified_or_flagged_never_fixed():
    t = table_of([("1", "Item A", "5", "100", "500"), ("2", "Item B", "2", "60", "60"),   # 2 x 60 != 60
                  ("3", "Item C", "", "50", "50"), ("4", "Item D", "4", "25", "100")], total="710")
    pt = tbl.lines_from_table(t)
    flags = [l.flags for l in pt.lines]
    assert "arithmetic_verified" in flags[0] and "arithmetic_mismatch" in flags[1]
    assert "unreadable_quantity" in flags[2] and pt.lines[2].quantity is None  # not guessed from 50/50
    assert pt.lines[1].line_total == 60  # the document's value is kept as read
    assert "table_total_verified" in pt.flags  # 500+60+50+100 = 710
    assert pt.lines[1].confidence <= 0.4 and pt.lines[0].confidence > 0.9


def test_dash_quantity_is_not_zero_and_foreign_currency_is_flagged():
    t = table_of([("1", "Security review", "-", "9,600", "9,600 دولار أمريكي")])
    ln = tbl.lines_from_table(t).lines[0]
    assert ln.quantity is None and "unreadable_quantity" in ln.flags and "non_egp_currency" in ln.flags


def test_adjustment_rows_are_kept_but_labelled_and_excluded_from_confirmation():
    t = table_of([("1", "Item A", "1", "100", "100"), ("", "", "", "", "14")], total="114")
    pt = tbl.lines_from_table(t)
    assert [l.kind for l in pt.lines] == ["item", "adjustment"] and "table_total_verified" in pt.flags


def test_row_sequence_gap_and_pound_piaster_columns():
    t = RawTable(roles=["seq", "description", "qty", "unit_price_pound", "unit_price_piaster", "total_pound", "total_piaster"],
                 rows=[[C("1"), C("A"), C("2"), C("10"), C("50"), C("21"), C("-")],
                       [C("3"), C("B"), C("1"), C("5"), C("-"), C("5"), C("-")]])
    pt = tbl.lines_from_table(t)
    assert pt.lines[0].unit_price == Decimal("10.5") and pt.lines[0].line_total == 21 and "arithmetic_verified" in pt.lines[0].flags
    assert "row_sequence_gap" in pt.flags


def test_price_basis_from_wording():
    assert tbl.lines_from_table(table_of([("1", "A", "1", "1", "1")], basis="الإجمالي شامل ضريبة القيمة المضافة")).price_basis == "incl_vat"
    assert tbl.lines_from_table(table_of([("1", "A", "1", "1", "1")], basis="السعر غير شامل الضريبة")).price_basis == "excl_vat"
    assert tbl.lines_from_table(table_of([("1", "A", "1", "1", "1")])).price_basis is None


def test_roles_inferred_by_arithmetic_when_headers_unreadable():
    cols = {0: [Decimal(1), Decimal(2), Decimal(3)], 1: [Decimal(5), Decimal(10), Decimal(2)],
            2: [Decimal(100), Decimal(50), Decimal(30)], 3: [Decimal(500), Decimal(500), Decimal(60)]}
    assert tbl.infer_numeric_roles(cols) == {1: "qty", 2: "unit_price", 3: "total", 0: "seq"}
    assert tbl.infer_numeric_roles({0: [Decimal(3), Decimal(9)], 1: [Decimal(4), Decimal(2)]}) == {}  # no triple: nothing invented


# ---------------------------------------------------------------- classification & headers
def test_classification_and_grouping():
    po = classify.classify_text("أمر شراء رقم ( 32 ) مكان التسليم المركز الرئيسي معدل التوريد دفعة واحدة سجل موردين رقم 6")
    assert po.doc_type == "purchase_order" and po.confidence > 0.8
    assert classify.classify_text("تابع أمر شراء رقم 32 المهمات مهلة التسليم غرامة التأخير").doc_type == "purchase_order_terms"
    assert classify.classify_text("السادة / لجنة المشتريات الموضوع شراء").doc_type == "committee_approval"
    assert classify.classify_text("إشعار الاحتياج REQUISITION الجهة الطالبة").doc_type == "requisition"
    assert classify.classify_text("نموذج فحص واستلام تم فحص ومعاينة").doc_type == "inspection_acceptance"
    assert classify.classify_text("lorem ipsum").doc_type == "unknown"
    # an attachments list must not turn a memo's last page into a PO
    assert classify.classify_text("مرفق أمر شراء رقم ( 32 )\nمرفق إشعار احتياج رقم 29").doc_type == "unknown"
    cls = [classify.classify_text(t) for t in ("السادة / لجنة المشتريات الموضوع", "lorem", "أمر شراء رقم 5 مكان التسليم معدل التوريد", "تابع أمر شراء رقم 5 المهمات مهلة التسليم")]
    assert classify.group_pages(cls) == [("committee_approval", 0, 1), ("purchase_order", 2, 3)]


def test_po_header_fields_keep_raw_text_and_confidence():
    lines = [headers.TextLine("1 ل ih : ( 32 ( : ش أمر شراء رقم", 0.76, 5), headers.TextLine("2026/ 05 / 19 : التاريخ", 0.8, 5),
             headers.TextLine("رقم الإشعار : ( 29 )", 0.9, 5), headers.TextLine("سجل موردين رقم 6", 0.9, 5)]
    h = headers.extract_po_header(lines)
    assert h["po_number"]["value"] == "32" and h["po_number"]["raw"].startswith("1 ل ih") and h["po_number"]["confidence"] == 0.76
    assert h["po_date"]["value"] == "2026-05-19" and h["requisition_no"]["value"] == "29" and h["supplier_register_no"]["value"] == "6"


# ---------------------------------------------------------------- native Word
def make_docx(path):
    d = Document()
    d.add_paragraph("التاريخ : 10 / 09 / 2025")
    d.add_paragraph("السيد الاستاذ / المدير المالي")
    d.add_paragraph("الموضوع : تحويل بنكي باسم / شركة اختبار")
    d.add_paragraph("في ضوء ماجاء بإشعار الإحتياج رقم ( 310) المعتمد وقد تم توريد الاجهزة")
    t = d.add_table(rows=4, cols=5)
    for i, h in enumerate(["م", "الكمية", "البيان", "سعر الوحدة شامل الضريبة", "الإجمالي شامل الضريبة"]):
        t.rows[0].cells[i].text = h
    for r, vals in enumerate([("1", "2", "Dell vostro 3530", "28100", "56,200"), ("2", "3", "DDR4 RAM", "2295", "6,885")], start=1):
        for i, v in enumerate(vals):
            t.rows[r].cells[i].text = v
    for i in range(5):
        t.rows[3].cells[i].text = "الإجمالي شامل الضريبة"
    t.rows[3].cells[4].text = "63,085"
    d.add_paragraph("لذا يرجي التكرم بالموافقة علي العرض المقدم من شركة اختبار بمبلغ وقدرة 63,085 جم")
    d.add_paragraph("مرفق أمر الشراء رقم (409)")
    d.add_paragraph("التاريخ : 16 / 09 / 2025")
    d.add_paragraph("السادة / لجنة المشتريات")
    d.add_paragraph("الموضوع : شراء خدمات")
    t2 = d.add_table(rows=3, cols=5)
    for i, h in enumerate(["م", "الكمية", "البيان", "سعر الوحدة غير شامل الضريبة", "الإجمالي غير شامل الضريبة"]):
        t2.rows[0].cells[i].text = h
    for i, v in enumerate(["1", "1", "Camera", "5,600", "5,600"]):
        t2.rows[1].cells[i].text = v
    t2.rows[2].cells[1].merge(t2.rows[2].cells[2]).text = "Installation and Programming"  # text merged over qty+description
    t2.rows[2].cells[0].text, t2.rows[2].cells[3].text, t2.rows[2].cells[4].text = "2", "1,000", "1,000"
    d.save(path)
    return path


def test_docx_memos_lines_and_merged_cells(tmp_path):
    memos = docx_reader.read_docx(make_docx(tmp_path / "m.docx"))
    assert len(memos) == 2
    h = headers.extract_memo_header(memos[0].lines)
    assert h["memo_date"]["value"] == "2025-09-10" and h["requisition_no"]["value"] == "310" and h["po_number"]["value"] == "409"
    assert h["stated_total"]["value"] == "63085"
    pt = tbl.lines_from_table(memos[0].tables[0])
    assert [(l.quantity, l.unit_price, l.line_total) for l in pt.lines] == [(2, 28100, 56200), (3, 2295, 6885)]
    assert "table_total_verified" in pt.flags and pt.price_basis == "incl_vat" and pt.stated_total == 63085
    pt2 = tbl.lines_from_table(memos[1].tables[0])
    assert pt2.price_basis == "excl_vat"
    merged = pt2.lines[1]
    assert merged.description == "Installation and Programming" and merged.quantity is None  # moved, and the missing qty is flagged
    assert "unreadable_quantity" in merged.flags


def test_docx_job_creates_documents_lines_and_links_by_po(tmp_path, session, base, monkeypatch):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "up"))
    from app.config import get_settings
    get_settings.cache_clear()
    rows = [po_row(1, "409/2025", datetime(2025, 9, 1), "Alpha Co", 1, "x", "310/2025", 63085)]
    run(session, "purchase_orders", po_book(rows), profile="register")
    path = make_docx(tmp_path / "m.docx")
    job = service.run_job(session, service.create_job(session, "m.docx", path.read_bytes(), "tester").id)
    assert job.status == "done", job.error
    docs = list(session.scalars(select(ExtractedDocument).order_by(ExtractedDocument.seq)))
    assert [d.doc_type for d in docs] == ["payment_request", "committee_approval"]
    assert docs[0].po_header_id is not None and docs[0].link_method == "po_number"  # memo cites PO 409 (year from memo date)
    assert docs[1].po_header_id is None
    assert session.scalar(select(func.count()).select_from(ExtractedLine)) == 4
    # a memo is a cross-check, never a source of PO lines
    with pytest.raises(service.ExtractionError, match="Only"):
        service.confirm_document(session, docs[0].id, "tester")
    get_settings.cache_clear()


# ---------------------------------------------------------------- scanned PDF end to end (real OCR)
@pytest.fixture
def scan_env(tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "up"))
    from app.config import get_settings
    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()


@needs_ocr
def test_scanned_po_is_read_validated_and_stays_a_proposal(scan_env, session, base):
    pdf = make_po_scan(scan_env / "scan.pdf", ROWS, "96,201.00")
    job = service.run_job(session, service.create_job(session, "scan.pdf", pdf.read_bytes(), "tester").id)
    assert job.status == "done", job.error
    assert job.engine == "tesseract" and job.page_count == 1
    doc = session.scalar(select(ExtractedDocument))
    assert doc.doc_type == "purchase_order" and "scanned_source_needs_review" in doc.flags
    assert "table_total_verified" in doc.flags and "header_missing_po_number" in doc.flags
    lines = list(session.scalars(select(ExtractedLine).order_by(ExtractedLine.line_no)))
    got = [(l.description, float(l.quantity), float(l.unit_price), float(l.line_total)) for l in lines]
    assert got == [("Laptop Dell 15", 3, 28100, 84300), ("Wireless Mouse", 10, 150, 1500),
                   ("HDMI Cable 2m", 20, 95, 1900), ("UPS 1000VA", 2, 4250.5, 8501)]
    assert all("arithmetic_verified" in l.flags and l.status == "extracted" for l in lines)
    assert all(l.description_raw and l.quantity_raw and l.bbox and l.page_no == 1 for l in lines)  # as-read + position kept
    assert all(l.branch_attribution_status == "needs_review" and l.branch_id is None for l in lines)  # no branch invented
    assert session.scalar(select(func.count()).select_from(FactPoLine)) == 0  # nothing is a fact before confirmation
    assert any(e.code == "extraction_po_not_in_register" for e in session.scalars(select(DataException)))
    original = (scan_env / "up" / "documents" / (job.file_id and next(iter((scan_env / "up" / "documents").iterdir())).name)).read_bytes()
    assert original == pdf.read_bytes()  # the stored original is byte-identical


@needs_ocr
def test_confirm_flow_with_review_corrections_and_lineage(scan_env, session, base):
    run(session, "purchase_orders", po_book([po_row(1, "12/2026", datetime(2026, 5, 1), "Alpha Co", 1, "x", "12/2026", 96201)]),
        profile="register")
    rows = list(ROWS)
    rows[1] = ("Wireless Mouse", "10", "150", "1800")  # printed total is wrong on the document: 10 x 150 = 1500
    pdf = make_po_scan(scan_env / "scan.pdf", rows, "96,501.00")
    service.run_job(session, service.create_job(session, "scan.pdf", pdf.read_bytes(), "tester").id)
    doc = session.scalar(select(ExtractedDocument))
    bad = session.scalar(select(ExtractedLine).where(ExtractedLine.line_no == 2))
    assert "arithmetic_mismatch" in bad.flags and float(bad.line_total) == 1800  # kept as printed, flagged
    service.link_document(session, doc.id, 2026, "12", "tester")
    assert doc.po_header_id is not None and doc.link_method == "manual"
    # correction with a reason; the as-read value is preserved on the line and in the correction record
    c = ov.propose(session, "extracted_line", str(bad.id), "line_total", "1500", "total on the PO is a typo: 10 x 150", "tester", auto_approve=True)
    session.refresh(bad)
    assert float(bad.line_total) == 1500 and bad.line_total_raw == "1800" and float(c.original_value) == 1800
    written = service.confirm_document(session, doc.id, "tester")
    assert len(written) == 4 and doc.status == "confirmed"
    header = session.scalar(select(PoHeader).where(PoHeader.po_number == "12"))
    assert header.granularity == "lines" and float(header.lines_total) == 96201 and float(header.total_amount) == 96201
    pl = session.scalar(select(FactPoLine).where(FactPoLine.po_header_id == header.id, FactPoLine.line_number == 2))
    assert (pl.source_kind, pl.extracted_line_id, float(pl.line_amount)) == ("document_extraction", bad.id, 1500)
    assert bad.po_line_id == pl.id and bad.status == "confirmed"
    from app.core.kpi.engine import compute_kpi
    from app.core.modules.registry import get_registry
    assert compute_kpi(session, get_registry().get("purchase_orders"), "total_spend")[None] == 96201  # lines replace the header row
    assert session.scalar(select(func.count()).select_from(ProcurementDocument).where(ProcurementDocument.file_id.is_not(None))) == 1
    env = session.scalar(select(ProcurementDocument).where(ProcurementDocument.file_id.is_not(None)))
    assert (env.doc_type, env.page_from, env.page_to, env.status) == ("purchase_order", 1, 1, "confirmed")


@needs_ocr
def test_confirm_refuses_incomplete_lines_and_allows_rejection(scan_env, session, base):
    run(session, "purchase_orders", po_book([po_row(1, "13/2026", datetime(2026, 5, 1), "Alpha Co", 1, "x", "13/2026", 100)]), profile="register")
    pdf = make_po_scan(scan_env / "scan.pdf", ROWS[:2], "1,650.00")
    service.run_job(session, service.create_job(session, "scan.pdf", pdf.read_bytes(), "t").id)
    doc = session.scalar(select(ExtractedDocument))
    service.link_document(session, doc.id, 2026, "13", "t")
    ln = session.scalar(select(ExtractedLine).where(ExtractedLine.line_no == 2))
    ln.quantity = None  # simulate an unreadable value
    session.commit()
    with pytest.raises(service.ExtractionError, match="incomplete"):
        service.confirm_document(session, doc.id, "t")
    service.set_line_status(session, ln.id, "rejected")
    written = service.confirm_document(session, doc.id, "t")
    assert len(written) == 1


@needs_ocr
def test_second_document_for_same_po_needs_explicit_replace(scan_env, session, base):
    run(session, "purchase_orders", po_book([po_row(1, "14/2026", datetime(2026, 5, 1), "Alpha Co", 1, "x", "14/2026", 100)]), profile="register")
    for name, rows, total in (("a.pdf", ROWS[:2], "1,650.00"), ("b.pdf", ROWS[2:], "10,401.00")):
        pdf = make_po_scan(scan_env / name, rows, total)
        service.run_job(session, service.create_job(session, name, pdf.read_bytes(), "t").id)
    d1, d2 = session.scalars(select(ExtractedDocument).order_by(ExtractedDocument.id)).all()
    service.link_document(session, d1.id, 2026, "14", "t")
    service.link_document(session, d2.id, 2026, "14", "t")
    service.confirm_document(session, d1.id, "t")
    with pytest.raises(service.ExtractionError, match="replace"):
        service.confirm_document(session, d2.id, "t")
    assert len(service.confirm_document(session, d2.id, "t", replace=True)) == 2
    assert session.scalar(select(func.count()).select_from(FactPoLine)) == 2


# ---------------------------------------------------------------- API
@pytest.fixture
def api(session, scan_env):
    app.dependency_overrides[get_session] = lambda: (yield session)
    yield TestClient(app)
    app.dependency_overrides.clear()


@needs_ocr
def test_extraction_api_roundtrip(api, session, base, scan_env):
    run(session, "purchase_orders", po_book([po_row(1, "15/2026", datetime(2026, 5, 1), "Alpha Co", 1, "x", "15/2026", 1650)]), profile="register")
    pdf = make_po_scan(scan_env / "s.pdf", ROWS[:2], "1,650.00")
    r = api.post("/api/extraction/jobs", params={"wait": True}, files={"file": ("s.pdf", pdf.read_bytes())})
    assert r.status_code == 202 and r.json()["status"] == "done"
    job = api.get(f"/api/extraction/jobs/{r.json()['job_id']}").json()
    doc = job["documents"][0]
    assert doc["doc_type"] == "purchase_order" and doc["lines"] == 2
    detail = api.get(f"/api/extraction/documents/{doc['id']}").json()
    first = detail["line_items"][0]
    assert first["as_read"]["quantity"] == "3" and first["parsed"]["quantity"] == 3 and first["confidence"] > 0.8
    assert api.get(f"/api/extraction/jobs/{job['id']}/pages/1/image").headers["content-type"] == "image/png"
    assert api.post(f"/api/extraction/documents/{doc['id']}/confirm", json={}).status_code == 422  # not linked yet
    assert api.post(f"/api/extraction/documents/{doc['id']}/link", json={"fiscal_year": 2026, "po_number": "15"}).status_code == 200
    # correction through the generic corrections endpoint, with reason and review status
    fix = api.post("/api/corrections", json={"entity_type": "extracted_line", "entity_key": str(detail["line_items"][1]["id"]),
                                             "field": "description", "corrected_value": "Wireless Mouse (corrected)", "reason": "typo"})
    assert fix.status_code == 201 and fix.json()["status"] == "proposed"
    api.post(f"/api/corrections/{fix.json()['id']}/approve", json={})
    ok = api.post(f"/api/extraction/documents/{doc['id']}/confirm", json={})
    assert ok.status_code == 200 and ok.json()["po_lines_written"] == 2
    again = api.get(f"/api/extraction/documents/{doc['id']}").json()
    assert again["status"] == "confirmed" and again["line_items"][1]["parsed"]["description"] == "Wireless Mouse (corrected)"
    assert again["line_items"][1]["as_read"]["description"] == "Wireless Mouse"  # original wording kept
    assert api.post("/api/extraction/jobs", files={"file": ("x.txt", b"hi")}).status_code == 415


def test_extraction_requires_analyst_role(session, monkeypatch):
    from app.config import get_settings
    monkeypatch.setenv("API_TOKENS", "v:viewer:v,a:analyst:a")
    get_settings.cache_clear()
    app.dependency_overrides[get_session] = lambda: (yield session)
    try:
        c = TestClient(app)
        assert c.get("/api/extraction/jobs", headers={"Authorization": "Bearer v"}).status_code == 403
        assert c.get("/api/extraction/jobs", headers={"Authorization": "Bearer a"}).status_code == 200
    finally:
        app.dependency_overrides.clear()
        monkeypatch.delenv("API_TOKENS")
        get_settings.cache_clear()


# ---------------------------------------------------------------- cross-document check
def test_cross_check_reports_agreement_and_differences(session, base):
    run(session, "purchase_orders", po_book([po_row(1, "20/2026", datetime(2026, 5, 1), "Alpha Co", 1, "x", "20/2026", 300)]), profile="register")
    po = session.scalar(select(PoHeader).where(PoHeader.po_number == "20"))
    from app.models import DocumentFile, ExtractionJob
    f = DocumentFile(file_name="f.pdf", sha256="0" * 64)
    session.add(f)
    session.flush()
    job = ExtractionJob(file_id=f.id, status="done")
    session.add(job)
    session.flush()

    def doc(dtype, lines, stated=None):
        d = ExtractedDocument(job_id=job.id, seq=1, doc_type=dtype, page_from=1, page_to=1, po_header_id=po.id,
                              header={"stated_total": {"value": stated}} if stated else {})
        session.add(d)
        session.flush()
        for i, (q, t) in enumerate(lines, start=1):
            session.add(ExtractedLine(extracted_document_id=d.id, line_no=i, description=f"item {i}", quantity=q, line_total=t, flags=[]))
        session.flush()
        return d

    doc("purchase_order", [(2, 100), (4, 200)])
    memo_ok = doc("committee_approval", [(4, 200), (2, 100)], "300")           # same lines, different order
    memo_bad = doc("payment_request", [(2, 100), (5, 250)], "350")             # one line differs
    out = service.cross_check(session, po.id)
    assert out["reference_total"] == 300 and out["reference_matches_register"] is True
    by = {d["document_id"]: d for d in out["documents"]}
    assert by[memo_ok.id]["total_matches_po"] and by[memo_ok.id]["lines_matched_to_po"] == 2
    bad = by[memo_bad.id]
    assert not bad["total_matches_po"] and bad["lines_matched_to_po"] == 1
    assert bad["lines_only_in_this_document"][0]["amount"] == 250 and bad["po_lines_missing_here"][0]["amount"] == 200
