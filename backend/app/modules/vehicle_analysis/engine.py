"""Vehicle fleet analytics. Costs are the statement's own stated figures (maintenance, fuel, grand total); a month a vehicle has no figure for is
«no figure», never zero. Fuel quantity in the repairs statement is derived from cost by the price written in its formula and is labelled so;
consumption (km/L) is computed only from the usage report's own distance and fuel taken. Cost per km uses only vehicle-months that have a distance."""
import statistics
from collections import defaultdict

from app.core.analysis.opsupport import months_between, period_str, period_tuple


def prev_period(p: str, n: int = 1) -> str:
    y, m = period_tuple(p)
    t = y * 12 + (m - 1) - n
    return period_str(t // 12, t % 12 + 1)


def _pct(a, b):
    return None if not b else (a - b) / b * 100


def _cv(v, key):
    return v["values"].get(key)


def _maint(x: dict):
    """The stated maintenance total; when a row states none but has cost-category cells, the sum of those cells (their own stated numbers)."""
    if x.get("maint_total") is not None:
        return x["maint_total"]
    cats = [v for k, v in x.items() if k.startswith("cat:")]
    return sum(cats) if cats else None


def best_km(v: dict, p: str):
    """(km, source) for a vehicle-month: the usage report's stated distance, else the repairs statement's, else the odometer difference between
    consecutive card readings."""
    u = v["usage"].get(p)
    if u and u["values"].get("km_total") is not None:
        return u["values"]["km_total"], "usage"
    c = v["cost"].get(p)
    if c and c["values"].get("km"):
        return c["values"]["km"], "statement"
    s, sp = v["service"].get(p), v["service"].get(prev_period(p))
    if s and sp and s["values"].get("odometer") and sp["values"].get("odometer"):
        d = s["values"]["odometer"] - sp["values"]["odometer"]
        if d >= 0:
            return d, "odometer"
    return None, None


def analyze(data: dict, th: dict, focus: str | None = None, filters: dict | None = None) -> dict:
    filters = filters or {}
    vs = data["vehicles"]
    if filters.get("vehicles"):
        keep = set(filters["vehicles"])
        vs = [v for v in vs if v["key"] in keep]
    all_periods = sorted({p for v in vs for slot in ("cost", "usage", "service") for p in v[slot]})
    if focus:
        all_periods = [p for p in all_periods if p <= focus]
    cost_periods = sorted({p for v in vs for p in v["cost"] if (not focus or p <= focus)})
    if not all_periods:
        return {"empty": True}
    cp = months_between(cost_periods[0], cost_periods[-1]) if cost_periods else []

    # ---------------------------------------------------------------- monthly cost
    months, cat_tot = [], defaultdict(float)
    cat_month: dict = defaultdict(lambda: defaultdict(float))
    for p in cp:
        rows = [(v, v["cost"][p]["values"]) for v in vs if p in v["cost"]]
        tot = [(v, x.get("grand_total")) for v, x in rows if x.get("grand_total") is not None]
        m = {"period": p, "vehicles": len(rows), "with_total": len(tot), "active": sum(1 for _v, t in tot if t),
             "total": sum(t for _v, t in tot), "maint": sum(_maint(x) or 0 for _v, x in rows), "fuel": sum(x.get("fuel_cost") or 0 for _v, x in rows),
             "fuel_qty": sum(x.get("fuel_qty") or 0 for _v, x in rows), "km": 0.0, "km_n": 0}
        for v, x in rows:
            km, _s = best_km(v, p)
            if km:
                m["km"] += km
                m["km_n"] += 1
            for k, val in x.items():
                if k.startswith("cat:"):
                    cat_tot[k[4:]] += val
                    cat_month[k[4:]][p] += val
        months.append(m)
    act = sorted(m["active"] for m in months)
    usual = statistics.median(act) if act else 0
    for i, m in enumerate(months):
        m["partial"] = bool(usual and m["active"] < th["partial_month_share"] * usual)
        if i:
            m["d"], m["dpct"] = m["total"] - months[i - 1]["total"], _pct(m["total"], months[i - 1]["total"])
        m["large"] = bool(i and m.get("dpct") is not None and abs(m["dpct"]) >= th["mom_change_pct"] and not m["partial"] and not months[i - 1]["partial"])
    cats = sorted(({"name": k, "total": v} for k, v in cat_tot.items()), key=lambda c: -c["total"])
    grand = sum(c["total"] for c in cats)
    run = 0.0
    for c in cats:
        c["share"] = c["total"] / grand * 100 if grand else None
        run += c["share"] or 0
        c["cum"] = run

    # ---------------------------------------------------------------- vehicles
    vrows, outliers = [], []
    for v in vs:
        ms = {p: x["values"] for p, x in v["cost"].items() if (not focus or p <= focus)}
        tots = {p: x["grand_total"] for p, x in ms.items() if x.get("grand_total") is not None}
        kms = {p: best_km(v, p) for p in set(ms) | set(v["usage"])}
        kmsum = costkm_num = costkm_den = 0.0
        km_months = 0
        for p, (k, _s) in kms.items():
            if k and p in tots and k > 0:
                costkm_num += tots[p]
                costkm_den += k
                km_months += 1
        usage = {p: x["values"] for p, x in v["usage"].items() if (not focus or p <= focus)}
        cons = [(u["km_total"] / u["fuel_qty"]) for u in usage.values() if u.get("km_total") and u.get("fuel_qty")]
        total = sum(tots.values())
        med = statistics.median([t for t in tots.values() if t > 0]) if len([t for t in tots.values() if t > 0]) else None
        row = {"key": v["key"], "plate": v["plate"], "type": v["type"], "months": len(tots), "maint": sum(_maint(x) or 0 for x in ms.values()), "fuel": sum(x.get("fuel_cost") or 0 for x in ms.values()),
               "total": total, "avg": total / len(tots) if tots else None, "max": max(tots.items(), key=lambda kv: kv[1]) if tots else None, "km_months": km_months, "km": costkm_den,
               "cost_per_km": costkm_num / costkm_den if costkm_den else None, "median": med, "consumption": statistics.mean(cons) if cons else None, "aliases": sorted(v["aliases"]),
               "sources": [s for s, has in (("cost", ms), ("usage", usage), ("service", v["service"])) if has], "by_month": tots}
        vrows.append(row)
        if med and len([t for t in tots.values() if t > 0]) >= th["min_outlier_months"]:
            for p, t in tots.items():
                if t >= th["outlier_factor"] * med:
                    note = (ms[p].get("note") or "")
                    outliers.append({"plate": v["plate"], "period": p, "total": t, "median": med, "factor": t / med, "note": note})
    gt = sum(r["total"] for r in vrows)
    for r in vrows:
        r["share"] = r["total"] / gt * 100 if gt else None
    vrows.sort(key=lambda r: (-r["total"], r["plate"] or ""))
    outliers.sort(key=lambda o: -o["factor"])

    # ---------------------------------------------------------------- distance / fuel cross-checks
    kmrows = []
    for v in vs:
        for p in sorted(set(v["cost"]) | set(v["usage"]) | set(v["service"])):
            if focus and p > focus:
                continue
            c, u = v["cost"].get(p), v["usage"].get(p)
            odo = None
            s, sp = v["service"].get(p), v["service"].get(prev_period(p))
            if s and sp and s["values"].get("odometer") and sp["values"].get("odometer"):
                odo = s["values"]["odometer"] - sp["values"]["odometer"]
            vals = {"statement": c["values"].get("km") if c else None, "usage": u["values"].get("km_total") if u else None, "daily": u["values"].get("km_daily_sum") if u else None, "odometer": odo}
            if sum(1 for x in vals.values() if x) >= 2:
                kmrows.append({"plate": v["plate"], "period": p, **vals})
    fuelrows = []
    for v in vs:
        for p, u in v["usage"].items():
            c = v["cost"].get(p)
            uq = u["values"].get("fuel_qty")
            if (not focus or p <= focus) and c and uq is not None and c["values"].get("fuel_qty") is not None:
                fuelrows.append({"plate": v["plate"], "period": p, "derived": c["values"]["fuel_qty"], "stated": uq, "price": c["values"].get("fuel_price_in_formula"),
                                 "km": u["values"].get("km_total"), "consumption": (u["values"]["km_total"] / uq) if u["values"].get("km_total") and uq else None, "stated_rate": u["values"].get("consumption_stated")})
    # ---------------------------------------------------------------- service due
    due = []
    for v in vs:
        if not v["service"]:
            continue
        p = max(q for q in v["service"] if not focus or q <= focus) if any(not focus or q <= focus for q in v["service"]) else None
        if p is None:
            continue
        vals = v["service"][p]["values"]
        names = sorted({k.split(":")[1] for k in vals if k.startswith("svc:")})
        for n in names:
            rem = vals.get(f"svc:{n}:remaining")
            if rem is not None:
                due.append({"plate": v["plate"], "period": p, "item": n, "odometer": vals.get("odometer"), "next_due": vals.get(f"svc:{n}:next_due"), "remaining": rem, "state": "overdue" if rem < 0 else "soon" if rem <= th["service_due_km"] else "ok"})
    due.sort(key=lambda d: (d["remaining"], d["plate"] or ""))
    # ---------------------------------------------------------------- claims, coverage, candidates
    claims = [c for c in data["claims"] if not focus or (c.get("period") or "0") <= focus]
    cov = []
    for v in vs:
        cells = {}
        for p in all_periods:
            cells[p] = "".join(ch for ch, slot in (("C", "cost"), ("U", "usage"), ("S", "service")) if p in v[slot])
        cov.append({"plate": v["plate"], "cells": cells})
    cands = []
    for cnd in data["candidates"]:
        plates_ = cnd["plates"]
        match = 0
        by = {v["plate"]: v for v in data["vehicles"]}
        pairs = [by.get(x) for x in plates_ if x in by]
        costv = [v for v in pairs if v and v["cost"]]
        usev = [v for v in pairs if v and v["usage"]]
        if costv and usev:
            for p, c in costv[0]["cost"].items():
                u = usev[0]["usage"].get(p)
                if u and c["values"].get("km") and u["values"].get("km_total") and abs(c["values"]["km"] - u["values"]["km_total"]) < 0.5:
                    match += 1
        cands.append({"number": cnd["number"], "plates": plates_, "km_matches": match})
    cur = months[-1] if months else None
    tots = {"first": cp[0] if cp else None, "last": cp[-1] if cp else None, "vehicles": len(vrows), "with_cost": sum(1 for r in vrows if r["months"]), "total": gt, "maint": sum(r["maint"] for r in vrows), "fuel": sum(r["fuel"] for r in vrows),
            "months": len(months), "cur": cur, "partial_last": bool(cur and cur["partial"]), "outliers": len(outliers), "claims": len(claims), "due_soon": sum(1 for d in due if d["state"] != "ok"),
            "cost_per_km": (sum(r["total"] for r in vrows if r["cost_per_km"]) and None)}
    num_, den_ = 0.0, 0.0
    for r in vrows:
        if r["cost_per_km"] and r["km"]:
            num_ += r["cost_per_km"] * r["km"]
            den_ += r["km"]
    tots["cost_per_km"] = num_ / den_ if den_ else None
    tots["km_known"] = den_
    tots["maint_from_cats"] = sum(1 for v in vs for p, x in v["cost"].items() if (not focus or p <= focus) and x["values"].get("maint_total") is None and any(k.startswith("cat:") for k in x["values"]))
    tots["claims_original"] = sum(c.get("original") or 0 for c in claims)
    tots["claims_company"] = sum(c.get("company_share") or 0 for c in claims)
    tots["claims_insurer"] = sum(c.get("insurer_share") or 0 for c in claims)
    return {"empty": False, "filtered": bool(filters), "periods": all_periods, "cost_periods": cp, "months": months, "categories": cats, "cat_month": {k: dict(v) for k, v in cat_month.items()}, "vehicles": vrows, "outliers": outliers,
            "km_rows": kmrows, "fuel_rows": fuelrows, "due": due, "claims": claims, "coverage": cov, "candidates": cands, "totals": tots, "thresholds": th}
