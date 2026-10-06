"""Leverage and entry/exit study for S1 on BTC and ETH daily data (docs/09).

    python3 -m backtest.leverage_study --data <dir with clean/*.csv> --out results/leverage_study.json

Parts
  1. Kelly growth curve g(L) of the S1 signal at fixed notional leverage L.
  2. Fixed-leverage sweep (retail "leverage trading"): notional = L * s * equity,
     with costs, funding and liquidation (cross margin, close-to-close moves only,
     so real intraday liquidation risk is HIGHER than shown).
  3. Vol-target sweep: the rulebook sizing scaled up.
  4. Pre-registered entry/exit variants (pullback entry, trailing exit), counted as
     extra trials in the deflated Sharpe ratio.
"""

import argparse
import json
import math
import os

from . import engine, stats
from .run_s1 import (BTC_START, BTC_WARMUP_FROM, COST, ETH_START, ETH_WARMUP_FROM, FUNDING,
                     SLEEVE_VOL, _clean_json, load, window)

MMR = 0.004
LOOKBACKS = (14, 28, 56, 112)
PPY = 365


def unit_strategy(dates, prices, start, cost_side, f_long, f_short):
    """Per-day net return of notional = s_t * 1x equity (no vol targeting), and asset returns."""
    rets = engine.simple_returns(prices)
    out_d, unit, asset, sig = [], [], [], []
    prev = 0.0
    for t in range(max(LOOKBACKS), len(prices) - 1):
        s = engine.signal_at(prices, t, LOOKBACKS)
        cost = abs(s - prev) * cost_side
        fund = -(f_long * s / PPY) if s > 0 else (f_short * (-s) / PPY if s < 0 else 0.0)
        prev = s
        if dates[t + 1] >= start:
            out_d.append(dates[t + 1])
            unit.append(s * rets[t] + fund - cost)
            asset.append(rets[t])
            sig.append(s)
    return out_d, unit, asset, sig


def kelly_curve(unit, grid):
    out = {}
    for L in grid:
        acc, ruined = 0.0, False
        for u in unit:
            x = 1 + L * u
            if x <= 0:
                ruined = True
                break
            acc += math.log(x)
        out[L] = None if ruined else acc / len(unit) * PPY
    return out


def levered_path(unit, sig, asset, L):
    """Compound L x unit returns with cross-margin liquidation (equity <= MMR * notional)."""
    eq, peak, mdd = 1.0, 1.0, 0.0
    for i, (u, s, a) in enumerate(zip(unit, sig, asset)):
        notional = abs(L * s)
        eq_new = eq * (1 + L * u)
        if eq_new <= MMR * notional * eq:
            return {"liquidated_at_index": i, "final": 0.0, "mdd": 1.0, "cagr": -1.0}
        eq = eq_new
        peak = max(peak, eq)
        mdd = max(mdd, 1 - eq / peak)
    years = len(unit) / PPY
    return {"liquidated_at_index": None, "final": eq, "mdd": mdd, "cagr": eq ** (1 / years) - 1}


