from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.core.kpi.engine import compute_kpi
from app.db import get_session
from app.main import app
from app.models import DimBranch, DimPeriod, DimSupplier, FactPoLine, FactSavings


def _seed(session):
    for m in (1, 2):
        session.add(DimPeriod(period=date(2025, m, 1), year=2025, quarter=1, month=m, fiscal_year=2025))
    session.add_all([DimBranch(id=1, code="A"), DimBranch(id=2, code="B"), DimSupplier(id=1, code="S1", name="S1")])
    session.flush()

    def line(po, n, m, branch, amt):
        session.add(FactPoLine(po_number=po, line_number=n, po_date=date(2025, m, 5), period=date(2025, m, 1),
                               branch_id=branch, supplier_id=1, quantity=1, unit_price=amt, line_amount=amt))
    line("P1", 1, 1, 1, 100); line("P1", 2, 1, 1, 300); line("P2", 1, 1, 2, 200); line("P3", 1, 2, 1, 400)
    session.add(FactSavings(period=date(2025, 1, 1), savings_type="negotiation",
                            baseline_amount=1000, actual_amount=900, savings_amount=100))
    session.commit()


def test_kpis(session, po_spec):
    _seed(session)
    assert compute_kpi(session, po_spec, "total_spend")[None] == 1000
    assert compute_kpi(session, po_spec, "po_count")[None] == 3
    assert compute_kpi(session, po_spec, "avg_po_value")[None] == pytest.approx(1000 / 3)
    assert compute_kpi(session, po_spec, "total_spend", group_by="branch") == {1: 800, 2: 200}
    jan = compute_kpi(session, po_spec, "total_spend", date(2025, 1, 1), date(2025, 1, 31), "period")
    assert jan == {date(2025, 1, 1): 600}
    assert compute_kpi(session, po_spec, "savings_rate")[None] == pytest.approx(10.0)


def test_kpi_unsupported_grouping(session, po_spec):
    _seed(session)
    with pytest.raises(ValueError, match="cannot be grouped"):
        compute_kpi(session, po_spec, "total_savings", group_by="branch")


@pytest.fixture
def client(session):
    app.dependency_overrides[get_session] = lambda: (yield session)
    # skip lifespan DB sync: build client without context manager
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_api_modules_and_upload_flow(client):
    assert client.get("/api/health").json() == {"status": "ok"}
    assert client.get("/api/modules").json()[0]["id"] == "purchase_orders"
    assert client.get("/api/modules/nope").status_code == 404
    csv_bytes = (__import__("pathlib").Path(__file__).parent / "fixtures" / "po_sample.csv").read_bytes()
    r = client.post("/api/imports", data={"module_id": "purchase_orders"}, files={"file": ("po.csv", csv_bytes)})
    assert r.status_code == 201
    body = r.json()
    assert body["suggested_mapping"]["Vendor"]["field"] == "supplier"
    bid = body["batch_id"]
    assert client.post("/api/imports", data={"module_id": "purchase_orders"}, files={"file": ("po.csv", csv_bytes)}).status_code == 409
    assert client.post(f"/api/imports/{bid}/load").status_code == 409  # not validated yet
    v = client.post(f"/api/imports/{bid}/validate").json()
    assert (v["rows_valid"], v["rows_rejected"]) == (3, 2)
    # first load: branches are unknown → everything held for review, nothing loaded
    loaded = client.post(f"/api/imports/{bid}/load").json()
    assert (loaded["rows_loaded"], loaded["rows_held"], loaded["status"]) == (0, 3, "partially_loaded")
    pending = client.get("/api/aliases").json()
    assert {a["raw"] for a in pending} == {"Branch A", "Branch B"}
    for a in pending:
        assert client.post(f"/api/aliases/{a['id']}/resolve", json={"create_new": True}).status_code == 200
    assert client.post(f"/api/aliases/{pending[0]['id']}/resolve", json={}).status_code == 422
    loaded = client.post(f"/api/imports/{bid}/load").json()
    assert (loaded["rows_loaded"], loaded["rows_held"], loaded["status"]) == (3, 0, "loaded")
    pos = client.get("/api/purchase-orders").json()
    assert {p["po_number"] for p in pos} == {"PO-0001", "PO-0002"}
    detail = client.get(f"/api/purchase-orders/{pos[0]['id']}").json()
    assert detail["documents"][0]["type"] == "purchase_order" and "quotation" in detail["missing_required_documents"]
    assert client.get("/api/kpis/purchase_orders/total_spend").json()["values"][0]["value"] == 9550 + 450 + 2400
    assert client.post(f"/api/imports/{bid}/rollback").json()["status"] == "rolled_back"
    assert client.get("/api/kpis/purchase_orders/total_spend").json()["values"][0]["value"] is None
    assert client.get(f"/api/imports/{bid}").json()["issues"]
