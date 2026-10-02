"""Branch attribution for a PO from ALL its supporting texts, with a full audit trail.

Evidence considered: the PO description, the linked requisition's description, and the subjects of linked
finance-handover memos. Rules (conservative):
  - any evidence with plural/multi-branch wording, or conflicting evidence      -> Unallocated, needs review
  - exactly one distinct explicit target across the evidence                    -> that branch/office, auto-assigned
  - nothing explicit                                                            -> Unallocated, needs review
The per-source results are stored in po_header.attrs["branch_evidence"]; the original texts are never altered.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.attribution import BranchAttributor
from app.core.exceptions import auto_resolve, raise_exception
from app.core.system_seed import UNALLOCATED
from app.models import FinanceHandover, PoHeader, Requisition

MODULE = "purchase_orders"
PRIMARY = ("po_description", "requisition_description")


def reattribute_po(session: Session, header: PoHeader, attributor: BranchAttributor, batch_id: int | None = None) -> None:
    sources: list[tuple[str, str | None]] = [("po_description", header.description_source)]
    if header.requisition_id:
        req = session.get(Requisition, header.requisition_id)
        if req is not None:
            sources.append(("requisition_description", req.description_source))
    for memo in session.scalars(select(FinanceHandover).where(FinanceHandover.po_header_id == header.id).order_by(FinanceHandover.memo_no)):
        sources.append((f"finance_handover_memo_{memo.memo_no}", memo.subject_source))

    evidence = []
    for name, text in sources:
        if not (text and text.strip()):
            continue
        a = attributor.attribute(text)
        evidence.append({"source": name, "method": a.method, "status": a.status, "branch_id": a.branch_id, "snippet": a.snippet})
    primary = [e for e in evidence if e["source"] in PRIMARY]  # the PO's own words (+ its requisition)
    supporting = [e for e in evidence if e["source"] not in PRIMARY]  # finance memos
    unalloc = attributor.ids[UNALLOCATED]
    conflict_note = None

    def summarize(items):
        assigned = {e["branch_id"]: e for e in items if e["status"] == "auto_assigned"}
        blockers = [e for e in items if e["method"] == "unallocated_multiple_or_plural_mentions"]
        return assigned, blockers

    def unallocated(method, items):
        shown = "; ".join(f"{e['source']}: {e['snippet']}" for e in items if e["snippet"])
        return method, "needs_review", unalloc, shown or None

    p_assigned, p_blockers = summarize(primary)
    if p_blockers:
        method, status, branch_id, snippet = unallocated("unallocated_multiple_or_plural_mentions", p_blockers)
    elif len(p_assigned) == 1:
        e = next(iter(p_assigned.values()))
        method, status, branch_id, snippet = e["method"], "auto_assigned", e["branch_id"], f"{e['source']}: {e['snippet']}"
        s_assigned, s_blockers = summarize(supporting)
        odd = s_blockers + [x for bid, x in s_assigned.items() if bid != e["branch_id"]]
        if odd:  # supporting documents say something different: keep the PO's explicit branch but ask for review
            conflict_note = {"assigned_from": e["source"], "conflicting": [{"source": x["source"], "snippet": x["snippet"], "method": x["method"]} for x in odd]}
    elif len(p_assigned) > 1:
        method, status, branch_id, snippet = unallocated("unallocated_conflicting_evidence", list(p_assigned.values()))
    else:
        s_assigned, s_blockers = summarize(supporting)
        if s_blockers:
            method, status, branch_id, snippet = unallocated("unallocated_multiple_or_plural_mentions", s_blockers)
        elif len(s_assigned) == 1:
            e = next(iter(s_assigned.values()))
            method, status, branch_id, snippet = e["method"], "auto_assigned", e["branch_id"], f"{e['source']}: {e['snippet']}"
        elif len(s_assigned) > 1:
            method, status, branch_id, snippet = unallocated("unallocated_conflicting_evidence", list(s_assigned.values()))
        else:
            method, status, branch_id, snippet = "unallocated_no_explicit_branch", "needs_review", unalloc, None
    if header.branch_attribution_status == "confirmed":  # a person's confirmation is never overwritten
        header.attrs = {**(header.attrs or {}), "branch_evidence": evidence}
        return
    header.branch_id, header.branch_attribution_method = branch_id, method
    header.branch_attribution_status, header.branch_source_text = status, snippet
    header.attrs = {**(header.attrs or {}), "branch_evidence": evidence}
    label = f"{header.fiscal_year}/{header.po_number}"
    if status == "needs_review":
        raise_exception(session, "po_branch_not_identified", "warning", "po_header", label,
                        "Branch could not be identified from explicit text: assigned to Unallocated, needs review",
                        {"method": method, "snippet": snippet}, MODULE, batch_id)
    else:
        auto_resolve(session, "po_branch_not_identified", "po_header", label, f"Branch identified: {method}")
    if conflict_note:
        raise_exception(session, "po_branch_evidence_conflict", "warning", "po_header", label,
                        "Branch assigned from the PO's own explicit text, but supporting documents use different or plural "
                        "wording: please confirm", conflict_note, MODULE, batch_id)
    else:
        auto_resolve(session, "po_branch_evidence_conflict", "po_header", label, "No conflicting evidence now")