def bootstrap_levered(unit, L, h, n_paths=2000, horizon=3 * PPY, block=20, seed=11):
    """3-year stationary bootstrap of the levered unit strategy with the mean edge cut by h."""
    m = sum(unit) / len(unit)
    shifted = [u - h * m for u in unit]
    paths = stats.stationary_bootstrap([max(L * u, -0.999999) for u in shifted], horizon, n_paths, block, seed)
    n = len(paths)
    return {"p_positive": sum(1 for t, _ in paths if t > 0) / n,
            "p_mdd_gt_50": sum(1 for _, d in paths if d > 0.5) / n,
            "p_lose_90pct": sum(1 for t, _ in paths if t < -0.9) / n,
            "median_total_return": sorted(t for t, _ in paths)[n // 2]}


def s1_variant(dates, prices, start, entry="immediate", trail_k=None, sleeve_vol=SLEEVE_VOL, cap=0.15,
               cost_side=COST["btc_perp_maker_taker"], fl=FUNDING["base_trend_conditional"][0],
               fs=FUNDING["base_trend_conditional"][1], stop_sigma=4.0, buffer_u=0.25, max_wait=5,
               pullback_sigma=0.5):
    """S1 sleeve with optional pullback entry and trailing exit (same sizing as engine.run_sleeve)."""
    rets = engine.simple_returns(prices)
    vol = engine.ewma_vol(rets, 20, PPY)
    med = engine._rolling_median(vol, PPY)
    pos, stopped_until, wait, best, blocked_s = 0.0, -1, 0, None, None
    out_d, out_r = [], []
    for t in range(max(LOOKBACKS), len(prices) - 1):
        if vol[t - 1] is None or med[t - 1] is None:
            continue
        sig = min(max(vol[t - 1], 0.5 * med[t - 1]), 2.0 * med[t - 1])
        sd = sig / math.sqrt(PPY)
        U = min(sleeve_vol / sig, cap)
        s = engine.signal_at(prices, t, LOOKBACKS)
        if t <= stopped_until:
            s = 0.0
        if blocked_s is not None:
            if s == blocked_s:
                s = 0.0
            else:
                blocked_s = None
        # trailing exit: retrace of trail_k * 5-day sigma from the best close since entry
        if trail_k and pos != 0.0:
            best = prices[t] if best is None else (max(best, prices[t]) if pos > 0 else min(best, prices[t]))
            lim = trail_k * sd * math.sqrt(5)
            if (pos > 0 and prices[t] <= best * (1 - lim)) or (pos < 0 and prices[t] >= best * (1 + lim)):
                blocked_s, s = engine.signal_at(prices, t, LOOKBACKS), 0.0
        target = s * U
        if pos != 0.0 and target != 0.0 and (target > 0) != (pos > 0):
            target = 0.0                                   # flips go through flat first
        adding = abs(target) > abs(pos) + 1e-12
        if entry == "pullback" and adding:
            r_today = rets[t - 1]                           # return of the bar ending at t
            dip = (target > 0 and r_today <= -pullback_sigma * sd) or (target < 0 and r_today >= pullback_sigma * sd)
            if not dip and wait < max_wait:
                wait += 1
                target = pos
            else:
                wait = 0
        else:
            wait = 0
        cost = 0.0
        if abs(target - pos) >= buffer_u * U or (target == 0.0 and pos != 0.0):
            cost = abs(target - pos) * cost_side
            if pos == 0.0 or target == 0.0 or (target > 0) != (pos > 0):
                best = None
            pos = target
        r = rets[t]
        fund = -(fl * pos / PPY) if pos > 0 else (fs * (-pos) / PPY if pos < 0 else 0.0)
        if stop_sigma and pos != 0.0 and ((pos > 0 and r < -stop_sigma * sd) or (pos < 0 and r > stop_sigma * sd)):
            stopped_until = t + 1
        if dates[t + 1] >= start:
            out_d.append(dates[t + 1])
            out_r.append(pos * r + fund - cost)
    return out_d, out_r


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    clean = os.path.join(a.data, "clean")
    assets = {
        "BTC": (window(*load(os.path.join(clean, "btc_coinmetrics.csv"), "close"), BTC_WARMUP_FROM), BTC_START),
        "ETH": (window(*load(os.path.join(clean, "eth_coinmetrics.csv"), "close"), ETH_WARMUP_FROM), ETH_START),
    }
    fl, fs = FUNDING["base_trend_conditional"]
    R = {"assumptions": {"mmr": MMR, "cost_per_side": COST["btc_perp_maker_taker"], "funding": [fl, fs],
                         "note": "close-to-close data: intraday wicks would liquidate earlier than shown"}}
    for name, ((d, p), start) in assets.items():
        ud, unit, asset, sig = unit_strategy(d, p, start, COST["btc_perp_maker_taker"], fl, fs)
        A = R.setdefault(name, {})
        m, sd, sk, ku = stats.moments(unit)
        A["unit_1x"] = {"ann_return": m * PPY, "ann_vol": sd * math.sqrt(PPY), "sharpe": m / sd * math.sqrt(PPY),
                        "worst_day": min(unit), "kelly_continuous": m / (sd * sd)}
        grid = [0.25, 0.5, 0.75, 1, 1.5, 2, 3, 4, 5, 7.5, 10, 20]
        A["kelly_growth_in_sample"] = kelly_curve(unit, grid)
        half = [u - 0.5 * m for u in unit]
        A["kelly_growth_edge_halved"] = kelly_curve(half, grid)
        A["kelly_continuous_edge_halved"] = (0.5 * m) / (sd * sd)
        A["fixed_leverage"] = {}
        for L in (0.5, 1, 2, 3, 5, 10, 20):
            path = levered_path(unit, sig, asset, L)
            if path["liquidated_at_index"] is not None:
                path["liquidated_on"] = ud[path["liquidated_at_index"]]
            path["bootstrap_3y_edge_halved"] = bootstrap_levered(unit, L, 0.5)
            path["bootstrap_3y_no_edge"] = bootstrap_levered(unit, L, 1.0)
            A["fixed_leverage"][str(L)] = path
        A["vol_target_sweep"] = {}
        for tv in (0.04, 0.08, 0.15, 0.25, 0.40, 0.60):
            r = engine.run_sleeve(d, p, engine.SleeveParams(
                lookbacks=LOOKBACKS, periods_per_year=PPY, sleeve_vol=tv, cap_u=50.0, vol_halflife=20,
                cost_per_side=COST["btc_perp_maker_taker"], stop_sigma=4.0, funding_long=fl, funding_short=fs))
            k = next(i for i, x in enumerate(r.dates) if x >= start)
            rr, pos = r.returns[k:], r.positions[k:]
            sm = stats.summary(rr, PPY, r.dates[k:])
            sm["avg_abs_notional"] = sum(abs(x) for x in pos) / len(pos)
            sm["max_abs_notional"] = max(abs(x) for x in pos)
            sm["ruined"] = any(x <= -0.99 for x in rr)
            mean_rr = sum(rr) / len(rr)
            for h, key in ((0.5, "bootstrap_3y_edge_halved"), (1.0, "bootstrap_3y_no_edge")):
                paths = stats.stationary_bootstrap([x - h * mean_rr for x in rr], 3 * PPY, 2000, 20, seed=5)
                b = stats.bootstrap_summary(paths)
                b["cagr_p50"] = (1 + b["total_return_p50"]) ** (1 / 3) - 1
                b["p_mdd_gt_30"] = sum(1 for _, dd in paths if dd > 0.30) / len(paths)
                sm[key] = b
            A["vol_target_sweep"][str(tv)] = sm
        A["entry_exit_variants"] = {}
        for vname, kw in (("baseline", {}), ("pullback_entry", {"entry": "pullback"}),
                          ("trailing_exit_3sigma5d", {"trail_k": 3.0}),
                          ("pullback_plus_trailing", {"entry": "pullback", "trail_k": 3.0})):
            vd, vr = s1_variant(d, p, start, **kw)
            A["entry_exit_variants"][vname] = stats.summary(vr, PPY, vd)
        # DSR for the best variant, counting all S1 configurations tried on this asset so far
        n_trials = 4 + 3                    # docs/06 (4) + three new entry/exit variants
        best_name, best = max(A["entry_exit_variants"].items(), key=lambda kv: kv[1]["sharpe"])
        srp = best["sharpe"] / math.sqrt(PPY)
        A["entry_exit_best"] = {"name": best_name, "n_trials_total": n_trials,
                                "dsr": stats.dsr(srp, best["n"], best["skew"], best["kurtosis"], n_trials,
                                                 1 / math.sqrt(best["n"]))}
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w") as f:
        json.dump(_clean_json(R), f, indent=1)
    return R


if __name__ == "__main__":
    main()
