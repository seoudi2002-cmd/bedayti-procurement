from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import get_settings
from app.core import overrides as ov
from app.db import get_session
from app.main import app
from app.models import DataException, DataOverride, DimBranch, FactCost, PoHeader, RawRow
from tests.test_master_data import run
from tests.test_procurement_registers import base, headers, po_book, po_row  # noqa: F401  (base is a fixture)


def register_with_bad_date(session):
    rows = [po_row(1, "55/2026", datetime(2062, 9, 6), "Alpha Co", 1, "x", "55/2026", 500),
            po_row(2, "56/2026", datetime(2026, 5, 1), "Alpha Co", 1, "y", "56/2026", 100, 250)]
    return run(session, "purchase_orders", po_book(rows), profile="register")


def header(session, n="55"):
    return session.scalar(select(PoHeader).where(PoHeader.po_number == n))


def status(session, code, key):
    return session.scalar(select(DataException.status).where(DataException.code == code, DataException.entity_key == key))


def test_correction_keeps_original_and_only_approved_value_applies(session, base):
    register_with_bad_date(session)
    h = header(session)
    assert h.po_date is None and h.period is None and session.scalar(select(FactCost).where(FactCost.attrs["po_number"].as_string() == "55")) is None
    c = ov.propose(session, "po_header", "2026/55", "po_date", "2026-09-06", "typo: year 2062 should be 2026", "alice")
    assert (c.status, c.original_value, c.corrected_value) == ("proposed", "2062-09-06T00:00:00", "2026-09-06")
    session.refresh(h)
    assert h.po_date is None  # proposals change nothing
    ov.approve(session, c.id, "bob", "checked against the PO document")
    session.refresh(h)
    assert str(h.po_date) == "2026-09-06" and str(h.period) == "2026-09-01"
    assert h.po_date_source == "2062-09-06T00:00:00"  # the source text is still there
    assert status(session, "po_date_invalid", "2026/55") == "resolved"
    assert float(session.scalar(select(FactCost.amount).where(FactCost.attrs["po_number"].as_string() == "55"))) == 500  # now in spend
    done = session.get(DataOverride, c.id)
    assert (done.proposed_by, done.reviewed_by, done.reason) == ("alice", "bob", "typo: year 2062 should be 2026")
    assert done.created_at is not None and done.reviewed_at is not None


def test_correction_survives_reload_and_can_be_reverted(session, base):
    b = register_with_bad_date(session)
    c = ov.propose(session, "po_header", "2026/55", "po_date", "2026-09-06", "typo", "alice", auto_approve=True)
    from app.core.modules.loader import get_loader
    get_loader("purchase_orders").load(session, b)  # source says 2062 again, correction must win
    session.refresh(header(session))
    assert str(header(session).po_date) == "2026-09-06"
    ov.revert(session, c.id, "alice", "was wrong")
    session.refresh(header(session))
    assert header(session).po_date is None  # back to the source's (invalid) value
    assert session.get(DataOverride, c.id).status == "reverted"
    assert session.scalar(select(FactCost).where(FactCost.attrs["po_number"].as_string() == "55")) is None


def test_second_correction_supersedes_first_and_original_stays_the_source_value(session, base):
    register_with_bad_date(session)
    a = ov.propose(session, "po_header", "2026/56", "total_amount", "120", "first fix", "alice", auto_approve=True)
    b = ov.propose(session, "po_header", "2026/56", "total_amount", "130", "second fix", "alice", auto_approve=True)
    assert b.original_value == "100.00" or b.original_value == "100"  # source value, not 120
    assert session.get(DataOverride, a.id).status == "superseded"
    assert float(header(session, "56").total_amount) == 130
    # handover (250) vs corrected total: exception reflects the working value
    assert status(session, "finance_handover_amount_exceeds_total", "2026/56") == "open"
    ov.propose(session, "po_header", "2026/56", "total_amount", "300", "total was 300", "alice", auto_approve=True)
    assert status(session, "finance_handover_amount_exceeds_total", "2026/56") == "resolved"


def test_branch_correction_is_confirmed_and_not_overwritten_by_attribution(session, base):
    b = register_with_bad_date(session)
    assert header(session).branch_attribution_status == "needs_review"
    belina = session.scalar(select(DimBranch.id).where(DimBranch.name_ar == "البلينا"))
    ov.propose(session, "po_header", "2026/55", "branch_id", str(belina), "delivery note names the branch", "alice", auto_approve=True)
    h = header(session)
    assert (h.branch_id, h.branch_attribution_status, h.branch_attribution_method) == (belina, "confirmed", "manual_override")
    assert status(session, "po_branch_not_identified", "2026/55") == "resolved"
    from app.core.modules.loader import get_loader
    get_loader("purchase_orders").load(session, b)  # re-attribution must respect the confirmation
    assert header(session).branch_attribution_status == "confirmed" and header(session).branch_id == belina


