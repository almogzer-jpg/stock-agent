"""backtesting/ — sanity-check the signals on history.

MVP backtester: for every past day the breakout setup fired, measure the
N-day forward return, then report hit-rate and average return. Intentionally
simple (no position sizing, stops, or costs) — a starting point to extend.
"""
