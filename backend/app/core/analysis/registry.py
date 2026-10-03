from app.core.analysis import AnalysisAdapter, AnalysisError

_ADAPTERS: dict[str, AnalysisAdapter] | None = None


def adapters() -> dict[str, AnalysisAdapter]:
    global _ADAPTERS
    if _ADAPTERS is None:
        from app.modules.copier_analysis.adapter import CopierAdapter
        from app.modules.custody_analysis.adapter import CustodyAdapter
        _ADAPTERS = {a.info.key: a for a in (CustodyAdapter(), CopierAdapter())}
    return _ADAPTERS


def get_adapter(key: str) -> AnalysisAdapter:
    try:
        return adapters()[key]
    except KeyError:
        raise AnalysisError(404, f"Unknown analysis module '{key}'") from None
