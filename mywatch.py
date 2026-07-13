# -*- coding: utf-8 -*-
"""Personal watchlist (V3) — the missing decision-loop closer.

Star a company at analysis time → we snapshot the thesis (price, score,
recommendation, support). Every visit answers: WHAT CHANGED since you saved it,
and what deserves attention — computed from real artifacts, no new data source.
Local JSON persistence (git-ignored), same pattern as rec_history. Never raises.
"""
import json
import os
from datetime import datetime

import config

WATCHLIST_PATH = os.path.join(config.DATA_DIR, "my_watchlist.json")
ATTENTION_SCORE_DELTA = 8          # |ΔScore V2| that warrants attention


def _load() -> dict:
    try:
        with open(WATCHLIST_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def _save(d: dict) -> bool:
    try:
        with open(WATCHLIST_PATH, "w", encoding="utf-8") as fh:
            json.dump(d, fh, ensure_ascii=False, indent=1)
        return True
    except Exception:
        return False


def items() -> dict:
    return _load()


def is_watched(ticker) -> bool:
    return ticker in _load()


def add(ticker, price=None, score_v2=None, recommendation=None, support=None, note="") -> bool:
    """Snapshot the thesis at save time — the baseline for 'what changed'."""
    d = _load()
    d[ticker] = {"added": datetime.now().strftime("%d/%m/%Y"),
                 "price": price, "score_v2": score_v2,
                 "recommendation": recommendation, "support": support, "note": note}
    return _save(d)


def remove(ticker) -> bool:
    d = _load()
    d.pop(ticker, None)
    return _save(d)


def _n(v):
    return v if isinstance(v, (int, float)) and v == v else None


def enrich(universe: dict, results_rows: list) -> list:
    """Join saved baselines with CURRENT artifact data → change report per ticker.

    Returns rows: baseline vs now (price/score/rec), deltas, attention flags.
    Tickers not in the latest scan are honestly marked "לא נסרק לאחרונה".
    """
    now_by = {}
    for r in (universe or {}).get("all", []):
        if r.get("Ticker"):
            now_by[r["Ticker"]] = r
    for r in results_rows or []:
        if r.get("Ticker"):
            now_by.setdefault(r["Ticker"], {}).update({k: v for k, v in r.items() if v is not None})

    out = []
    for tk, base in _load().items():
        cur = now_by.get(tk, {})
        price_now = _n(cur.get("Price"))
        score_now = _n(cur.get("ScoreV2"))
        d_price = (round((price_now / base["price"] - 1) * 100, 1)
                   if price_now and _n(base.get("price")) else None)
        d_score = (round(score_now - base["score_v2"], 1)
                   if score_now is not None and _n(base.get("score_v2")) is not None else None)
        attention = []
        if d_score is not None and abs(d_score) >= ATTENTION_SCORE_DELTA:
            attention.append(f"ציון V2 השתנה {d_score:+.0f}")
        sup = _n(base.get("support"))
        if sup and price_now and price_now < sup:
            attention.append(f"המחיר ירד מתחת לתמיכה ששמרת (${sup})")
        if d_price is not None and abs(d_price) >= 10:
            attention.append(f"תזוזת מחיר {d_price:+.1f}% מאז השמירה")
        out.append({"ticker": tk, **base,
                    "price_now": price_now, "score_now": score_now,
                    "d_price": d_price, "d_score": d_score,
                    "scanned": tk in now_by, "attention": attention})
    out.sort(key=lambda r: (-len(r["attention"]), -(abs(r["d_score"] or 0))))
    return out
