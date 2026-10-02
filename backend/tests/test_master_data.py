from datetime import date

from sqlalchemy import func, select

from app.core.exceptions import decide_exception
from app.core.ingestion.pipeline import stage_file, validate_batch
from app.core.modules.loader import get_loader
from app.core.modules.registry import get_registry
from app.core.system_seed import HEAD_OFFICE, UNALLOCATED, ensure_system_branches
from app.models import (
    BranchContact, DataException, DimBranch, DimEmployee, DimRegion, DimSupplier, EntityAlias, SupplierContact,
)
from tests.helpers import SUPPLIER_HEADER, branch_workbook, employee_workbook, xlsx


def run(session, module, content, profile="default", name="f.xlsx"):
    spec = get_registry().get(module)
    batch, _ = stage_file(session, spec, name, content, profile=profile)
    validate_batch(session, spec, batch)
    get_loader(module).load(session, batch)
    return batch


def exceptions(session, code=None):
    q = select(DataException)
    if code:
        q = q.where(DataException.code == code)
    return list(session.scalars(q))


# ---------------------------------------------------------------- branches
def test_branch_master_fill_down_skips_subtotals_and_never_invents_codes(session):
    ensure_system_branches(session)
    b = run(session, "branches", branch_workbook())
    assert (b.rows_valid, b.rows_skipped, b.rows_loaded) == (3, 2, 3)  # the 2 subtotal rows are skipped, not loaded
    names = {x.name_ar: x for x in session.scalars(select(DimBranch).where(DimBranch.branch_type == "branch"))}
    assert set(names) == {"ابوحماد", "كفر صقر", "طنطا"}
    assert all(x.code is None for x in names.values())  # no invented codes
    regions = {r.id: r.name for r in session.scalars(select(DimRegion))}
    assert {regions[names["كفر صقر"].region_id], regions[names["طنطا"].region_id]} == {"الشرقية", "الغربية"}
    contact = {c.branch_id: c for c in session.scalars(select(BranchContact))}
    # merged region manager filled down within the region ...
    assert contact[names["كفر صقر"].id].region_manager_name_source == "مدير شرقية"
    # ... but not into the next region
    assert contact[names["طنطا"].id].region_manager_name_source is None
    assert contact[names["ابوحماد"].id].branch_phone == "553413434"  # number cell, no ".0"
    assert contact[names["ابوحماد"].id].manager_phone_2 is None


def test_system_branches_exist_and_are_seeded_once(session):
    ids = ensure_system_branches(session)
    assert set(ids) == {HEAD_OFFICE, UNALLOCATED}
    ensure_system_branches(session)
    assert session.scalar(select(func.count()).select_from(DimBranch)) == 2
    assert session.scalar(select(DimBranch.branch_type).where(DimBranch.system_key == UNALLOCATED)) == "unallocated"


def test_branch_shared_email_flagged_not_changed(session):
    run(session, "branches", branch_workbook())
    ex = exceptions(session, "branch_shared_email")
    assert len(ex) == 1 and ex[0].status == "open"
    assert {c.email for c in session.scalars(select(BranchContact))} >= {"a@x.test"}


# ---------------------------------------------------------------- employees
def _emp_rows():
    return [[1, "Employee One", date(2024, 1, 5), "مدير فرع", "ابو حماد", "الشرقية"],          # compact match to ابوحماد
            [2, "Employee Two", date(2024, 2, 1), "مسئول تمويل", "كفر صقر", "#N/A"],         # exact + source error
            [3, "Employee Three", date(2024, 3, 1), "مدير منطقة", "منطقة الشرقية", "الشرقية"],  # unresolved (no regional office)
            [4, "Employee Four", date(2023, 1, 1), "رئيس", "المركز الرئيسي", "القاهره"],      # head office alias
            [5, "Employee Five", date(2023, 1, 1), "مسئول تمويل", None, None]]


def test_employee_master_labels_missing_fields_and_flags_freshness(session):
    run(session, "branches", branch_workbook())
    b = run(session, "employees", employee_workbook(_emp_rows()))
    emps = {e.employee_code: e for e in session.scalars(select(DimEmployee))}
    assert emps[1].branch_match_method == "compact" and emps[2].branch_match_method == "exact"
    assert emps[3].branch_id is None and emps[3].branch_match_method == "unresolved"
    assert emps[3].branch_source_text == "منطقة الشرقية"  # source text kept
    assert emps[4].branch_match_method == "alias"
    assert session.get(DimBranch, emps[4].branch_id).system_key == HEAD_OFFICE
    assert emps[5].branch_id is None and emps[5].branch_match_method is None
    # absent columns are labelled missing, not turned into zero/unknown
    assert emps[1].missing_fields == ["department", "cost_center", "manager"]
    assert emps[1].department_id is None and emps[1].manager_employee_id is None
    assert emps[2].governorate_source is None and emps[2].governorate_issue == "source_error:#N/A"
    # latest hire date 2024-03 is far older than "today" in the test clock → freshness warning
    assert b.warnings and b.warnings[0]["code"] == "data_freshness"
    assert exceptions(session, "employee_data_freshness")
    pending = session.scalars(select(EntityAlias).where(EntityAlias.status == "pending")).all()
    assert [a.alias_raw for a in pending] == ["منطقة الشرقية"]


