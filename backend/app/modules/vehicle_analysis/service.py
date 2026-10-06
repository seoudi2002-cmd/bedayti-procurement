"""Vehicle fleet: ingest (one version per uploaded file; three file layouts) and load (effective values across versions, vehicles linked
across files by exact / digits-only / approved-alias plate match only)."""
from sqlalchemy.orm import Session

from app.core.analysis import AnalysisError, UploadResult
from app.core.analysis import opsupport as ops
from app.core.settings_store import effective_struct
from app.modules.vehicle_analysis import cards, grid, plates, repairs
from app.modules.vehicle_analysis.settings import alias_map

MODULE_ID = "vehicle_analysis"


def detect(gs, name: str) -> str | None:
    if repairs.is_repairs(gs):
        return "repairs_statement"
    if cards.is_usage(gs):
        return "usage_report"
    if cards.is_card(gs):
        return "maintenance_card"
    return None


def ingest(session: Session, content: bytes, filename: str, user: str | None, options: dict) -> UploadResult:
    if not filename.lower().endswith((".xlsx", ".xlsm", ".xls")):
        raise AnalysisError(422, "A vehicle file is an Excel workbook (.xlsx or .xls)")
    try:
        gs = grid.grids(content, filename)
    except Exception as exc:  # noqa: BLE001
        raise AnalysisError(422, f"The workbook could not be read: {exc}") from exc
    layout = detect(gs, filename)
    if layout is None:
        raise AnalysisError(422, "Not a recognised vehicle file (repairs statement, usage report or maintenance card)")
    digest, path = ops.store_file(MODULE_ID, content, filename)
    ops.check_duplicate(session, MODULE_ID, digest)
    recs: list[dict] = []
    summary: dict = {}
    year = year_source = None
    try:
        if layout == "repairs_statement":
            p = repairs.parse(gs, options.get("year"), filename)
            year, year_source = p.year, p.year_source
            for r in p.rows:
                vals = dict(r.values)
                if r.note:
                    vals["note"] = r.note
                recs.append({"kind": "vehicle_cost", "key": r.plate_key, "label": r.plate, "period": r.period, "ref": r.ref, "values": vals})
            for c in p.claims:
                recs.append({"kind": "vehicle_claim", "key": f"{ops.fold(c['desc'])}|{c['period']}", "label": c["desc"], "period": c["period"], "ref": c["ref"],
                             "values": {**c["values"], **({"note": c["note"]} if c["note"] else {})}})
            summary = {"controls": p.controls, "halfyear": p.halfyear, "prices": {k: sorted(v) for k, v in p.prices.items()}}
            periods = p.periods
            issues = p.issues
        else:
            p = cards.parse_usage(gs, filename) if layout == "usage_report" else cards.parse_card(gs, filename)
            for r in p.rows:
                recs.append({"kind": "vehicle_usage" if layout == "usage_report" else "vehicle_service", "key": r.plate_key, "label": r.plate, "period": r.period, "ref": r.ref,
                             "values": {**r.values, **({"type": r.vtype} if r.vtype else {})}, "personal": r.personal})
            periods, issues = p.periods, p.issues
            summary = {"skipped_periods": p.skipped}
    except (repairs.NotRepairs, cards.NotACard):
        raise AnalysisError(422, "The file looks like a vehicle file but no readable month sheet was found (the year or month could not be determined)") from None
    summary["issues"] = issues.json()
    ds = ops.create_dataset(session, MODULE_ID, layout, "vehicles", filename, digest, path, user, summary, periods, personal=True, title=layout, year=year, year_source=year_source)
    ops.add_records(session, ds, recs)
    return UploadResult(item_id="all", meta={"id": "all", "version": ds.id, "layout": layout, "months": [periods[0], periods[-1]], "records": len(recs), "issues": summary["issues"], "status": "ready"})


def load(session: Session) -> dict:
    recs = ops.load_records(session, MODULE_ID)
    if not recs:
        return {"vehicles": [], "claims": [], "candidates": [], "changes": [], "versions": [], "summaries": [], "layouts": []}
    res = ops.resolve(recs, replace_prefix={"vehicle_cost": "cat:"})
    cur = res["current"]
    cfg, _o = effective_struct(session, "vehicles.plates")
    aliases = alias_map(cfg["aliases"])
    order = [k for (kind, k, _p) in cur if kind == "vehicle_cost"] + [k for (kind, k, _p) in cur if kind != "vehicle_cost" and kind != "vehicle_claim"]
    canon, cand = plates.link(list(dict.fromkeys(order)), aliases)
    vehicles: dict[str, dict] = {}
    claims = []
    for (kind, key, period), c in cur.items():
        if kind == "vehicle_claim":
            claims.append({"desc": c["label"], "period": period, **c["values"]})
            continue
        ck = canon.get(key, key)
        v = vehicles.setdefault(ck, {"key": ck, "plate": None, "type": None, "cost": {}, "usage": {}, "service": {}, "aliases": set()})
        if key != ck:
            v["aliases"].add(c["label"] or key)
        if kind == "vehicle_cost" and (v["plate"] is None or key == ck):
            v["plate"] = c["label"]
        elif v["plate"] is None:
            v["plate"] = c["label"]
        if c["values"].get("type") and (v["type"] is None or kind == "vehicle_cost"):
            v["type"] = c["values"]["type"]
        slot = {"vehicle_cost": "cost", "vehicle_usage": "usage", "vehicle_service": "service"}[kind]
        v[slot][period] = {"values": c["values"], "personal": c["personal"], "versions": c["versions"]}
    dss = ops.datasets(session, MODULE_ID)
    cand_out = [{"number": d, "plates": [vehicles[k]["plate"] if k in vehicles else k for k in ks]} for d, ks in cand]
    return {"vehicles": sorted(vehicles.values(), key=lambda v: v["plate"] or ""), "claims": claims, "candidates": cand_out, "changes": res["changes"],
            "versions": ops.versions_table(session, MODULE_ID, recs, res["changes"]), "summaries": [d.summary or {} for d in dss], "layouts": sorted({d.layout for d in dss}),
            "aliases_origin": cfg["aliases"]}


def has_data(session: Session) -> bool:
    return bool(ops.datasets(session, MODULE_ID))
