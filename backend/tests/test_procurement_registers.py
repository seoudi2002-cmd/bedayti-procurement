from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.core.attribution import BranchAttributor
from app.core.kpi.engine import compute_kpi
from app.core.loader_utils import parse_number_year
from app.core.modules.registry import get_registry
from app.core.system_seed import UNALLOCATED, ensure_system_branches
from app.models import (
    DataException, DimBranch, DimSupplier, FactCost, FinanceHandover, PoHeader, ProcurementCase, ProcurementDocument,
    Requisition,
)
from tests.helpers import HANDOVER_HEADER, PO_HEADER, REQ_HEADER, xlsx
from tests.test_master_data import run


@pytest.fixture
def base(session):
    """Branches (no codes), the supplier register and the system rows."""
    ensure_system_branches(session)
    session.add_all([DimBranch(name_ar="البلينا", branch_type="branch"), DimBranch(name_ar="الواسطي", branch_type="branch"),
                     DimSupplier(code="SUP001", register_no=1, name="Alpha Co"),
                     DimSupplier(code="SUP002", register_no=2, name="Beta Co"),
                     DimSupplier(code="SUP003", register_no=3, name="Gamma Co"),
                     DimSupplier(code="SUP004", register_no=3, name="Delta Co")])  # register no. 3 is shared
    session.commit()


def po_book(rows):
    return xlsx({"اوامر الشراء": [PO_HEADER, *rows]})


def po_row(n, ref, date_, supplier, regno, desc, req, total, handed=None, status="تم إصدار أمر الشراء"):
    return [n, ref, date_, supplier, regno, "cat", desc, req, "pocat", "تم إصدار أمر الشراء", total, status, handed, None]


def headers(session):
    return {(h.fiscal_year, h.po_number): h for h in session.scalars(select(PoHeader))}


def codes(session):
    return {(e.code, e.entity_key) for e in session.scalars(select(DataException))}


def test_parse_number_year():
    assert parse_number_year("35/2026") == ("35", 2026)
    assert parse_number_year(" 07 / 2026 ") == ("7", 2026)
    assert parse_number_year("35") is None and parse_number_year("abc") is None and parse_number_year(None) is None


# ---------------------------------------------------------------- PO register
def test_register_loads_header_level_and_flags_without_modifying_source(session, base):
    rows = [po_row(1, "1/2026", datetime(2026, 1, 12), "Alpha Co", 1, "شراء ورق", "1/2026", 1000, 1000),
            po_row(2, "2/2026", datetime(2062, 9, 6), "Beta Co", 2, "شراء شاشات", "2/2026", 500),         # invalid date
            po_row(3, "3/2026", datetime(2026, 2, 1), None, None, "طلب ملغي", "3/2026", None, status="الطلب ملغي"),  # unpriced, no supplier
            po_row(4, "4/2026", datetime(2026, 2, 2), "Alpha Co", 1, "شراء", "4/2026", 100, 150)]         # handover > total
    b = run(session, "purchase_orders", po_book(rows), profile="register")
    assert (b.rows_loaded, b.rows_held) == (4, 0)
    h = headers(session)
    assert h[(2026, "1")].granularity == "header_only" and float(h[(2026, "1")].total_amount) == 1000
    # invalid date: NULL + raw kept, flagged, excluded from spend (no period)
    assert h[(2026, "2")].po_date is None and "2062" in h[(2026, "2")].po_date_source
    assert ("po_date_invalid", "2026/2") in codes(session)
    # missing total stays NULL (not 0) and is not counted as spend
    assert h[(2026, "3")].total_amount is None and ("po_total_missing", "2026/3") in codes(session)
    assert ("po_supplier_missing", "2026/3") in codes(session)
    # handover > total is an exception, and it is NOT called "paid"
    assert float(h[(2026, "4")].finance_handover_amount_register) == 150
    assert ("finance_handover_amount_exceeds_total", "2026/4") in codes(session)
    # spend: PO1 (1000) + PO4 (100); PO2 has no valid date, PO3 no total
    assert compute_kpi(session, get_registry().get("purchase_orders"), "total_spend")[None] == 1100
    assert compute_kpi(session, get_registry().get("purchase_orders"), "po_count")[None] == 4
    assert compute_kpi(session, get_registry().get("purchase_orders"), "priced_po_count")[None] == 3


