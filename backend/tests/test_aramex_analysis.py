from datetime import date
from decimal import Decimal

import pytest

from app.core.analysis import AnalysisError
from app.core.reporting.excel import ExcelExporter
from app.core.reporting.pdf import PdfExporter
from app.core.settings_store import effective_struct, set_setting, struct_defaults
from app.models import DimBranch
from app.modules.aramex_analysis import allocation, engine, service
from app.modules.aramex_analysis import invoice as pdf_mod
from app.modules.aramex_analysis import shipments as xl_mod
from app.modules.aramex_analysis.adapter import AramexAdapter
from tests.aramex_helpers import HQ_CONTACT, invoice_pdf, scanned_appendix_pdf, shipments_workbook
from tests.test_copier_analysis import api, auth  # noqa: F401  (fixtures)

BILL_A, BILL_B = "1365000001", "1365000002"


def _upload_all(session, ad=None, contacts=(HQ_CONTACT,)):
    ad = ad or AramexAdapter()
    set_setting(session, "aramex.parties", {"head_office_contacts": list(contacts)}, "t")
    for content, name in ((invoice_pdf(BILL_A, "A"), "a.pdf"), (shipments_workbook(BILL_A, "A"), "a.xlsx"),
                          (shipments_workbook(BILL_B, "B"), "b.xlsx"), (invoice_pdf(BILL_B, "B"), "b.pdf")):   # B arrives Excel-first
        ad.ingest(session, content, name, "bob", {})
    return ad


# ---------------------------------------------------------------- readers
def test_pdf_reader_dates_lines_and_totals():
    inv = pdf_mod.parse_invoice(invoice_pdf())
    assert (inv.bill_doc, inv.doc_date, inv.due_date, inv.customer_no, inv.currency) == (BILL_A, date(2026, 9, 28), date(2026, 10, 28), "12345678", "EGP")
    assert len(inv.shipments) == 6 and inv.shipments[0].pickup_on == date(2026, 8, 29) and inv.shipments[0].product == "OND"
    assert inv.totals["total"] == inv.totals["net"] + inv.totals["vat"] and not inv.issues
    assert pdf_mod.parse_invoice(invoice_pdf(unreadable=True)).issues[0].code == "unreadable_line"       # never skipped silently
    with pytest.raises(pdf_mod.UnrecognisedInvoice):
        pdf_mod.parse_invoice(scanned_appendix_pdf())


def test_xlsx_reader_keeps_adjustment_apart_and_notes_misleading_columns():
    x = xl_mod.parse_shipments_xlsx(shipments_workbook())
    assert len(x.shipments) == 6 and x.bill_doc == BILL_A and [a["label"] for a in x.adjustments] == ["TAX Rounding Diff"]
    codes = {i.code for i in x.issues}
    assert {"net_value_includes_tax", "amount_equals_base", "awb_date_not_pickup", "adjustment_rows"} <= codes and "total_row_differs" not in codes
    with pytest.raises(xl_mod.UnrecognisedShipments):
        xl_mod.parse_shipments_xlsx(shipments_workbook(extra_bill=True))     # two invoices in one sheet
    assert not xl_mod.is_shipments_workbook(b"not a workbook")


# ---------------------------------------------------------------- allocation: explicit evidence only
RULES = allocation.rules_from({**struct_defaults("aramex.parties"), "head_office_contacts": [HQ_CONTACT]})
RES = lambda n: {"key": "name:" + n, "display": n, "kind": "branch", "registered": False}  # noqa: E731


def test_branch_only_from_an_explicit_name_never_from_a_city():
    f = allocation.allocate_side
    assert f(["شركة بدايتي فرع الفيوم", "x"], "Fayoum", RULES, RES)["display"] == "الفيوم"
    assert f(["بدايتى فرع الفيوم"], None, RULES, RES)["key"] == f(["شركة بدايتي فرع الفيوم"], None, RULES, RES)["key"]     # spelling variants of one label
    assert f(["Company", "someone"], "Fayoum", RULES, RES)["reason"] == "no_branch_evidence"                  # city alone: no branch
    assert f(["Company"], "Giza", RULES, RES)["kind"] == "head_office"                                         # configured Head Office location
    assert f(["Company", HQ_CONTACT], "Qena", RULES, RES)["kind"] == "head_office"                           # configured contact, exact
    assert f(["Company", HQ_CONTACT + " Jr"], "Qena", RULES, RES)["kind"] == "unallocated"                    # no fuzzy matching
    assert f(["شركة بدايتي المركز الرئيسي"], "Qena", RULES, RES)["kind"] == "head_office"
    assert f(["شركة بدايتي فرع طما"], "Giza", RULES, RES)["reason"] == "conflicting_evidence"                 # branch name + Head Office marker
    assert f(["شركة بدايتي فرع طما", "بدايتي فرع دشنا"], None, RULES, RES)["reason"] == "conflicting_branches"


