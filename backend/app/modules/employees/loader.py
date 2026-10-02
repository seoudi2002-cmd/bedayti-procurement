"""Employee master loader (personal data → admin-only).

- Upsert on employee_code. Source values are kept as written (position/branch/governorate text).
- Branch is resolved through aliases/names only; unresolved text keeps branch_id NULL + method 'unresolved'
  and a pending alias for review. Nothing is guessed.
- department / cost centre / manager are not in the source: they stay NULL and are listed in `missing_fields`.
- A data-freshness warning is attached to the batch (latest hire date vs today).
"""
from collections import Counter
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.cleaning.normalizers import normalize_text
from app.core.entities import EntityResolver
from app.core.exceptions import raise_exception
from app.core.loader_utils import date_from_json, flag_for, rows_with_status
from app.core.modules.registry import get_registry
from app.core.reconcile import reconcile_branch_managers
from app.core.system_seed import ensure_system_branches
from app.models import DimEmployee, ImportBatch

MODULE = "employees"
STALE_AFTER_DAYS = 90
MISSING_FIELDS = ["department", "cost_center", "manager"]  # not provided by the HR file


def load(session: Session, batch: ImportBatch) -> int:
    ensure_system_branches(session)
    spec = get_registry().get(MODULE)
    resolver = EntityResolver(session, spec.manifest.entity_policy)
    rows = rows_with_status(session, batch, ("valid", "loaded"))
    existing = {e.employee_code: e for e in session.scalars(select(DimEmployee))}
    unresolved: Counter = Counter()
    gov_errors = 0
    hire_dates: list[date] = []
    names = Counter()

    for r in rows:
        c = r.cleaned
        code = int(c["employee_code"])
        emp = existing.get(code)
        if emp is None:
            emp = DimEmployee(employee_code=code, full_name=c["full_name"])
            session.add(emp)
            existing[code] = emp
        emp.full_name = c["full_name"]
        emp.hire_date = date_from_json(c.get("hire_date"))
        if emp.hire_date:
            hire_dates.append(emp.hire_date)
        emp.position_source = c.get("position")
        emp.branch_source_text = c.get("branch")
        res = resolver.resolve("branch", c.get("branch"))
        if res is None:
            emp.branch_id, emp.branch_match_method = None, None
        elif res.status == "resolved":
            emp.branch_id, emp.branch_match_method = res.entity_id, res.method
        else:
            emp.branch_id, emp.branch_match_method = None, "unresolved"
            unresolved[c.get("branch")] += 1
        emp.governorate_source = c.get("governorate")
        gflag = flag_for(r, "governorate")
        emp.governorate_issue = f"source_error:{gflag['raw']}" if gflag and gflag["code"] == "source_error" else None
        gov_errors += emp.governorate_issue is not None
        emp.missing_fields = MISSING_FIELDS
        emp.source_batch_id = batch.id
        names[normalize_text(c["full_name"])] += 1
        r.status = "loaded"
    session.flush()

    if unresolved:
        raise_exception(session, "employee_branch_unresolved", "warning", "import_batch", str(batch.id),
                        f"{sum(unresolved.values())} employees have a branch text that matches no branch "
                        f"({len(unresolved)} distinct values) - see /api/aliases", {"values": dict(unresolved)}, MODULE, batch.id)
    if gov_errors:
        raise_exception(session, "employee_governorate_source_error", "warning", "import_batch", str(batch.id),
                        f"{gov_errors} employees have an Excel error value (e.g. #N/A) instead of a governorate",
                        {"count": gov_errors}, MODULE, batch.id)
    dupes = [n for n, k in names.items() if k > 1]
    if dupes:
        raise_exception(session, "employee_duplicate_name", "info", "import_batch", str(batch.id),
                        f"{len(dupes)} full names occur more than once (different employee codes)", {"count": len(dupes)}, MODULE, batch.id)

    warnings = []
    if hire_dates:
        latest = max(hire_dates)
        age = (date.today() - latest).days
        if age > STALE_AFTER_DAYS:
            msg = (f"Data freshness: the latest hire date in this file is {latest.isoformat()} ({age} days ago). "
                   "The file may be out of date; confirm its as-of date before relying on headcount or branch assignment.")
            warnings.append({"code": "data_freshness", "severity": "warning", "message": msg})
            raise_exception(session, "employee_data_freshness", "warning", "import_batch", str(batch.id), msg,
                            {"latest_hire_date": latest.isoformat(), "days": age}, MODULE, batch.id)
    batch.warnings = warnings
    batch.rows_loaded, batch.rows_held = len(rows), 0
    batch.status = "loaded"
    batch.loaded_at = func.now()
    session.flush()
    reconcile_branch_managers(session)
    session.commit()
    return batch.rows_loaded


def rollback(session: Session, batch: ImportBatch) -> None:
    raise NotImplementedError("Master data is not rolled back; re-import a corrected file instead")
