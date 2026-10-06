"""Download price data from an allowlist and verify it before use.

Security model (downloads are untrusted until they pass every check):
  1. Only HTTPS URLs on an explicit host + path-prefix allowlist.
  2. Streamed download with a hard byte cap and timeout; Content-Type must be text.
  3. Reject binary/executable/archive/HTML content (magic bytes, NUL bytes, tags).
  4. Strict CSV schema: every cell must be empty, a number, or a date in the date
     column. This also rejects spreadsheet formula injection (=, +, @ ...).
  5. Dates strictly increasing; prices positive; extreme moves are counted.
  6. Plausibility cross-check against independently known reference prices.
  7. The raw file is never executed or imported. Only the parsed numbers are
     re-serialised into a clean CSV, and a SHA-256 manifest is written.

Usage:  python3 -I backtest/fetch.py --out <empty-or-new-dir>   (run from outside the data dir)
"""

import argparse
import csv
import hashlib
import io
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone

ALLOWED_HOSTS = {"raw.githubusercontent.com"}
ALLOWED_PATH_PREFIXES = ("/coinmetrics/data/", "/datasets/gold-prices/")
MAX_BYTES = 40 * 1024 * 1024
TIMEOUT_S = 60

# Each source: url, date column, wanted price columns -> output names, reference checks.
SOURCES = {
    "btc_coinmetrics": {
        "url": "https://raw.githubusercontent.com/coinmetrics/data/master/csv/btc.csv",
        "date_col": "time",
        "columns": {"PriceUSD": "close"},
        "license": "CC BY-NC 4.0 (Coin Metrics, Inc.)",
        # Independently known closes (well-documented market events).
        "reference": [("2017-12-15", "2017-12-18", "close", 19000.0, 0.12),   # Dec-2017 peak
                      ("2020-03-12", "2020-03-13", "close", 5000.0, 0.20),    # Covid crash
                      ("2021-11-08", "2021-11-10", "close", 66000.0, 0.10),   # Nov-2021 ATH
                      ("2024-03-13", "2024-03-14", "close", 72000.0, 0.10),   # Mar-2024 ATH
                      ("2025-10-05", "2025-10-06", "close", 123000.0, 0.10)], # Oct-2025 ATH
    },
    "eth_coinmetrics": {
        "url": "https://raw.githubusercontent.com/coinmetrics/data/master/csv/eth.csv",
        "date_col": "time",
        "columns": {"PriceUSD": "close"},
        "license": "CC BY-NC 4.0 (Coin Metrics, Inc.)",
        "reference": [("2018-01-12", "2018-01-14", "close", 1350.0, 0.15),
                      ("2021-11-08", "2021-11-09", "close", 4700.0, 0.10),
                      ("2022-06-17", "2022-06-18", "close", 1050.0, 0.20)],
    },
    "gold_worldbank_monthly": {
        "url": "https://raw.githubusercontent.com/datasets/gold-prices/main/data/monthly.csv",
        "date_col": "Date",
        "columns": {"Price": "avg_price"},
        "license": "PDDL (World Bank Pink Sheet monthly averages)",
        # Known monthly averages + spot ~$4,130 on 2026-10-05 (kitco / 150currency).
        "reference": [("1980-01", "1980-01", "avg_price", 675.0, 0.10),
                      ("2011-09", "2011-09", "avg_price", 1772.0, 0.10),
                      ("2020-08", "2020-08", "avg_price", 1968.0, 0.10),
                      ("2026-08", "2026-10", "avg_price", 4130.0, 0.25)],
    },
}

BAD_MAGIC = (b"MZ", b"\x7fELF", b"PK\x03\x04", b"%PDF", b"\xca\xfe\xba\xbe", b"#!", b"\x1f\x8b", b"Rar!", b"7z\xbc\xaf")
HTML_MARKERS = (b"<script", b"<html", b"<!doctype", b"<iframe", b"<?php")
NUM_RE = re.compile(r"^-?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?$")
DATE_RE = re.compile(r"^\d{4}-\d{2}(-\d{2})?$")


class UnsafeData(Exception):
    pass


def check_url(url):
    p = urllib.parse.urlparse(url)
    if p.scheme != "https" or p.hostname not in ALLOWED_HOSTS or not p.path.startswith(ALLOWED_PATH_PREFIXES):
        raise UnsafeData(f"URL not on allowlist: {url}")


def download(url):
    check_url(url)
    req = urllib.request.Request(url, headers={"User-Agent": "trading-backtest/0.1"})
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
        final = resp.geturl()
        check_url(final)  # refuse redirects off the allowlist
        ctype = resp.headers.get("Content-Type", "")
        if not ctype.startswith("text/plain"):
            raise UnsafeData(f"unexpected Content-Type {ctype!r}")
        chunks, total = [], 0
        while True:
            chunk = resp.read(1 << 16)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_BYTES:
                raise UnsafeData("file exceeds size cap")
            chunks.append(chunk)
    return b"".join(chunks), ctype


def check_bytes(raw):
    """Content-level checks that do not depend on the CSV layout."""
    if not raw:
        raise UnsafeData("empty file")
    if raw.startswith(BAD_MAGIC):
        raise UnsafeData("binary/executable/archive signature")
    if b"\x00" in raw:
        raise UnsafeData("NUL byte found (binary content)")
    low = raw[:4096].lower()
    if any(m in low for m in HTML_MARKERS):
        raise UnsafeData("HTML/script content instead of CSV")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise UnsafeData(f"not UTF-8 text: {e}")
    return text


