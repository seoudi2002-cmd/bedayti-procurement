from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.orm import Session

from app.api.routes import router
from app.core.modules.registry import get_registry
from app.db import get_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    registry = get_registry()  # fails fast if any module package is invalid
    with Session(get_engine()) as session:
        registry.sync_to_db(session)
    yield


app = FastAPI(title="Procurement & Administrative Intelligence Platform", version="0.1.0", lifespan=lifespan)
app.include_router(router, prefix="/api")