def test_shipped_defaults_hold_no_staff_names_or_prices():
    assert struct_defaults("aramex.parties")["head_office_contacts"] == [] and struct_defaults("aramex.rates") == {"first_kg": [], "additional_kg": []}


# ---------------------------------------------------------------- engine
def _rows(session):
    set_setting(session, "aramex.parties", {"head_office_contacts": [HQ_CONTACT]}, "t")
    return service.load_analysis_rows(session, allocation.rules_from(effective_struct(session, "aramex.parties")[0]))


def test_totals_controls_and_per_party_figures(session):
    _upload_all(session)
    rows, exc, info = _rows(session)
    assert len(rows) == 10 and not exc and set(info) == {1, 2}
    th = {"heavy_weight_kg": 5, "outlier_cost_multiple": 2, "top_n": 10, "mom_change_pct": 25, "low_allocation_pct": 80, "weight_band_1_kg": 1, "weight_band_2_kg": 5,
          "weight_band_3_kg": 10, "weekend_day_1": 4, "weekend_day_2": 5, "reconcile_tolerance": 0.01}
    a = engine.analyze(rows, rows, th, {}, None, (date(2026, 8, 29), date(2026, 9, 3)), False)
    inv_net = sum(i["pdf_totals"]["net"] for i in info.values())
    assert a["totals"]["n"] == 10 and a["totals"]["net"] == inv_net == sum(i["net_rows"] for i in info.values())
    c = a["controls"]
    assert c["ok"] and c["sent_n"] == c["recv_n"] == 10 and c["sent_cost"] == c["recv_cost"] == inv_net and c["duplicate_awb"] == 0
    by = {p["name"] or p["kind"]: p for p in a["parties"]}
    fay, dish = by["الفيوم"], by["دشنا"]
    assert (fay["sent_n"], fay["recv_n"]) == (4, 2) and (dish["sent_n"], dish["recv_n"]) == (0, 3)      # Fayoum sent 4 (incl. the one whose receiver conflicts), received 2
    assert fay["total_n"] == 6 and fay["total_cost"] == fay["sent_cost"] + fay["recv_cost"] and fay["avg_cost"] == fay["total_cost"] / 6
    assert by["head_office"]["sent_n"] == 4 and by["head_office"]["recv_n"] == 4          # HQ->HQ is counted on both of its sides
    un = by["unallocated"]
    assert un["sent_n"] == 2 and un["recv_n"] == 1 and a["allocation"]["sides"]["receiver"]["reasons"] == {"conflicting_evidence": {"n": 1, "cost": un["recv_cost"]}}
    assert a["allocation"]["sides"]["sender"]["reasons"]["no_branch_evidence"]["n"] == 2   # the two Qena shipments: a city is not evidence
    assert [p["kind"] for p in a["parties"]][-2:] == ["head_office", "unallocated"]        # fixed order: branches, Head Office, Unallocated


def test_months_partial_flags_and_month_over_month(session):
    _upload_all(session)
    rows, _e, _i = _rows(session)
    th = {"mom_change_pct": 25}
    ms = engine.months_table(rows, (date(2026, 8, 29), date(2026, 9, 3)))
    assert [(m["period"], m["n"], m["partial"]) for m in ms] == [((2026, 8), 6, True), ((2026, 9), 4, True)]
    assert ms[1]["d_n"] == -2 and ms[1]["d_net_pct"] is not None
    mom = engine.mom_table(rows, (2026, 9), th)
    assert mom["prev"] == (2026, 8) and mom["prev_available"]
    fay = next(r for r in mom["rows"] if r["name"] == "الفيوم")
    assert (fay["cur_n"], fay["prev_n"], fay["d_n"]) == (3, 3, 0) and fay["d_cost"] == fay["cur_cost"] - fay["prev_cost"]
    assert engine.mom_table(rows, (2026, 8), th)["prev_available"] is False                 # no July uploaded: no comparison, not zeros
    full = engine.months_table(rows, (date(2026, 8, 1), date(2026, 9, 30)))           # fully covered months are not flagged
    assert [m["partial"] for m in full] == [False, False]


