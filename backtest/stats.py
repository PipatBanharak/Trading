"""Performance and validation statistics (formula ids refer to data/schema.yaml)."""

import math
import random
from statistics import NormalDist

_N = NormalDist()
EULER_GAMMA = 0.5772156649


def moments(x):
    n = len(x)
    m = sum(x) / n
    var = sum((v - m) ** 2 for v in x) / (n - 1)
    sd = math.sqrt(var)
    if sd == 0:
        return m, 0.0, 0.0, 3.0
    skew = sum(((v - m) / sd) ** 3 for v in x) / n
    kurt = sum(((v - m) / sd) ** 4 for v in x) / n
    return m, sd, skew, kurt


def equity_curve(rets):
    eq, out = 1.0, []
    for r in rets:
        eq *= 1.0 + r
        out.append(eq)
    return out


def max_drawdown(rets):
    peak, mdd, eq = 1.0, 0.0, 1.0
    for r in rets:
        eq *= 1.0 + r
        peak = max(peak, eq)
        mdd = max(mdd, 1.0 - eq / peak)
    return mdd


def psr(sr_period, n, skew, kurt, sr_star_period=0.0):
    """F07 Probabilistic Sharpe Ratio (per-period SR, n observations)."""
    den = 1.0 - skew * sr_period + (kurt - 1.0) / 4.0 * sr_period ** 2
    if den <= 0 or n < 3:
        return float("nan")
    return _N.cdf((sr_period - sr_star_period) * math.sqrt(n - 1) / math.sqrt(den))


def min_trl_years(sr_period, skew, kurt, ppy, sr_star_period=0.0, alpha=0.05):
    """F10 Minimum track record length, in years."""
    if sr_period <= sr_star_period:
        return float("inf")
    z = _N.inv_cdf(1 - alpha)
    obs = 1 + (1 - skew * sr_period + (kurt - 1) / 4 * sr_period ** 2) * (z / (sr_period - sr_star_period)) ** 2
    return obs / ppy


def expected_max_sr(n_trials):
    """F08 expected maximum of n standard normal draws (multiply by sd of SR estimates)."""
    if n_trials <= 1:
        return 0.0
    return (1 - EULER_GAMMA) * _N.inv_cdf(1 - 1 / n_trials) + EULER_GAMMA * _N.inv_cdf(1 - 1 / (n_trials * math.e))


def dsr(sr_period, n, skew, kurt, n_trials, sr_period_sd):
    """F09 Deflated Sharpe: PSR against the expected max SR of n_trials null strategies."""
    return psr(sr_period, n, skew, kurt, sr_star_period=sr_period_sd * expected_max_sr(n_trials))


def summary(rets, ppy, dates=None):
    n = len(rets)
    m, sd, skew, kurt = moments(rets)
    years = n / ppy
    eq = equity_curve(rets)
    sr_p = m / sd if sd else 0.0
    out = {
        "n": n,
        "years": round(years, 2),
        "start": dates[0] if dates else None,
        "end": dates[-1] if dates else None,
        "cagr": eq[-1] ** (1 / years) - 1 if years > 0 and eq[-1] > 0 else float("nan"),
        "ann_mean": m * ppy,
        "ann_vol": sd * math.sqrt(ppy),
        "sharpe": sr_p * math.sqrt(ppy),
        "skew": skew,
        "kurtosis": kurt,
        "max_drawdown": max_drawdown(rets),
        "pct_positive_periods": sum(1 for r in rets if r > 0) / n,
        "t_stat": sr_p * math.sqrt(n),
        "psr_0": psr(sr_p, n, skew, kurt),
        "min_trl_years": min_trl_years(sr_p, skew, kurt, ppy),
        "total_return": eq[-1] - 1,
    }
    return out


def calendar_returns(dates, rets, key_len):
    """Compound returns by date prefix (key_len=4 -> years, 7 -> months)."""
    out = {}
    for d, r in zip(dates, rets):
        k = d[:key_len]
        out[k] = out.get(k, 1.0) * (1.0 + r)
    return {k: v - 1.0 for k, v in out.items()}


def stationary_bootstrap(rets, horizon, n_paths, mean_block, seed=7):
    """F27 Politis-Romano stationary bootstrap; returns list of (total_return, mdd) per path."""
    rng = random.Random(seed)
    n = len(rets)
    p_new = 1.0 / mean_block
    paths = []
    for _ in range(n_paths):
        i = rng.randrange(n)
        eq, peak, mdd = 1.0, 1.0, 0.0
        for _ in range(horizon):
            if rng.random() < p_new:
                i = rng.randrange(n)
            else:
                i = (i + 1) % n
            eq *= 1.0 + rets[i]
            peak = max(peak, eq)
            mdd = max(mdd, 1.0 - eq / peak)
        paths.append((eq - 1.0, mdd))
    return paths


def bootstrap_summary(paths):
    tot = sorted(p[0] for p in paths)
    mdd = sorted(p[1] for p in paths)
    q = lambda a, x: a[int(x * (len(a) - 1))]
    n = len(paths)
    return {
        "p_positive": sum(1 for t in tot if t > 0) / n,
        "p_positive_and_mdd_lt_25": sum(1 for t, d in paths if t > 0 and d < 0.25) / n,
        "total_return_p5": q(tot, 0.05), "total_return_p50": q(tot, 0.5), "total_return_p95": q(tot, 0.95),
        "mdd_p50": q(mdd, 0.5), "mdd_p90": q(mdd, 0.9), "mdd_p95": q(mdd, 0.95), "mdd_p99": q(mdd, 0.99),
        "p_mdd_gt_15": sum(1 for d in mdd if d > 0.15) / n,
        "p_mdd_gt_20": sum(1 for d in mdd if d > 0.20) / n,
    }
