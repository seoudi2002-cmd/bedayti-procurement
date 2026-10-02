from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.core.documents import DocumentLinkError, attach_document, case_overview
from app.core.entities import resolve_alias
from app.core.ingestion.pipeline import stage_file, validate_batch
from app.models import (
    DimBranch, DimSupplier, EntityAlias, FactCost, FactPoLine, PoHeader, ProcurementCase, ProcurementDocument,
)
from app.modules.purchase_orders import loader

FIXTURE = Path(__file__).parent / "fixtures" / "po_multiline.csv"


def _count(session, model):
    return session.scalar(select(func.count()).select_from(model))


@pytest.fixture
def branches(session):
    """Branches (synthetic, no codes - the platform never invents them) and the supplier register."""
    session.add_all([DimBranch(name_en="Head Office", branch_type="branch"), DimBranch(name_en="Branch North", branch_type="branch"),
                     DimSupplier(code="S1", name="Vendor Alpha"), DimSupplier(code="S2", name="Vendor Beta"),
                     DimSupplier(code="S3", name="Vendor Gamma")])
    session.commit()


def _batch(session, po_spec, content=None, name="po.csv"):
    batch, table = stage_file(session, po_spec, name, content or FIXTURE.read_bytes())
    validate_batch(session, po_spec, batch, headers=table.headers)
    return batch


def test_validation_derives_amount_and_checks_fixture(session, po_spec):
    batch = _batch(session, po_spec)
    assert (batch.rows_valid, batch.rows_rejected) == (4, 0)


def test_load_builds_headers_lines_costs_and_anchors(session, po_spec, branches):
    batch = _batch(session, po_spec)
    # "Branch Nrth" is a typo of "Branch North": near-match → held for review, never silently merged
    loader.load(session, batch)
    assert (batch.rows_loaded, batch.rows_held, batch.status) == (3, 1, "partially_loaded")
    assert _count(session, PoHeader) == 2  # PO 35 and 36 loaded, PO 37 held
    h35 = session.scalar(select(PoHeader).where(PoHeader.po_number == "35"))
    assert (h35.fiscal_year, float(h35.total_amount), h35.payment_days, h35.purchase_method) == (2026, 634500.0, 60, "Negotiated")
    h36 = session.scalar(select(PoHeader).where(PoHeader.po_number == "36"))
    assert float(h36.total_amount) == 100 * 0 + 20 * 120 + 5 * 30
    assert _count(session, FactPoLine) == 3 and _count(session, FactCost) == 3
    assert _count(session, ProcurementCase) == 2
    assert session.scalar(select(ProcurementDocument.doc_type).where(ProcurementDocument.po_header_id == h35.id)) == "purchase_order"
    cc = session.scalar(select(FactCost).where(FactCost.attrs["po_number"].as_string() == "35"))
    assert cc.cost_center_id is not None and float(cc.amount) == 634500.0


def test_review_then_reload_completes_and_is_idempotent(session, po_spec, branches):
    batch = _batch(session, po_spec)
    loader.load(session, batch)
    alias = session.scalar(select(EntityAlias).where(EntityAlias.status == "pending"))
    assert alias.entity_type == "branch" and alias.alias_raw == "Branch Nrth" and alias.entity_id is not None
    north = session.scalar(select(DimBranch).where(DimBranch.name_en == "Branch North"))
    assert alias.entity_id == north.id  # suggestion points at the right branch
    resolve_alias(session, alias, entity_id=north.id)
    loader.load(session, batch)
    assert (batch.rows_loaded, batch.rows_held, batch.status) == (4, 0, "loaded")
    loader.load(session, batch)  # reload: no duplicates
    assert (_count(session, PoHeader), _count(session, FactPoLine), _count(session, FactCost)) == (3, 4, 4)


def test_same_po_number_in_two_fiscal_years_are_distinct(session, po_spec, branches):
    csv_2025 = (b"FY,PO No,Date,Branch,Vendor,Qty,Price\n2025,35,10/03/2025,Head Office,Vendor Alpha,10,100\n"
                b"2026,35,10/03/2026,Head Office,Vendor Alpha,20,100\n")
    loader.load(session, _batch(session, po_spec, csv_2025, "fy.csv"))
    assert sorted((h.fiscal_year, float(h.total_amount)) for h in session.scalars(select(PoHeader))) == [(2025, 1000.0), (2026, 2000.0)]


