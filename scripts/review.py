#!/usr/bin/env python3
"""Summarise the daily paper-trading snapshots in data/daily and audit their quality.

Usage: python3 scripts/review.py [data_dir]

Standard library only. Every number in LEARNINGS.md comes from this script,
so re-run it instead of trusting hand-copied figures.
"""
import glob
import json
import os
import sys
from collections import Counter
from datetime import date, datetime, timedelta, timezone

# NYSE full-day closures inside the range this repo covers. Extend when the data does.
NYSE_HOLIDAYS_2026 = {
    date(2026, 5, 25),  # Memorial Day
    date(2026, 6, 19),  # Juneteenth
    date(2026, 7, 3),   # Independence Day (observed)
    date(2026, 9, 7),   # Labor Day
}
# One-day equity moves bigger than this are treated as bad readings, not performance.
MAX_PLAUSIBLE_DAILY_MOVE = 0.20


def load(data_dir):
    snaps = []
    for path in sorted(glob.glob(os.path.join(data_dir, "*.json"))):
        with open(path) as f:
            snaps.append(json.load(f))
    return snaps


def trading_days(start, end):
    d = start
    while d <= end:
        if d.weekday() < 5 and d not in NYSE_HOLIDAYS_2026:
            yield d
        d += timedelta(days=1)


def eastern_date(ts):
    # Fixed offset is enough here: every snapshot falls inside US daylight time (UTC-4).
    return (datetime.fromisoformat(ts) - timedelta(hours=4)).date()


def audit(snaps):
    issues = []
    by_date = {date.fromisoformat(s["review_date"]): s for s in snaps}
    dates = sorted(by_date)

    for d in dates:
        s = by_date[d]
        if d in NYSE_HOLIDAYS_2026 or d.weekday() >= 5:
            issues.append((d, "snapshot written for a day the market was closed"))
        gen = eastern_date(s["generated_at"])
        if gen != d:
            issues.append((d, f"generated at {s['generated_at']} = {gen} US/Eastern, not the review date"))
        if s["spy"]["review_date_close"] is None and d not in NYSE_HOLIDAYS_2026:
            issues.append((d, "SPY close missing on a trading day"))

    missing = [d for d in trading_days(dates[0], dates[-1]) if d not in by_date]

    # Is portfolio_history.review_date_close_equity closer to today's post-close equity or
    # to yesterday's? Closer to yesterday's means the field is mislabelled (off by one day).
    # Only consecutive trading days count, so a gap in the data can't fake a match.
    lag_hits = lag_checks = 0
    for prev, cur in zip(dates, dates[1:]):
        v = by_date[cur]["portfolio_history"]["review_date_close_equity"]
        today, yesterday = by_date[cur]["account"]["equity"], by_date[prev]["account"]["equity"]
        if v is None or next(trading_days(prev + timedelta(days=1), cur), None) != cur or today == yesterday:
            continue
        lag_checks += 1
        if abs(v - yesterday) < abs(v - today):
            lag_hits += 1
    null_close = sum(1 for s in snaps if s["portfolio_history"]["review_date_close_equity"] is None)

    bad_equity = []
    for prev, cur in zip(dates, dates[1:]):
        a, b = by_date[prev]["account"]["equity"], by_date[cur]["account"]["equity"]
        nxt = dates.index(cur) + 1
        c = by_date[dates[nxt]]["account"]["equity"] if nxt < len(dates) else b
        if abs(b / a - 1) > MAX_PLAUSIBLE_DAILY_MOVE and abs(c / a - 1) < MAX_PLAUSIBLE_DAILY_MOVE:
            bad_equity.append((cur, a, b, c))

    return issues, missing, (lag_hits, lag_checks, null_close), bad_equity


