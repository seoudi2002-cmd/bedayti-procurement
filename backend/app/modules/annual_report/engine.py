"""Annual management report: links rent, vehicle fleet and overtime for one year.

Nothing is stored here and nothing is recomputed differently: each module's own `service.load` (effective values across versions) and `engine.analyze`
produce the monthly series; the report slices them to the year. So the dashboards and this report show the same numbers from the same source.

Administrative operating cost (money) = rent + fleet (maintenance + fuel as stated), summed over the months in which BOTH are complete.
Overtime is in hours only (the statement has no amounts) so it is shown beside the cost and never added to it. A month a module marks partial / not available is
not an official figure of that module and is listed in the exclusions."""
import statistics
from collections import defaultdict

from app.core.analysis.opsupport import months_between
from app.core.settings_store import effective_thresholds
from app.modules.overtime_analysis import engine as ot_engine
from app.modules.overtime_analysis import service as ot_service
from app.modules.rent_analysis import engine as rent_engine
from app.modules.rent_analysis import service as rent_service
from app.modules.vehicle_analysis import engine as veh_engine
from app.modules.vehicle_analysis import service as veh_service


def _pct(a, b):
    return None if not b else (a - b) / b * 100


def years(session) -> list[int]:
    ys = set()
    if rent_service.has_data(session):
        ys |= {int(p[:4]) for c in rent_service.load(session)["contracts"] for p in c["months"]}
    if veh_service.has_data(session):
        ys |= {int(p[:4]) for v in veh_service.load(session)["vehicles"] for slot in ("cost", "usage", "service") for p in v[slot]}
    if ot_service.has_data(session):
        ys |= {int(r["period"][:4]) for r in ot_service.load(session)["roster"]}
    return sorted(ys, reverse=True)


def _split(items: list[dict], key, n: int):
    return items[:n]


