"""MetaTrader 5 execution bridge for rulebook S1 (BTCUSD + XAUUSD CFDs).

Design (docs/08_mt5_connection.md):
  * Signals reuse backtest.engine so live sizing matches the backtest exactly.
  * Talks to a running MT5 terminal through the official `MetaTrader5` Python
    package (Windows, or Linux via Wine + mt5linux). The module object is
    injected, so the logic is testable with a fake terminal.
  * DRY-RUN BY DEFAULT: requests are built and validated with order_check()
    but only sent when live mode is explicitly enabled (see main()).
  * Protective stops are stored server-side as position SL, so they survive
    a crash of this process.
  * Credentials come only from environment variables, never from the repo.

Run one evaluation (dry-run):
    python3 -m live.mt5_bridge --once
"""

import argparse
import json
import math
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from backtest import engine

UTC = timezone.utc


@dataclass
class AssetRule:
    broker_symbol: str
    lookbacks: tuple            # bars of UTC-daily closes
    periods_per_year: int
    cap_u: float                # max notional/equity at full signal (rulebook caps)
    weekend_closed: bool = False


@dataclass
class BridgeConfig:
    assets: dict = field(default_factory=lambda: {
        "BTC": AssetRule("BTCUSD", (14, 28, 56, 112), 365, 0.15),
        # gold trades ~5 days/week: 14/28/56/112 calendar days ~ 10/20/40/80 daily bars
        "XAU": AssetRule("XAUUSD", (10, 20, 40, 80), 252, 0.20, weekend_closed=True),
    })
    portfolio_vol: float = 0.04          # incubation level (rulebook global_risk)
    rho: float = 0.1
    vol_halflife_days: float = 20
    vol_clip: tuple = (0.5, 2.0)
    buffer_u: float = 0.25
    stop_sigma: float = 4.0
    magic: int = 20261006
    deviation_points: int = 50
    server_utc_offset_hours: int = None  # None -> detect from the last tick
    history_days: int = 500
    daily_loss_soft: float = 0.015
    daily_loss_hard: float = 0.03
    dd_ladder: tuple = ((0.10, "review"), (0.15, "halve_risk"), (0.20, "flatten_and_stop"))
    log_path: str = "logs/mt5_decisions.jsonl"
    state_path: str = "logs/mt5_state.json"

    @property
    def sleeve_vol(self):
        n = len(self.assets)
        return self.portfolio_vol / math.sqrt(n * (1 + (n - 1) * self.rho))   # F35


# --------------------------------------------------------------------------- time & data
def detect_server_offset_hours(mt5, symbol, now_utc):
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        raise RuntimeError(f"no tick for {symbol}")
    return round((tick.time - now_utc.timestamp()) / 3600.0)


def utc_daily_closes(rates, offset_hours, now_utc):
    """H1 bars stamped in broker server time -> closes of completed UTC days.

    The close of UTC day D is the close of the last H1 bar that ends at or
    before D+1 00:00 UTC (the 00:00 UTC close used in the backtest).
    """
    today = now_utc.date()
    by_day = {}
    for r in rates:
        start_utc = datetime.fromtimestamp(int(r["time"]) - offset_hours * 3600, UTC)
        day = (start_utc + timedelta(hours=1) - timedelta(microseconds=1)).date()
        if day < today:
            by_day[day] = float(r["close"])   # later bars of the same day overwrite earlier ones
    days = sorted(by_day)
    return [d.isoformat() for d in days], [by_day[d] for d in days]


# --------------------------------------------------------------------------- sizing
def target_from_closes(closes, rule: AssetRule, cfg: BridgeConfig):
    """Signal, vol and target notional fraction using the backtest engine's functions."""
    if len(closes) < max(rule.lookbacks) + 30:
        raise ValueError("not enough history")
    rets = engine.simple_returns(closes)
    vol = engine.ewma_vol(rets, cfg.vol_halflife_days, rule.periods_per_year)
    med = engine._rolling_median(vol, rule.periods_per_year)
    sigma = min(max(vol[-1], cfg.vol_clip[0] * med[-1]), cfg.vol_clip[1] * med[-1])
    u = min(cfg.sleeve_vol / sigma, rule.cap_u)
    s = engine.signal_at(closes, len(closes) - 1, rule.lookbacks)
    return {"signal": s, "sigma_annual": sigma, "sigma_daily": sigma / math.sqrt(rule.periods_per_year),
            "u": u, "target_fraction": s * u}


