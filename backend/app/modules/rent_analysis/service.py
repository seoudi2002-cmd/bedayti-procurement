"""Rent register: ingest (one version per uploaded file) and load (effective values across versions)."""
from datetime import date

from sqlalchemy.orm import Session

from app.core.analysis import AnalysisError, UploadResult
from app.core.analysis import opsupport as ops
from app.modules.rent_analysis import workbook as wb

MODULE_ID = "rent_analysis"
LAYOUT = "rent_register"
HQ_LABEL = "المركز الرئيسي"


def _iso(d: date | None):
    return d.isoformat() if d else None


def build_records(p: wb.Parsed, a: dict) -> list[dict]:
    recs = []
    for c in a["contracts"]:
        cp: wb.Copy = c["copy"]
        recs.append({"kind": "rent_contract", "key": c["key"], "label": cp.name, "period": None, "ref": f"{cp.sheet}!{cp.row}",
                     "values": {"governorate": c["governorate"], "evidence": c["evidence"], "scope": "hq" if cp.hq else "branch", "start": _iso(cp.start), "start_raw": cp.start_raw,
                                "end": _iso(cp.end), "end_raw": cp.end_raw, "advance": cp.advance, "deposit": cp.deposit, "contract_rent": cp.contract_rent,
                                "current_rent_stated": cp.current_rent},
                     "personal": {"landlord": cp.landlord} if cp.landlord else None, "flags": [f for f in cp.flags if not f.startswith("non_numeric")]})
        for pe in sorted(set(cp.months) | cp.nopay):
            recs.append({"kind": "rent_value", "key": c["key"], "label": cp.name, "period": pe, "ref": f"{cp.sheet}!{cp.row}",
                         "values": {"rent": cp.months.get(pe), "no_payment": True if pe in cp.nopay and pe not in cp.months else None}})
    return recs


def controls(p: wb.Parsed, a: dict) -> list[dict]:
    """The file's own footer totals compared with the sum of the contracts they cover."""
    by_gov: dict[str, dict] = {}
    for c in a["contracts"]:
        g = c["governorate"]
        if g is None:
            continue
        d = by_gov.setdefault(g, {})
        for pe, v in c["copy"].months.items():
            d[pe] = d.get(pe, 0.0) + v
    out = []
    for ct in p.controls:
        label = ct.label or ""
        if not (ct.owner_rows or ct.sheet == HQ_LABEL) or ct.sheet not in by_gov:
            continue
        comp = by_gov[ct.sheet]
        stated = {pe: v for pe, v in ct.values.items() if pe in comp or v}
        bad = [(pe, v, round(comp.get(pe, 0.0), 2)) for pe, v in sorted(stated.items()) if abs(v - comp.get(pe, 0.0)) > 0.5]
        out.append({"sheet": ct.sheet, "row": ct.row, "label": label or None, "periods": len(stated), "matched": len(stated) - len(bad), "mismatched": len(bad),
                    "examples": [{"period": pe, "stated": v, "computed": c} for pe, v, c in bad[:6]]})
    return out


def _sig(months: dict):
    return tuple(sorted(months.items()))


def _exception_summary(e: dict, a: dict) -> dict:
    """The copies of a contract grouped by what they state (sheets that agree are listed together) — values and their source, for the exceptions table."""
    groups: dict = {}
    for c in e["copies"]:
        groups.setdefault((_sig(c["months"]), c["start"], c["contract_rent"]), []).append(c)
    out = []
    for (sig, start, rent), cps in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        out.append({"sheets": sorted({f"{c['sheet']}!{c['row']}" for c in cps})[:4], "n_sheets": len({c["sheet"] for c in cps}), "start": start, "contract_rent": rent, "months": dict(sig)})
    return {"name": e["name"], "status": e["status"], "evidence": e["evidence"], "chosen": e.get("chosen"), "groups": out}


