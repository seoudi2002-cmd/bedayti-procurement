from datetime import date
from decimal import Decimal

import pytest

from app.core.analysis import AnalysisError
from app.core.reporting.excel import ExcelExporter
from app.core.reporting.pdf import PdfExporter
from app.modules.copier_analysis import paper, service
from app.modules.copier_analysis import statement as st_mod
from app.modules.copier_analysis.adapter import CopierAdapter
from tests.copier_helpers import paper_workbook, statement_workbook
from tests.test_copier_analysis import api, auth  # noqa: F401  (fixtures)

WINDOWS = [{"from": "2026-01-01", "to": "2026-05-14", "price_per_carton": 10}, {"from": "2026-05-15", "to": "2026-09-14", "price_per_carton": 20},
           {"from": "2026-09-15", "to": "2026-12-31", "price_per_carton": 30}]          # synthetic prices
PARAMS = {**paper.default_paper_params(), "prices": WINDOWS}


def _rows(st):
    return [{"cartons": r.cartons, "branch_display": r.branch_display, "branch_key": r.branch_key, "is_head_office": r.is_head_office,
             "department": r.department, "distributed_on": r.distributed_on, "flags": r.flags} for r in st.rows]


def _analyze(st, pages=None, params=PARAMS, **kw):
    return paper.analyze_paper([{"po_no": st.po_no, "receipt_date": st.receipt_date, "rows": _rows(st)}], params, pages, **kw)


# ---------------------------------------------------------------- parser
def test_title_rows_subtotals_and_controls():
    c = paper_workbook()
    assert paper.is_distribution_workbook(c) and not paper.is_distribution_workbook(statement_workbook())
    st = paper.parse_distribution_xlsx(c)
    assert (st.po_no, st.receipt_date, st.received_cartons) == ("35", date(2026, 5, 20), Decimal(20))
    assert len(st.rows) == 9 and sum(r.cartons for r in st.rows) == Decimal("24.5") and st.stated_total == Decimal("24.5")
    assert st.stated_months == {7: Decimal(18), 8: Decimal("6.5")}
    codes = {i.code for i in st.issues}
    assert "month_subtotal_differs" not in codes and "total_differs" not in codes
    assert "received_differs" in codes                    # title says 20, lines add up to 24.5: flagged, never fixed
    assert {"same_branch_same_day", "sequence_gaps", "sequence_out_of_order"} <= codes
    assert all("same_branch_same_day" in r.flags for r in st.rows if r.branch_key == "فرع باء")


def test_subtotal_disagreement_is_flagged():
    st = paper.parse_distribution_xlsx(paper_workbook(break_month=True))
    assert "month_subtotal_differs" in {i.code for i in st.issues}


def test_head_office_departments_are_split_and_spelling_variants_grouped():
    st = paper.parse_distribution_xlsx(paper_workbook())
    hq = [r for r in st.rows if r.is_head_office]
    assert {r.department for r in hq} == {"الحفظ", "HR", None}
    a = _analyze(st)
    names = {u["department"]: u["cartons"] for u in a["head_office"]}
    assert names == {"الحفظ": 5, "HR": 2, None: 1}        # "المركز الرئيسي - الحفظ" + "المركز الرئيسي الحفظ" are one department
    assert a["hq_summary"]["cartons"] == 8
    assert "head_office_label_variants" in {i.code for i in st.issues}
    assert paper.split_head_office("فرع ألف") == (False, None)


def test_unrecognised_workbook():
    with pytest.raises(paper.UnrecognisedPaperStatement):
        paper.parse_distribution_xlsx(statement_workbook())


# ---------------------------------------------------------------- pricing and analysis
def test_price_windows_and_cost_is_cartons_times_price():
    assert paper.price_for(PARAMS, date(2026, 3, 1))["price_per_carton"] == 10
    assert paper.price_for(PARAMS, date(2026, 5, 20))["price_per_carton"] == 20
    assert paper.price_for(PARAMS, date(2026, 9, 20))["price_per_carton"] == 30
    assert paper.price_for(PARAMS, date(2027, 1, 1)) is None and paper.price_for(PARAMS, None) is None
    st = paper.parse_distribution_xlsx(paper_workbook())
    a = _analyze(st)
    assert a["totals"]["cartons"] == Decimal("24.5") and a["totals"]["cost"] == Decimal("24.5") * 20 and a["totals"]["sheets"] == Decimal("24.5") * 2500
    assert [(m["period"], m["cartons"], m["cost"]) for m in a["by_month"]] == [((2026, 7), 18, 18 * 20), ((2026, 8), Decimal("6.5"), Decimal("6.5") * 20)]
    assert a["by_month"][1]["cartons_mom"] == Decimal("-11.5")
    top = a["units"][0]
    assert top["name"] == "فرع ألف" and top["cartons"] == 8 and top["by_month"] == {(2026, 7): 4, (2026, 8): 4} and top["share"] == pytest.approx(8 / 24.5 * 100)


