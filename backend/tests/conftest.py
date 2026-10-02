import os

os.environ["UPLOAD_DIR"] = os.path.join(os.path.dirname(__file__), "..", ".test_uploads")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.modules.registry import get_registry
from app.models import Base


@pytest.fixture
def engine():
    eng = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def session(engine):
    with Session(engine) as s:
        get_registry().sync_to_db(s)
        yield s


@pytest.fixture
def po_spec():
    return get_registry().get("purchase_orders")
