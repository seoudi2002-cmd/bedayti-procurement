"""Supplier register loader: dim_supplier + supplier_contact (personal data, separate table).

Upsert key: supplier code (SUPnnn from the register). register_no is NOT unique in the source, so it is
stored but never used as a key. Tax IDs are kept exactly as written; format problems are exceptions, not edits.
Source notes (e.g. payment regime, do-not-use) are stored verbatim and not interpreted.
"""
import re
from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import raise_exception
from app.core.loader_utils import rows_with_status
from app.models import DimSupplier, ImportBatch, SupplierContact

MODULE = "suppliers"
TAX_ID = re.compile(r"^\d{3}-\d{3}-\d{3}$")


def load(session: Session, batch: ImportBatch) -> int:
    rows = rows_with_status(session, batch, ("valid", "loaded"))
    existing = {s.code: s for s in session.scalars(select(DimSupplier)) if s.code}
    codes: dict[str, int] = defaultdict(int)
    reg_nos: dict[int, list[str]] = defaultdict(list)
    tax_ids: dict[str, list[str]] = defaultdict(list)
    bad_tax: list[str] = []
    no_tax: list[str] = []
    no_cr: list[str] = []

    for r in rows:
        c = r.cleaned
        code = c["code"]
        codes[code] += 1
        sup = existing.get(code)
        if sup is None:
            sup = DimSupplier(code=code, name=c["name"])
            session.add(sup)
            existing[code] = sup
        sup.name = c["name"]
        sup.register_no = c.get("register_no")
        sup.commercial_reg_no, sup.address = c.get("commercial_reg_no"), c.get("address")
        sup.category_source, sup.services_source = c.get("category_source"), c.get("services_source")
        sup.notes_source, sup.tax_id = c.get("notes"), c.get("tax_id")
        session.flush()
        contact = session.scalar(select(SupplierContact).where(SupplierContact.supplier_id == sup.id))
        if contact is None:
            contact = SupplierContact(supplier_id=sup.id)
            session.add(contact)
        contact.contact_name_source, contact.phone_source, contact.email = c.get("contact_name"), c.get("phone"), c.get("email")
        if c.get("register_no") is not None:
            reg_nos[c["register_no"]].append(code)
        if c.get("tax_id"):
            tax_ids[c["tax_id"]].append(code)
            if not TAX_ID.match(c["tax_id"]):
                bad_tax.append(code)
        else:
            no_tax.append(code)
        if not c.get("commercial_reg_no"):
            no_cr.append(code)
        r.status = "loaded"

    def exc(code, sev, key, msg, details, entity="supplier"):
        raise_exception(session, code, sev, entity, key, msg, details, MODULE, batch.id)

    for code, n in codes.items():
        if n > 1:
            exc("supplier_duplicate_code", "error", code, "Supplier code appears more than once in the register", {"count": n})
    for no, cs in reg_nos.items():
        if len(cs) > 1:
            exc("supplier_duplicate_register_no", "warning", ",".join(cs),
                f"Supplier register no. {no} is used by several suppliers", {"register_no": no, "codes": cs})
    for tid, cs in tax_ids.items():
        if len(cs) > 1:
            exc("supplier_shared_tax_id", "warning", ",".join(cs), "Several suppliers share one tax ID", {"codes": cs})
    if bad_tax:
        exc("supplier_tax_id_format", "warning", str(batch.id),
            f"{len(bad_tax)} suppliers have a tax ID cell that is not in ddd-ddd-ddd form (kept as written)", {"codes": bad_tax}, "import_batch")
    if no_tax:
        exc("supplier_tax_id_missing", "info", str(batch.id), f"{len(no_tax)} suppliers have no tax ID", {"codes": no_tax}, "import_batch")
    if no_cr:
        exc("supplier_commercial_reg_missing", "info", str(batch.id), f"{len(no_cr)} suppliers have no commercial registry no.",
            {"codes": no_cr}, "import_batch")
    batch.rows_loaded, batch.rows_held, batch.status = len(rows), 0, "loaded"
    batch.loaded_at = func.now()
    session.commit()
    return batch.rows_loaded


def rollback(session: Session, batch: ImportBatch) -> None:
    raise NotImplementedError("Master data is not rolled back; re-import a corrected file instead")
