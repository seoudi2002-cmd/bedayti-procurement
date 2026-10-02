"""Branch attribution for transactions that carry no branch column.

Hierarchy (as decided by the business owner), applied conservatively and recorded for audit:
  1. an explicit branch named in the text ("فرع <name>")            -> that branch
  2. explicit Head Office wording and no branch wording               -> Head Office
  3. an explicit regional/area office name                            -> that regional office
  4. anything else, or any plural/multiple-branch wording             -> Unallocated / Branch Not Identified, flagged
Never guesses from partial text. The matched snippet and the method are stored with the transaction.
"""
import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.cleaning.normalizers import normalize_text
from app.core.system_seed import HEAD_OFFICE, UNALLOCATED, ensure_system_branches
from app.models import DimBranch

# plural wording or a count of branches ("5 فروع", "100 فرع"): never attributable to a single branch
_PLURAL = re.compile(r"(?<!\w)[لبوف]?(?:ال)?فروع(?!\w)|(?<!\w)\d+\s*فرع(?!\w)")
_HEAD_OFFICE = normalize_text("المركز الرئيسي")
# "المركز" with the usual attached prefixes: للمركز / بالمركز / والمركز ...
_HEAD_OFFICE_RE = re.compile(r"(?<!\w)(?:[بوفك]?ال|لل)" + re.escape(_HEAD_OFFICE[2:]) + r"(?!\w)")


@dataclass
class Attribution:
    branch_id: int
    method: str
    status: str  # auto_assigned | needs_review
    snippet: str | None = None


class BranchAttributor:
    def __init__(self, session: Session):
        self.ids = ensure_system_branches(session)
        branches = session.scalars(select(DimBranch).where(DimBranch.branch_type.in_(("branch", "regional_office"))))
        self.branches: list[tuple[str, int, str]] = []  # (normalized name, id, kind)
        for b in branches:
            for name in (b.name_ar, b.name_en):
                n = normalize_text(name)
                if n:
                    self.branches.append((n, b.id, b.branch_type))
        self.branches.sort(key=lambda x: -len(x[0]))  # longest name first

    def attribute(self, text: str | None) -> Attribution:
        unalloc = self.ids[UNALLOCATED]
        norm = normalize_text(text)
        if not norm:
            return Attribution(unalloc, "unallocated_no_text", "needs_review")
        hits: dict[int, str] = {}
        for name, bid, kind in self.branches:
            pattern = (rf"(?<!\w)[لبوف]?فرع\s+{re.escape(name)}(?!\w)" if kind == "branch"
                       else rf"(?<!\w){re.escape(name)}(?!\w)")
            m = re.search(pattern, norm)
            if m:
                hits.setdefault(bid, m.group(0).strip())
        plural = _PLURAL.search(norm) is not None
        head = _HEAD_OFFICE_RE.search(norm) is not None
        if plural or len(hits) > 1:
            return Attribution(unalloc, "unallocated_multiple_or_plural_mentions", "needs_review",
                               "; ".join(hits.values()) or (_PLURAL.search(norm).group(0) if plural else None))
        if len(hits) == 1:
            bid, snippet = next(iter(hits.items()))
            kind = next(k for _, i, k in self.branches if i == bid)
            return Attribution(bid, "explicit_branch_text" if kind == "branch" else "explicit_regional_office_text",
                               "auto_assigned", snippet)
        if head:
            return Attribution(self.ids[HEAD_OFFICE], "explicit_head_office_text", "auto_assigned", _HEAD_OFFICE)
        return Attribution(unalloc, "unallocated_no_explicit_branch", "needs_review")
