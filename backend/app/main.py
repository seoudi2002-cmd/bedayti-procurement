from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.orm import Session

from app.api.extraction import router as extraction_router
from app.api.masterdata import router as masterdata_router
from app.api.procurement import router as procurement_router
from app.api.routes import router
from app.core.modules.registry import get_registry
from app.core.system_seed import ensure_system_branches
from app.db import get_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    registry = get_registry()  # fails fast if any module package is invalid
    with Session(get_engine()) as session:
        registry.sync_to_db(session)
        ensure_system_branches(session)
    yield


app = FastAPI(title="Procurement & Administrative Intelligence Platform", version="0.1.0", lifespan=lifespan)
app.include_router(router, prefix="/api")
app.include_router(procurement_router, prefix="/api")
app.include_router(masterdata_router, prefix="/api")
app.include_router(extraction_router, prefix="/api")