def test_duplicate_po_number_is_held_for_manual_review(session, base):
    rows = [po_row(1, "36/2026", datetime(2026, 5, 3), "Alpha Co", 1, "AC units", "36/2026", 200),
            po_row(2, "36/2026", datetime(2026, 5, 11), "Beta Co", 2, "office supplies", "34/2026", 50),
            po_row(3, "37/2026", datetime(2026, 5, 12), "Alpha Co", 1, "x", "37/2026", 10)]
    b = run(session, "purchase_orders", po_book(rows), profile="register")
    assert (b.rows_loaded, b.rows_held, b.status) == (1, 2, "partially_loaded")
    assert set(headers(session)) == {(2026, "37")}  # neither conflicting row is loaded or merged
    ex = session.scalar(select(DataException).where(DataException.code == "po_number_conflict"))
    assert ex.entity_key == "2026/36" and ex.details["rows"] == [2, 3]  # excel rows (header is row 1)


def test_supplier_by_register_number_with_name_crosscheck(session, base):
    rows = [po_row(1, "1/2026", datetime(2026, 1, 1), "Alpha Co", 1, "x", "1/2026", 10),
            po_row(2, "2/2026", datetime(2026, 1, 2), "Wrong Name", 2, "x", "2/2026", 10),          # id decides, name flagged
            po_row(3, "3/2026", datetime(2026, 1, 3), "Delta Co", 3, "x", "3/2026", 10),            # shared reg no: name decides
            po_row(4, "4/2026", datetime(2026, 1, 4), "Whoever", 3, "x", "4/2026", 10),             # shared reg no: ambiguous
            po_row(5, "5/2026", datetime(2026, 1, 5), "Nobody", 99, "x", "5/2026", 10)]             # not in register
    run(session, "purchase_orders", po_book(rows), profile="register")
    h = headers(session)
    sup = {s.id: s.code for s in session.scalars(select(DimSupplier))}
    assert sup[h[(2026, "1")].supplier_id] == "SUP001"
    assert sup[h[(2026, "2")].supplier_id] == "SUP002" and ("po_supplier_name_mismatch", "2026/2") in codes(session)
    assert sup[h[(2026, "3")].supplier_id] == "SUP004"
    assert h[(2026, "4")].supplier_id is None and ("po_supplier_ambiguous_register_no", "2026/4") in codes(session)
    assert h[(2026, "5")].supplier_id is None and ("po_supplier_register_no_not_found", "2026/5") in codes(session)
    assert len(session.scalars(select(DimSupplier)).all()) == 4  # nothing invented


def test_branch_attribution_hierarchy_is_explicit_and_audited(session, base):
    rows = [po_row(1, "1/2026", datetime(2026, 1, 1), "Alpha Co", 1, "تجهيز فرع البلينا بالأجهزة", "1/2026", 10),       # explicit branch
            po_row(2, "2/2026", datetime(2026, 1, 2), "Alpha Co", 1, "شراء أثاث للمركز الرئيسي", "2/2026", 10),        # explicit HQ
            po_row(3, "3/2026", datetime(2026, 1, 3), "Alpha Co", 1, "أدوات لعدد 100 فرع + المركز الرئيسي", "3/2026", 10),  # plural → review
            po_row(4, "4/2026", datetime(2026, 1, 4), "Alpha Co", 1, "شراء ورق", "4/2026", 10),                        # nothing → review
            po_row(5, "5/2026", datetime(2026, 1, 5), "Alpha Co", 1, "لفرع البلينا وفرع الواسطي", "5/2026", 10)]      # two branches → review
    run(session, "purchase_orders", po_book(rows), profile="register")
    h = headers(session)
    name = {b.id: b.name_ar or b.name_en for b in session.scalars(select(DimBranch))}
    unalloc = session.scalar(select(DimBranch.id).where(DimBranch.system_key == UNALLOCATED))
    assert name[h[(2026, "1")].branch_id] == "البلينا" and h[(2026, "1")].branch_attribution_method == "explicit_branch_text"
    assert h[(2026, "1")].branch_attribution_status == "auto_assigned" and "فرع البلينا" in h[(2026, "1")].branch_source_text
    assert session.scalar(select(DimBranch.system_key).where(DimBranch.id == h[(2026, "2")].branch_id)) == "HEAD_OFFICE"
    for n in ("3", "4", "5"):
        assert h[(2026, n)].branch_id == unalloc and h[(2026, n)].branch_attribution_status == "needs_review"
        assert ("po_branch_not_identified", f"2026/{n}") in codes(session)
    assert h[(2026, "3")].branch_attribution_method == "unallocated_multiple_or_plural_mentions"
    assert h[(2026, "4")].branch_attribution_method == "unallocated_no_explicit_branch"
    assert h[(2026, "1")].description_source == "تجهيز فرع البلينا بالأجهزة"  # original text kept
    assert h[(2026, "1")].attrs["branch_evidence"][0]["source"] == "po_description"
    # spend by branch carries the Unallocated bucket explicitly
    by_branch = compute_kpi(session, get_registry().get("purchase_orders"), "total_spend", group_by="branch")
    assert by_branch[unalloc] == 30


