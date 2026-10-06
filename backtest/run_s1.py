"""Run the rulebook S1 study on validated data and write a results JSON.

Usage (from repo root):
    python3 -m backtest.run_s1 --data <dir with clean/*.csv> --out results/s1_results.json

All configuration below was fixed *before* looking at results (see docs/06).
Every signal configuration evaluated is recorded in TRIALS so the deflated
Sharpe ratio uses the true number of trials.
"""

import argparse
import csv
import json
import math
import os

from . import engine, stats

PORTFOLIO_VOL = 0.08
RHO_PLAN = 0.1
SLEEVE_VOL = PORTFOLIO_VOL / math.sqrt(2 * (1 + RHO_PLAN))      # F35 -> 0.0539

COST = {  # per side, fraction of notional (data/instruments.yaml)
    "btc_perp_maker_taker": 0.0004,
    "btc_spot_taker": 0.0011,
    "xau_ecn_cfd": 0.00003,
    "xauusdt_maker_taker": 0.00035,
}
FUNDING = {  # annual (paid by longs, received by shorts) — perps funding history is not reachable
    "base_trend_conditional": (0.16, 0.03),
    "constant_clamp": (0.1095, 0.1095),
    "stress": (0.25, 0.0),
}

BTC_START, ETH_START, GOLD_START = "2015-01-01", "2017-01-01", "1972-01"
BTC_WARMUP_FROM, ETH_WARMUP_FROM, GOLD_WARMUP_FROM = "2014-01-01", "2016-01-01", "1968-04"


def load(path, col):
    with open(path) as f:
        rows = [(r["date"], float(r[col])) for r in csv.DictReader(f) if r[col]]
    return [d for d, _ in rows], [p for _, p in rows]


def window(dates, prices, start):
    i = next(k for k, d in enumerate(dates) if d >= start)
    return dates[i:], prices[i:]


def crypto_params(**kw):
    base = dict(lookbacks=(14, 28, 56, 112), periods_per_year=365, sleeve_vol=SLEEVE_VOL, cap_u=0.15,
                vol_halflife=20, buffer_u=0.25, cost_per_side=COST["btc_perp_maker_taker"],
                stop_sigma=4.0, funding_long=FUNDING["base_trend_conditional"][0],
                funding_short=FUNDING["base_trend_conditional"][1])
    base.update(kw)
    return engine.SleeveParams(**base)


def gold_params(**kw):
    # Monthly adaptation fixed a priori: 28/56/112 days -> 1/2/4 months; EWMA half-life 6 months
    # (a 20-day half-life cannot be estimated from monthly bars); lag=1 removes the 0.25
    # autocorrelation that monthly *averages* induce (Working 1960).
    base = dict(lookbacks=(1, 2, 4), periods_per_year=12, sleeve_vol=SLEEVE_VOL, cap_u=0.20,
                vol_halflife=6, buffer_u=0.25, cost_per_side=COST["xau_ecn_cfd"], lag=1, stop_sigma=0.0)
    base.update(kw)
    return engine.SleeveParams(**base)


def from_start(res, start):
    k = next(i for i, d in enumerate(res.dates) if d >= start)
    return res.dates[k:], res.returns[k:], res.positions[k:], res


def sleeve_report(res, start, ppy, extra=None):
    d, r, pos, full = from_start(res, start)
    k0 = len(full.dates) - len(d)
    out = stats.summary(r, ppy, d)
    yrs = out["years"]
    out.update(
        turnover_equity_per_year=sum(abs(b - a) for a, b in zip(pos, pos[1:])) / yrs,
        cost_drag_per_year=sum(full.cost[k0:]) / yrs,
        funding_drag_per_year=-sum(full.funding[k0:]) / yrs,
        time_long=sum(1 for p in pos if p > 0) / len(pos),
        time_short=sum(1 for p in pos if p < 0) / len(pos),
        avg_abs_position=sum(abs(p) for p in pos) / len(pos),
        stops=full.stops,
        calendar_years=stats.calendar_returns(d, r, 4),
    )
    if extra:
        out.update(extra)
    return out


def rolling_sharpe(dates, rets, ppy, years):
    """Annualised Sharpe over a trailing window, sampled at each calendar year-end."""
    w = int(ppy * years)
    out = {}
    for i in range(w, len(rets) + 1):
        if i == len(rets) or dates[i][:4] != dates[i - 1][:4]:
            m, sd, _, _ = stats.moments(rets[i - w:i])
            out[dates[i - 1][:4]] = m / sd * math.sqrt(ppy) if sd else None
    return out


