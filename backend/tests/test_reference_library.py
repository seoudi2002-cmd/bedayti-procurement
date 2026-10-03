from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.core.reference import assets, service
from app.models import AssetRegisterRow, ReferenceSource
from tests.reference_helpers import asset_workbook, regulation_pdf
from tests.test_copier_analysis import api, auth  # noqa: F401  (fixtures)


def test_reader_keeps_the_source_as_received_and_reports_observations():
    c = asset_workbook()
    assert assets.is_asset_register(c) and not assets.is_asset_register(b"x")
    p = assets.parse_assets(c)
    assert len(p.rows) == 8 and [r["asset_number"] for r in p.rows][:3] == ["10000", "10001", "10002"]
    r2 = p.rows[2]
    assert r2["in_service_raw"] == "31-07-2024" and r2["in_service_date"] == date(2024, 7, 31)          # text kept as written; parsed day-first only
    assert p.rows[0]["serial_number"] is None and p.rows[0]["life_raw"] == "010.00"                      # empty stays empty; life is not converted
    assert (p.rows[0]["location_governorate"], p.rows[0]["location_city"], p.rows[0]["location_office"]) == ("Gov1", "CityA", "CityA Office")
    assert p.rows[4].get("location_governorate") is None and "location_not_split" in p.rows[4]["flags"]      # not split when the shape differs
    codes = {i.code: i.count for i in p.issues}
    assert codes["duplicate_asset_number"] == 2 and codes["in_service_date_is_text"] == 1 and codes["zero_or_negative_cost"] == 1
    assert codes["accounting_date_after_report_period"] == 1 and codes["accounting_before_in_service"] == 1 and codes["ytd_not_sum_of_months"] == 1
    assert "nbv_not_cost_minus_accumulated" not in codes and codes["serial_number_mostly_empty"] == 7
    assert sum(1 for r in p.rows if r["asset_number"] == "10005") == 2                                    # duplicates are kept, both flagged
    assert all("duplicate_asset_number" in r["flags"] for r in p.rows if r["asset_number"] == "10005")
    prof = assets.profile(p)
    assert prof["rows"] == 8 and prof["distinct_asset_numbers"] == 7 and Decimal(prof["totals"]["cost"]) == Decimal(102600)
    assert prof["head_office_assets"] == 2 and prof["locations"] == 5 and prof["current_period"] == "2024-09-24"


def test_unrecognised_workbook():
    import io

    from openpyxl import Workbook
    wb = Workbook()
    wb.active.append(["a", "b"])
    buf = io.BytesIO()
    wb.save(buf)
    with pytest.raises(assets.UnrecognisedAssetRegister):
        assets.parse_assets(buf.getvalue())


def test_versions_are_kept_and_the_difference_is_recorded(session):
    v1 = service.register(session, asset_workbook(1), "assets1.xlsx", "bob")
    assert (v1.kind, v1.version_no, v1.is_current, v1.status, v1.rows_count, v1.as_of_date, v1.as_of_source) == ("asset_register", 1, True, "ready", 8, date(2024, 9, 24), "file")
    with pytest.raises(service.ReferenceError) as e:
        service.register(session, asset_workbook(1), "again.xlsx", "bob")
    assert e.value.status == 409
    v2 = service.register(session, asset_workbook(2), "assets2.xlsx", "bob", notes="updated export")
    session.refresh(v1)
    assert v2.version_no == 2 and v2.as_of_date == date(2024, 12, 31)
    assert v2.is_current and not v1.is_current                                                             # the latest as-of is current ...
    assert session.query(AssetRegisterRow).filter_by(source_id=v1.id).count() == 8                          # ... and version 1 is still stored
    d = v2.summary["diff_vs_previous"]
    assert d["added"] == 1 and d["removed"] == 1 and d["added_examples"] == ["10007"] and d["removed_examples"] == ["10000"] and d["previous_version"] == 1
    assert d["changed_by_field"]["location_text"] >= 1 and d["changed_by_field"]["cost"] >= 1
    assert [s.version_no for s in session.scalars(select(ReferenceSource).order_by(ReferenceSource.version_no))] == [1, 2]


def test_older_as_of_does_not_become_current(session):
    v2 = service.register(session, asset_workbook(2), "assets2.xlsx", "bob")
    v1 = service.register(session, asset_workbook(1), "assets1.xlsx", "bob")        # uploaded later, but its content is older
    session.refresh(v2)
    assert v1.version_no == 2 and not v1.is_current and v2.is_current


