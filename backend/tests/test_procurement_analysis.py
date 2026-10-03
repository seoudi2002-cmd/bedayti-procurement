from datetime import datetime
from decimal import Decimal
from functools import lru_cache

import pytest

from app.core.analysis import AnalysisError
from app.core.reporting.excel import ExcelExporter
from app.core.reporting.pdf import PdfExporter
from app.core.settings_store import effective_thresholds
from app.modules.procurement_analysis import engine, service
from app.modules.procurement_analysis.adapter import ProcurementAdapter
from tests.helpers import HANDOVER_HEADER, PO_HEADER, REQ_HEADER, branch_workbook, xlsx
from tests.test_copier_analysis import api, auth
from tests.test_procurement_registers import (
    base,
    ho_row,
    po_row,
    req_row,
)


@lru_cache(maxsize=None)
def register_book(extra_sheet=False):   # cached: a re-saved workbook embeds a timestamp, which made the same-file-twice assertions flaky
    reqs = [req_row(1, "1/2026", datetime(2026, 1, 5), "IT"), req_row(2, "2/2026", datetime(2026, 1, 6), "Admin"),
            req_row(3, "3/2026", datetime(2026, 2, 3), "IT"), req_row(4, "4/2026", datetime(2026, 2, 4), "Admin")]
    pos = [po_row(1, "1/2026", datetime(2026, 1, 12), "Alpha Co", 1, "x", "1/2026", 1000, 1000, status="مكتمل وتم السداد"),
           po_row(2, "2/2026", datetime(2026, 1, 20), "Beta Co", 2, "x", "2/2026", 500, 200),
           po_row(3, "3/2026", datetime(2026, 2, 10), "Alpha Co", 1, "x", "3/2026", None),
           po_row(4, "4/2026", datetime(2026, 2, 11), "Beta Co", 2, "x", "9/2026", 300, 400, status="الطلب ملغي")]
    memos = [ho_row(1, "امر شراء", datetime(2026, 1, 25), "1/2026", "Alpha Co", "x", 1000), ho_row(2, "امر شراء", datetime(2026, 2, 20), "2/2026", "Beta Co", "x", 200),
             ho_row(3, "خدمات", datetime(2026, 1, 22), None, "Svc Ltd", "صيانة", 50)]
    sheets = {"اشعارات الاحتياج": [REQ_HEADER, *reqs], "اوامر الشراء": [PO_HEADER, *pos], "استلامات المالية": [HANDOVER_HEADER, *memos]}
    if extra_sheet:
        sheets["ورقة غير معروفة"] = [["a", "b"], [1, 2]]
    return xlsx(sheets)


@pytest.fixture
def loaded(session, base):
    ad = ProcurementAdapter()
    r = ad.ingest(session, register_book(), "register.xlsx", "bob", {})
    return ad, r


def test_recognises_sheets_in_load_order_and_ignores_unknown_ones():
    got = service.recognise(register_book(extra_sheet=True))
    assert [m for _s, m, _p in got] == ["requisitions", "purchase_orders", "finance_handover"] and got[1][2] == "register"
    assert [m for _s, m, _p in service.recognise(branch_workbook())] == ["branches"]
    assert service.recognise(xlsx({"other": [["a"], [1]]})) == []


def test_ingest_loads_through_the_existing_loaders_and_rejects_repeats_and_unknown_files(session, base):
    ad = ProcurementAdapter()
    r = ad.ingest(session, register_book(), "register.xlsx", "bob", {})
    assert r.item_id == "all" and [(x["module"], x["loaded"]) for x in r.meta["loaded"]] == [("requisitions", 4), ("purchase_orders", 4), ("finance_handover", 3)]
    with pytest.raises(AnalysisError) as e:
        ad.ingest(session, register_book(), "again.xlsx", "bob", {})
    assert e.value.status == 409
    with pytest.raises(AnalysisError) as e:
        ad.ingest(session, xlsx({"other": [["a"], [1]]}), "x.xlsx", "bob", {})
    assert e.value.status == 422
    with pytest.raises(AnalysisError) as e:
        ad.ingest(session, b"x", "x.pdf", "bob", {})
    assert e.value.status == 400


