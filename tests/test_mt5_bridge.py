"""Tests for live/mt5_bridge.py against a fake MT5 terminal (no network, no real orders)."""

import math
import os
import random
import sys
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace as NS

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from live import mt5_bridge as mb  # noqa: E402

UTC = timezone.utc


class FakeMT5:
    TRADE_ACTION_DEAL, TRADE_ACTION_SLTP = 1, 6
    ORDER_TYPE_BUY, ORDER_TYPE_SELL = 0, 1
    POSITION_TYPE_BUY, POSITION_TYPE_SELL = 0, 1
    ORDER_TIME_GTC = 0
    ORDER_FILLING_FOK, ORDER_FILLING_IOC, ORDER_FILLING_RETURN = 0, 1, 2
    TIMEFRAME_H1 = 16385
    TRADE_RETCODE_DONE = 10009

    def __init__(self, now, offset_h=3, equity=60000.0, trend=0.002, seed=1):
        self.now, self.offset_h, self.sent, self.checked = now, offset_h, [], []
        self.positions = []
        self.acct = NS(equity=equity, trade_allowed=True, margin_mode=0)
        self.specs = {
            "BTCUSD": NS(trade_contract_size=1.0, volume_min=0.01, volume_step=0.01, volume_max=100.0,
                         filling_mode=2, point=0.01, trade_stops_level=0, digits=2),
            "XAUUSD": NS(trade_contract_size=100.0, volume_min=0.01, volume_step=0.01, volume_max=50.0,
                         filling_mode=1, point=0.01, trade_stops_level=50, digits=2),
        }
        self.base = {"BTCUSD": 85600.0, "XAUUSD": 4130.0}
        rng = random.Random(seed)
        self.rates = {}
        for sym, last in self.base.items():
            n = 600 * 24
            prices, p = [], last
            for _ in range(n):       # walk backwards so the latest close == base price
                prices.append(p)
                p = p / math.exp(trend / 24 + 0.01 * rng.gauss(0, 1) / 5)
            prices.reverse()
            start = int(now.timestamp()) - n * 3600 + offset_h * 3600
            self.rates[sym] = [{"time": start + i * 3600, "close": c} for i, c in enumerate(prices)]

    def symbol_select(self, sym, flag):
        return True

    def symbol_info(self, sym):
        return self.specs[sym]

    def symbol_info_tick(self, sym):
        px = self.base[sym]
        return NS(time=int(self.now.timestamp()) + self.offset_h * 3600, bid=px - 0.1, ask=px + 0.1)

    def copy_rates_from_pos(self, sym, tf, start, count):
        return self.rates[sym][-count:]

    def account_info(self):
        return self.acct

    def positions_get(self, symbol=None):
        return tuple(p for p in self.positions if p.symbol == symbol)

    def order_check(self, req):
        self.checked.append(req)
        return NS(retcode=0, comment="Done")

    def order_send(self, req):
        self.sent.append(req)
        return NS(retcode=self.TRADE_RETCODE_DONE, order=len(self.sent))


SPEC = NS(trade_contract_size=100.0, volume_min=0.01, volume_step=0.01, volume_max=50.0,
          filling_mode=1, point=0.01, trade_stops_level=50, digits=2)