def test_reconciliation_detects_differences_and_never_edits_sources(session):
    ad = AramexAdapter()
    ad.ingest(session, invoice_pdf(BILL_A, "A", vat_wrong=True), "a.pdf", "bob", {})
    ad.ingest(session, shipments_workbook(BILL_A, "A", base_bump_awb="1000000003"), "a.xlsx", "bob", {})
    r = service.reconcile_invoice(session, 1, 0.01)
    bad = {c["id"] for c in r["checks"] if c["status"] == "diff" and c["group"] == "primary"}
    assert {"base_per_awb", "sum_base", "net_per_awb", "net_total", "vat_total", "grand_total"} <= bad
    assert next(c for c in r["checks"] if c["id"] == "base_per_awb")["refs"] == ["1000000003"]


def test_awb_in_one_source_only_is_excluded_and_reported(session):
    ad = AramexAdapter()
    ad.ingest(session, invoice_pdf(BILL_A, "A"), "a.pdf", "bob", {})
    ad.ingest(session, shipments_workbook(BILL_A, "A", drop_awb="1000000006"), "a.xlsx", "bob", {})
    rows, exc, _ = _rows(session)
    assert len(rows) == 5 and [(e["code"], e["awb"]) for e in exc] == [("awb_only_in_pdf", "1000000006")]
    rm, a = ad.build(session, "all", "en", True, {})
    assert a["controls"]["ok"] is True and any(t["key"] == "merge_exc" for s in rm.sections for t in s.tables)
    assert next(t for t in rm.sections[4].tables if t["key"] == "invoice_control")["rows"][0]["diff"] != 0       # the control row shows the gap


# ---------------------------------------------------------------- service / adapter
def test_upload_any_order_duplicates_incomplete_and_reference(session):
    ad = AramexAdapter()
    r1 = ad.ingest(session, shipments_workbook(BILL_A, "A"), "a.xlsx", "bob", {})
    assert r1.item_id == "inv:1" and r1.meta["status"] == "incomplete"
    with pytest.raises(AnalysisError) as e:
        ad.build(session, "inv:1", "en", True, {})
    assert e.value.status == 409
    r2 = ad.ingest(session, invoice_pdf(BILL_A, "A"), "a.pdf", "bob", {})
    assert r2.item_id == "inv:1" and r2.meta["status"] == "ready" and r2.meta["shipments"] == {"pdf": 6, "xlsx": 6}
    for content, name in ((shipments_workbook(BILL_A, "A"), "a2.xlsx"), (invoice_pdf(BILL_A, "A"), "a2.pdf")):
        with pytest.raises(AnalysisError) as e:
            ad.ingest(session, content, name, "bob", {})
        assert e.value.status == 409
    with pytest.raises(AnalysisError) as e:                                   # a different PDF for the same invoice
        ad.ingest(session, invoice_pdf(BILL_A, "A", vat_wrong=True), "a3.pdf", "bob", {})
    assert e.value.status == 409
    ref = ad.ingest(session, scanned_appendix_pdf(), "appendix.pdf", "bob", {})
    assert ref.item_id == "all" and ref.meta["uploaded"]["role"] == "contract_reference"
    with pytest.raises(AnalysisError):
        ad.ingest(session, b"garbage", "x.pdf", "bob", {})
    with pytest.raises(AnalysisError):
        ad.ingest(session, b"garbage", "x.xlsx", "bob", {})