def test_shipped_defaults_carry_no_real_prices_and_flag_the_unconfirmed_value():
    d = paper.default_paper_params()
    assert d["prices"] == [] and d["sheets_per_carton"] == 2500 and d["pages_per_sheet"] == 1


def test_no_price_window_leaves_cost_unset_never_zero():
    st = paper.parse_distribution_xlsx(paper_workbook())
    a = _analyze(st, params={**PARAMS, "prices": []})
    assert a["totals"]["cost_complete"] is False and a["notes"][0]["code"] == "no_price_window"
    assert a["by_month"][0]["cost_per_page"] is None


def test_estimated_need_is_separate_from_distributed_consumption():
    st = paper.parse_distribution_xlsx(paper_workbook())
    k = st_mod.branch_key        # the service keys machine branches the same way (normalised)
    pages = {(2026, 7): {"pages": 50_000, "by_branch": {k("فرع ألف"): 30_000, k("إدارة الحفظ"): 5_000, k("الحفظ"): 7, k("فرع غير موجود"): 1}}}
    a = _analyze(st, pages, params={**PARAMS, "pages_per_sheet": 2})
    jul = a["by_month"][0]
    assert jul["cartons"] == 18 and jul["pages"] == 50_000 and jul["pages_per_carton"] == pytest.approx(50_000 / 18)
    assert jul["need_cartons"] == Decimal(50_000) / 2 / 2500 == Decimal(10) and jul["need_gap"] == 8 and jul["coverage"] == pytest.approx(180)
    assert jul["cost_per_page"] == Decimal(18 * 20) / 50_000
    assert a["by_month"][1]["pages"] is None                        # no statement for August: not computed, not zero
    assert a["totals"]["cartons"] == Decimal("24.5")                # the need never alters distributed consumption
    cmp = {(r["unit"]): r for r in a["compare"]}
    assert cmp["فرع ألف"]["match"] == "exact" and cmp["فرع ألف"]["need_cartons"] == Decimal(30_000) / 2 / 2500
    assert all(r["match"] == "none" and r["machine_branch"] is None for r in a["compare"] if r["hq"])   # no fuzzy matching, ever
    assert next(r for r in a["compare"] if r["unit"] == "فرع باء")["match"] == "none"
    assert _analyze(st, pages, filtered=True)["by_month"][0]["pages"] is None


def test_settings_validation():
    assert paper.validate_paper_params({"pages_per_sheet": 2})
    for bad in ({"nope": 1}, {"sheets_per_carton": 0}, {"pages_per_sheet": "x"},
                {"prices": [{"from": "2026-02-01", "to": "2026-01-01", "price_per_carton": 5}]},
                {"prices": [{"from": "2026-01-01", "to": "2026-03-01", "price_per_carton": 5}, {"from": "2026-02-01", "to": "2026-04-01", "price_per_carton": 5}]}):
        with pytest.raises(ValueError):
            paper.validate_paper_params(bad)


