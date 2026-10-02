"""Reconcile the branch file's branch manager with the HR file. Neither source is overwritten: both values are
kept and the disagreement is a status (+ data_exception)."""
from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.cleaning.normalizers import normalize_text
from app.core.exceptions import raise_exception
from app.models import BranchContact, DimBranch, DimEmployee


def reconcile_branch_managers(session: Session) -> dict[str, int]:
    if not session.scalar(select(func.count()).select_from(DimEmployee)):
        return {}  # HR file not loaded yet: nothing to compare against
    by_name: dict[str, list[DimEmployee]] = defaultdict(list)
    for e in session.scalars(select(DimEmployee)):
        by_name[normalize_text(e.full_name)].append(e)
    counts: dict[str, int] = defaultdict(int)
    for contact, branch in session.execute(select(BranchContact, DimBranch).join(DimBranch, DimBranch.id == BranchContact.branch_id)):
        if not contact.branch_manager_name_source:
            contact.manager_employee_id, contact.manager_reconciliation_status = None, "no_manager_in_branch_file"
        else:
            matches = by_name.get(normalize_text(contact.branch_manager_name_source), [])
            if len(matches) == 1:
                emp = matches[0]
                contact.manager_employee_id = emp.id
                same = emp.branch_id == branch.id
                contact.manager_reconciliation_status = "matched" if same else "matched_name_different_branch"
                if not same:
                    raise_exception(session, "branch_manager_hr_branch_differs", "warning", "branch", str(branch.id),
                                    "Branch manager name matches an HR employee recorded at a different branch (or one that "
                                    "could not be resolved)", {"employee_code": emp.employee_code,
                                                                "hr_branch_text": emp.branch_source_text,
                                                                "hr_branch_match": emp.branch_match_method}, "branches")
            elif len(matches) > 1:
                contact.manager_employee_id, contact.manager_reconciliation_status = None, "ambiguous_name"
                raise_exception(session, "branch_manager_hr_ambiguous", "warning", "branch", str(branch.id),
                                "Branch manager name matches several HR employees",
                                {"employee_codes": [m.employee_code for m in matches]}, "branches")
            else:
                contact.manager_employee_id, contact.manager_reconciliation_status = None, "not_found_in_hr"
                raise_exception(session, "branch_manager_not_in_hr", "info", "branch", str(branch.id),
                                "Branch manager named in the branch file was not found in the HR file "
                                "(by exact name). Both sources are kept.", {}, "branches")
        counts[contact.manager_reconciliation_status] += 1
    session.commit()
    return dict(counts)