def round_lots(lots, info):
    """Round toward zero to volume_step; below volume_min -> 0 (never round up risk)."""
    step = info.volume_step
    sign = 1 if lots >= 0 else -1
    q = math.floor(abs(lots) / step + 1e-9) * step
    if q < info.volume_min - 1e-12:
        return 0.0
    return sign * round(min(q, info.volume_max), 8)


def fraction_to_lots(fraction, equity, price, info):
    return round_lots(fraction * equity / (info.trade_contract_size * price), info)


# --------------------------------------------------------------------------- orders
def filling_type(mt5, info):
    mode = int(info.filling_mode)
    if mode & 2:               # SYMBOL_FILLING_IOC
        return mt5.ORDER_FILLING_IOC
    if mode & 1:               # SYMBOL_FILLING_FOK
        return mt5.ORDER_FILLING_FOK
    return mt5.ORDER_FILLING_RETURN


def net_position(mt5, symbol, magic):
    """Signed lots and the list of our positions (works in netting and hedging accounts)."""
    pos = [p for p in (mt5.positions_get(symbol=symbol) or ()) if p.magic == magic]
    net = sum(p.volume if p.type == mt5.POSITION_TYPE_BUY else -p.volume for p in pos)
    return round(net, 8), pos


def deal_request(mt5, symbol, info, tick, side, volume, cfg, position=None, comment="S1"):
    req = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": float(volume),
        "type": mt5.ORDER_TYPE_BUY if side > 0 else mt5.ORDER_TYPE_SELL,
        "price": tick.ask if side > 0 else tick.bid,
        "deviation": cfg.deviation_points,
        "magic": cfg.magic,
        "comment": comment,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": filling_type(mt5, info),
    }
    if position is not None:
        req["position"] = position
    return req


def plan_requests(mt5, symbol, info, tick, current, target, u_lots, positions, cfg):
    """Close/reduce existing tickets first, then open the remainder (no accidental hedges)."""
    if target == current:
        return []
    if not (target == 0.0 or abs(target - current) >= cfg.buffer_u * u_lots - 1e-12):
        return []
    reqs = []
    remaining_close = 0.0
    if current != 0 and (target == 0 or (target > 0) != (current > 0) or abs(target) < abs(current)):
        remaining_close = abs(current) if (target == 0 or (target > 0) != (current > 0)) else abs(current) - abs(target)
        for p in sorted(positions, key=lambda x: -x.volume):
            if remaining_close <= 1e-12:
                break
            vol = round(min(p.volume, remaining_close), 8)
            side = -1 if p.type == mt5.POSITION_TYPE_BUY else 1
            reqs.append(deal_request(mt5, symbol, info, tick, side, vol, cfg, position=p.ticket, comment="S1 reduce"))
            remaining_close = round(remaining_close - vol, 8)
    after_close = current
    if reqs:
        after_close = 0.0 if (target == 0 or (target > 0) != (current > 0)) else target
    open_vol = round(abs(target - after_close), 8)
    if open_vol > 0 and target != 0:
        reqs.append(deal_request(mt5, symbol, info, tick, 1 if target > after_close else -1, open_vol, cfg))
    return reqs


def stop_price(side, entry, sigma_daily, info, cfg):
    """Server-side SL at stop_sigma daily sigmas, never closer than the broker's stops level."""
    dist = max(cfg.stop_sigma * sigma_daily * entry, (info.trade_stops_level + 1) * info.point)
    sl = entry - dist if side > 0 else entry + dist
    return round(sl, info.digits)


def sltp_request(mt5, symbol, ticket, sl):
    return {"action": mt5.TRADE_ACTION_SLTP, "symbol": symbol, "position": ticket, "sl": sl, "tp": 0.0}