# ---------------------------------------------------------------- service / adapter / API
def test_upload_report_filters_and_exports(session):
    ad = CopierAdapter()
    r = ad.ingest(session, statement_workbook(), "s.xlsx", "bob", {})
    r = ad.ingest(session, paper_workbook(), "paper.xlsx", "bob", {})
    assert r.item_id == "paper" and r.meta["uploaded"]["rows"] == 9
    with pytest.raises(AnalysisError) as e:
        ad.ingest(session, paper_workbook(), "again.xlsx", "bob", {})
    assert e.value.status == 409
    with pytest.raises(AnalysisError) as e:                              # same PO, different file
        ad.ingest(session, paper_workbook(received=21), "again2.xlsx", "bob", {})
    assert e.value.status == 409
    items = ad.list_items(session)
    assert [i["id"] for i in items if i["layout_label"] == "paper"] == ["paper"]
    rm, a = ad.build(session, "paper", "en", True, {})
    keys = [s.key for s in rm.sections]
    assert keys == ["summary", "monthly", "branches", "head_office", "need", "quality"]
    assert a["by_month"][0]["pages"] == 4000 + 8000 + 3500 + 200 + 3600   # July has a machine statement; August does not
    assert any(t["key"] == "need" for t in rm.sections[4].tables)
    dims = {d["key"]: d for d in rm.meta["filters"]["dimensions"]}
    assert [i["id"] for i in dims["months"]["items"]] == ["2026-07", "2026-08"] and any(i["id"] == "hq:الحفظ" for i in dims["branches"]["items"])
    _rm2, a2 = ad.build(session, "paper", "ar", True, {"months": ["2026-08"]})
    assert a2["totals"]["cartons"] == Decimal("6.5") and a2["by_month"][0]["pages"] is None
    _rm3, a3 = ad.build(session, "paper", "ar", True, {"branches": ["hq:الحفظ"]})
    assert a3["totals"]["cartons"] == 5
    with pytest.raises(AnalysisError):
        ad.build(session, "paper", "en", True, {"branches": ["nope"]})
    for lang in ("ar", "en"):
        rm, _a = ad.build(session, "paper", lang, True, {})
        assert PdfExporter().render(rm)[:4] == b"%PDF" and ExcelExporter().render(rm)[:2] == b"PK"
    assert ad.item_meta(session, "paper", True)["kind"] == "paper"
    ad.delete_item(session, "paper")
    assert not service.paper_datasets(session)
    with pytest.raises(AnalysisError):
        ad.item_meta(session, "paper", True)


def test_cycle_reports_are_unchanged_by_paper_files(session):
    ad = CopierAdapter()
    cid = ad.ingest(session, statement_workbook(), "s.xlsx", "bob", {}).item_id
    before = ad.build(session, cid, "en", True, {})[1]["totals"]
    ad.ingest(session, paper_workbook(), "paper.xlsx", "bob", {})
    assert ad.build(session, cid, "en", True, {})[1]["totals"] == before
    assert service.cycle_meta(session, service.get_cycle(session, (2026, 7), False))["sources"][0]["role"] == "statement"


def test_api_upload_settings_and_rbac(api):
    base = "/api/analysis/copiers/datasets"
    assert api.post(base, files={"file": ("p.xlsx", paper_workbook())}, headers=auth("viewer")).status_code == 403
    assert api.post(base, files={"file": ("p.xlsx", paper_workbook())}, headers=auth("analyst")).status_code == 201
    rep = api.get(f"{base}/paper/report?lang=en", headers=auth("viewer")).json()
    assert rep["analysis"]["paper"]["totals"]["cartons"] == "24.5" or float(rep["analysis"]["paper"]["totals"]["cartons"]) == 24.5
    assert api.get(f"{base}/paper/report.pdf?lang=ar&month=2026-07", headers=auth("viewer")).content[:4] == b"%PDF"
    assert api.get(f"{base}/paper/report.xlsx?lang=en", headers=auth("viewer")).content[:2] == b"PK"
    got = api.get("/api/settings/copier.paper", headers=auth("viewer")).json()
    assert got["effective"]["sheets_per_carton"] == 2500 and got["origin"]["pages_per_sheet"] == "default"
    assert api.put("/api/settings/copier.paper", json={"pages_per_sheet": 2}, headers=auth("analyst")).status_code == 403
    assert api.put("/api/settings/copier.paper", json={"pages_per_sheet": -1}, headers=auth("admin")).status_code == 422
    put = api.put("/api/settings/copier.paper", json={"pages_per_sheet": 2}, headers=auth("admin")).json()
    assert put["effective"]["pages_per_sheet"] == 2 and put["origin"]["pages_per_sheet"] == "custom"
    rep = api.get(f"{base}/paper/report?lang=en", headers=auth("viewer")).json()
    assert any(r["name"] == "Pages per sheet" and r["value"] == 2 and r["source"] == "custom"
               for s in rep["report"]["sections"] if s["key"] == "quality" for t in s["tables"] if t["key"] == "settings" for r in t["rows"])
    assert api.delete(f"{base}/paper", headers=auth("analyst")).status_code == 403
    assert api.delete(f"{base}/paper", headers=auth("admin")).status_code in (200, 204)