def test_fiscal_year_derived_from_date_when_column_missing(session, po_spec, branches):
    csv = b"PO No,Date,Branch,Vendor,Qty,Price\n7,10/03/2026,Head Office,Vendor Alpha,1,50\n"
    loader.load(session, _batch(session, po_spec, csv, "nofy.csv"))
    assert session.scalar(select(PoHeader.fiscal_year)) == 2026


def test_cumulative_reexport_updates_instead_of_duplicating(session, po_spec, branches):
    first = b"FY,PO No,Line,Date,Branch,Vendor,Qty,Price\n2026,1,1,01/02/2026,Head Office,Vendor Alpha,10,100\n"
    second = first + b"2026,1,2,01/02/2026,Head Office,Vendor Alpha,5,40\n2026,2,1,05/02/2026,Head Office,Vendor Beta,1,10\n"
    loader.load(session, _batch(session, po_spec, first, "jan.csv"))
    loader.load(session, _batch(session, po_spec, second, "feb.csv"))
    assert (_count(session, PoHeader), _count(session, FactPoLine)) == (2, 3)
    assert float(session.scalar(select(PoHeader.total_amount).where(PoHeader.po_number == "1"))) == 1200.0
    assert _count(session, DimSupplier) == 3  # the seeded register only; none invented


def test_inconsistent_supplier_within_po_is_rejected(session, po_spec, branches):
    csv = (b"FY,PO No,Line,Date,Branch,Vendor,Qty,Price\n2026,9,1,01/02/2026,Head Office,Vendor Alpha,1,1\n"
           b"2026,9,2,01/02/2026,Head Office,Vendor Beta,1,1\n")
    batch = _batch(session, po_spec, csv, "bad.csv")
    loader.load(session, batch)
    assert (batch.rows_loaded, batch.rows_rejected) == (0, 2) and _count(session, PoHeader) == 0


def test_rollback_removes_batch_and_allows_reupload(session, po_spec, branches):
    batch = _batch(session, po_spec)
    loader.load(session, batch)
    loader.rollback(session, batch)
    assert batch.status == "rolled_back"
    assert (_count(session, PoHeader), _count(session, FactPoLine), _count(session, FactCost), _count(session, ProcurementCase)) == (0, 0, 0, 0)
    again, _ = stage_file(session, po_spec, "po.csv", FIXTURE.read_bytes())  # not blocked as duplicate
    assert again.id != batch.id


def test_attach_documents_builds_case_timeline(session, po_spec, branches):
    loader.load(session, _batch(session, po_spec))
    attach_document(session, po_spec, "requisition", fiscal_year=2026, po_number="35", doc_number="35", amount=621000,
                    attrs={"estimated_unit_price": 690})
    attach_document(session, po_spec, "supplier_invoice", fiscal_year=2026, requisition_no="35", doc_number="INV-1",
                    amount=634500, attrs={"po_reference": None})
    h = session.scalar(select(PoHeader).where(PoHeader.po_number == "35"))
    ov = case_overview(session, po_spec, h.case_id)
    assert [d.doc_type for d in ov["documents"]] == ["requisition", "purchase_order", "supplier_invoice"]
    assert ov["current_stage"] == "supplier_invoice"
    assert {"quotation", "committee_approval", "inspection_acceptance", "payment_request"} <= set(ov["missing_required"])
    with pytest.raises(DocumentLinkError):
        attach_document(session, po_spec, "nonsense", fiscal_year=2026, po_number="35")
    with pytest.raises(DocumentLinkError):
        attach_document(session, po_spec, "requisition", fiscal_year=2026, po_number="999")


def test_kpis_after_load(session, po_spec, branches):
    from app.core.kpi.engine import compute_kpi
    loader.load(session, _batch(session, po_spec))
    assert compute_kpi(session, po_spec, "total_spend")[None] == pytest.approx(634500 + 2400 + 150)
    assert compute_kpi(session, po_spec, "po_count")[None] == 2
