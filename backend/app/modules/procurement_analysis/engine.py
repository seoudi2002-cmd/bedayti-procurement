"""Procurement register analytics over plain dicts (see service.load). Money is Decimal. A PO without a stated total is counted as a PO but
never as 0 spend; cancelled POs are kept and shown separately, never silently dropped. Register wording (statuses, 'paid', 'remaining') is the
source's own text: «handed to Finance» is what the register records, not a confirmed bank payment."""
import statistics
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

ZERO = Decimal(0)


def _pct(a, b):
    return float(Decimal(a) / Decimal(b) * 100) if b else None


def _month(d):
    return (d.year, d.month) if d else None


def _prev(m):
    return (m[0] - 1, 12) if m[1] == 1 else (m[0], m[1] - 1)


def _pctile(vals, p):
    if not vals:
        return None
    v = sorted(vals)
    k = (len(v) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(v) - 1)
    return v[lo] + (v[hi] - v[lo]) * (k - lo)


def apply_filters(data: dict, filters: dict) -> dict:
    """months (YYYY-MM): by each entity's own date; suppliers: POs, their memos and the requisitions that led to them; departments: requisitions and the POs they led to."""
    months, sups, deps = set(filters.get("months") or ()), set(filters.get("suppliers") or ()), set(filters.get("departments") or ())
    ym = lambda d: d.strftime("%Y-%m") if d else None
    pos = [p for p in data["pos"] if (not months or ym(p["date"]) in months) and (not sups or p["supplier"] in sups) and (not deps or p["department"] in deps)]
    ids = {p["id"] for p in pos}
    memos = [m for m in data["memos"] if (not months or ym(m["date"]) in months) and (not sups or m["supplier"] in sups or any(p["id"] == m["po_id"] and p["supplier"] in sups for p in data["pos"]))
             and (not deps or m["po_id"] in ids)]
    led = {p["requisition_id"] for p in pos if p["requisition_id"]}      # a supplier filter keeps the requisitions that led to those POs
    reqs = [r for r in data["requisitions"] if (not months or ym(r["date"]) in months) and (not deps or r["department"] in deps) and (not sups or r["id"] in led)]
    return {**data, "pos": pos, "memos": memos, "requisitions": reqs}