def parse_strict(text, date_col, columns, optional_columns=False):
    """Every cell must be empty / numeric / (date in date_col). Returns rows of floats."""
    reader = csv.reader(io.StringIO(text))
    header = next(reader)
    if date_col not in header:
        raise UnsafeData(f"missing date column {date_col!r}")
    wanted = {c: n for c, n in columns.items() if c in header}
    if not optional_columns and len(wanted) != len(columns):
        raise UnsafeData(f"missing columns: {set(columns) - set(wanted)}")
    if not wanted:
        raise UnsafeData("none of the wanted columns present")
    di = header.index(date_col)
    idx = {header.index(c): n for c, n in wanted.items()}
    rows, prev, n_cells = [], None, 0
    for line_no, row in enumerate(reader, start=2):
        if not row:
            continue
        if len(row) != len(header):
            raise UnsafeData(f"line {line_no}: {len(row)} cells, header has {len(header)}")
        for j, cell in enumerate(row):
            n_cells += 1
            cell = cell.strip()
            if j == di:
                if not DATE_RE.match(cell):
                    raise UnsafeData(f"line {line_no}: bad date {cell[:20]!r}")
            elif cell and not NUM_RE.match(cell):
                raise UnsafeData(f"line {line_no} col {header[j]!r}: non-numeric cell {cell[:20]!r}")
        d = row[di].strip()
        if prev is not None and d <= prev:
            raise UnsafeData(f"line {line_no}: dates not strictly increasing ({prev} -> {d})")
        prev = d
        vals = {}
        for j, name in idx.items():
            cell = row[j].strip()
            if cell:
                v = float(cell)
                if v <= 0:
                    raise UnsafeData(f"line {line_no}: non-positive price {v}")
                vals[name] = v
        if vals:
            rows.append((d, vals))
    return rows, n_cells, sorted(wanted.values())


def sanity(rows, names):
    out = {}
    for name in names:
        series = [(d, v[name]) for d, v in rows if name in v]
        big = sum(1 for (_, a), (_, b) in zip(series, series[1:]) if abs(b / a - 1) > 0.5)
        out[name] = {"n": len(series), "first": series[0][0] if series else None,
                     "last": series[-1][0] if series else None, "moves_gt_50pct": big}
    return out


def reference_check(rows, refs):
    results = []
    for start, end, name, expected, tol in refs:
        vals = [v[name] for d, v in rows if start <= d <= end and name in v]
        if not vals:
            results.append({"window": [start, end], "status": "no data in window"})
            continue
        dev = vals[-1] / expected - 1
        ok = abs(dev) <= tol
        results.append({"window": [start, end], "last_value": vals[-1], "expected": expected,
                        "deviation": round(dev, 4), "status": "ok" if ok else "FAIL"})
        if not ok:
            raise UnsafeData(f"reference check failed for {name}: {vals[-1]} vs {expected}")
    return results


def write_clean(path, rows, names):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date"] + names)
        for d, v in rows:
            w.writerow([d] + [repr(v[n]) if n in v else "" for n in names])


def fetch_all(out_dir, only=None):
    raw_dir = os.path.join(out_dir, "raw")
    clean_dir = os.path.join(out_dir, "clean")
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(clean_dir, exist_ok=True)
    manifest = {"fetched_at": datetime.now(timezone.utc).isoformat(), "sources": {}}
    for key, src in SOURCES.items():
        if only and key not in only:
            continue
        entry = {"url": src["url"], "license": src["license"], "checks": []}
        try:
            raw, ctype = download(src["url"])
            entry.update(bytes=len(raw), content_type=ctype, sha256=hashlib.sha256(raw).hexdigest())
            entry["checks"].append("allowlisted https url + size cap + text content-type")
            text = check_bytes(raw)
            entry["checks"].append("no binary/executable/archive/HTML signatures, UTF-8 text")
            rows, n_cells, names = parse_strict(text, src["date_col"], src["columns"], src.get("optional_columns", False))
            entry["checks"].append(f"strict CSV schema: {n_cells} cells numeric/date only (no formulas)")
            entry["series"] = sanity(rows, names)
            entry["reference_checks"] = reference_check(rows, src["reference"])
            entry["checks"].append("dates strictly increasing, prices > 0, reference prices plausible")
            raw_path = os.path.join(raw_dir, key + ".csv.untrusted")
            with open(raw_path, "wb") as f:
                f.write(raw)
            os.chmod(raw_path, 0o444)
            clean_path = os.path.join(clean_dir, key + ".csv")
            write_clean(clean_path, rows, names)
            with open(clean_path, "rb") as f:
                entry["clean_sha256"] = hashlib.sha256(f.read()).hexdigest()
            entry["status"] = "accepted"
        except (UnsafeData, OSError, ValueError, StopIteration) as e:
            entry["status"] = "rejected"
            entry["reason"] = str(e)
        manifest["sources"][key] = entry
        print(f"{key}: {entry['status']}" + (f" ({entry.get('reason')})" if entry["status"] != "accepted" else ""))
    with open(os.path.join(out_dir, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    return manifest


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True, help="output directory (outside the repo)")
    ap.add_argument("--only", nargs="*", help="subset of source keys")
    a = ap.parse_args(argv)
    m = fetch_all(a.out, a.only)
    return 0 if all(s["status"] == "accepted" for s in m["sources"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