# --------------------------------------------------------------------------- schedule & risk
REBALANCE_WINDOWS = {"BTC": (0 * 60 + 16, 1 * 60), "XAU": (15 * 60 + 30, 16 * 60 + 30)}   # UTC minutes


def is_reducing(current, target):
    return current != 0 and (target == 0 or ((target > 0) == (current > 0) and abs(target) < abs(current)))


def blackout_reason(asset, now_utc, news_events=(), reducing=False):
    """Return a reason string if trading should wait now, else None (docs/05 §G)."""
    hm = now_utc.hour * 60 + now_utc.minute
    if asset == "XAU":
        if 20 * 60 + 45 <= hm <= 22 * 60 + 15:
            return "rollover window"
        if now_utc.weekday() == 4 and hm >= 20 * 60 + 30 and not reducing:
            return "friday cutoff before weekend halt"
        if now_utc.weekday() == 5 or (now_utc.weekday() == 6 and hm < 22 * 60 + 15):
            return "market closed (weekend)"
    lo, hi = REBALANCE_WINDOWS.get(asset, (0, 24 * 60))
    if not lo <= hm <= hi:
        return "outside rebalance window"
    if asset == "BTC" and min(now_utc.minute % 15, 15 - now_utc.minute % 15) <= 3:
        return "quarter-hour burst"
    for ev_time, minutes in news_events:
        if abs((now_utc - ev_time).total_seconds()) <= minutes * 60:
            return "news blackout"
    return None


def risk_action(state, equity, now_utc, cfg):
    """Update peak/day-start equity in `state`; return the strongest triggered action."""
    day = now_utc.date().isoformat()
    if state.get("day") != day:
        state["day"], state["day_start_equity"] = day, equity
    state["peak_equity"] = max(state.get("peak_equity", equity), equity)
    day_loss = 1 - equity / state["day_start_equity"]
    dd = 1 - equity / state["peak_equity"]
    action = "ok"
    for level, name in cfg.dd_ladder:
        if dd >= level:
            action = name
    if day_loss >= cfg.daily_loss_hard:
        action = "flatten_and_stop"
    elif day_loss >= cfg.daily_loss_soft and action == "ok":
        action = "no_new_risk"
    state.update(last_equity=equity, drawdown=dd, day_loss=day_loss, action=action)
    return action


# --------------------------------------------------------------------------- orchestration
def evaluate(mt5, cfg: BridgeConfig, now_utc=None, news_events=(), live=False, state=None):
    now_utc = now_utc or datetime.now(UTC)
    state = {} if state is None else state
    acct = mt5.account_info()
    action = risk_action(state, acct.equity, now_utc, cfg)
    scale = 0.5 if action == "halve_risk" else 1.0
    decisions = []
    for asset, rule in cfg.assets.items():
        sym = rule.broker_symbol
        d = {"time": now_utc.isoformat(), "asset": asset, "symbol": sym, "risk_action": action, "live": live}
        try:
            mt5.symbol_select(sym, True)
            info = mt5.symbol_info(sym)
            tick = mt5.symbol_info_tick(sym)
            offset = cfg.server_utc_offset_hours
            if offset is None:
                offset = detect_server_offset_hours(mt5, sym, now_utc)
            rates = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_H1, 0, cfg.history_days * 24)
            _, closes = utc_daily_closes(rates, offset, now_utc)
            t = target_from_closes(closes, rule, cfg)
            price = (tick.bid + tick.ask) / 2
            frac = 0.0 if action == "flatten_and_stop" else t["target_fraction"] * scale
            target = fraction_to_lots(frac, acct.equity, price, info)
            u_lots = t["u"] * acct.equity / (info.trade_contract_size * price)
            current, positions = net_position(mt5, sym, cfg.magic)
            hm = now_utc.hour * 60 + now_utc.minute
            friday_cutoff = asset == "XAU" and now_utc.weekday() == 4 and hm >= 20 * 60 + 30
            if (action == "no_new_risk" or friday_cutoff) and not is_reducing(current, target) and target != current:
                flip = current != 0 and target != 0 and (target > 0) != (current > 0)
                target = 0.0 if flip else current          # allow closing, never add risk
            reducing = is_reducing(current, target)
            reason = blackout_reason(asset, now_utc, news_events, reducing=reducing)
            d.update(t, server_offset_h=offset, price=price, equity=acct.equity,
                     current_lots=current, target_lots=target, u_lots=u_lots)
            if reason and action != "flatten_and_stop":
                d["skipped"] = reason
                decisions.append(d)
                continue
            reqs = plan_requests(mt5, sym, info, tick, current, target, u_lots, positions, cfg)
            d["requests"], d["results"] = reqs, []
            for req in reqs:
                chk = mt5.order_check(req)
                res = {"check_retcode": getattr(chk, "retcode", None), "check_comment": getattr(chk, "comment", "")}
                if live and res["check_retcode"] == 0:
                    sent = mt5.order_send(req)
                    res.update(send_retcode=getattr(sent, "retcode", None), order=getattr(sent, "order", None))
                    if res["send_retcode"] != mt5.TRADE_RETCODE_DONE:
                        d["results"].append(res)
                        break
                d["results"].append(res)
            if target != 0:
                _, positions = net_position(mt5, sym, cfg.magic)
                sl_reqs = [sltp_request(mt5, sym, p.ticket,
                                        stop_price(1 if p.type == mt5.POSITION_TYPE_BUY else -1,
                                                   p.price_open, t["sigma_daily"], info, cfg))
                           for p in positions if not p.sl]
                d["sl_requests"] = sl_reqs
                if live:
                    d["sl_results"] = [getattr(mt5.order_send(r), "retcode", None) for r in sl_reqs]
        except Exception as e:     # never let one asset break the loop; the error is logged
            d["error"] = f"{type(e).__name__}: {e}"
        decisions.append(d)
    return decisions, state


