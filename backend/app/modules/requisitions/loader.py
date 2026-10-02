"""Requisition register loader → requisition + procurement case/document, and links existing POs.

Key: (fiscal_year, number) parsed from "n/yyyy". Unparseable or duplicated references are held and flagged.
Department values come straight from the source (no department master exists): created with source recorded.
"""
from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.attribution import BranchAttributor
from app.core.documents import ensure_requisition_case, link_po_to_requisition
from app.core.po_costs import sync_po_cost
from app.core.procurement_attribution import reattribute_po
from app.core.entities import EntityResolver
from app.core.exceptions import auto_resolve, raise_exception
from app.core.loader_utils import date_from_json, flag_for, parse_number_year, rows_with_status
from app.core.modules.registry import get_registry
from app.models import ImportBatch, PoHeader, Requisition

MODULE = "requisitions"


def load(session: Session, batch: ImportBatch) -> int:
    spec = get_registry().get(MODULE)
    resolver = EntityResolver(session, spec.manifest.entity_policy)
    attributor = BranchAttributor(session)
    rows = rows_with_status(session, batch, ("valid", "held", "loaded"))
    parsed: dict[int, tuple[str, int] | None] = {r.id: parse_number_year(r.cleaned["number_source"]) for r in rows}
    groups: dict[tuple[str, int], list] = defaultdict(list)
    for r in rows:
        if parsed[r.id]:
            groups[parsed[r.id]].append(r)
    missing_date: list[str] = []
    no_dept: list[str] = []
    loaded = held = 0

    for r in rows:
        c = r.cleaned
        key = parsed[r.id]
        if key is None:
            r.status = "held"
            held += 1
            raise_exception(session, "requisition_number_format", "error", "requisition_row", f"{batch.id}:{r.row_number}",
                            f"Requisition number '{c['number_source']}' is not in n/yyyy form; row held", {}, MODULE, batch.id)
            continue
        if len(groups[key]) > 1:
            r.status = "held"
            held += 1
            raise_exception(session, "requisition_number_duplicate", "error", "requisition", f"{key[1]}/{key[0]}",
                            "Requisition number appears on more than one row; rows held for manual review",
                            {"rows": [x.row_number for x in groups[key]]}, MODULE, batch.id)
            continue
        number, fy = key
        req = session.scalar(select(Requisition).where(Requisition.fiscal_year == fy, Requisition.req_number == number))
        if req is None:
            req = Requisition(fiscal_year=fy, req_number=number, number_source=c["number_source"])
            session.add(req)
        req.number_source = c["number_source"]
        req.source_seq = int(c["seq"]) if str(c.get("seq") or "").isdigit() else None
        req.request_date = date_from_json(c.get("request_date"))
        req.department_source = c.get("department")
        res = resolver.resolve("department", c.get("department"))
        req.department_id = res.entity_id if res and res.status == "resolved" else None
        req.description_source, req.priority_source = c.get("description"), c.get("priority")
        req.status_source, req.notes_source = c.get("status"), c.get("notes")
        req.batch_id, req.raw_row_id = batch.id, r.id
        session.flush()
        if req.request_date is None:
            missing_date.append(c["number_source"])
            flag = flag_for(r, "request_date")
            if flag:
                raise_exception(session, "requisition_invalid_date", "warning", "requisition", c["number_source"],
                                flag["message"], {"raw": flag["raw"]}, MODULE, batch.id)
        if not c.get("department"):
            no_dept.append(c["number_source"])
        ensure_requisition_case(session, req)
        for header in session.scalars(select(PoHeader).where(PoHeader.fiscal_year == fy)):
            ref = parse_number_year(header.requisition_no)
            if ref == (number, fy):
                link_po_to_requisition(session, header, req)
                auto_resolve(session, "po_requisition_not_found", "po_header", f"{header.fiscal_year}/{header.po_number}",
                             "Requisition loaded and linked")
                reattribute_po(session, header, attributor, batch.id)
                sync_po_cost(session, header)
        r.status = "loaded"
        loaded += 1

    if missing_date:
        raise_exception(session, "requisition_date_missing", "info", "import_batch", str(batch.id),
                        f"{len(missing_date)} requisitions have no (valid) request date - left empty, not defaulted",
                        {"requisitions": missing_date}, MODULE, batch.id)
    if no_dept:
        raise_exception(session, "requisition_department_missing", "info", "import_batch", str(batch.id),
                        f"{len(no_dept)} requisitions have no department", {"requisitions": no_dept}, MODULE, batch.id)
    batch.rows_loaded, batch.rows_held = loaded, held
    batch.status = "partially_loaded" if held else "loaded"
    batch.loaded_at = func.now()
    session.commit()
    return loaded


def rollback(session: Session, batch: ImportBatch) -> None:
    raise NotImplementedError("Requisition rollback is not implemented; re-import a corrected file")