def buy_and_hold_scaled(dates, prices, p: engine.SleeveParams, start):
    """Always-long benchmark with the same vol targeting, caps and lag (no trading costs)."""
    rets = engine.simple_returns(prices)
    vol = engine.ewma_vol(rets, p.vol_halflife, p.periods_per_year)
    med = engine._rolling_median(vol, int(round(p.periods_per_year)))
    warm = max(max(p.lookbacks), 21)
    out_d, out_r = [], []
    for t in range(warm + p.lag, len(prices) - 1):
        k = t - p.lag                     # decision bar
        if vol[k - 1] is None or med[k - 1] is None:
            continue
        sig = min(max(vol[k - 1], p.vol_clip[0] * med[k - 1]), p.vol_clip[1] * med[k - 1])
        out_d.append(dates[t + 1])
        out_r.append(min(p.sleeve_vol / sig, p.cap_u) * rets[t])
    k = next(i for i, d in enumerate(out_d) if d >= start)
    return stats.summary(out_r[k:], p.periods_per_year, out_d[k:])


def _clean_json(x):
    if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
        return None
    if isinstance(x, dict):
        return {k: _clean_json(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_clean_json(v) for v in x]
    return x


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    clean = os.path.join(a.data, "clean")

    btc_d, btc_p = window(*load(os.path.join(clean, "btc_coinmetrics.csv"), "close"), BTC_WARMUP_FROM)
    eth_d, eth_p = window(*load(os.path.join(clean, "eth_coinmetrics.csv"), "close"), ETH_WARMUP_FROM)
    au_d, au_p = window(*load(os.path.join(clean, "gold_worldbank_monthly.csv"), "avg_price"), GOLD_WARMUP_FROM)

    trials = {"BTC": [], "GOLD": []}
    R = {"config": {"portfolio_vol": PORTFOLIO_VOL, "rho_plan": RHO_PLAN, "sleeve_vol": SLEEVE_VOL,
                    "cost": COST, "funding": FUNDING,
                    "starts": {"BTC": BTC_START, "ETH": ETH_START, "GOLD": GOLD_START},
                    "data_end": {"BTC": btc_d[-1], "ETH": eth_d[-1], "GOLD": au_d[-1]}}}

    # ---------------- BTC primary + venue/funding variants
    base = engine.run_sleeve(btc_d, btc_p, crypto_params())
    R["btc_primary"] = sleeve_report(base, BTC_START, 365)
    trials["BTC"].append(("primary 14/28/56/112 lag0", R["btc_primary"]))
    R["btc_variants"] = {}
    for name, (fl, fs) in FUNDING.items():
        r = engine.run_sleeve(btc_d, btc_p, crypto_params(funding_long=fl, funding_short=fs))
        R["btc_variants"]["perp_funding_" + name] = sleeve_report(r, BTC_START, 365)
    r = engine.run_sleeve(btc_d, btc_p, crypto_params(long_only=True, cost_per_side=COST["btc_spot_taker"],
                                                      funding_long=0.0, funding_short=0.0))
    R["btc_variants"]["spot_long_flat"] = sleeve_report(r, BTC_START, 365)
    for mult in (1.5, 2.0):
        r = engine.run_sleeve(btc_d, btc_p, crypto_params(cost_per_side=COST["btc_perp_maker_taker"] * mult))
        R["btc_variants"][f"cost_x{mult}"] = sleeve_report(r, BTC_START, 365)
    for name, lbs in (("lookbacks_x0.5", (7, 14, 28, 56)), ("lookbacks_x2", (28, 56, 112, 224))):
        r = engine.run_sleeve(btc_d, btc_p, crypto_params(lookbacks=lbs))
        R["btc_variants"][name] = sleeve_report(r, BTC_START, 365)
        trials["BTC"].append((name, R["btc_variants"][name]))
    r = engine.run_sleeve(btc_d, btc_p, crypto_params(lag=1))
    R["btc_variants"]["execution_lag_1d"] = sleeve_report(r, BTC_START, 365)
    trials["BTC"].append(("execution_lag_1d", R["btc_variants"]["execution_lag_1d"]))
    R["btc_buy_hold_vol_scaled"] = buy_and_hold_scaled(btc_d, btc_p, crypto_params(), BTC_START)
    R["btc_subperiods"] = {}
    d, rr, _, _ = from_start(base, BTC_START)
    for lo, hi in (("2015", "2017-12-31"), ("2018", "2020-12-31"), ("2021", "2023-12-31"), ("2024", "2026-12-31")):
        seg = [x for dd, x in zip(d, rr) if lo <= dd <= hi]
        R["btc_subperiods"][f"{lo}-{hi[:4]}"] = stats.summary(seg, 365)

    d19 = [(dd, x) for dd, x in zip(d, rr) if dd >= "2019-01-01"]
    R["btc_post_publication_2019_plus"] = stats.summary([x for _, x in d19], 365, [dd for dd, _ in d19])
    R["btc_rolling_2y_sharpe"] = rolling_sharpe(d, rr, 365, 2)

    # ---------------- ETH: cross-asset out-of-sample, identical parameters
    eth = engine.run_sleeve(eth_d, eth_p, crypto_params())
    R["eth_oos"] = sleeve_report(eth, ETH_START, 365)

    ed, er, _, _ = from_start(eth, ETH_START)
    R["eth_rolling_2y_sharpe"] = rolling_sharpe(ed, er, 365, 2)

    # ---------------- Gold monthly
    gold = engine.run_sleeve(au_d, au_p, gold_params())
    R["gold_primary"] = sleeve_report(gold, GOLD_START, 12)
    trials["GOLD"].append(("primary 1/2/4m lag1", R["gold_primary"]))
    R["gold_variants"] = {}
    r = engine.run_sleeve(au_d, au_p, gold_params(cost_per_side=COST["xauusdt_maker_taker"]))
    R["gold_variants"]["xauusdt_costs"] = sleeve_report(r, GOLD_START, 12)
    for name, lbs in (("lookbacks_x2", (2, 4, 8)), ("lookbacks_x1.5", (2, 3, 6))):
        r = engine.run_sleeve(au_d, au_p, gold_params(lookbacks=lbs))
        R["gold_variants"][name] = sleeve_report(r, GOLD_START, 12)
        trials["GOLD"].append((name, R["gold_variants"][name]))
    r = engine.run_sleeve(au_d, au_p, gold_params(lag=0))
    R["gold_variants"]["lag0_biased_by_averaging"] = sleeve_report(r, GOLD_START, 12)
    R["gold_buy_hold_vol_scaled"] = buy_and_hold_scaled(au_d, au_p, gold_params(), GOLD_START)
    R["gold_subperiods"] = {}
    d, rr, _, _ = from_start(gold, GOLD_START)
    for lo in ("1972", "1980", "1990", "2000", "2010", "2020"):
        hi = str(int(lo) + 9) if lo != "1972" else "1979"
        seg = [x for dd, x in zip(d, rr) if lo <= dd[:4] <= hi]
        R["gold_subperiods"][f"{lo}-{hi}"] = stats.summary(seg, 12)
    R["gold_rolling_10y_sharpe"] = rolling_sharpe(d, rr, 12, 10)
    R["gold_note"] = ("monthly World Bank averages: vol understated ~18% vs month-end prices, "
                      "so Sharpe is multiplied by sqrt(2/3)=0.816 in 'sharpe_adj'")
    for rep in [R["gold_primary"], *R["gold_variants"].values()]:
        rep["sharpe_adj"] = rep["sharpe"] * math.sqrt(2 / 3)

    # ---------------- Deflated Sharpe per asset (N = all signal configs evaluated)
    R["dsr"] = {}
    for asset, lst, ppy in (("BTC", trials["BTC"], 365), ("GOLD", trials["GOLD"], 12)):
        prim = lst[0][1]
        n = prim["n"]
        sr_p = prim["sharpe"] / math.sqrt(ppy)
        R["dsr"][asset] = {"n_trials": len(lst), "trials": [t[0] for t in lst],
                           "dsr": stats.dsr(sr_p, n, prim["skew"], prim["kurtosis"], len(lst), 1 / math.sqrt(n))}

    # ---------------- Portfolio BTC + gold (monthly), common window
    bm_d, bm_r = engine.to_monthly(*from_start(base, BTC_START)[:2])
    gd, gr, _, _ = from_start(gold, BTC_START[:7])
    gmap = dict(zip(gd, gr))
    pd_, pr, b_only, g_only = [], [], [], []
    for d_, r_ in zip(bm_d, bm_r):
        if d_ in gmap:
            pd_.append(d_)
            pr.append(r_ + gmap[d_])
            b_only.append(r_)
            g_only.append(gmap[d_])
    m_b, sd_b, _, _ = stats.moments(b_only)
    m_g, sd_g, _, _ = stats.moments(g_only)
    corr = sum((x - m_b) * (y - m_g) for x, y in zip(b_only, g_only)) / ((len(b_only) - 1) * sd_b * sd_g)
    R["portfolio"] = stats.summary(pr, 12, pd_)
    R["portfolio"]["sleeve_return_correlation"] = corr
    R["portfolio"]["calendar_years"] = stats.calendar_returns(pd_, pr, 4)
    eq, peak, hits = 1.0, 1.0, {0.10: 0, 0.15: 0, 0.20: 0}
    armed = dict.fromkeys(hits, True)
    for r_ in pr:
        eq *= 1 + r_
        peak = max(peak, eq)
        dd = 1 - eq / peak
        for lvl in hits:
            if dd >= lvl and armed[lvl]:
                hits[lvl] += 1
                armed[lvl] = False
            if dd == 0:
                armed[lvl] = True
    R["portfolio"]["dd_ladder_triggers"] = {str(k): v for k, v in hits.items()}
    R["portfolio_bootstrap_3y"] = stats.bootstrap_summary(stats.stationary_bootstrap(pr, 36, 5000, 6))
    # Haircut bootstraps: keep the realised volatility/fat tails but shrink the mean edge
    # (McLean-Pontiff decay 26-58%; 100% = no edge at all).
    mean_pr = sum(pr) / len(pr)
    R["portfolio_bootstrap_3y_haircut"] = {
        f"edge_cut_{int(h * 100)}pct": stats.bootstrap_summary(
            stats.stationary_bootstrap([x - h * mean_pr for x in pr], 36, 5000, 6))
        for h in (0.5, 1.0)}
    _, btc_r, _, _ = from_start(base, BTC_START)
    R["btc_bootstrap_3y"] = stats.bootstrap_summary(stats.stationary_bootstrap(btc_r, 3 * 365, 2000, 20))

    # ---------------- Binance-USDⓈ-M-only configuration (BTCUSDT + XAUUSDT perps)
    # XAUUSDT funding history is not reachable; Binance's default funding has an interest
    # component of 0.01%/8h (~10.95%/yr) paid by longs when the premium is ~0.
    R["binance_futures"] = {"gold_funding_assumptions": {}}
    gold_fund = {"symmetric_10.95": (0.1095, 0.1095), "long_pays_only_10.95": (0.1095, 0.0),
                 "symmetric_5": (0.05, 0.05)}
    bin_gold = {}
    for name, (fl, fs) in gold_fund.items():
        g = engine.run_sleeve(au_d, au_p, gold_params(cost_per_side=COST["xauusdt_maker_taker"],
                                                     funding_long=fl, funding_short=fs))
        bin_gold[name] = g
        rep = sleeve_report(g, GOLD_START, 12)
        rep["sharpe_adj"] = rep["sharpe"] * math.sqrt(2 / 3)
        R["binance_futures"]["gold_funding_assumptions"][name] = rep
    for name, g in bin_gold.items():
        gd2, gr2, _, _ = from_start(g, BTC_START[:7])
        gm = dict(zip(gd2, gr2))
        dd_, rr_ = [], []
        for d_, r_ in zip(bm_d, bm_r):
            if d_ in gm:
                dd_.append(d_)
                rr_.append(r_ + gm[d_])
        rep = stats.summary(rr_, 12, dd_)
        mean_ = sum(rr_) / len(rr_)
        rep["bootstrap_3y"] = {f"edge_cut_{int(h * 100)}pct": stats.bootstrap_summary(
            stats.stationary_bootstrap([x - h * mean_ for x in rr_], 36, 5000, 6)) for h in (0.0, 0.5, 1.0)}
        R["binance_futures"]["portfolio_gold_funding_" + name] = rep

    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w") as f:
        json.dump(_clean_json(R), f, indent=1)
    return R


if __name__ == "__main__":
    main()