def ingest(session: Session, content: bytes, filename: str, user: str | None, options: dict) -> UploadResult:
    if not filename.lower().endswith((".xlsx", ".xlsm")):
        raise AnalysisError(422, "The rent register is an Excel workbook (.xlsx)")
    if not wb.is_rent_workbook(content):
        raise AnalysisError(422, "Not a rent contract register (no contract start/end columns found)")
    digest, path = ops.store_file(MODULE_ID, content, filename)
    ops.check_duplicate(session, MODULE_ID, digest)
    try:
        p = wb.parse(content)
    except wb.NotARentWorkbook:
        raise AnalysisError(422, "Not a rent contract register (no readable sheet)") from None
    a = wb.assemble(p)
    recs = build_records(p, a)
    periods = sorted({r["period"] for r in recs if r["kind"] == "rent_value" and r["values"].get("rent") is not None})
    ctr = controls(p, a)
    ev: dict[str, int] = {}
    for c in a["contracts"]:
        ev[c["evidence"] or "none"] = ev.get(c["evidence"] or "none", 0) + 1
    summary = {"issues": p.issues.json(), "controls": ctr, "sheets": p.sheets, "hidden_sheets": p.hidden, "contracts": len(a["contracts"]), "excluded": a["excluded"],
               "evidence": ev, "stale_contracts": a["stale_contracts"], "stale_cells": a["stale_cells"], "exceptions": [_exception_summary(e, a) for e in a["exceptions"]]}
    ds = ops.create_dataset(session, MODULE_ID, LAYOUT, "rent", filename, digest, path, user, summary, periods, personal=True, title="rent register", year_source="file")
    ops.add_records(session, ds, recs)
    return UploadResult(item_id="all", meta={"id": "all", "version": ds.id, "layout": LAYOUT, "contracts": len(a["contracts"]), "months": [periods[0], periods[-1]] if periods else None,
                                            "issues": summary["issues"], "status": "ready"})


def _d(s):
    return date.fromisoformat(s) if s else None


def load(session: Session) -> dict:
    """Effective contracts (values from the newest file that states them) + the change log + the version list."""
    recs = ops.load_records(session, MODULE_ID)
    if not recs:
        return {"contracts": [], "changes": [], "versions": [], "datasets": [], "issues": []}
    res = ops.resolve(recs, ignore=("evidence",))
    cur = res["current"]
    contracts: dict[str, dict] = {}
    for (kind, key, period), c in cur.items():
        if kind != "rent_contract":
            continue
        v = c["values"]
        contracts[key] = {"key": key, "name": c["label"], "governorate": v.get("governorate"), "evidence": v.get("evidence"), "scope": v.get("scope", "branch"),
                          "start": _d(v.get("start")), "end": _d(v.get("end")), "start_raw": v.get("start_raw"), "end_raw": v.get("end_raw"), "advance": v.get("advance"),
                          "deposit": v.get("deposit"), "contract_rent": v.get("contract_rent"), "current_rent_stated": v.get("current_rent_stated"), "landlord": c["personal"].get("landlord"),
                          "flags": c["flags"], "months": {}, "nopay": set(), "versions": c["versions"], "last_dataset": c["last_dataset"]}
    for (kind, key, period), c in cur.items():
        if kind == "rent_value" and key in contracts:
            v = c["values"]
            if v.get("rent") is not None:
                contracts[key]["months"][period] = v["rent"]
            elif v.get("no_payment"):
                contracts[key]["nopay"].add(period)
    dss = ops.datasets(session, MODULE_ID)
    latest = dss[-1].id
    for c in contracts.values():
        c["in_latest_file"] = c["last_dataset"] == latest
    return {"contracts": list(contracts.values()), "changes": res["changes"], "versions": ops.versions_table(session, MODULE_ID, recs, res["changes"]), "datasets": dss,
            "summaries": [d.summary or {} for d in dss]}


def has_data(session: Session) -> bool:
    return bool(ops.datasets(session, MODULE_ID))