def connect(mt5):
    """Initialise the terminal with credentials from environment variables only."""
    kwargs = {}
    if os.environ.get("MT5_PATH"):
        kwargs["path"] = os.environ["MT5_PATH"]
    if os.environ.get("MT5_LOGIN"):
        kwargs.update(login=int(os.environ["MT5_LOGIN"]), password=os.environ["MT5_PASSWORD"],
                      server=os.environ["MT5_SERVER"])
    if not mt5.initialize(**kwargs):
        raise RuntimeError(f"initialize() failed: {mt5.last_error()}")
    term, acct = mt5.terminal_info(), mt5.account_info()
    if not (term and term.trade_allowed and acct and acct.trade_allowed):
        raise RuntimeError("algo trading is disabled in the terminal or for this account")
    return acct


def main(argv=None):
    ap = argparse.ArgumentParser(description="S1 MT5 bridge (dry-run unless --live)")
    ap.add_argument("--once", action="store_true", help="evaluate once and exit")
    ap.add_argument("--live", action="store_true", help="send orders (also needs MT5_ALLOW_LIVE=1)")
    ap.add_argument("--portfolio-vol", type=float, default=0.04)
    a = ap.parse_args(argv)
    live = a.live and os.environ.get("MT5_ALLOW_LIVE") == "1"
    if a.live and not live:
        print("refusing live mode: set MT5_ALLOW_LIVE=1 after the compliance check (docs/07 §0, docs/08 §0)")
        return 2
    import MetaTrader5 as mt5  # Windows-only package (or mt5linux on Linux)
    cfg = BridgeConfig(portfolio_vol=a.portfolio_vol)
    connect(mt5)
    try:
        state = json.load(open(cfg.state_path)) if os.path.exists(cfg.state_path) else {}
        decisions, state = evaluate(mt5, cfg, live=live, state=state)
        os.makedirs(os.path.dirname(cfg.log_path), exist_ok=True)
        with open(cfg.log_path, "a") as f:
            for d in decisions:
                f.write(json.dumps(d, default=str) + "\n")
        with open(cfg.state_path, "w") as f:
            json.dump(state, f)
        for d in decisions:
            print(json.dumps({k: d.get(k) for k in ("asset", "signal", "current_lots", "target_lots",
                                                     "skipped", "error", "risk_action")}, default=str))
    finally:
        mt5.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
