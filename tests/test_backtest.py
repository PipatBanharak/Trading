"""Unit tests: run with  python3 -m unittest discover -s tests  (from repo root)."""

import math
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backtest import engine, fetch, stats  # noqa: E402


def gbm(n, mu_ann, vol_ann, ppy=365, seed=1):
    rng = random.Random(seed)
    p, out = 100.0, [100.0]
    for _ in range(n - 1):
        p *= math.exp((mu_ann - 0.5 * vol_ann ** 2) / ppy + vol_ann / math.sqrt(ppy) * rng.gauss(0, 1))
        out.append(p)
    return out


def params(**kw):
    base = dict(lookbacks=(14, 28, 56, 112), periods_per_year=365, sleeve_vol=0.054, cap_u=0.15,
                vol_halflife=20, cost_per_side=0.0)
    base.update(kw)
    return engine.SleeveParams(**base)


DATES = [f"d{i:05d}" for i in range(1500)]


class EngineTests(unittest.TestCase):
    def test_no_lookahead(self):
        prices = gbm(1500, 0.0, 0.5)
        a = engine.run_sleeve(DATES, prices, params())
        shocked = prices[:1000] + [p * 3.0 for p in prices[1000:]]
        b = engine.run_sleeve(DATES, shocked, params())
        k = a.dates.index(DATES[1000])  # position held over bar 999 -> 1000
        self.assertEqual(a.positions[: k + 1], b.positions[: k + 1])

    def test_strong_uptrend_is_long_and_profitable(self):
        prices = [100 * math.exp(0.002 * i + 0.01 * math.sin(i)) for i in range(1500)]
        r = engine.run_sleeve(DATES, prices, params())
        self.assertGreater(sum(1 for p in r.positions if p > 0), 0.9 * len(r.positions))
        self.assertGreater(stats.equity_curve(r.returns)[-1], 1.0)

    def test_costs_equal_turnover_times_rate(self):
        prices = gbm(1500, 0.0, 0.5, seed=3)
        free = engine.run_sleeve(DATES, prices, params())
        paid = engine.run_sleeve(DATES, prices, params(cost_per_side=0.001))
        self.assertEqual(free.positions, paid.positions)
        diff = sum(f - p for f, p in zip(free.returns, paid.returns))
        self.assertAlmostEqual(diff, paid.turnover * 0.001, places=10)

    def test_long_pays_funding_short_receives(self):
        up = [100 * (1.001 ** i) for i in range(400)]
        r = engine.run_sleeve(DATES[:400], up, params(funding_long=0.10))
        self.assertTrue(all(f <= 0 for f, p in zip(r.funding, r.positions) if p > 0))
        down = [100 * (0.999 ** i) for i in range(400)]
        r2 = engine.run_sleeve(DATES[:400], down, params(funding_short=0.10))
        self.assertTrue(all(f >= 0 for f, p in zip(r2.funding, r2.positions) if p < 0))

    def test_long_only_never_short(self):
        r = engine.run_sleeve(DATES, gbm(1500, -0.3, 0.6, seed=5), params(long_only=True))
        self.assertTrue(all(p >= 0 for p in r.positions))

    def test_cap_respected(self):
        r = engine.run_sleeve(DATES, gbm(1500, 0.0, 0.05, seed=9), params(cap_u=0.15))
        self.assertTrue(all(abs(p) <= 0.15 + 1e-12 for p in r.positions))

    def test_lag_delays_positions(self):
        prices = gbm(1500, 0.0, 0.5, seed=11)
        r0 = engine.run_sleeve(DATES, prices, params(lag=0))
        r1 = engine.run_sleeve(DATES, prices, params(lag=1))
        self.assertEqual(r0.positions[:-1], r1.positions[1:])


class StatsTests(unittest.TestCase):
    def test_mdd(self):
        self.assertAlmostEqual(stats.max_drawdown([0.1, -0.5, 0.2]), 0.5)

    def test_psr_half_at_zero(self):
        self.assertAlmostEqual(stats.psr(0.0, 100, 0.0, 3.0), 0.5)

    def test_expected_max_sr_table(self):
        self.assertAlmostEqual(stats.expected_max_sr(45), 2.236, places=2)  # data/scenarios.yaml T3


class FetchSafetyTests(unittest.TestCase):
    def test_rejects_non_allowlisted_urls(self):
        for u in ["http://raw.githubusercontent.com/coinmetrics/data/master/csv/btc.csv",
                  "https://evil.example.com/coinmetrics/data/btc.csv",
                  "https://raw.githubusercontent.com/someone/else/btc.csv"]:
            with self.assertRaises(fetch.UnsafeData):
                fetch.check_url(u)

    def test_rejects_binary_and_html(self):
        for raw in [b"MZ\x90\x00binary", b"\x7fELF...", b"PK\x03\x04zip", b"<!DOCTYPE html><html>",
                    b"date,close\n2020-01-01,1\x00\n"]:
            with self.assertRaises(fetch.UnsafeData):
                fetch.check_bytes(raw)

    def test_rejects_formula_injection_and_text(self):
        bad = ["time,PriceUSD\n2020-01-01,=cmd|' /C calc'!A0\n",
               "time,PriceUSD\n2020-01-01,@SUM(1+1)\n",
               "time,PriceUSD\n2020-01-01,+1\n",
               "time,PriceUSD\n2020-01-01,hello\n",
               "time,PriceUSD\n=HYPERLINK(1),5\n"]
        for text in bad:
            with self.assertRaises(fetch.UnsafeData):
                fetch.parse_strict(text, "time", {"PriceUSD": "close"})

    def test_rejects_unsorted_and_nonpositive(self):
        with self.assertRaises(fetch.UnsafeData):
            fetch.parse_strict("time,PriceUSD\n2020-01-02,1\n2020-01-01,2\n", "time", {"PriceUSD": "close"})
        with self.assertRaises(fetch.UnsafeData):
            fetch.parse_strict("time,PriceUSD\n2020-01-01,-5\n", "time", {"PriceUSD": "close"})

    def test_accepts_clean_csv(self):
        rows, _, names = fetch.parse_strict("time,PriceUSD,X\n2020-01-01,1.5,\n2020-01-02,2e3,7\n",
                                            "time", {"PriceUSD": "close"})
        self.assertEqual(rows, [("2020-01-01", {"close": 1.5}), ("2020-01-02", {"close": 2000.0})])


if __name__ == "__main__":
    unittest.main()