def test_attributor_does_not_match_partial_names(session, base):
    a = BranchAttributor(session)
    assert a.attribute("بجوار البلينا").status == "needs_review"     # name without 'فرع' is not explicit
    assert a.attribute("فرع البلينا الجديد").status == "auto_assigned"
    assert a.attribute("فروع الشركة").method == "unallocated_multiple_or_plural_mentions"
    assert a.attribute(None).method == "unallocated_no_text"


# ---------------------------------------------------------------- requisitions + linking
def req_book(rows):
    return xlsx({"اشعارات الاحتياج": [REQ_HEADER, *rows]})


def req_row(n, ref, dt, dept, desc="x", status="s"):
    return [n, ref, dt, dept, desc, "عادي", status, None]


def test_requisitions_load_departments_from_source_and_keep_missing_dates_empty(session, base):
    rows = [req_row(1, "1/2026", datetime(2026, 1, 5), "IT"), req_row(2, "2/2026", None, "Admin"),
            req_row(3, "2/2026", datetime(2026, 1, 6), "Admin"),  # duplicate number → held
            req_row(4, "x", datetime(2026, 1, 6), "IT")]          # bad format → held
    b = run(session, "requisitions", req_book(rows))
    assert (b.rows_loaded, b.rows_held) == (1, 3)
    # NOTE: the duplicate pair and the malformed row are held; nothing is defaulted
    assert {(r.fiscal_year, r.req_number) for r in session.scalars(select(Requisition))} == {(2026, "1")}
    assert ("requisition_number_duplicate", "2026/2") in codes(session)
    assert any(c == "requisition_number_format" for c, _ in codes(session))
    dept = session.scalar(select(Requisition.department_source).where(Requisition.req_number == "1"))
    assert dept == "IT"


def test_po_and_requisition_link_in_either_load_order(session, base):
    req = req_book([req_row(1, "1/2026", datetime(2026, 1, 5), "IT", "شراء شاشات لفرع البلينا")])
    po = po_book([po_row(1, "1/2026", datetime(2026, 1, 12), "Alpha Co", 1, "شاشات", "1/2026", 100),
                  po_row(2, "2/2026", datetime(2026, 1, 13), "Alpha Co", 1, "x", "9/2026", 50)])  # req 9 never loaded
    run(session, "purchase_orders", po, profile="register")              # PO first: requisition missing
    assert ("po_requisition_not_found", "2026/1") in codes(session)
    run(session, "requisitions", req)                                     # requisition later: links + resolves
    h = headers(session)
    r = session.scalar(select(Requisition))
    assert h[(2026, "1")].requisition_id == r.id and h[(2026, "1")].case_id == r.case_id
    st = session.scalar(select(DataException.status).where(DataException.code == "po_requisition_not_found",
                                                           DataException.entity_key == "2026/1"))
    assert st == "resolved"
    assert ("po_requisition_not_found", "2026/2") in codes(session) and h[(2026, "2")].requisition_id is None
    # requisition text is evidence for the branch: PO text had none, requisition names the branch
    assert h[(2026, "1")].branch_attribution_status == "auto_assigned"
    assert "requisition_description" in h[(2026, "1")].branch_source_text
    # one case per transaction: requisition + PO share it
    case_docs = session.scalars(select(ProcurementDocument.doc_type).where(ProcurementDocument.case_id == r.case_id)).all()
    assert sorted(case_docs) == ["purchase_order", "requisition"]
    assert session.scalar(select(func.count()).select_from(ProcurementCase)) == 2  # case of PO 2 + the shared one