def test_unresolved_branch_can_be_resolved_to_a_regional_office_then_reloaded(session):
    from app.core.entities import resolve_alias
    run(session, "branches", branch_workbook())
    b = run(session, "employees", employee_workbook(_emp_rows()))
    alias = session.scalar(select(EntityAlias).where(EntityAlias.status == "pending"))
    resolve_alias(session, alias, create_new=True, branch_kind="regional_office")
    get_loader("employees").load(session, b)
    emp = session.scalar(select(DimEmployee).where(DimEmployee.employee_code == 3))
    office = session.get(DimBranch, emp.branch_id)
    assert office.branch_type == "regional_office" and office.name_ar == "منطقة الشرقية" and emp.branch_match_method == "alias"


def test_branch_manager_reconciliation_keeps_both_values(session):
    rows = [[10, "مدير فرع واحد", date(2024, 1, 1), "مدير فرع", "ابوحماد", "الشرقية"],      # same branch → matched
            [11, "مدير فرع اثنين", date(2024, 1, 1), "مدير فرع", "طنطا", "الغربية"]]       # other branch → differs
    run(session, "branches", branch_workbook())
    run(session, "employees", employee_workbook(rows))
    by = {b.name_ar: b for b in session.scalars(select(DimBranch).where(DimBranch.branch_type == "branch"))}
    st = {session.get(DimBranch, c.branch_id).name_ar: c for c in session.scalars(select(BranchContact))}
    assert st["ابوحماد"].manager_reconciliation_status == "matched"
    assert st["كفر صقر"].manager_reconciliation_status == "matched_name_different_branch"
    assert st["طنطا"].manager_reconciliation_status == "no_manager_in_branch_file"
    assert st["كفر صقر"].branch_manager_name_source == "مدير فرع اثنين"  # branch-file value untouched
    assert st["كفر صقر"].manager_employee_id is not None and by["طنطا"].id != st["كفر صقر"].branch_id
    assert exceptions(session, "branch_manager_hr_branch_differs")


def test_exception_decision_survives_reload(session):
    b = run(session, "branches", branch_workbook())
    ex = exceptions(session, "branch_shared_email")[0]
    decide_exception(session, ex.id, "accepted", "tester", "known shared mailbox")
    get_loader("branches").load(session, b)
    session.refresh(ex)
    assert ex.status == "accepted" and ex.decided_by == "tester"


# ---------------------------------------------------------------- suppliers
def _sup_rows():
    return [[1, "Supplier A", 1, "SUP001", "IT", "ink", "Contact A", "0100", "a@s.test", "addr", 160130.0, "111-111-111", None],
            [2, "Supplier B", 2, "SUP002", "IT", "ink", None, None, None, None, None, "111-111-111", "خاضع لنظام الدفعات المقدمة"],
            [3, "Supplier C", 3, "SUP003", "Furniture", "x", None, None, None, None, None, "BLACKLISTED", None],
            [4, "Supplier D", 3, "SUP004", "Furniture", "x", None, None, None, None, "55", 594613086.0, None]]


def test_supplier_register_keeps_raw_values_and_flags_conflicts(session):
    b = run(session, "suppliers", xlsx({"سجل الموردين": [SUPPLIER_HEADER, *_sup_rows()]}))
    assert b.rows_loaded == 4
    sup = {s.code: s for s in session.scalars(select(DimSupplier))}
    assert sup["SUP001"].commercial_reg_no == "160130"  # numeric cell → text without ".0"
    assert sup["SUP003"].tax_id == "BLACKLISTED"  # raw, never reinterpreted
    assert sup["SUP004"].tax_id == "594613086"  # not reformatted to ddd-ddd-ddd
    assert sup["SUP002"].notes_source == "خاضع لنظام الدفعات المقدمة"  # stored verbatim, not interpreted
    assert sup["SUP001"].category_source == "IT"
    assert session.scalar(select(SupplierContact.contact_name_source).where(SupplierContact.supplier_id == sup["SUP001"].id)) == "Contact A"
    codes = {e.code for e in exceptions(session)}
    assert {"supplier_shared_tax_id", "supplier_duplicate_register_no", "supplier_tax_id_format"} <= codes
    assert not any(s.code is None for s in sup.values())


def test_supplier_reimport_upserts_by_code(session):
    run(session, "suppliers", xlsx({"سجل الموردين": [SUPPLIER_HEADER, *_sup_rows()]}))
    changed = _sup_rows()
    changed[0][1] = "Supplier A renamed"
    run(session, "suppliers", xlsx({"سجل الموردين": [SUPPLIER_HEADER, *changed]}), name="g.xlsx")
    assert session.scalar(select(func.count()).select_from(DimSupplier)) == 4
    assert session.scalar(select(DimSupplier.name).where(DimSupplier.code == "SUP001")) == "Supplier A renamed"