def build(session, year: int) -> dict:
    """Everything the report needs for `year`, computed from the effective data."""
    ys = str(year)
    inyear = lambda p: p[:4] == ys
    th = effective_thresholds(session, "annual")[0]
    out = {"year": year, "thresholds": th, "modules": {}, "loads": {}, "module_thresholds": {}}

    # ---------------------------------------------------------------- rent
    rent = None
    if rent_service.has_data(session):
        d = rent_service.load(session)
        rth = effective_thresholds(session, "rent")[0]
        out["loads"]["rent"], out["module_thresholds"]["rent"] = d, rth
        a = rent_engine.analyze(d["contracts"], rth)
        if not a.get("empty"):
            ok = {m["period"]: m for m in a["avail"]}
            allm = {m["period"]: m for m in a["months"]}
            ymonths = [m for p, m in sorted(allm.items()) if inyear(p)]
            if ymonths:
                comp = [m for m in ymonths if m["available"] and m["period"] in ok]
                partial = [m["period"] for m in ymonths if m["available"] and m["period"] not in ok]
                missing = [m["period"] for m in ymonths if not m["available"]]
                gov: dict = defaultdict(float)
                for g in a["governorates"]:
                    for p, v in g["by_month"].items():
                        if p in {m["period"] for m in comp}:
                            gov[g["name"]] += v
                cons: dict = defaultdict(float)
                firstlast = []
                cps = [m["period"] for m in comp]
                for c in d["contracts"]:
                    tot = sum(v for p, v in c["months"].items() if p in cps)
                    if tot:
                        cons[c["key"]] = tot
                    if cps:
                        v0, v1 = c["months"].get(cps[0]), c["months"].get(cps[-1])
                        if v0 and v1 and abs(v1 - v0) > 0.005:
                            firstlast.append({"name": c["name"], "governorate": c["governorate"], "first": v0, "last": v1, "d": v1 - v0, "pct": _pct(v1, v0), "from": cps[0], "to": cps[-1]})
                names = {c["key"]: (c["name"], c["governorate"]) for c in d["contracts"]}
                prev = {m["period"]: m for m in a["avail"]}
                yoy = []
                for m in comp:
                    py = f"{year - 1}{m['period'][4:]}"
                    if py in prev:
                        yoy.append({"period": m["period"], "this": m["total"], "prev": prev[py]["total"], "d": m["total"] - prev[py]["total"], "pct": _pct(m["total"], prev[py]["total"])})
                rent = {"analysis": a, "months": ymonths, "complete": comp, "partial": partial, "missing": missing, "total": sum(m["total"] for m in comp),
                        "hq": sum(m["hq"] for m in comp), "branches": sum(m["branches"] for m in comp), "gov": sorted(({"name": k, "total": v} for k, v in gov.items()), key=lambda r: -r["total"]),
                        "contracts": sorted(({"name": names[k][0], "governorate": names[k][1], "total": v} for k, v in cons.items()), key=lambda r: -r["total"]),
                        "rises": sorted((r for r in firstlast if r["d"] > 0), key=lambda r: -r["d"]), "falls": sorted((r for r in firstlast if r["d"] < 0), key=lambda r: r["d"]), "yoy": yoy,
                        "expiring": a["expiring"], "expiring_long": a["totals"]["expiring_long"], "windows": (a["totals"]["expiring_window"], a["totals"]["expiring_long_window"]),
                        "advance": a["totals"]["advance_total"], "deposit": a["totals"]["deposit_total"], "contracts_n": a["totals"]["contracts"], "steps": [s for s in a["steps"] if inyear(s["period"])],
                        "periodic": len(a["periodic"]), "data": d}
    out["modules"]["rent"] = rent

    # ---------------------------------------------------------------- fleet
    fleet = None
    if veh_service.has_data(session):
        d = veh_service.load(session)
        vth = effective_thresholds(session, "vehicles")[0]
        out["loads"]["vehicles"], out["module_thresholds"]["vehicles"] = d, vth
        a = veh_engine.analyze(d, vth)
        if not a.get("empty") and a["months"]:
            ym = [m for m in a["months"] if inyear(m["period"])]
            if ym:
                comp = [m for m in ym if not m["partial"]]
                cps = {m["period"] for m in comp}
                allp = {m["period"] for m in ym}
                vrows = []
                for v in a["vehicles"]:
                    tot = sum(t for p, t in v["by_month"].items() if p in allp)
                    if tot or any(p in allp for p in v["by_month"]):
                        vrows.append({"plate": v["plate"], "type": v["type"], "total": tot, "total_complete": sum(t for p, t in v["by_month"].items() if p in cps), "months": sum(1 for p in v["by_month"] if p in allp),
                                      "cost_per_km": v["cost_per_km"], "km": v["km"], "by_month": {p: t for p, t in v["by_month"].items() if p in allp}})
                vrows.sort(key=lambda r: -r["total"])
                cats: dict = defaultdict(float)
                for k, bm in a["cat_month"].items():
                    for p, v in bm.items():
                        if p in cps:
                            cats[k] += v
                moves = []
                prevm = None
                for m in comp:
                    if prevm and m["period"] == _next(prevm["period"]):
                        for v in vrows:
                            x, y = v["by_month"].get(prevm["period"]), v["by_month"].get(m["period"])
                            if x is not None and y is not None and abs(y - x) > 0.005:
                                moves.append({"plate": v["plate"], "from": prevm["period"], "to": m["period"], "old": x, "new": y, "d": y - x, "pct": _pct(y, x)})
                    prevm = m
                fleet = {"analysis": a, "months": ym, "complete": comp, "partial": [m["period"] for m in ym if m["partial"]], "total": sum(m["total"] for m in ym), "total_complete": sum(m["total"] for m in comp),
                         "maint": sum(m["maint"] for m in ym), "fuel": sum(m["fuel"] for m in ym), "vehicles": vrows, "cats": sorted(({"name": k, "total": v} for k, v in cats.items()), key=lambda r: -r["total"]),
                         "rises": sorted((x for x in moves if x["d"] > 0), key=lambda r: -r["d"]), "falls": sorted((x for x in moves if x["d"] < 0), key=lambda r: r["d"]),
                         "outliers": [o for o in a["outliers"] if inyear(o["period"])], "claims": [c for c in a["claims"] if (c.get("period") or "")[:4] == ys], "due": a["due"], "candidates": a["candidates"], "data": d}
    out["modules"]["fleet"] = fleet

    # ---------------------------------------------------------------- overtime
    ot = None
    if ot_service.has_data(session):
        d = ot_service.load(session)
        oth = effective_thresholds(session, "overtime")[0]
        out["loads"]["overtime"], out["module_thresholds"]["overtime"] = d, oth
        a = ot_engine.analyze(d["rows"], d["roster"], oth)
        if not a.get("empty") and a["avail"]:
            ym = [m for m in a["avail"] if inyear(m["period"])]
            if ym:
                miss = [p for p in a["totals"]["missing"] if inyear(p)]
                emps = []
                for e in a["employees"]:
                    h = sum(v for p, v in e["by_month"].items() if inyear(p))
                    if h or any(inyear(p) for p in e["by_month"]):
                        emps.append({"code": e["code"], "name": e["name"], "hours": h, "months": sum(1 for p in e["by_month"] if inyear(p)), "by_month": {p: v for p, v in e["by_month"].items() if inyear(p)}})
                emps.sort(key=lambda r: -r["hours"])
                tot = sum(e["hours"] for e in emps)
                moves = []
                for i, m in enumerate(ym[1:], 1):
                    if m["period"] == _next(ym[i - 1]["period"]):
                        for e in emps:
                            x, y = e["by_month"].get(ym[i - 1]["period"]), e["by_month"].get(m["period"])
                            if x is not None and y is not None and abs(y - x) > 0.005:
                                moves.append({"code": e["code"], "name": e["name"], "from": ym[i - 1]["period"], "to": m["period"], "old": x, "new": y, "d": y - x, "pct": _pct(y, x)})
                ot = {"analysis": a, "months": ym, "missing": miss, "hours": sum(m["hours"] for m in ym), "day": sum(m["day_hours"] for m in ym), "night": sum(m["night_hours"] for m in ym),
                      "weighted": sum(m["weighted"] for m in ym), "meals": sum(m["meals"] for m in ym), "missions": sum(m["mission_day"] + m["mission_night"] for m in ym), "employees": emps,
                      "top_share": sum(e["hours"] for e in emps[:int(oth["concentration_top_n"])]) / tot * 100 if tot else None, "conc_n": int(oth["concentration_top_n"]),
                      "rises": sorted((x for x in moves if x["d"] > 0), key=lambda r: -r["d"]), "falls": sorted((x for x in moves if x["d"] < 0), key=lambda r: r["d"]), "high": [h for h in a["high"] if inyear(h["period"])],
                      "excluded": [e for s in d["summaries"] for e in s.get("excluded_sheets", []) if e["period"][:4] == ys], "data": d}
    out["modules"]["overtime"] = ot

    # ---------------------------------------------------------------- the combined cost (money only; complete months of both)
    r, f, o = out["modules"]["rent"], out["modules"]["fleet"], out["modules"]["overtime"]
    rm = {m["period"]: m for m in r["complete"]} if r else {}
    fm = {m["period"]: m for m in f["complete"]} if f else {}
    common = sorted(set(rm) & set(fm))
    allp = sorted(set(rm) | {m["period"] for m in (f["months"] if f else [])} | {m["period"] for m in (o["months"] if o else [])} | set(r["partial"] if r else []) | set(r["missing"] if r else []))
    om = {m["period"]: m for m in o["months"]} if o else {}
    rows = []
    for p in months_between(allp[0], allp[-1]) if allp else []:
        row = {"period": p, "rent": rm[p]["total"] if p in rm else None, "fleet": fm[p]["total"] if p in fm else None, "overtime_hours": om[p]["hours"] if p in om else None,
               "rent_state": "ok" if p in rm else ("partial" if r and p in r["partial"] else "missing"), "fleet_state": "ok" if p in fm else ("partial" if f and any(m["period"] == p for m in f["months"]) else "missing"),
               "overtime_state": "ok" if p in om else "missing"}
        row["combined"] = row["rent"] + row["fleet"] if p in common else None
        rows.append(row)
    comb = [x for x in rows if x["combined"] is not None]
    for i, x in enumerate(comb):
        if i:
            x["d"] = x["combined"] - comb[i - 1]["combined"]
            x["dpct"] = _pct(x["combined"], comb[i - 1]["combined"])
            x["gap_before"] = x["period"] != _next(comb[i - 1]["period"])
        x["large"] = bool(i and x.get("dpct") is not None and abs(x["dpct"]) >= th["mom_change_pct"] and not x.get("gap_before"))
    c_rent = sum(rm[p]["total"] for p in common)
    c_fleet = sum(fm[p]["total"] for p in common)
    out["combined"] = {"rows": rows, "common": common, "rent": c_rent, "fleet": c_fleet, "total": c_rent + c_fleet, "rent_share": c_rent / (c_rent + c_fleet) * 100 if c_rent + c_fleet else None,
                       "maint": sum(fm[p]["maint"] for p in common), "fuel": sum(fm[p]["fuel"] for p in common),
                       "avg_month": (c_rent + c_fleet) / len(common) if common else None, "peak": max(comb, key=lambda x: x["combined"]) if comb else None, "low": min(comb, key=lambda x: x["combined"]) if comb else None}
    # drivers over the common months only (so shares are of the same total)
    drivers = {"rent_gov": [], "rent_contracts": [], "fleet_cats": [], "fleet_vehicles": []}
    if r and common:
        g: dict = defaultdict(float)
        for gv in r["analysis"]["governorates"]:
            g[gv["name"]] = sum(v for p, v in gv["by_month"].items() if p in common)
        drivers["rent_gov"] = sorted(({"name": k, "total": v} for k, v in g.items() if v), key=lambda x: -x["total"])
        cc = []
        for c in r["data"]["contracts"]:
            t = sum(v for p, v in c["months"].items() if p in common)
            if t:
                cc.append({"name": c["name"], "governorate": c["governorate"], "total": t})
        drivers["rent_contracts"] = sorted(cc, key=lambda x: -x["total"])
    if f and common:
        cats: dict = defaultdict(float)
        for k, bm in f["analysis"]["cat_month"].items():
            for p, v in bm.items():
                if p in common:
                    cats[k] += v
        drivers["fleet_cats"] = sorted(({"name": k, "total": v} for k, v in cats.items() if v), key=lambda x: -x["total"])
        vv = [{"plate": v["plate"], "total": sum(t for p, t in v["by_month"].items() if p in common)} for v in f["vehicles"]]
        drivers["fleet_vehicles"] = sorted((x for x in vv if x["total"]), key=lambda x: -x["total"])
    out["drivers"] = drivers
    out["common"] = common
    return out


def _next(p: str) -> str:
    y, m = int(p[:4]), int(p[5:7])
    return f"{y + (m == 12)}-{m % 12 + 1:02d}"
