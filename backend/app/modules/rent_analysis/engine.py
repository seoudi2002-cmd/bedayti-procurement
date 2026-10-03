"""Rent analytics over the effective contracts (values from the newest file that states them).

The measure is the monthly rent *as recorded* (the file's own monthly cell). A blank «_____» means no payment is recorded for the month — it is
shown separately and never counted as zero. Contracts paid quarterly or irregularly therefore show their payments in the months they were
recorded; nothing is spread or estimated."""
import statistics
from collections import defaultdict
from datetime import date

from app.core.analysis.opsupport import months_between, period_str, period_tuple

UNALLOC = None


def prev_period(p: str, n: int = 1) -> str:
    y, m = period_tuple(p)
    t = y * 12 + (m - 1) - n
    return period_str(t // 12, t % 12 + 1)


def month_end(p: str) -> date:
    y, m = period_tuple(p)
    nxt = date(y + (m == 12), m % 12 + 1, 1)
    return date.fromordinal(nxt.toordinal() - 1)


def month_start(p: str) -> date:
    y, m = period_tuple(p)
    return date(y, m, 1)


def apply_filters(contracts: list[dict], filters: dict) -> list[dict]:
    out = contracts
    if filters.get("governorates"):
        gs = set(filters["governorates"])
        out = [c for c in out if (c["governorate"] or "") in gs or ("" in gs and c["governorate"] is None)]
    if filters.get("contracts"):
        ks = set(filters["contracts"])
        out = [c for c in out if c["key"] in ks]
    return out


def _pct(a, b):
    return None if not b else (a - b) / b * 100


def analyze(contracts: list[dict], th: dict, focus: str | None = None, filtered: bool = False) -> dict:
    periods_all = sorted({p for c in contracts for p in c["months"]})
    if focus:
        periods_all = [p for p in periods_all if p <= focus]
    if not periods_all:
        return {"empty": True, "periods": [], "filtered": filtered}
    first, last = periods_all[0], periods_all[-1]
    periods = months_between(first, last)
    stated = {p for c in contracts for p in (set(c["months"]) | set(c["nopay"])) if p <= last}      # months the file has a column with entries for
    missing = [p for p in periods if p not in stated]
    end_last = month_end(last)

    def val(c, p):
        return c["months"].get(p)

    # ---------------------------------------------------------------- monthly
    months = []
    for p in periods:
        if p not in stated:
            months.append({"period": p, "available": False})
            continue
        vs = [(c, val(c, p)) for c in contracts if val(c, p) is not None]
        total = sum(v for _c, v in vs)
        months.append({"period": p, "available": True, "total": total, "n": sum(1 for _c, v in vs if v > 0), "recorded": len(vs),
                       "nopay": sum(1 for c in contracts if p in c["nopay"] and p not in c["months"]),
                       "hq": sum(v for c, v in vs if c["scope"] == "hq"), "branches": sum(v for c, v in vs if c["scope"] != "hq")})
    avail_all = [m for m in months if m["available"]]
    usual = statistics.median(m["recorded"] for m in avail_all)
    for m in avail_all:
        m.setdefault("large", False)
    for m in avail_all:       # a month only a few contracts have an entry for (e.g. the governorate sheets have no column for it) is not comparable
        m["partial"] = bool(usual and m["recorded"] < th["partial_coverage_share"] * usual)
    avail = [m for m in avail_all if not m["partial"]] or avail_all
    partial = [m["period"] for m in avail_all if m["partial"] and m in avail_all and m not in avail]
    for i, m in enumerate(avail):
        if i:
            pm = avail[i - 1]
            m["d"] = m["total"] - pm["total"]
            m["dpct"] = _pct(m["total"], pm["total"])
            m["gap_before"] = pm["period"] != prev_period(m["period"])
        m["large"] = bool(i and m["dpct"] is not None and abs(m["dpct"]) >= th["mom_change_pct"] and not m["gap_before"])
    mlast = avail[-1]
    last = mlast["period"]
    prev = avail[-2]["period"] if len(avail) > 1 else None
    yoy = prev_period(last, 12)
    window = prev_period(last, 12)
    last12 = [m for m in avail if m["period"] > window]
    byp = {m["period"]: m for m in avail}

    # ---------------------------------------------------------------- governorates
    gov: dict = defaultdict(lambda: {"contracts": 0, "by_month": defaultdict(float), "n_last": 0})
    for c in contracts:
        g = gov[c["governorate"]]
        g["contracts"] += 1
        for p, v in c["months"].items():
            if p <= last:
                g["by_month"][p] += v
        if (val(c, last) or 0) > 0:
            g["n_last"] += 1
    grows = []
    for name, g in gov.items():
        lv, pv = g["by_month"].get(last, 0.0), (g["by_month"].get(prev, 0.0) if prev else 0.0)
        grows.append({"name": name, "contracts": g["contracts"], "n_last": g["n_last"], "last": lv, "prev": pv, "d": lv - pv, "dpct": _pct(lv, pv), "share": lv / mlast["total"] * 100 if mlast["total"] else None,
                      "year": sum(v for p, v in g["by_month"].items() if p > window), "by_month": dict(g["by_month"])})
    grows.sort(key=lambda r: (-r["last"], str(r["name"])))
    matrix_periods = [m["period"] for m in avail][-int(th["matrix_months"]):]

    # ---------------------------------------------------------------- per contract + steps
    rows, steps = [], []
    for c in contracts:
        seq = [(p, v) for p, v in sorted(c["months"].items()) if p <= last and v > 0]
        lastp, lastv = (seq[-1] if seq else (None, None))
        firstp, firstv = (seq[0] if seq else (None, None))
        cs = []
        for (p0, v0), (p1, v1) in zip(seq, seq[1:]):
            if abs(v1 - v0) > 0.005:
                cs.append({"name": c["name"], "governorate": c["governorate"], "period": p1, "old": v0, "new": v1, "pct": _pct(v1, v0), "large": abs(_pct(v1, v0)) >= th["large_step_pct"]})
        steps += cs
        blanks = sum(1 for p in c["nopay"] if p not in c["months"] and p <= last)
        end = c["end"]
        status = "unknown_end" if end is None else "expired" if end < month_start(last) else "ending" if end <= month_end(prev_period(last, -int(th["expiry_window_months"]))) else "active"
        rows.append({"key": c["key"], "name": c["name"], "governorate": c["governorate"], "scope": c["scope"], "start": c["start"], "start_raw": c["start_raw"], "end": end, "advance": c["advance"], "deposit": c["deposit"],
                     "contract_rent": c["contract_rent"], "first_period": firstp, "first": firstv, "last_period": lastp, "last": lastv, "steps": len(cs), "blank_months": blanks,
                     "recorded_months": len(seq), "status": status, "stated_current": c["current_rent_stated"], "in_latest_file": c.get("in_latest_file", True),
                     "has_last": (val(c, last) or 0) > 0, "flags": c["flags"], "versions": c.get("versions", 1), "landlord": c.get("landlord")})
    rows.sort(key=lambda r: (-(r["last"] or 0), r["name"]))
    steps.sort(key=lambda s: (s["period"], s["name"]), reverse=True)
    ups = [s for s in steps if s["pct"] and s["pct"] > 0 and not s["large"]]
    step_months = defaultdict(lambda: {"n": 0, "pcts": []})
    for s in steps:
        step_months[s["period"]]["n"] += 1
        step_months[s["period"]]["pcts"].append(s["pct"])
    step_by_month = [{"period": p, "n": d["n"], "avg_pct": statistics.mean(d["pcts"]), "max_pct": max(d["pcts"])} for p, d in sorted(step_months.items(), reverse=True)]
    buckets: dict = defaultdict(int)
    for s in ups:
        buckets[round(s["pct"], 1)] += 1
    step_dist = sorted(({"pct": k, "n": n} for k, n in buckets.items()), key=lambda x: -x["n"])[:8]

    # ---------------------------------------------------------------- expiry
    win = int(th["expiry_window_months"])
    expiring = sorted((r for r in rows if r["status"] == "ending"), key=lambda r: r["end"])
    expired_with_value = [r for r in rows if r["status"] == "expired" and r["has_last"]]
    expiry_months: dict = defaultdict(int)
    for r in rows:
        if r["end"] and r["end"] >= month_start(last):
            expiry_months[period_str(r["end"].year, r["end"].month)] += 1
    long_win = int(th["expiry_window_months_long"])
    lim_long = month_end(prev_period(last, -long_win))
    expiring_long = sum(1 for r in rows if r["end"] and month_start(last) <= r["end"] <= lim_long)

    # ---------------------------------------------------------------- quality
    before_start = after_end = 0
    ex_before, ex_after = [], []
    for c in contracts:
        for p, v in c["months"].items():
            if p > last or v <= 0:
                continue
            if c["start"] and month_end(p) < c["start"]:
                before_start += 1
                if len(ex_before) < 5:
                    ex_before.append(f"{c['name']}: {p}")
            if c["end"] and month_start(p) > c["end"]:
                after_end += 1
                if len(ex_after) < 5:
                    ex_after.append(f"{c['name']}: {p}")
    active_no_value = [r for r in rows if r["status"] in ("active", "ending") and not r["has_last"] and r["first_period"] and r["first_period"] <= last]
    periodic = [r for r in rows if r["blank_months"] >= int(th["periodic_min_blank_months"])]
    nodate = sum(1 for c in contracts if c["start"] is None or c["end"] is None)
    adv = [c["advance"] for c in contracts if c["advance"]]
    dep = [c["deposit"] for c in contracts if c["deposit"]]
    totals = {"contracts": len(contracts), "with_value_last": sum(1 for r in rows if r["has_last"]), "last": last, "prev": prev, "first": first, "total_last": mlast["total"], "total_prev": byp.get(prev, {}).get("total"),
              "d": mlast.get("d"), "dpct": mlast.get("dpct"), "gap_before_last": mlast.get("gap_before"), "year_total": sum(m["total"] for m in last12), "year_months": len(last12), "missing": missing, "partial_months": partial,
              "yoy_total": byp.get(yoy, {}).get("total"), "yoy": yoy,
              "yoy_pct": _pct(mlast["total"], byp[yoy]["total"]) if yoy in byp and byp[yoy]["total"] else None, "avg_per_contract": mlast["total"] / mlast["n"] if mlast["n"] else None,
              "advance_total": sum(adv), "advance_n": len(adv), "deposit_total": sum(dep), "deposit_n": len(dep), "hq_last": mlast["hq"], "branches_last": mlast["branches"],
              "expiring": len(expiring), "expiring_window": win, "expiring_long": expiring_long, "expiring_long_window": long_win, "expired_with_value": len(expired_with_value),
              "step_events": len(steps), "avg_up_pct": statistics.mean([s["pct"] for s in ups]) if ups else None, "periodic": len(periodic), "unresolved": sum(1 for c in contracts if c["governorate"] is None)}
    return {"empty": False, "filtered": filtered, "periods": periods, "avail": avail, "totals": totals, "months": months, "governorates": grows, "matrix_periods": matrix_periods, "rows": rows,
            "steps": steps, "step_by_month": step_by_month, "step_dist": step_dist, "expiring": expiring, "expired_with_value": expired_with_value, "expiry_months": dict(sorted(expiry_months.items())),
            "periodic": periodic, "active_no_value": active_no_value,
            "quality": {"before_start": before_start, "after_end": after_end, "ex_before": ex_before, "ex_after": ex_after, "nodate": nodate, "unresolved": totals["unresolved"]}, "thresholds": th}
