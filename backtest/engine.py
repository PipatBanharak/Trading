"""Rulebook S1: vol-targeted multi-horizon time-series momentum sleeve.

Timing convention (no look-ahead):
    position decided with prices up to bar t is held over the return of bar
    t+1+lag. lag=0 means "trade right after the close" (BTC rebalances 20 min
    after the 00:00 UTC close); lag=1 skips one bar, required for monthly
    *average* prices whose consecutive returns are mechanically autocorrelated.

All positions are notional as a fraction of sleeve equity (e.g. 0.12 = 12%).
"""

import math
from dataclasses import dataclass, field


@dataclass
class SleeveParams:
    lookbacks: tuple                 # in bars
    periods_per_year: float
    sleeve_vol: float                # annualised vol target of the sleeve at |s| = 1
    cap_u: float                     # max notional / equity at |s| = 1 (stress cap)
    vol_halflife: float              # EWMA half-life in bars
    vol_clip: tuple = (0.5, 2.0)     # clip sigma-hat vs rolling 1y median
    buffer_u: float = 0.25           # trade only if |target - pos| >= buffer * U
    cost_per_side: float = 0.0       # fraction of traded notional
    lag: int = 0
    stop_sigma: float = 0.0          # close-based protective stop in daily sigmas (0 = off)
    long_only: bool = False          # spot venue: negative signal -> flat
    funding_long: float = 0.0        # annual carry paid on long notional (perps funding / swap)
    funding_short: float = 0.0       # annual carry *received* on short notional
    warmup: int = 0                  # bars before trading starts (defaults to max lookback)


@dataclass
class SleeveResult:
    dates: list
    returns: list                    # net sleeve return per bar (aligned with dates)
    positions: list                  # position held during each bar
    gross: list = field(default_factory=list)
    cost: list = field(default_factory=list)
    funding: list = field(default_factory=list)
    turnover: float = 0.0            # sum |delta position| (equity units)
    turnover_u: float = 0.0          # sum |delta position| / U
    stops: int = 0


def simple_returns(prices):
    return [prices[i] / prices[i - 1] - 1.0 for i in range(1, len(prices))]


def _rolling_median(values, window):
    out = []
    for i in range(len(values)):
        w = sorted(v for v in values[max(0, i - window + 1): i + 1] if v is not None)
        out.append(w[len(w) // 2] if w else None)
    return out


def ewma_vol(rets, halflife, periods_per_year, seed_n=20):
    """Annualised EWMA vol known at the end of each bar (index aligned to rets)."""
    lam = 0.5 ** (1.0 / halflife)
    out, var = [], None
    for i, r in enumerate(rets):
        if var is None:
            if i + 1 < seed_n:
                out.append(None)
                continue
            seed = rets[i + 1 - seed_n: i + 1]
            var = sum(x * x for x in seed) / len(seed)
        else:
            var = lam * var + (1 - lam) * r * r
        out.append(math.sqrt(var * periods_per_year))
    return out


def signal_at(prices, t, lookbacks):
    """Mean of sign(price_t / price_{t-L} - 1) over lookbacks, using prices[0..t] only."""
    s = 0.0
    for L in lookbacks:
        r = prices[t] / prices[t - L] - 1.0
        s += 1.0 if r > 0 else (-1.0 if r < 0 else 0.0)
    return s / len(lookbacks)


def run_sleeve(dates, prices, p: SleeveParams):
    n = len(prices)
    rets = simple_returns(prices)                 # rets[i] = return from bar i to i+1
    vol = ewma_vol(rets, p.vol_halflife, p.periods_per_year)   # known at end of bar i+1
    med = _rolling_median(vol, int(round(p.periods_per_year)))
    warm = max(p.warmup, max(p.lookbacks), 21)
    daily_sigma_scale = 1.0 / math.sqrt(p.periods_per_year)

    pos = 0.0
    res = SleeveResult(dates=[], returns=[], positions=[])
    stopped_until = -1
    pending = []                                  # (apply_bar, target, U) queue for lag
    for t in range(warm, n - 1):
        # --- decide target with info up to bar t
        sig_hat = vol[t - 1]                      # vol known at end of bar t
        m = med[t - 1]
        if sig_hat is not None and m is not None:
            sig_hat = min(max(sig_hat, p.vol_clip[0] * m), p.vol_clip[1] * m)
        if sig_hat:
            U = min(p.sleeve_vol / sig_hat, p.cap_u)
            s = signal_at(prices, t, p.lookbacks)
            if p.long_only:
                s = max(s, 0.0)
            if t <= stopped_until:
                s = 0.0
            pending.append((t + p.lag, s * U, U))
        # --- apply decisions whose time has come (executed at close of bar t)
        while pending and pending[0][0] <= t:
            _, target, U = pending.pop(0)
            if abs(target - pos) >= p.buffer_u * U or (target == 0.0 and pos != 0.0):
                delta = abs(target - pos)
                res.turnover += delta
                res.turnover_u += delta / U if U else 0.0
                trade_cost = delta * p.cost_per_side
                pos = target
            else:
                trade_cost = 0.0
            res.cost.append(trade_cost)
            break
        else:
            res.cost.append(0.0)
        # --- hold pos over bar t -> t+1
        r = rets[t]
        gross = pos * r
        dt = 1.0 / p.periods_per_year
        fund = -(p.funding_long * pos * dt) if pos > 0 else (p.funding_short * (-pos) * dt if pos < 0 else 0.0)
        net = gross + fund - res.cost[-1]
        # close-based protective stop: an adverse bar beyond k daily sigmas flattens for one bar
        if p.stop_sigma and sig_hat and pos != 0.0:
            bar_sigma = sig_hat * daily_sigma_scale
            if (pos > 0 and r < -p.stop_sigma * bar_sigma) or (pos < 0 and r > p.stop_sigma * bar_sigma):
                res.stops += 1
                stopped_until = t + 1
        res.dates.append(dates[t + 1])
        res.returns.append(net)
        res.positions.append(pos)
        res.gross.append(gross)
        res.funding.append(fund)
    return res


def combine(results, weights=None):
    """Sum sleeve returns on common dates (sleeves share one equity)."""
    weights = weights or [1.0] * len(results)
    common = set(results[0].dates)
    for r in results[1:]:
        common &= set(r.dates)
    maps = [dict(zip(r.dates, r.returns)) for r in results]
    dates = sorted(common)
    return dates, [sum(w * m[d] for w, m in zip(weights, maps)) for d in dates]


def to_monthly(dates, rets):
    """Compound per-bar returns into calendar months keyed 'YYYY-MM'."""
    out_d, out_r, cur, acc = [], [], None, 1.0
    for d, r in zip(dates, rets):
        k = d[:7]
        if cur is not None and k != cur:
            out_d.append(cur)
            out_r.append(acc - 1.0)
            acc = 1.0
        cur = k
        acc *= 1.0 + r
    if cur is not None:
        out_d.append(cur)
        out_r.append(acc - 1.0)
    return out_d, out_r