def analyze(data: dict, th: dict, filtered: bool, as_of: date | None) -> dict:
    pos, reqs, memos = data["pos"], data["requisitions"], data["memos"]
    priced = [p for p in pos if p["total"] is not None]
    spend = sum((p["total"] for p in priced), ZERO)
    canc = [p for p in pos if p["cancelled"]]
    canc_value = sum((p["total"] for p in canc if p["total"] is not None), ZERO)
    handed_reg = sum((p["handed"] for p in pos if p["handed"] is not None), ZERO)
    remaining_reg = sum((p["remaining"] for p in pos if p["remaining"] is not None), ZERO)
    memo_po = sum((m["amount"] for m in memos if m["type"] == "po" and m["amount"] is not None), ZERO)
    memo_svc = sum((m["amount"] for m in memos if m["type"] == "service" and m["amount"] is not None), ZERO)
    linked = {p["requisition_id"] for p in pos if p["requisition_id"]}
    t = {"po_n": len(pos), "priced_n": len(priced), "unpriced_n": len(pos) - len(priced), "spend": spend, "avg_po": spend / len(priced) if priced else None,
         "suppliers_n": len({p["supplier"] for p in pos if p["supplier"]}), "po_no_supplier_n": sum(1 for p in pos if not p["supplier"]),
         "cancelled_n": len(canc), "cancelled_value": canc_value, "handed_register": handed_reg, "remaining_register": remaining_reg,
         "req_n": len(reqs), "req_with_po_n": sum(1 for r in reqs if r["id"] in linked), "memo_n": len(memos), "memo_amount": memo_po + memo_svc,
         "memo_po_amount": memo_po, "memo_service_amount": memo_svc, "memo_po_n": sum(1 for m in memos if m["type"] == "po"),
         "memo_service_n": sum(1 for m in memos if m["type"] == "service"), "memo_no_amount_n": sum(1 for m in memos if m["amount"] is None)}
    t["req_conversion_pct"] = _pct(t["req_with_po_n"], t["req_n"])

    # ---------------------------------------------------------------- months
    mm: dict = defaultdict(lambda: {"po_n": 0, "po_value": ZERO, "priced_n": 0, "req_n": 0, "memo_po": ZERO, "memo_svc": ZERO, "memo_n": 0})
    for p in pos:
        if p["date"]:
            c = mm[_month(p["date"])]
            c["po_n"] += 1
            if p["total"] is not None:
                c["po_value"] += p["total"]
                c["priced_n"] += 1
    for r in reqs:
        if r["date"]:
            mm[_month(r["date"])]["req_n"] += 1
    for m in memos:
        if m["date"] and m["amount"] is not None:
            c = mm[_month(m["date"])]
            c["memo_n"] += 1
            c["memo_po" if m["type"] == "po" else "memo_svc"] += m["amount"]
    months = []
    prev = None
    for k in sorted(mm):
        c = {"period": k, **mm[k]}
        y, mo = k
        last = date(y + (mo == 12), mo % 12 + 1, 1) - timedelta(days=1)
        c["partial"] = bool(as_of and last > as_of)           # the latest month of the data may not be complete
        if prev is not None and _prev(k) == prev["period"]:
            c["d_value"], c["d_value_pct"] = c["po_value"] - prev["po_value"], _pct(c["po_value"] - prev["po_value"], prev["po_value"])
            c["d_po_n"] = c["po_n"] - prev["po_n"]
        months.append(c)
        prev = c
    undated = {"po": sum(1 for p in pos if not p["date"]), "req": sum(1 for r in reqs if not r["date"]), "memo": sum(1 for m in memos if not m["date"])}

    # ---------------------------------------------------------------- suppliers / categories
    def grp(keyf, valf=lambda p: p["total"]):
        d: dict = {}
        for p in pos:
            k = keyf(p) or None
            c = d.setdefault(k, {"key": k, "n": 0, "priced_n": 0, "value": ZERO})
            c["n"] += 1
            v = valf(p)
            if v is not None:
                c["value"] += v
                c["priced_n"] += 1
        out = sorted(d.values(), key=lambda c: (-c["value"], -c["n"], str(c["key"])))
        cum = ZERO
        for c in out:
            cum += c["value"]
            c["share"], c["cum_share"] = _pct(c["value"], spend), _pct(cum, spend)
            c["avg"] = c["value"] / c["priced_n"] if c["priced_n"] else None
        return out
    sup = grp(lambda p: p["supplier"])
    k = int(th["concentration_top_n"])
    named = [s for s in sup if s["key"]]
    conc = _pct(sum((s["value"] for s in named[:k]), ZERO), spend)
    cats = grp(lambda p: p["po_category"])
    scats = grp(lambda p: p["supplier_category"])

    # ---------------------------------------------------------------- requisitions / departments / statuses
    dep: dict = {}
    for r in reqs:
        c = dep.setdefault(r["department"], {"key": r["department"], "req_n": 0, "urgent_n": 0, "with_po_n": 0, "po_n": 0, "po_value": ZERO})
        c["req_n"] += 1
        c["urgent_n"] += 1 if r["priority"] and "عاجل" in r["priority"] else 0
        c["with_po_n"] += 1 if r["id"] in linked else 0
    for p in pos:
        if p["department"] in dep or p["department"] is None:
            c = dep.setdefault(p["department"], {"key": p["department"], "req_n": 0, "urgent_n": 0, "with_po_n": 0, "po_n": 0, "po_value": ZERO})
            c["po_n"] += 1
            c["po_value"] += p["total"] or ZERO
    departments = sorted(dep.values(), key=lambda c: (-c["req_n"], str(c["key"])))
    for c in departments:
        c["conversion"] = _pct(c["with_po_n"], c["req_n"])
    req_status = _count(r["status"] for r in reqs)
    prio = _count(r["priority"] for r in reqs)
    po_status = defaultdict(lambda: {"n": 0, "value": ZERO})
    for p in pos:
        c = po_status[p["order_status"]]
        c["n"] += 1
        c["value"] += p["total"] or ZERO
    po_status = sorted(({"key": k_, **v} for k_, v in po_status.items()), key=lambda c: -c["n"])

    # ---------------------------------------------------------------- pipeline: lead times and handover coverage
    lt_req = [(p["date"] - p["req_date"]).days for p in pos if p["date"] and p["req_date"]]
    by_po = {p["id"]: p for p in pos}
    lt_fin = [(m["date"] - by_po[m["po_id"]]["date"]).days for m in memos if m["po_id"] in by_po and m["date"] and by_po[m["po_id"]]["date"]]
    tol = Decimal(str(th["reconcile_tolerance"]))
    cov = {"none": 0, "partial": 0, "full": 0, "exceeds": 0, "no_total": 0}
    for p in pos:
        if p["total"] is None:
            cov["no_total"] += 1
        elif not p["handed"]:
            cov["none"] += 1
        elif p["handed"] > p["total"] + tol:
            cov["exceeds"] += 1
        elif abs(p["handed"] - p["total"]) <= tol:
            cov["full"] += 1
        else:
            cov["partial"] += 1
    long = th["long_lead_days"]
    pipeline = {"req_to_po_days": {"n": len(lt_req), "median": statistics.median(lt_req) if lt_req else None, "p90": _pctile(lt_req, 0.9),
                                   "negative": sum(1 for x in lt_req if x < 0), "long": sum(1 for x in lt_req if x > long)},
                "po_to_memo_days": {"n": len(lt_fin), "median": statistics.median(lt_fin) if lt_fin else None, "p90": _pctile(lt_fin, 0.9),
                                    "negative": sum(1 for x in lt_fin if x < 0), "long": sum(1 for x in lt_fin if x > long)},
                "coverage": cov}

    # ---------------------------------------------------------------- memos by purchase category; branch attribution
    mcat: dict = {}
    for m in memos:
        c = mcat.setdefault((m["type"], m["category"]), {"type": m["type"], "key": m["category"], "n": 0, "amount": ZERO})
        c["n"] += 1
        c["amount"] += m["amount"] or ZERO
    memo_cats = sorted(mcat.values(), key=lambda c: -c["amount"])
    attr = {"auto": 0, "review": 0, "other": 0}
    bval: dict = defaultdict(lambda: {"n": 0, "value": ZERO})
    for p in pos:
        st = p["branch_status"]
        attr["auto" if st in ("auto_assigned", "confirmed") else "review" if st == "needs_review" else "other"] += 1
        label = p["branch"] if st in ("auto_assigned", "confirmed") and p["branch"] else ("HQ" if st in ("auto_assigned", "confirmed") and p["branch_type"] == "head_office" else None)
        bval[label]["n"] += 1
        bval[label]["value"] += p["total"] or ZERO
    branches = sorted(({"key": k_, **v} for k_, v in bval.items()), key=lambda c: (c["key"] is None, -c["value"]))
    return {"totals": t, "months": months, "undated": undated, "suppliers": sup, "concentration_pct": conc, "categories": cats, "supplier_categories": scats,
            "departments": departments, "req_status": req_status, "priority": prio, "po_status": po_status, "pipeline": pipeline, "memo_categories": memo_cats,
            "attribution": attr, "branch_value": branches, "filtered": filtered, "thresholds": th}


def _count(it):
    d: dict = defaultdict(int)
    for x in it:
        d[x] += 1
    return sorted(({"key": k, "n": n} for k, n in d.items()), key=lambda c: -c["n"])


def exception_summary(exceptions: list[dict]) -> list[dict]:
    d: dict = {}
    for e in exceptions:
        if e["status"] != "open":
            continue
        c = d.setdefault((e["code"], e["severity"]), {"code": e["code"], "severity": e["severity"], "n": 0, "examples": []})
        c["n"] += 1
        if len(c["examples"]) < 4:
            c["examples"].append(e["key"])
    order = {"error": 0, "warning": 1, "info": 2}
    return sorted(d.values(), key=lambda c: (order.get(c["severity"], 3), -c["n"]))
