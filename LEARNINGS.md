# Learnings

Rule for this file: **every claim needs evidence you can re-check.** That can be a command, a file, a commit, or a number. "Claude Code is powerful" teaches nothing. "Asking Claude to audit my data found a one-day lag I had missed for 4 months" is a lesson.

All numbers below come from `python3 scripts/review.py`. Re-run it and don't trust copied figures.

---

## 1. Paper-trading experiment, 7 May – 23 Sep 2026 (81 snapshots)

### What happened

| | Start | End | Change |
|---|---|---|---|
| Account equity | 100,413.88 | 97,024.24 | **−3.38%** |
| SPY (price only) | 731.53 | 767.93 | **+4.98%** |

- **Lost 8.35 points to buy-and-hold SPY** over about 4.5 months. Max drawdown was −5.45% (trough on 5 Aug).
- 235 fills across 90 symbols on 47 of the days with snapshots. Most traded: TSLA, NVDA, SPY, CDNS, LRCX.
- **Exits:** 25 stop-loss sells, but only **1** limit (take-profit) sell. The profit targets almost never fired. Positions either got stopped out or were closed at market.
- Activity stopped. There were 8 fills after 1 Aug, and the account has been fully flat (no positions, no orders) since 16 Sep. The daily sync still commits snapshots of an idle account.

### What that means

- Trading 90 names did not beat just holding the index. Any new strategy has to beat SPY after costs, or it isn't worth running.
- With 25 stop exits and 1 target exit, either the targets are too far away or the stops are too tight. That is the first thing to check in the strategy code.
- The strategy code is **not in this repo**, so none of this can be traced to a specific rule. Until it is, this repo shows results but can't explain them.

### Pipeline bugs the data exposes

1. **`portfolio_history.review_date_close_equity` is off by one day.** In 39 of 45 checkable cases it is closer to the *previous* day's equity than to the review day's. It is also `null` in 21 of 81 snapshots, mostly Mondays and the day after a gap. Don't use it. `account.equity` (captured at about 16:30 ET, after the close) is the usable number.
2. **19 trading days have no snapshot** (listed by the script). The job misses roughly 1 day in 5, so any daily-return statistic built on this data has holes.
3. **The job runs on market holidays** (25 May, 19 Jun, 3 Jul, 7 Sep) and writes files with a `null` SPY close.
4. **Date bug:** the `2026-07-24` file was generated at 01:22 UTC, which is still 23 Jul in New York. The review date was taken from UTC, not exchange time.
5. **Bad equity reading on 7 Jul:** 96,686 → **47,368** → 95,758. It was captured while orders were being replaced (4 positions, 12 open orders). The script excludes it. A raw chart would show a fake 51% crash.

### Fixes, in priority order

- [ ] Commit the strategy and sync code to this repo, so results and logic sit next to each other.
- [ ] Use the exchange calendar (e.g. Alpaca's `/v2/calendar`) to decide whether to run and which date to stamp. Stamp dates in `America/New_York`, not UTC.
- [ ] Drop `review_date_close_equity` or fix its window. Add a check that fails when equity moves more than 20% in a day.
- [ ] Add alerting or a retry for missed runs (19 are missing right now).
- [ ] Decide whether the bot is retired. If it is, stop the daily sync. If it isn't, find out why it stopped trading in August.

---

## 2. Claude Code: my own lessons

*Empty on purpose. Only you know these. Use one block per lesson and delete lessons that don't meet the bar.*

```
### <one-line lesson>
- Context: what I was trying to do
- What I expected vs. what happened
- Evidence: commit / file / command / screenshot
- What I'll do differently
```
