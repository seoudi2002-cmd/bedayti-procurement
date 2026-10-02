"""Per-module load step: validated raw rows → dimensions + facts.

Each module package may provide `loader.py` exposing `load(session, batch) -> int`.
It resolves entities (branch/supplier/...) through entity_alias, writes fact_cost / fact_usage
and any module-specific table, and must be idempotent per batch (delete-then-insert by batch_id).
Implemented per module in its own implementation phase.
"""
import importlib
from typing import Protocol

from sqlalchemy.orm import Session

from app.models.meta import ImportBatch


class ModuleLoader(Protocol):
    def load(self, session: Session, batch: ImportBatch) -> int:  # rows written
        ...


class LoaderNotImplemented(NotImplementedError):
    pass


def get_loader(module_id: str) -> ModuleLoader:
    try:
        return importlib.import_module(f"app.modules.{module_id}.loader")
    except ModuleNotFoundError:
        raise LoaderNotImplemented(f"Module '{module_id}' has no loader yet") from None