def test_guards(session, base, monkeypatch):
    register_with_bad_date(session)
    with pytest.raises(ov.OverrideError, match="reason"):
        ov.propose(session, "po_header", "2026/55", "po_date", "2026-09-06", " ", "alice")
    with pytest.raises(ov.OverrideError, match="cannot be corrected"):
        ov.propose(session, "po_header", "2026/55", "description_source", "x", "r", "alice")
    with pytest.raises(ov.OverrideError, match="not available"):
        ov.propose(session, "dim_employee", "1", "full_name", "x", "r", "alice")
    with pytest.raises(ov.OverrideError, match="not found"):
        ov.propose(session, "po_header", "2026/999", "po_date", "2026-01-01", "r", "alice")
    with pytest.raises(ov.OverrideError, match="does not exist"):
        ov.propose(session, "po_header", "2026/55", "branch_id", "99999", "r", "alice")
    with pytest.raises(ov.OverrideError, match="implausible"):
        ov.propose(session, "po_header", "2026/55", "po_date", "2062-01-01", "r", "alice")
    c = ov.propose(session, "po_header", "2026/55", "po_date", "2026-09-06", "typo", "alice")
    monkeypatch.setenv("ALLOW_SELF_APPROVAL", "false")
    get_settings.cache_clear()
    with pytest.raises(ov.OverrideError, match="different user"):
        ov.approve(session, c.id, "alice")
    ov.reject(session, c.id, "bob", "not convinced")
    assert session.get(DataOverride, c.id).status == "rejected" and header(session).po_date is None
    with pytest.raises(ov.OverrideError):
        ov.approve(session, c.id, "bob")  # rejected corrections cannot be approved later
    monkeypatch.delenv("ALLOW_SELF_APPROVAL")
    get_settings.cache_clear()


def test_source_row_correction_releases_conflicting_rows(session, base):
    rows = [po_row(1, "36/2026", datetime(2026, 5, 3), "Alpha Co", 1, "AC units", "36/2026", 200),
            po_row(2, "36/2026", datetime(2026, 5, 11), "Beta Co", 2, "office supplies", "34/2026", 50)]
    b = run(session, "purchase_orders", po_book(rows), profile="register")
    assert (b.rows_loaded, b.rows_held) == (0, 2)
    c = ov.propose_row_correction(session, b, 3, "po_ref", "34/2026", "requisition 34 shows this is PO 34", "alice")
    assert c.original_value == "36/2026"
    from app.core.modules.loader import get_loader
    get_loader("purchase_orders").load(session, b)
    assert b.rows_held == 2  # a proposal alone changes nothing
    ov.approve(session, c.id, "alice")
    get_loader("purchase_orders").load(session, b)
    assert (b.rows_loaded, b.rows_held, b.status) == (2, 0, "loaded")
    assert set(headers(session)) == {(2026, "36"), (2026, "34")}
    raw = session.scalar(select(RawRow).where(RawRow.batch_id == b.id, RawRow.row_number == 3))
    assert raw.payload["رقم امر الشراء"] == "36/2026"  # the raw staged row is untouched
    ov.revert(session, c.id, "alice")
    get_loader("purchase_orders").load(session, b)
    assert b.rows_held == 2  # reverting restores the conflict


@pytest.fixture
def api(session):
    app.dependency_overrides[get_session] = lambda: (yield session)
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_corrections_api_roundtrip(api, session, base):
    register_with_bad_date(session)
    r = api.post("/api/corrections", json={"entity_type": "po_header", "entity_key": "2026/55", "field": "po_date",
                                           "corrected_value": "2026-09-06", "reason": "typo"})
    assert r.status_code == 201 and r.json()["status"] == "proposed" and r.json()["original_value"].startswith("2062")
    cid = r.json()["id"]
    assert api.post("/api/corrections", json={"entity_type": "po_header", "entity_key": "2026/55", "field": "nope",
                                              "corrected_value": "1", "reason": "x"}).status_code == 422
    assert api.post(f"/api/corrections/{cid}/approve", json={"note": "ok"}).json()["status"] == "approved"
    po = next(p for p in api.get("/api/purchase-orders").json() if p["po_number"] == "55")
    detail = api.get(f"/api/purchase-orders/{po['id']}").json()
    assert detail["po_date"] == "2026-09-06" and detail["po_date_source"].startswith("2062")
    assert detail["corrections"][0]["original_value"].startswith("2062") and detail["corrections"][0]["reason"] == "typo"
    assert api.get("/api/corrections", params={"status": "approved"}).json()[0]["reviewed_by"] == "local-dev"
    assert api.post(f"/api/corrections/{cid}/revert", json={}).json()["status"] == "reverted"


def test_cancelled_status_is_flagged_but_still_in_spend(session, base):
    from app.core.kpi.engine import compute_kpi
    from app.core.modules.registry import get_registry
    rows = [po_row(1, "7/2026", datetime(2026, 3, 1), "Alpha Co", 1, "x", "7/2026", 100, status="الطلب ملغي"),
            po_row(2, "8/2026", datetime(2026, 3, 1), "Alpha Co", 1, "y", "8/2026", 50)]
    run(session, "purchase_orders", po_book(rows), profile="register")
    flagged = {e.entity_key for e in session.scalars(select(DataException).where(DataException.code == "po_status_indicates_cancellation"))}
    assert flagged == {"2026/7"}
    assert compute_kpi(session, get_registry().get("purchase_orders"), "total_spend")[None] == 150  # not excluded