def test_reports_match_the_invoices_and_the_primary_table(session):
    ad = _upload_all(session)
    items = ad.list_items(session)
    assert [i["id"] for i in items][:3] == ["all", "m:2026-09", "m:2026-08"] and {"inv:1", "inv:2"} <= {i["id"] for i in items}
    inv_net = {i: service.invoices(session)[i - 1].pdf_totals["net"] for i in (1, 2)}
    rm, a = ad.build(session, "all", "en", True, {})
    assert a["totals"]["net"] == Decimal(inv_net[1]) + Decimal(inv_net[2]) and a["controls"]["ok"]
    assert [s.key for s in rm.sections] == ["summary", "branches", "monthly", "allocation", "recon", "support", "exceptions", "quality"]
    table = next(t for t in rm.sections[1].tables if t["key"] == "branch_table")
    assert [c["key"] for c in table["columns"]] == ["branch", "sent_n", "sent_c", "recv_n", "recv_c", "tot_n", "tot_c", "avg"]
    assert table["rows"][-1]["sent_c"] == table["rows"][-1]["recv_c"] == a["totals"]["net"]
    assert any(t["key"] == "pm_c" for t in rm.sections[2].tables)                                      # party x month matrix with 2+ months
    det = next(t for t in rm.sections[2].tables if t["key"] == "branch_by_month")["rows"]               # the primary table, for every month
    fay8, fay9 = (next(d for d in det if d["month"].startswith(m) and d["branch"] == "الفيوم") for m in ("Aug", "Sep"))
    assert (fay8["sent_n"], fay8["recv_n"], fay9["sent_n"], fay9["recv_n"]) == (2, 1, 2, 1)
    assert fay8["dc"] is None and fay9["dc"] == fay9["tot_c"] - fay8["tot_c"]
    for mm in ("Aug", "Sep"):                                                                           # each month's Σ sent = Σ received
        rr = [d for d in det if d["month"].startswith(mm)]
        assert sum(d["sent_c"] for d in rr) == sum(d["recv_c"] for d in rr) and sum(d["sent_n"] for d in rr) == sum(d["recv_n"] for d in rr)
    for iid in (1, 2):
        _rm, ai = ad.build(session, f"inv:{iid}", "ar", True, {})
        assert ai["totals"]["net"] == Decimal(inv_net[iid]) and ai["recons"][iid]["summary"]["diff"] == 0
    rm9, a9 = ad.build(session, "m:2026-09", "en", True, {})
    assert a9["totals"]["n"] == 4 and a9["mom"]["prev_available"] and any(t["key"] == "mom" for t in rm9.sections[2].tables)
    assert any(i["metric"] == "mom_partial" for i in rm9.executive_summary and rm9.meta["summary_items"])
    rm8, a8 = ad.build(session, "m:2026-08", "en", True, {})
    assert not a8["mom"]["prev_available"] and not any(t["key"] == "mom" for t in rm8.sections[2].tables)
    for kind in ("all", "m:2026-09", "inv:1"):
        for lang in ("ar", "en"):
            rm, _a = ad.build(session, kind, lang, True, {})
            assert PdfExporter().render(rm)[:4] == b"%PDF" and ExcelExporter().render(rm)[:2] == b"PK"


def test_filters_and_gross_is_additional(session):
    ad = _upload_all(session)
    rm, a = ad.build(session, "all", "en", True, {"services": ["ONP"]})
    assert a["totals"]["n"] == 1 and a["filtered"] and a["totals"]["gross"] > a["totals"]["net"]
    dims = {d["key"]: d for d in rm.meta["filters"]["dimensions"]}
    assert {"branches", "services", "cities"} == set(dims) and any(i["id"] == "head_office" for i in dims["branches"]["items"])
    _rm, a2 = ad.build(session, "all", "en", True, {"branches": ["head_office"]})
    assert a2["controls"]["ok"] and a2["totals"]["n"] < 10
    with pytest.raises(AnalysisError):
        ad.build(session, "all", "en", True, {"cities": ["Nowhere"]})


def test_branch_register_confirms_names_and_flags_the_rest(session):
    session.add(DimBranch(name_ar="الفيوم", branch_type="branch"))
    session.commit()
    ad = _upload_all(session)
    _rm, a = ad.build(session, "all", "en", True, {})
    fay = next(p for p in a["parties"] if p["key"].startswith("branch:"))
    assert fay["registered"] is True and fay["total_n"] == 6
    assert next(p for p in a["parties"] if p["name"] == "دشنا")["registered"] is False
    assert a["allocation"]["sides"]["receiver"]["unregistered"] and "الفيوم" not in a["allocation"]["sides"]["receiver"]["unregistered"]
    rm, _ = ad.build(session, "all", "en", True, {})
    assert any(t["key"] == "unregistered" for s in rm.sections for t in s.tables)


