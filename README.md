# ClaudeCode-knowledge
I am new to Claude Code and I am discovering its features. I wanted to try GitHub repo to see what it can do and how it can improve Claude Code. If you have anything that could be cool to add feel free to do so

## What's here

| Path | What it is |
|---|---|
| `data/daily/*.json` | End-of-day snapshots of an Alpaca paper-trading account (equity, fills, positions, open orders, SPY close), committed by a daily sync job |
| `scripts/review.py` | Performance summary + data-quality audit of those snapshots (stdlib only) |
| `LEARNINGS.md` | What the experiment and the tooling taught me, each point backed by evidence |

```sh
python3 scripts/review.py
```
