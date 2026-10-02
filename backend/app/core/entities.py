"""Resolve messy source text to canonical dimension rows via entity_alias.

Order: approved alias → exact match on the dimension's own names/codes → same name ignoring spaces/hyphens
("ابو حماد" = "ابوحماد") → fuzzy near-match (always held for review, never auto-merged) → module policy
("create" a row from the source text, or hold for "review").

Rules: codes/SKUs are only ever taken from a source, never generated. Every resolution carries the method
used, so attribution is auditable.
"""
import re
from dataclasses import dataclass
from difflib import SequenceMatcher, get_close_matches

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.cleaning.normalizers import clean_text, normalize_text
from app.models import (
    DimBranch, DimCategory, DimCostCenter, DimDepartment, DimItem, DimSupplier, EntityAlias,
)

FUZZY_CUTOFF = 0.88
_ARABIC = re.compile("[؀-ۿ]")


@dataclass(frozen=True)
class DimSpec:
    model: type
    name_cols: tuple[str, ...]  # columns whose values are matched against
    fuzzy: bool


DIMS: dict[str, DimSpec] = {
    "branch": DimSpec(DimBranch, ("code", "name_en", "name_ar"), True),
    "supplier": DimSpec(DimSupplier, ("code", "name", "name_ar"), True),
    "category": DimSpec(DimCategory, ("code", "name"), True),
    "item": DimSpec(DimItem, ("sku", "name"), False),  # matched by code; fuzzy on SKUs is unsafe
    "cost_center": DimSpec(DimCostCenter, ("code", "name"), True),
    "department": DimSpec(DimDepartment, ("name",), True),
}


def compact(text: str) -> str:
    """Normalised text without spaces: spacing/hyphen variants of one name collapse to one key."""
    return normalize_text(text).replace(" ", "")


@dataclass
class Resolution:
    status: str  # "resolved" | "review"
    entity_id: int | None = None
    alias_id: int | None = None
    created: bool = False
    method: str = ""  # alias | exact | compact | created | fuzzy_suggestion | unresolved


def create_entity(session: Session, entity_type: str, raw: str, name: str | None = None,
                  branch_kind: str | None = None, region_id: int | None = None, source: str | None = None) -> int:
    spec = DIMS[entity_type]
    text = clean_text(raw) or raw
    kwargs: dict = {}
    if entity_type == "branch":
        kwargs["name_ar" if _ARABIC.search(text) else "name_en"] = text
        kwargs["branch_type"] = branch_kind or "branch"
        kwargs["region_id"] = region_id
    elif entity_type == "supplier":
        kwargs["name"] = text
    elif entity_type == "category":
        kwargs.update(name=text, level=1)
    elif entity_type == "item":
        kwargs.update(sku=text, name=clean_text(name) or text)
    elif entity_type == "cost_center":
        kwargs["name"] = text
    elif entity_type == "department":
        kwargs.update(name=text, source=source)
    row = spec.model(**kwargs)
    session.add(row)
    session.flush()
    return row.id


class EntityResolver:
    def __init__(self, session: Session, policy: dict[str, str] | None = None):
        self.session = session
        self.policy = policy or {}
        self._index: dict[str, tuple[dict[str, int], dict[str, int | None]]] = {}
        self._memo: dict[tuple[str, str], Resolution] = {}

    def _names(self, entity_type: str):
        if entity_type not in self._index:
            spec = DIMS[entity_type]
            exact: dict[str, int] = {}
            comp: dict[str, int | None] = {}  # None = ambiguous (two different rows share the compact key)
            for row in self.session.scalars(select(spec.model)):
                for col in spec.name_cols:
                    value = getattr(row, col, None)
                    n = normalize_text(value)
                    if not n:
                        continue
                    exact.setdefault(n, row.id)
                    c = compact(value)
                    if c in comp and comp[c] != row.id:
                        comp[c] = None
                    else:
                        comp.setdefault(c, row.id)
            self._index[entity_type] = (exact, comp)
        return self._index[entity_type]

    def invalidate(self, entity_type: str | None = None) -> None:
        for key in ([entity_type] if entity_type else list(self._index)):
            self._index.pop(key, None)
        self._memo.clear()

    def _alias(self, entity_type: str, norm: str) -> EntityAlias | None:
        return self.session.scalar(select(EntityAlias).where(
            EntityAlias.entity_type == entity_type, EntityAlias.alias_norm == norm))

    def resolve(self, entity_type: str, raw: object, name: str | None = None) -> Resolution | None:
        """None means the source cell was empty (nothing to resolve)."""
        norm = normalize_text(raw)
        if not norm:
            return None
        memo_key = (entity_type, norm)
        if memo_key in self._memo:
            return self._memo[memo_key]
        res = self._resolve(entity_type, str(raw), norm, name)
        self._memo[memo_key] = res
        return res

    def _resolve(self, entity_type: str, raw: str, norm: str, name: str | None) -> Resolution:
        spec = DIMS[entity_type]
        alias = self._alias(entity_type, norm)
        if alias and alias.status == "approved" and alias.entity_id:
            return Resolution("resolved", alias.entity_id, alias.id, method="alias")
        if alias and alias.status == "pending":
            return Resolution("review", alias.entity_id, alias.id, method="unresolved")

        exact, comp = self._names(entity_type)
        if norm in exact:
            return Resolution("resolved", exact[norm], method="exact")
        c = compact(raw)
        if comp.get(c) is not None:
            return Resolution("resolved", comp[c], method="compact")

        if spec.fuzzy and exact:
            close = get_close_matches(norm, exact.keys(), n=1, cutoff=FUZZY_CUTOFF)
            if close:
                return self._pending(entity_type, raw, norm, exact[close[0]],
                                     SequenceMatcher(None, norm, close[0]).ratio(), "fuzzy_suggestion")

        if self.policy.get(entity_type, "review") == "create":
            new_id = create_entity(self.session, entity_type, raw, name, source="source_value")
            self.invalidate(entity_type)
            self.session.add(EntityAlias(entity_type=entity_type, alias_raw=raw[:400], alias_norm=norm[:400],
                                         entity_id=new_id, confidence=1, status="approved", method="policy_create"))
            self.session.flush()
            return Resolution("resolved", new_id, created=True, method="created")
        return self._pending(entity_type, raw, norm, None, None, "unresolved")

    def _pending(self, entity_type, raw, norm, suggested_id, score, method) -> Resolution:
        alias = EntityAlias(entity_type=entity_type, alias_raw=raw[:400], alias_norm=norm[:400],
                            entity_id=suggested_id, confidence=score, status="pending")
        self.session.add(alias)
        self.session.flush()
        return Resolution("review", suggested_id, alias.id, method=method)


def resolve_alias(session: Session, alias: EntityAlias, entity_id: int | None = None, create_new: bool = False,
                  branch_kind: str | None = None, region_id: int | None = None) -> EntityAlias:
    """Review decision: map the alias to an existing row, or create a new canonical row from its text."""
    if alias.entity_type not in DIMS:
        raise ValueError(f"Unknown entity type {alias.entity_type}")
    if create_new == (entity_id is not None):
        raise ValueError("Provide exactly one of entity_id or create_new")
    spec = DIMS[alias.entity_type]
    if create_new:
        entity_id = create_entity(session, alias.entity_type, alias.alias_raw, branch_kind=branch_kind,
                                  region_id=region_id)
    elif session.get(spec.model, entity_id) is None:
        raise ValueError(f"{alias.entity_type} {entity_id} does not exist")
    alias.entity_id, alias.status, alias.confidence, alias.method = entity_id, "approved", 1, "review"
    session.commit()
    return alias