def performance(snaps, bad_dates):
    rows = [
        (date.fromisoformat(s["review_date"]), s["account"]["equity"], s["spy"]["review_date_close"])
        for s in snaps
        if date.fromisoformat(s["review_date"]) not in bad_dates
    ]
    eq = [r for r in rows if r[1] is not None]
    spy = [r for r in rows if r[2] is not None]
    peak, max_dd, dd_at = eq[0][1], 0.0, eq[0][0]
    for d, e, _ in eq:
        peak = max(peak, e)
        if e / peak - 1 < max_dd:
            max_dd, dd_at = e / peak - 1, d
    return {
        "first": eq[0][:2],
        "last": eq[-1][:2],
        "ret": eq[-1][1] / eq[0][1] - 1,
        "spy_first": (spy[0][0], spy[0][2]),
        "spy_last": (spy[-1][0], spy[-1][2]),
        "spy_ret": spy[-1][2] / spy[0][2] - 1,
        "max_dd": max_dd,
        "max_dd_at": dd_at,
    }


def activity(snaps):
    fills = [f for s in snaps for f in s["fills"]]
    last_fill_day = max((s["review_date"] for s in snaps if s["fills"]), default=None)
    first_flat = next(
        (s["review_date"] for s in snaps if not s["open_positions"] and not s["open_orders"]), None
    )
    return {
        "fills": len(fills),
        "days_with_fills": sum(1 for s in snaps if s["fills"]),
        "symbols": len({f["symbol"] for f in fills}),
        "by_side_type": Counter((f["side"], f["order_type"]) for f in fills),
        "top_symbols": Counter(f["symbol"] for f in fills).most_common(5),
        "last_fill_day": last_fill_day,
        "first_flat_day": first_flat,
        "fills_after_jul": sum(len(s["fills"]) for s in snaps if s["review_date"] >= "2026-08-01"),
    }


def main():
    data_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "data", "daily")
    snaps = load(data_dir)
    issues, missing, (lag_hits, lag_checks, null_close), bad_equity = audit(snaps)
    perf = performance(snaps, {b[0] for b in bad_equity})
    act = activity(snaps)

    print(f"Snapshots: {len(snaps)}  ({snaps[0]['review_date']} -> {snaps[-1]['review_date']})")
    print("\n== Performance (account.equity, bad readings excluded) ==")
    print(f"Equity  {perf['first'][0]} {perf['first'][1]:>12,.2f} -> {perf['last'][0]} {perf['last'][1]:>12,.2f}  {perf['ret']:+.2%}")
    print(f"SPY     {perf['spy_first'][0]} {perf['spy_first'][1]:>12,.2f} -> {perf['spy_last'][0]} {perf['spy_last'][1]:>12,.2f}  {perf['spy_ret']:+.2%}")
    print(f"Gap vs SPY: {perf['ret'] - perf['spy_ret']:+.2%} (percentage points, price return only)")
    print(f"Max drawdown: {perf['max_dd']:.2%} (trough {perf['max_dd_at']})")

    print("\n== Activity (only days that have a snapshot) ==")
    print(f"Fills: {act['fills']} on {act['days_with_fills']} days, {act['symbols']} symbols")
    for (side, typ), n in sorted(act["by_side_type"].items()):
        print(f"  {side:<4} {typ:<7} {n}")
    print(f"Most traded: {', '.join(f'{s} ({n})' for s, n in act['top_symbols'])}")
    print(f"Fills since 2026-08-01: {act['fills_after_jul']}; last fill {act['last_fill_day']}; flat from {act['first_flat_day']}")

    print("\n== Data quality ==")
    print(f"Trading days with no snapshot: {len(missing)}")
    print("  " + ", ".join(d.isoformat() for d in missing))
    print(f"portfolio_history.review_date_close_equity: null in {null_close}/{len(snaps)} snapshots; "
          f"closer to the PREVIOUS day's equity than the review day's in {lag_hits}/{lag_checks} checkable cases")
    for d, a, b, c in bad_equity:
        print(f"Implausible equity reading {d}: {a:,.2f} -> {b:,.2f} -> {c:,.2f} (excluded above)")
    for d, msg in issues:
        print(f"{d}: {msg}")


if __name__ == "__main__":
    main()