def test_po_requisition_number_mismatch_flagged_but_loaded(session, base):
    req = req_book([req_row(1, "32/2026", datetime(2026, 4, 1), "IT")])
    po = po_book([po_row(1, "29/2026", datetime(2026, 5, 1), "Alpha Co", 1, "x", "32/2026", 10)])
    run(session, "requisitions", req)
    run(session, "purchase_orders", po, profile="register")
    assert ("po_requisition_number_differs", "2026/29") in codes(session)
    assert headers(session)[(2026, "29")].requisition_id is not None  # linked by the stated number, flagged for review


# ---------------------------------------------------------------- finance handover
def ho_book(rows):
    return xlsx({"استلامات المالية": [HANDOVER_HEADER, *rows]})


def ho_row(n, typ, dt, po, supplier, subject, amount):
    return [n, typ, dt, po, supplier, "scat", subject, "pcat", amount]


def test_finance_handover_types_duplicates_and_labels(session, base):
    run(session, "purchase_orders", po_book([po_row(1, "5/2026", datetime(2026, 1, 12), "Alpha Co", 1, "x", "5/2026", 100)]),
        profile="register")
    rows = [ho_row(1, "امر شراء", datetime(2026, 1, 20), "5/2026", "Alpha Co", "الدفعة الأولى", 100),
            ho_row(2, "امر شراء", datetime(2026, 2, 20), "5/2026", "Alpha Co", "الدفعة الثانية", 100),   # same PO/amount again
            ho_row(3, "خدمات", datetime(2026, 1, 21), None, "Unknown Services Ltd", "صيانة", "1,234.50"),  # service, text amount
            ho_row(4, "خدمات", datetime(2026, 1, 22), "9/2025", "Alpha Co", "x", 5),                    # service with PO no.
            ho_row(5, "امر شراء", datetime(2026, 1, 23), None, "Alpha Co", "x", 5)]                     # PO type, no PO no.
    b = run(session, "finance_handover", ho_book(rows))
    assert b.rows_loaded == 5
    memos = {m.memo_no: m for m in session.scalars(select(FinanceHandover))}
    assert memos[3].memo_type == "service" and memos[3].po_header_id is None and memos[3].amount == Decimal("1234.50")
    assert memos[3].supplier_id is None and memos[3].supplier_name_source == "Unknown Services Ltd"
    assert memos[1].po_header_id is not None and memos[1].memo_type_source == "امر شراء"
    c = codes(session)
    assert ("handover_possible_duplicate", "5/2026") in c and ("handover_exceeds_po_total", "5/2026") in c
    assert ("handover_service_memo_with_po", "4") in c and ("handover_po_memo_without_po", "5") in c
    assert any(code == "handover_supplier_unresolved" for code, _ in c)
    fh = get_registry().get("finance_handover")
    assert compute_kpi(session, fh, "handover_amount_service")[None] == pytest.approx(1234.5 + 5)
    assert fh.kpi("handover_amount").name == "Finance Handover Amount"  # never labelled "paid"


def test_unknown_memo_type_is_rejected_not_guessed(session, base):
    b = run(session, "finance_handover", ho_book([ho_row(1, "something else", datetime(2026, 1, 1), None, "Alpha Co", "x", 1)]))
    assert b.rows_rejected == 1 and b.rows_loaded == 0


def test_register_then_lines_do_not_double_count_spend(session, base):
    from tests.test_po_loader import FIXTURE  # noqa: F401  (line-level fixture lives there)
    run(session, "purchase_orders", po_book([po_row(1, "7/2026", datetime(2026, 3, 1), "Alpha Co", 1, "x", "7/2026", 1000)]),
        profile="register")
    po = get_registry().get("purchase_orders")
    assert compute_kpi(session, po, "total_spend")[None] == 1000
    csv = ("FY,PO No,Line,Date,Branch,Vendor,Qty,Price\n"
           "2026,7,1,01/03/2026,البلينا,Alpha Co,2,300\n2026,7,2,01/03/2026,البلينا,Alpha Co,1,400\n").encode()
    run(session, "purchase_orders", csv, name="lines.csv")
    assert compute_kpi(session, po, "total_spend")[None] == 1000  # lines (600+400) replace the header-level cost row
    assert session.scalar(select(func.count()).select_from(FactCost)) == 2
    h = headers(session)[(2026, "7")]
    assert h.granularity == "lines" and float(h.total_amount) == 1000 and h.number_source == "7/2026"
