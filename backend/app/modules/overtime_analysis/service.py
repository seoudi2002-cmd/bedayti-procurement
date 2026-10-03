"""Overtime statement: ingest (one version per uploaded file) and load (effective values across versions)."""
from sqlalchemy.orm import Session

from app.core.analysis import AnalysisError, UploadResult
from app.core.analysis import opsupport as ops
from app.modules.overtime_analysis import workbook as wb

MODULE_ID = "overtime_analysis"
LAYOUT = "overtime_monthly"
NUM = [f for f in wb.FIELDS]


def build_records(sheets: list[wb.SheetData]) -> list[dict]:
    recs = []
    for sd in sheets:
        for r in sd.rows:
            personal = {"name": r.name} if r.name else None
            recs.append({"kind": "overtime_roster", "key": r.code, "label": r.code, "period": sd.period, "ref": r.ref, "values": {"listed": True}, "personal": personal})
            vals = {k: v for k, v in r.values.items() if v is not None}
            if vals:
                recs.append({"kind": "overtime", "key": r.code, "label": r.code, "period": sd.period, "ref": r.ref, "values": vals, "personal": personal})
    return recs


def controls(p: wb.Parsed, sheets: list[wb.SheetData]) -> list[dict]:
    """The annual sheet's stated totals against the sum of the months actually read."""
    comp: dict[str, float] = {}
    for sd in sheets:
        for r in sd.rows:
            for f, v in r.values.items():
                if v is not None:
                    comp[f] = comp.get(f, 0.0) + v
    return [{"field": f, "stated": s, "computed": round(comp.get(f, 0.0), 4), "diff": round(s - comp.get(f, 0.0), 4)} for f, s in p.summary_controls.items() if f != "raw_total"]


def ingest(session: Session, content: bytes, filename: str, user: str | None, options: dict) -> UploadResult:
    if not filename.lower().endswith((".xlsx", ".xlsm")):
        raise AnalysisError(422, "The overtime statement is an Excel workbook (.xlsx)")
    if not wb.is_overtime_workbook(content):
        raise AnalysisError(422, "Not an overtime statement (no «code» / «overtime hours» headers found)")
    digest, path = ops.store_file(MODULE_ID, content, filename)
    ops.check_duplicate(session, MODULE_ID, digest)
    try:
        p = wb.parse(content, options.get("year"))
    except wb.NotAnOvertimeWorkbook:
        raise AnalysisError(422, "No readable monthly sheet (a sheet needs a title that states the month and year)") from None
    sheets = wb.select(p)
    wb.check(p, sheets)
    recs = build_records(sheets)
    periods = sorted(sd.period for sd in sheets)
    summary = {"issues": p.issues.json(), "controls": controls(p, sheets), "periods": periods, "sheets": [{"sheet": s.sheet, "period": s.period, "employees": len(s.rows)} for s in p.sheets],
               "factors": list(p.factors) if p.factors else None}
    ds = ops.create_dataset(session, MODULE_ID, LAYOUT, "overtime", filename, digest, path, user, summary, periods, personal=True, title="overtime", year_source="file")
    ops.add_records(session, ds, recs)
    return UploadResult(item_id="all", meta={"id": "all", "version": ds.id, "layout": LAYOUT, "months": [periods[0], periods[-1]], "issues": summary["issues"], "status": "ready"})


def load(session: Session) -> dict:
    recs = ops.load_records(session, MODULE_ID)
    if not recs:
        return {"rows": [], "roster": [], "changes": [], "versions": [], "summaries": []}
    res = ops.resolve(recs)
    rows, roster = [], []
    for (kind, key, period), c in res["current"].items():
        base = {"code": key, "name": c["personal"].get("name"), "period": period, "versions": c["versions"]}
        if kind == "overtime":
            rows.append({**base, **{f: c["values"].get(f) for f in wb.FIELDS}})
        elif kind == "overtime_roster":
            roster.append(base)
    dss = ops.datasets(session, MODULE_ID)
    return {"rows": rows, "roster": roster, "changes": res["changes"], "versions": ops.versions_table(session, MODULE_ID, recs, res["changes"]), "summaries": [d.summary or {} for d in dss]}


def has_data(session: Session) -> bool:
    return bool(ops.datasets(session, MODULE_ID))
