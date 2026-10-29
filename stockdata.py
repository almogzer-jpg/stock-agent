# -*- coding: utf-8 -*-
"""Canonical per-stock data — one row and one verdict per ticker, app-wide.

The daily pipeline writes two overlapping artifacts:
  results.csv   watchlist, full model (fundamentals, sector, news, risk)
  universe.json 500-stock scan; top-N "opportunities" are enriched with
                fundamentals, the rest are technical-only
Pages used to read whichever was closest, so one ticker could carry two
different scores. Here a ticker resolves to exactly one row, by precedence:
results.csv > enriched universe row > technical-only universe row.
"""
import json
import os

import pandas as pd

import config
import verdict as V


def _read_json(path, default):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return default


def _clean(d: dict) -> dict:
    return {k: v for k, v in d.items() if not (isinstance(v, float) and v != v)}


def load_rows(results_df: pd.DataFrame | None = None, universe: dict | None = None,
              events: dict | None = None) -> dict:
    """{ticker: row} with the precedence above, plus provenance + earnings days."""
    if results_df is None:
        inv = {v: k for k, v in config.COLUMN_LABELS_HE.items()}
        try:
            results_df = pd.read_csv(config.RESULTS_CSV, encoding="utf-8-sig").rename(columns=inv)
        except Exception:
            results_df = pd.DataFrame()
    universe = universe if universe is not None else _read_json(config.UNIVERSE_JSON, {})
    events = events if events is not None else _read_json(config.EVENTS_JSON, {})
    uni_date = None
    if isinstance(results_df, pd.DataFrame) and "Date" in results_df.columns and len(results_df):
        uni_date = str(results_df["Date"].iloc[0])

    rows = {}
    for r in universe.get("all", []) or []:
        if r.get("Ticker"):
            rows[r["Ticker"]] = {**_clean(r), "_tier": "technical", "Date": r.get("Date") or uni_date}
    for r in universe.get("opportunities", []) or []:
        if r.get("Ticker"):
            rows[r["Ticker"]] = {**rows.get(r["Ticker"], {}), **_clean(r), "_tier": "enriched",
                                 "Date": r.get("Date") or uni_date}
    if isinstance(results_df, pd.DataFrame):
        for r in results_df.to_dict("records"):
            t = r.get("Ticker")
            if t:
                rows[t] = {**rows.get(t, {}), **_clean(r), "_tier": "full"}
    for t, row in rows.items():
        ev = (events or {}).get(t) or {}
        if isinstance(ev.get("days_to_earnings"), (int, float)):
            row["DaysToEarnings"] = ev["days_to_earnings"]
            row["EarningsDate"] = ev.get("earnings_date")
    return rows


def verdicts(rows: dict) -> dict:
    """{ticker: verdict} for every canonical row."""
    return {t: V.verdict_for_row(r) for t, r in rows.items()}


def ranked(vmap: dict, rows: dict, action: str | None = None, tiers=("full", "enriched"),
           limit: int | None = None) -> list:
    """Verdicts filtered by action and data tier, best first (quality, then reliability)."""
    out = [v for t, v in vmap.items()
           if rows.get(t, {}).get("_tier") in tiers and (action is None or v["action"] == action)]
    out.sort(key=lambda v: (v["rank"], -(v["quality"] or 0), -v["reliability"]["score"]))
    return out[:limit] if limit else out