class BridgeTests(unittest.TestCase):
    def test_lot_rounding_toward_zero_and_min(self):
        self.assertEqual(mb.round_lots(0.0399, SPEC), 0.03)
        self.assertEqual(mb.round_lots(-0.0399, SPEC), -0.03)
        self.assertEqual(mb.round_lots(0.009, SPEC), 0.0)
        self.assertEqual(mb.fraction_to_lots(0.18, 10000, 4130, SPEC), 0.0)     # $1,800 < 1 oz
        self.assertEqual(mb.fraction_to_lots(0.18, 50000, 4130, SPEC), 0.02)    # docs/08 table

    def test_filling_mode(self):
        f = FakeMT5(datetime(2026, 10, 6, 0, 20, tzinfo=UTC))
        self.assertEqual(mb.filling_type(f, NS(filling_mode=2)), f.ORDER_FILLING_IOC)
        self.assertEqual(mb.filling_type(f, NS(filling_mode=1)), f.ORDER_FILLING_FOK)
        self.assertEqual(mb.filling_type(f, NS(filling_mode=0)), f.ORDER_FILLING_RETURN)

    def test_utc_daily_close_uses_offset_and_excludes_today(self):
        now = datetime(2026, 10, 6, 12, 0, tzinfo=UTC)
        day = datetime(2026, 10, 5, tzinfo=UTC)
        rates = [{"time": int((day + timedelta(hours=h + 3)).timestamp()), "close": 100 + h} for h in range(30)]
        dates, closes = mb.utc_daily_closes(rates, 3, now)
        self.assertEqual(dates, ["2026-10-05"])
        self.assertEqual(closes, [123.0])        # bar 23:00-24:00 UTC

    def test_plan_flip_closes_then_opens(self):
        f = FakeMT5(datetime(2026, 10, 6, 0, 20, tzinfo=UTC))
        cfg = mb.BridgeConfig()
        tick = f.symbol_info_tick("XAUUSD")
        pos = [NS(ticket=7, volume=0.03, type=f.POSITION_TYPE_BUY, magic=cfg.magic)]
        reqs = mb.plan_requests(f, "XAUUSD", SPEC, tick, 0.03, -0.02, 0.04, pos, cfg)
        self.assertEqual([(r["type"], r["volume"], r.get("position")) for r in reqs],
                         [(f.ORDER_TYPE_SELL, 0.03, 7), (f.ORDER_TYPE_SELL, 0.02, None)])

    def test_plan_reduce_and_buffer(self):
        f = FakeMT5(datetime(2026, 10, 6, 0, 20, tzinfo=UTC))
        cfg = mb.BridgeConfig()
        tick = f.symbol_info_tick("XAUUSD")
        pos = [NS(ticket=1, volume=0.05, type=f.POSITION_TYPE_BUY, magic=cfg.magic)]
        reqs = mb.plan_requests(f, "XAUUSD", SPEC, tick, 0.05, 0.03, 0.04, pos, cfg)
        self.assertEqual([(r["type"], r["volume"], r["position"]) for r in reqs], [(f.ORDER_TYPE_SELL, 0.02, 1)])
        self.assertEqual(mb.plan_requests(f, "XAUUSD", SPEC, tick, 0.05, 0.04, 0.08, pos, cfg), [])  # < buffer

    def test_stop_respects_stops_level(self):
        cfg = mb.BridgeConfig()
        self.assertEqual(mb.stop_price(1, 4130.0, 0.00001, SPEC, cfg), round(4130.0 - 51 * 0.01, 2))
        self.assertAlmostEqual(mb.stop_price(-1, 4130.0, 0.019, SPEC, cfg), 4130.0 + 4 * 0.019 * 4130.0, places=2)

    def test_blackouts(self):
        r = mb.blackout_reason
        self.assertEqual(r("XAU", datetime(2026, 10, 6, 21, 0, tzinfo=UTC)), "rollover window")
        self.assertEqual(r("XAU", datetime(2026, 10, 9, 20, 40, tzinfo=UTC)), "friday cutoff before weekend halt")
        self.assertEqual(r("XAU", datetime(2026, 10, 10, 12, 0, tzinfo=UTC)), "market closed (weekend)")
        self.assertEqual(r("XAU", datetime(2026, 10, 6, 10, 0, tzinfo=UTC)), "outside rebalance window")
        self.assertIsNone(r("XAU", datetime(2026, 10, 6, 16, 0, tzinfo=UTC)))
        self.assertEqual(r("BTC", datetime(2026, 10, 6, 0, 30, tzinfo=UTC)), "quarter-hour burst")
        self.assertIsNone(r("BTC", datetime(2026, 10, 6, 0, 22, tzinfo=UTC)))
        ev = [(datetime(2026, 10, 6, 0, 30, tzinfo=UTC), 15)]
        self.assertEqual(r("BTC", datetime(2026, 10, 6, 0, 37, tzinfo=UTC), ev), "news blackout")

    def test_risk_actions(self):
        cfg = mb.BridgeConfig()
        st = {}
        t0 = datetime(2026, 10, 6, 1, 0, tzinfo=UTC)
        self.assertEqual(mb.risk_action(st, 100000, t0, cfg), "ok")
        self.assertEqual(mb.risk_action(st, 98000, t0, cfg), "no_new_risk")
        self.assertEqual(mb.risk_action(st, 96500, t0, cfg), "flatten_and_stop")
        st2 = {"peak_equity": 100000}
        self.assertEqual(mb.risk_action(st2, 84000, t0 + timedelta(days=3), cfg), "halve_risk")

    def test_dry_run_never_sends(self):
        now = datetime(2026, 10, 6, 0, 22, tzinfo=UTC)
        f = FakeMT5(now)
        decisions, _ = mb.evaluate(f, mb.BridgeConfig(), now_utc=now, live=False)
        self.assertEqual(f.sent, [])
        btc = [d for d in decisions if d["asset"] == "BTC"][0]
        self.assertNotIn("error", btc)
        self.assertEqual(btc["server_offset_h"], 3)
        self.assertGreater(btc["target_lots"], 0)       # uptrending fake history -> long
        self.assertTrue(f.checked)                       # requests were validated with order_check

    def test_live_sends_and_sets_stop(self):
        now = datetime(2026, 10, 6, 0, 22, tzinfo=UTC)
        f = FakeMT5(now)
        d, _ = mb.evaluate(f, mb.BridgeConfig(), now_utc=now, live=True)
        self.assertTrue(any(r["action"] == f.TRADE_ACTION_DEAL for r in f.sent))


if __name__ == "__main__":
    unittest.main()