def test_documents_need_a_kind_and_a_series(session):
    with pytest.raises(service.ReferenceError) as e:
        service.register(session, regulation_pdf(), "reg.pdf", "bob")
    assert e.value.status == 422
    with pytest.raises(service.ReferenceError) as e:
        service.register(session, regulation_pdf(), "reg.pdf", "bob", kind="regulation")
    assert e.value.status == 422
    with pytest.raises(service.ReferenceError):
        service.register(session, b"x", "reg.txt", "bob", kind="regulation", series="admin_regulation")


def test_document_text_is_kept_by_page(session):
    src = service.register(session, regulation_pdf(3), "reg.pdf", "bob", kind="regulation", series="admin_regulation", title="Reg", as_of=date(2025, 1, 1))
    assert src.status == "processing" and src.as_of_source == "uploader" and src.is_current
    service.process_document_job(session, src.id)
    session.refresh(src)
    assert src.status == "ready" and src.summary["pages"] == 3 and src.summary["words"] > 0 and src.summary["empty_pages"] == []
    from app.models import ExtractedPage
    texts = [p.raw_text for p in session.scalars(select(ExtractedPage).where(ExtractedPage.job_id == src.job_id).order_by(ExtractedPage.page_no))]
    assert "Article 2" in texts[1]
    v2 = service.register(session, regulation_pdf(4), "reg2.pdf", "bob", kind="regulation", series="admin_regulation", as_of=date(2026, 1, 1))
    session.refresh(src)
    assert v2.version_no == 2 and v2.is_current and not src.is_current and src.status == "ready"       # the earlier version and its text stay


def test_api_upload_list_pages_rbac_and_no_delete(api, monkeypatch, engine):
    import app.api.reference as ref_api
    monkeypatch.setattr(ref_api, "get_engine", lambda: engine)
    base = "/api/reference"
    assert api.post(base, files={"file": ("a.xlsx", asset_workbook(1))}, headers=auth("viewer")).status_code == 403
    r = api.post(base, files={"file": ("a.xlsx", asset_workbook(1))}, headers=auth("analyst"))
    assert r.status_code == 201 and r.json()["version"] == 1 and r.json()["summary"]["rows"] == 8
    rid = r.json()["id"]
    assert api.post(base, files={"file": ("a.xlsx", asset_workbook(1))}, headers=auth("analyst")).status_code == 409
    assert api.post(base, files={"file": ("a.xlsx", asset_workbook(2))}, headers=auth("analyst")).json()["version"] == 2
    listed = api.get(base, headers=auth("viewer")).json()
    assert [(x["version"], x["current"]) for x in listed] == [(2, True), (1, False)]
    rows = api.get(f"{base}/{rid}/assets?location=Head", headers=auth("viewer")).json()["rows"]
    assert [x["asset_number"] for x in rows] == ["10002", "10003"] and rows[0]["in_service_raw"] == "31-07-2024"
    assert api.get(f"{base}/{rid}/assets?category=Chairs-1", headers=auth("viewer")).json()["rows"][0]["asset_number"] == "10000"
    assert api.get(f"{base}/{rid}/file", headers=auth("analyst")).status_code == 403 and api.get(f"{base}/{rid}/file", headers=auth("admin")).status_code == 200
    assert api.patch(f"{base}/{rid}", json={"notes": "n"}, headers=auth("analyst")).status_code == 403
    assert api.patch(f"{base}/{rid}", json={"description": "x"}, headers=auth("admin")).status_code == 422
    assert api.patch(f"{base}/{rid}", json={"notes": "first export, not up to date"}, headers=auth("admin")).json()["notes"] == "first export, not up to date"
    assert api.delete(f"{base}/{rid}", headers=auth("admin")).status_code == 405              # versions are never deleted from here
    d = api.post(base, files={"file": ("reg.pdf", regulation_pdf(2))}, data={"kind": "regulation", "series": "admin_regulation", "as_of": "2025-01-01"}, headers=auth("analyst"))
    assert d.status_code == 201, d.text
    did = d.json()["id"]
    info = api.get(f"{base}/{did}", headers=auth("viewer")).json()
    assert info["status"] == "ready" and info["summary"]["pages"] == 2
    assert "Article 1" in api.get(f"{base}/{did}/pages/1", headers=auth("viewer")).json()["text"] and api.get(f"{base}/{did}/pages/9", headers=auth("viewer")).status_code == 404
    assert api.get(f"{base}/{did}/assets", headers=auth("viewer")).status_code == 409