def test_totals_months_suppliers_and_flows(loaded, session):
    ad, _ = loaded
    rm, a = ad.build(session, "all", "en", True, {})
    t = a["totals"]
    assert (t["po_n"], t["priced_n"], t["unpriced_n"], t["spend"], t["suppliers_n"]) == (4, 3, 1, Decimal(1800), 2)      # the unpriced PO is a PO, not 0 spend
    assert t["avg_po"] == Decimal(600) and (t["cancelled_n"], t["cancelled_value"]) == (1, Decimal(300))              # cancelled is kept, flagged and shown apart
    assert (t["req_n"], t["req_with_po_n"]) == (4, 3) and t["req_conversion_pct"] == 75.0
    assert (t["memo_n"], t["memo_po_amount"], t["memo_service_amount"], t["memo_amount"]) == (3, Decimal(1200), Decimal(50), Decimal(1250))
    assert t["handed_register"] == Decimal(1600)
    jan, feb = a["months"][0], a["months"][1]
    assert (jan["po_n"], jan["po_value"], feb["po_n"], feb["po_value"]) == (2, Decimal(1500), 2, Decimal(300))
    assert feb["d_value"] == Decimal(-1200) and feb["d_value_pct"] == -80.0
    assert feb["partial"] is True and jan["partial"] is False      # the data ends on 20 Feb: February is flagged incomplete
    assert a["months"][-1]["period"] == (2026, 2)
    assert [s["key"] for s in a["suppliers"]][:2] == ["Alpha Co", "Beta Co"] and a["suppliers"][0]["share"] == pytest.approx(1000 / 1800 * 100)
    assert a["concentration_pct"] == 100.0
    assert a["pipeline"]["coverage"] == {"none": 0, "partial": 1, "full": 1, "exceeds": 1, "no_total": 1}
    lt = a["pipeline"]
    assert lt["req_to_po_days"]["median"] == 7 and lt["po_to_memo_days"]["median"] == 22 and lt["po_to_memo_days"]["long"] == 1
    dep = {d["key"]: d for d in a["departments"]}
    assert dep["IT"]["req_n"] == 2 and dep["IT"]["with_po_n"] == 2 and dep["Admin"]["conversion"] == 50.0
    assert a["attribution"]["auto"] + a["attribution"]["review"] == 4                       # nothing is guessed: unexplained POs are "review"
    assert [s.key for s in rm.sections] == ["summary", "monthly", "suppliers", "categories", "departments", "finance", "quality"]
    assert any(i["metric"] == "unpriced" for i in rm.meta["summary_items"]) and any(i["metric"] == "canc" for i in rm.meta["summary_items"])
    assert any(r["m"] == "purchase_orders" and r["loaded"] == 4 for r in next(t for t in rm.sections[6].tables if t["key"] == "batches")["rows"])


def test_filters_and_exports(loaded, session):
    ad, _ = loaded
    rm, a = ad.build(session, "all", "ar", True, {"months": ["2026-01"]})
    assert (a["totals"]["po_n"], a["totals"]["req_n"], a["totals"]["memo_n"]) == (2, 2, 2) and a["filtered"]
    dims = {d["key"]: d for d in rm.meta["filters"]["dimensions"]}
    assert [i["id"] for i in dims["months"]["items"]] == ["2026-01", "2026-02"] and {"Alpha Co", "Beta Co"} == {i["id"] for i in dims["suppliers"]["items"]}
    _rm, a2 = ad.build(session, "all", "en", True, {"suppliers": ["Beta Co"]})
    assert a2["totals"]["po_n"] == 2 and a2["totals"]["spend"] == Decimal(800)
    _rm, a3 = ad.build(session, "all", "en", True, {"departments": ["IT"]})
    assert a3["totals"]["po_n"] == 2 and a3["totals"]["req_n"] == 2
    _rm, a4 = ad.build(session, "all", "en", True, {"suppliers": ["Beta Co"]})
    assert a4["totals"]["req_n"] == 1                                  # only the requisition that led to Beta Co's linked PO
    with pytest.raises(AnalysisError):
        ad.build(session, "all", "en", True, {"suppliers": ["Nobody"]})
    for lang in ("ar", "en"):
        rm, _a = ad.build(session, "all", lang, True, {})
        assert PdfExporter().render(rm)[:4] == b"%PDF" and ExcelExporter().render(rm)[:2] == b"PK"