def test_settings_change_the_allocation_without_code(session):
    ad = _upload_all(session, contacts=())
    _rm, before = ad.build(session, "all", "en", True, {})
    set_setting(session, "aramex.parties", {"head_office_contacts": [HQ_CONTACT]}, "t")
    _rm, after = ad.build(session, "all", "en", True, {})
    assert after["allocation"]["both_confirmed_pct"] >= before["allocation"]["both_confirmed_pct"]
    assert after["totals"]["net"] == before["totals"]["net"] and after["controls"]["ok"] and before["controls"]["ok"]


def test_rate_check_only_with_a_card_and_delete(session):
    ad = _upload_all(session)
    _rm, a = ad.build(session, "all", "en", True, {})
    assert a["support"]["rate_check"] is None and "rate_off_card" not in a["support"]["exceptions"]       # no card: not available
    set_setting(session, "aramex.rates", {"first_kg": [60, 75], "additional_kg": [5]}, "t")
    _rm, a = ad.build(session, "all", "en", True, {})
    assert a["support"]["rate_check"]["checked"] == 10 and a["support"]["rate_check"]["off_card"] == 2     # base 100 and 65 are not on this card
    ad.delete_item(session, "inv:2")
    assert [i["id"] for i in ad.list_items(session) if i["layout_label"] == "invoice"] == ["inv:1"]
    with pytest.raises(AnalysisError):
        ad.delete_item(session, "all")
    with pytest.raises(AnalysisError):
        ad.item_meta(session, "inv:99", True)


# ---------------------------------------------------------------- API
def test_api_upload_report_settings_and_rbac(api):
    base = "/api/analysis/aramex/datasets"
    assert api.post(base, files={"file": ("a.pdf", invoice_pdf(BILL_A, "A"))}, headers=auth("viewer")).status_code == 403
    assert api.post(base, files={"file": ("a.pdf", invoice_pdf(BILL_A, "A"))}, headers=auth("analyst")).status_code == 201
    assert api.post(base, files={"file": ("a.xlsx", shipments_workbook(BILL_A, "A"))}, headers=auth("analyst")).status_code == 201
    assert api.post(base, files={"file": ("a.xlsx", shipments_workbook(BILL_A, "A"))}, headers=auth("analyst")).status_code == 409
    rep = api.get(f"{base}/all/report?lang=en", headers=auth("viewer")).json()
    assert float(rep["analysis"]["totals"]["net"]) > 0 and rep["analysis"]["controls"]["ok"] is True
    assert "attention" not in str(rep) and "someone" not in str(rep) and HQ_CONTACT not in str(rep)           # no person names leave the server
    assert api.get(f"{base}/m:2026-08/report.pdf?lang=ar&service=OND", headers=auth("viewer")).content[:4] == b"%PDF"
    assert api.get(f"{base}/inv:1/report.xlsx?lang=en", headers=auth("viewer")).content[:2] == b"PK"
    assert api.get("/api/settings/aramex.parties", headers=auth("viewer")).status_code == 403             # staff names: admin only
    assert api.put("/api/settings/aramex.parties", json={"head_office_contacts": [HQ_CONTACT]}, headers=auth("analyst")).status_code == 403
    assert api.put("/api/settings/aramex.parties", json={"head_office_contacts": "x"}, headers=auth("admin")).status_code == 422
    assert api.put("/api/settings/aramex.parties", json={"nope": []}, headers=auth("admin")).status_code == 422
    put = api.put("/api/settings/aramex.parties", json={"head_office_contacts": [HQ_CONTACT]}, headers=auth("admin")).json()
    assert put["effective"]["head_office_contacts"] == [HQ_CONTACT] and put["origin"]["head_office_contacts"] == "custom"
    assert api.put("/api/settings/aramex.rates", json={"first_kg": [0]}, headers=auth("admin")).status_code == 422
    assert api.put("/api/settings/aramex.rates", json={"first_kg": [60], "additional_kg": [5]}, headers=auth("admin")).status_code == 200
    assert api.put("/api/settings/aramex.thresholds", json={"heavy_weight_kg": 8}, headers=auth("admin")).status_code == 200
    assert api.put("/api/settings/aramex.thresholds", json={"nope": 1}, headers=auth("admin")).status_code == 422
    assert api.delete(f"{base}/inv:1", headers=auth("analyst")).status_code == 403
    assert api.delete(f"{base}/inv:1", headers=auth("admin")).status_code in (200, 204)
