import shutil
from pathlib import Path

import pytest

from app.core.modules.registry import ModuleConfigError, ModuleRegistry, load_module


def test_purchase_orders_module_loads():
    from app.core.modules.registry import get_registry
    spec = get_registry().get("purchase_orders")
    assert spec.manifest.category == "procurement"
    assert {"total_spend", "savings_rate"} <= {k.code for k in spec.kpis}
    assert spec.schema_.field("supplier").dimension == "supplier"


def test_template_is_not_loaded_as_module():
    assert "_template" not in {m.manifest.id for m in ModuleRegistry().all()}


def test_registry_syncs_to_db(session):
    from app.models import ReportModule
    assert session.get(ReportModule, "purchase_orders").name.startswith("Purchase Orders")


def _clone(tmp_path: Path) -> Path:
    src = Path(__file__).resolve().parents[1] / "app" / "modules" / "purchase_orders"
    dst = tmp_path / "purchase_orders"
    shutil.copytree(src, dst)
    return dst


def test_bad_kpi_reference_rejected(tmp_path):
    pkg = _clone(tmp_path)
    (pkg / "kpis.yaml").write_text("kpis:\n  - {code: r, name: R, kind: ratio, numerator: nope, denominator: nada}\n")
    with pytest.raises(ModuleConfigError, match="unknown KPI"):
        load_module(pkg)


def test_folder_must_match_id(tmp_path):
    pkg = _clone(tmp_path)
    pkg.rename(tmp_path / "other")
    with pytest.raises(ModuleConfigError, match="must match folder"):
        load_module(tmp_path / "other")