def test_empty_state_and_registers_are_not_deleted_from_here(session, base):
    ad = ProcurementAdapter()
    assert ad.list_items(session) == []
    with pytest.raises(AnalysisError) as e:
        ad.build(session, "all", "en", True, {})
    assert e.value.status == 409
    ad.ingest(session, register_book(), "register.xlsx", "bob", {})
    assert [i["id"] for i in ad.list_items(session)] == ["all"] and ad.item_meta(session, "all", True)["status"] == "ready"
    with pytest.raises(AnalysisError) as e:
        ad.delete_item(session, "all")
    assert e.value.status == 409 and ad.list_items(session)               # cumulative reference data: corrected by re-uploading
    with pytest.raises(AnalysisError):
        ad.item_meta(session, "nope", True)


def test_thresholds_are_settings(session):
    th, origin = effective_thresholds(session, "procurement")
    assert th["top_n"] == 10 and set(origin.values()) == {"default"}


def test_engine_never_counts_missing_totals_as_zero():
    data = {"pos": [{"id": 1, "fy": 2026, "number": "1/2026", "date": None, "supplier_id": None, "supplier": None, "total": None, "po_category": None, "supplier_category": None,
                     "order_status": None, "issuance_status": None, "handed": None, "remaining": None, "requisition_id": None, "req_date": None, "department": None,
                     "branch_status": None, "branch": None, "branch_type": None, "cancelled": False}], "requisitions": [], "memos": []}
    a = engine.analyze(data, {"top_n": 10, "concentration_top_n": 5, "mom_change_pct": 25, "long_lead_days": 30, "reconcile_tolerance": 0.01}, False, None)
    assert a["totals"]["spend"] == 0 and a["totals"]["priced_n"] == 0 and a["totals"]["avg_po"] is None and a["undated"]["po"] == 1 and a["months"] == []


def test_api_upload_report_settings_and_rbac(api, base):
    base_url = "/api/analysis/procurement/datasets"
    book = register_book()
    assert api.post(base_url, files={"file": ("r.xlsx", book)}, headers=auth("viewer")).status_code == 403
    r = api.post(base_url, files={"file": ("r.xlsx", book)}, headers=auth("analyst"))
    assert r.status_code == 201, r.text
    rep = api.get(f"{base_url}/all/report?lang=en", headers=auth("viewer")).json()
    assert float(rep["analysis"]["totals"]["spend"]) == 1800 and rep["analysis"]["totals"]["po_n"] == 4
    assert api.get(f"{base_url}/all/report.pdf?lang=ar&month=2026-01", headers=auth("viewer")).content[:4] == b"%PDF"
    assert api.get(f"{base_url}/all/report.xlsx?lang=en", headers=auth("viewer")).content[:2] == b"PK"
    assert api.put("/api/settings/procurement.thresholds", json={"top_n": 5}, headers=auth("analyst")).status_code == 403
    assert api.put("/api/settings/procurement.thresholds", json={"top_n": 5}, headers=auth("admin")).status_code == 200
    assert api.put("/api/settings/procurement.thresholds", json={"nope": 1}, headers=auth("admin")).status_code == 422
    assert api.delete(f"{base_url}/all", headers=auth("analyst")).status_code == 403
    assert api.delete(f"{base_url}/all", headers=auth("admin")).status_code == 409
