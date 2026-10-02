"""Branch master loader: dim_region + dim_branch + branch_contact (personal data, separate table).

- The branch master is authoritative for branches; this is the only loader that creates ordinary branches.
- Upsert key: normalised branch name (the source has no code; none is generated).
- Both manager values (branch file vs HR) are kept; reconciliation never overwrites either.
"""
from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.cleaning.normalizers import normalize_text
from app.core.exceptions import raise_exception
from app.core.loader_utils import rows_with_status
from app.core.reconcile import reconcile_branch_managers
from app.core.system_seed import ensure_system_branches
from app.models import BranchContact, DimBranch, DimRegion, ImportBatch

MODULE = "branches"


def load(session: Session, batch: ImportBatch) -> int:
    ensure_system_branches(session)
    rows = rows_with_status(session, batch, ("valid", "loaded"))
    regions = {normalize_text(r.name): r for r in session.scalars(select(DimRegion))}
    branches = {normalize_text(b.name_ar): b for b in session.scalars(
        select(DimBranch).where(DimBranch.branch_type == "branch")) if b.name_ar}
    names_seen: dict[str, int] = defaultdict(int)
    emails: dict[str, list[int]] = defaultdict(list)
    missing = defaultdict(list)

    for r in rows:
        c = r.cleaned
        key = normalize_text(c["name"])
        names_seen[key] += 1
        region = regions.get(normalize_text(c["region"]))
        if region is None:
            region = DimRegion(name=c["region"])
            session.add(region)
            session.flush()
            regions[normalize_text(c["region"])] = region
        branch = branches.get(key)
        if branch is None:
            branch = DimBranch(name_ar=c["name"], branch_type="branch")
            session.add(branch)
            branches[key] = branch
        branch.name_ar, branch.source_seq, branch.region_id, branch.address = c["name"], c.get("seq"), region.id, c.get("address")
        branch.region = c["region"]
        session.flush()
        contact = session.scalar(select(BranchContact).where(BranchContact.branch_id == branch.id))
        if contact is None:
            contact = BranchContact(branch_id=branch.id)
            session.add(contact)
        contact.branch_manager_name_source = c.get("branch_manager")
        contact.branch_phone, contact.manager_phone_1, contact.manager_phone_2 = (
            c.get("branch_phone"), c.get("manager_phone_1"), c.get("manager_phone_2"))
        contact.region_manager_name_source, contact.region_manager_phone = c.get("region_manager"), c.get("region_manager_phone")
        contact.email = c.get("email")
        r.status = "loaded"
        for fld, label in (("branch_manager", "manager"), ("address", "address"), ("email", "email")):
            if not c.get(fld):
                missing[label].append(c["name"])
        if c.get("email"):
            emails[c["email"].lower()].append(branch.id)
        if c.get("_filled_down"):
            r.cleaned = {**c}  # provenance of fill-down stays in raw_row.cleaned

    for key, n in names_seen.items():
        if n > 1:
            raise_exception(session, "branch_duplicate_name", "warning", "import_batch", f"{batch.id}:{key}",
                            "Same branch name appears more than once in the branch master", {"count": n}, MODULE, batch.id)
    for email, ids in emails.items():
        if len(ids) > 1:
            raise_exception(session, "branch_shared_email", "info", "branch", ",".join(map(str, ids)),
                            "Several branches share one e-mail address", {"branch_ids": ids}, MODULE, batch.id)
    for label, names in missing.items():
        raise_exception(session, f"branch_missing_{label}", "info", "import_batch", str(batch.id),
                        f"{len(names)} branches have no {label} in the source", {"count": len(names), "branches": names}, MODULE, batch.id)
    session.flush()
    reconcile_branch_managers(session)
    batch.rows_loaded = len(rows)
    batch.rows_held = 0
    batch.status = "loaded"
    batch.loaded_at = func.now()
    session.commit()
    return batch.rows_loaded


def rollback(session: Session, batch: ImportBatch) -> None:
    raise NotImplementedError("Master data is not rolled back; re-import a corrected file instead")
