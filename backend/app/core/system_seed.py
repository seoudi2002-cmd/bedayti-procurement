"""System rows every deployment needs. Created by the platform (not invented business data): they are the
fixed targets of the branch-attribution hierarchy."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.cleaning.normalizers import normalize_text
from app.models import DimBranch, EntityAlias

HEAD_OFFICE = "HEAD_OFFICE"
UNALLOCATED = "UNALLOCATED"


def ensure_system_branches(session: Session) -> dict[str, int]:
    ids: dict[str, int] = {}
    specs = {
        HEAD_OFFICE: dict(name_en="Head Office", name_ar="المركز الرئيسي", branch_type="head_office"),
        UNALLOCATED: dict(name_en="Unallocated / Branch Not Identified", name_ar=None, branch_type="unallocated"),
    }
    for key, vals in specs.items():
        row = session.scalar(select(DimBranch).where(DimBranch.system_key == key))
        if row is None:
            row = DimBranch(system_key=key, **vals)
            session.add(row)
            session.flush()
        ids[key] = row.id
    for raw in ("المركز الرئيسي", "Head Office"):
        norm = normalize_text(raw)
        if session.scalar(select(EntityAlias).where(EntityAlias.entity_type == "branch", EntityAlias.alias_norm == norm)) is None:
            session.add(EntityAlias(entity_type="branch", alias_raw=raw, alias_norm=norm, entity_id=ids[HEAD_OFFICE],
                                    confidence=1, status="approved", method="system_seed"))
    session.commit()
    return ids


def system_branch_id(session: Session, key: str) -> int:
    return ensure_system_branches(session)[key]
