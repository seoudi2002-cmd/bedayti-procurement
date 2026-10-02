"""Resolve messy source text to canonical dimension rows via entity_alias.

Order: approved alias → exact match on the dimension's own names/codes → fuzzy near-match (always held for
review, never auto-merged) → module policy ("create" a new row, or hold for "review").
"""
from dataclasses import dataclass
from difflib import SequenceMatcher, get_close_matches
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.cleaning.normalizers import clean_text, normalize_text
from app.models import DimBranch, DimCategory, DimCostCenter, DimItem, DimSupplier, EntityAlias

FUZZY_CUTOFF = 0.88


@dataclass(frozen=True)
class DimSpec:
    model: type
    name_cols: tuple[str, ...]  # columns whose values are matched against
    fuzzy: bool
    code_col: str | None = None  # auto-generated when a row is created without a natural code
    code_prefix: str = ""


DIMS: dict[str, DimSpec] = {
    "branch": DimSpec(DimBranch, ("code", "name_en", "name_ar"), True, "code", "BR"),
    "supplier": DimSpec(DimSupplier, ("code", "name", "name_ar"), True, "code", "SUP"),
    "category": DimSpec(DimCategory, ("code", "name"), True),
    "item": DimSpec(DimItem, ("sku", "name"), False),  # matched by code; fuzzy on SKUs is unsafe
    "cost_center": DimSpec(DimCostCenter, ("code", "name"), True, "code", "CC"),
}


@dataclass
class Resolution:
    status: str  # "resolved" | "review"
    entity_id: int | None = None
    alias_id: int | None = None
    created: bool = False


def create_entity(session: Session, entity_type: str, raw: str, name: str | None = None) -> int:
    spec = DIMS[entity_type]
    text = clean_text(raw) or raw
    kwargs: dict = {}
    if entity_type == "branch":
        kwargs["name_en"] = text
    elif entity_type == "supplier":
        kwargs["name"] = text
    elif entity_type == "category":
        kwargs.update(name=text, level=1)
    elif entity_type == "item":
        kwargs.update(sku=text, name=clean_text(name) or text)
    elif entity_type == "cost_center":
        kwargs["name"] = text
    if spec.code_col:
        kwargs[spec.code_col] = f"tmp-{uuid4().hex[:12]}"
    row = spec.model(**kwargs)
    session.add(row)
    session.flush()
    if spec.code_col:
        setattr(row, spec.code_col, f"{spec.code_prefix}-{row.id:05d}")
        session.flush()
    return row.id


class EntityResolver:
    def __init__(self, session: Session, policy: dict[str, str] | None = None):
        self.session = session
        self.policy = policy or {}
        self._index: dict[str, dict[str, int]] = {}
        self._memo: dict[tuple[str, str], Resolution] = {}

    def _names(self, entity_type: str) -> dict[str, int]:
        if entity_type not in self._index:
            spec = DIMS[entity_type]
            idx: dict[str, int] = {}
            for row in self.session.scalars(select(spec.model)):
                for col in spec.name_cols:
                    n = normalize_text(getattr(row, col, None))
                    if n:
                        idx.setdefault(n, row.id)
            self._index[entity_type] = idx
        return self._index[entity_type]

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
            return Resolution("resolved", alias.entity_id, alias.id)
        if alias and alias.status == "pending":
            return Resolution("review", alias.entity_id, alias.id)

        names = self._names(entity_type)
        if norm in names:
            return Resolution("resolved", names[norm])

        if spec.fuzzy and names:
            close = get_close_matches(norm, names.keys(), n=1, cutoff=FUZZY_CUTOFF)
            if close:
                return self._pending(entity_type, raw, norm, names[close[0]],
                                     SequenceMatcher(None, norm, close[0]).ratio())

        if self.policy.get(entity_type, "review") == "create":
            new_id = create_entity(self.session, entity_type, raw, name)
            self._index.pop(entity_type, None)
            self.session.add(EntityAlias(entity_type=entity_type, alias_raw=raw[:400], alias_norm=norm[:400],
                                         entity_id=new_id, confidence=1, status="approved"))
            self.session.flush()
            return Resolution("resolved", new_id, created=True)
        return self._pending(entity_type, raw, norm, None, None)

    def _pending(self, entity_type, raw, norm, suggested_id, score) -> Resolution:
        alias = EntityAlias(entity_type=entity_type, alias_raw=raw[:400], alias_norm=norm[:400],
                            entity_id=suggested_id, confidence=score, status="pending")
        self.session.add(alias)
        self.session.flush()
        return Resolution("review", suggested_id, alias.id)


def resolve_alias(session: Session, alias: EntityAlias, entity_id: int | None = None, create_new: bool = False) -> EntityAlias:
    """Review decision: map the alias to an existing row, or create a new canonical row from its text."""
    if alias.entity_type not in DIMS:
        raise ValueError(f"Unknown entity type {alias.entity_type}")
    if create_new == (entity_id is not None):
        raise ValueError("Provide exactly one of entity_id or create_new")
    spec = DIMS[alias.entity_type]
    if create_new:
        entity_id = create_entity(session, alias.entity_type, alias.alias_raw)
    elif session.get(spec.model, entity_id) is None:
        raise ValueError(f"{alias.entity_type} {entity_id} does not exist")
    alias.entity_id, alias.status, alias.confidence = entity_id, "approved", 1
    session.commit()
    return alias
