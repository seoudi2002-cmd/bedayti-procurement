from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.core.cleaning.normalizers import excel_error, parse_date, text_from_cell
from app.db import get_session
from app.main import app
from tests.helpers import branch_workbook, employee_workbook, xlsx


@pytest.fixture
def api(session, monkeypatch):
    monkeypatch.setenv("API_TOKENS", "tk-admin:admin:alice,tk-analyst:analyst:bob,tk-viewer:viewer:carol")
    get_settings.cache_clear()
    app.dependency_overrides[get_session] = lambda: (yield session)
    yield TestClient(app)
    app.dependency_overrides.clear()
    monkeypatch.delenv("API_TOKENS")
    get_settings.cache_clear()


def auth(role):
    return {"Authorization": f"Bearer tk-{role}"}


def test_requests_without_valid_token_are_refused(api):
    assert api.get("/api/modules").status_code == 401
    assert api.get("/api/modules", headers={"Authorization": "Bearer nope"}).status_code == 401
    assert api.get("/api/modules", headers=auth("viewer")).status_code == 200


def test_fails_closed_outside_development_without_tokens(session, monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("API_TOKENS", raising=False)
    get_settings.cache_clear()
    app.dependency_overrides[get_session] = lambda: (yield session)
    try:
        assert TestClient(app).get("/api/modules").status_code == 401
    finally:
        app.dependency_overrides.clear()
        monkeypatch.delenv("APP_ENV")
        get_settings.cache_clear()


def test_roles_gate_writes_and_personal_data(api):
    csv = b"x,y\n1,2\n"
    files = {"file": ("a.csv", csv)}
    assert api.post("/api/imports", data={"module_id": "purchase_orders"}, files=files, headers=auth("viewer")).status_code == 403
    # a personal-data module cannot even be staged by an analyst
    emp = {"file": ("hr.xlsx", employee_workbook([[1, "Employee One", date(2024, 1, 1), "x", "y", "z"]]))}
    assert api.post("/api/imports", data={"module_id": "employees"}, files=emp, headers=auth("analyst")).status_code == 403
    r = api.post("/api/imports", data={"module_id": "employees"}, files=emp, headers=auth("admin"))
    assert r.status_code == 201
    bid = r.json()["batch_id"]
    assert api.get(f"/api/imports/{bid}", headers=auth("analyst")).status_code == 403  # raw HR rows/issues: admin only
    assert api.post(f"/api/imports/{bid}/validate", headers=auth("admin")).status_code == 200
    assert api.post(f"/api/imports/{bid}/load", headers=auth("admin")).json()["warnings"][0]["code"] == "data_freshness"
    assert api.get("/api/employees", headers=auth("analyst")).status_code == 403
    listed = api.get("/api/employees", headers=auth("admin")).json()
    assert listed[0]["missing_fields"] == ["department", "cost_center", "manager"]


def test_branch_listing_exposes_no_personal_data_and_flags_headcount_freshness(api):
    r = api.post("/api/imports", data={"module_id": "branches"}, files={"file": ("b.xlsx", branch_workbook())}, headers=auth("admin"))
    bid = r.json()["batch_id"]
    api.post(f"/api/imports/{bid}/validate", headers=auth("admin"))
    api.post(f"/api/imports/{bid}/load", headers=auth("admin"))
    body = api.get("/api/branches", headers=auth("viewer")).json()
    assert body["headcount_warnings"][0]["code"] == "hr_not_loaded"
    text = str(body)
    assert "مدير فرع" not in text and "a@x.test" not in text and "553413434" not in text  # no managers/phones/e-mail
    first = next(b for b in body["branches"] if b["name_ar"] == "ابوحماد")
    assert api.get(f"/api/branches/{first['id']}/contact", headers=auth("analyst")).status_code == 403
    contact = api.get(f"/api/branches/{first['id']}/contact", headers=auth("admin")).json()
    assert contact["branch_manager_name_source"] == "مدير فرع واحد"
    assert {b["system_key"] for b in body["branches"]} >= {"HEAD_OFFICE", "UNALLOCATED"}


def test_intake_identifies_module_and_profile_per_sheet(api):
    from tests.helpers import PO_HEADER, REQ_HEADER, SUPPLIER_HEADER
    book = xlsx({"سجل الموردين": [SUPPLIER_HEADER], "اشعارات الاحتياج": [REQ_HEADER], "اوامر الشراء": [PO_HEADER],
                 "random": [["foo", "bar"], [1, 2]]})
    r = api.post("/api/intake/analyze", files={"file": ("w.xlsx", book)}, headers=auth("analyst"))
    got = {s["sheet"]: s["recommended"] for s in r.json()["sheets"]}
    assert (got["سجل الموردين"]["module_id"], got["سجل الموردين"]["profile"]) == ("suppliers", "default")
    assert got["اشعارات الاحتياج"]["module_id"] == "requisitions"
    assert (got["اوامر الشراء"]["module_id"], got["اوامر الشراء"]["profile"]) == ("purchase_orders", "register")
    assert got["random"] is None  # unknown layouts are not forced onto a module


def test_word_and_pdf_are_not_silently_accepted(api):
    r = api.post("/api/intake/analyze", files={"file": ("doc.pdf", b"%PDF-1.4")}, headers=auth("analyst"))
    assert r.status_code == 415 and "extractor" in r.json()["detail"]


def test_exceptions_api_and_decision(api):
    r = api.post("/api/imports", data={"module_id": "branches"}, files={"file": ("b.xlsx", branch_workbook())}, headers=auth("admin"))
    bid = r.json()["batch_id"]
    api.post(f"/api/imports/{bid}/validate", headers=auth("admin"))
    api.post(f"/api/imports/{bid}/load", headers=auth("admin"))
    assert api.get("/api/exceptions", headers=auth("viewer")).status_code == 403
    items = api.get("/api/exceptions", params={"code": "branch_shared_email"}, headers=auth("analyst")).json()
    assert len(items) == 1
    done = api.post(f"/api/exceptions/{items[0]['id']}/decide", json={"status": "accepted", "note": "shared inbox"}, headers=auth("analyst"))
    assert done.json()["decided_by"] == "bob"
    assert api.get("/api/exceptions", params={"code": "branch_shared_email"}, headers=auth("analyst")).json() == []
    assert api.post(f"/api/exceptions/{items[0]['id']}/decide", json={"status": "bogus"}, headers=auth("analyst")).status_code == 422


# ---------------------------------------------------------------- cleaning helpers
def test_iso_datetime_text_is_parsed_as_a_date():
    assert parse_date("2026-05-12T00:00:00") == date(2026, 5, 12)  # how staged Excel dates are stored
    assert parse_date("2026-05-12 00:00:00") == date(2026, 5, 12)


def test_text_from_cell_and_excel_errors():
    assert text_from_cell(160130.0) == "160130" and text_from_cell(553413434) == "553413434"
    assert text_from_cell("  a   b ") == "a b" and text_from_cell(None) is None
    assert excel_error("#N/A") == "#N/A" and excel_error(" #ref! ") == "#REF!" and excel_error("n/a") is None
