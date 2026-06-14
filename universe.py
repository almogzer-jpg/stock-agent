# -*- coding: utf-8 -*-
"""Master security universe (Phase 14, Part 5).

Builds the scannable universe from free index-constituent lists:
  • S&P 500   — Wikipedia
  • Nasdaq-100 — Wikipedia
The master universe is their de-duplicated union (~500 large/mid-cap US names).
Cached weekly to disk (constituents change rarely). If the network fetch fails,
falls back to the local watchlist so the system still runs.

Russell 2000 (2,000 small-caps) has no clean free constituent table and is
impractical to scan in <5 min on free data — it is intentionally NOT in the
default master universe; `get_universe("RUSSELL2000")` is a documented hook that
returns [] unless a holdings file is provided. (Architect's call: scan quality
over raw breadth.)
"""
import io
import json
import os
from datetime import date

from config import DATA_DIR, WATCHLIST_FILE

UNIVERSE_CACHE = os.path.join(DATA_DIR, "universe_tickers.json")
TTL_DAYS = 7
_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def _norm(sym: str) -> str:
    return str(sym).strip().upper().replace(".", "-")


def _fetch_table(url: str):
    import requests
    import pandas as pd
    html = requests.get(url, headers=_HEADERS, timeout=30).text
    return pd.read_html(io.StringIO(html))


def _sp500() -> list:
    t = _fetch_table("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")[0]
    return [_norm(s) for s in t["Symbol"].tolist()]


def _nasdaq100() -> list:
    for t in _fetch_table("https://en.wikipedia.org/wiki/Nasdaq-100"):
        for col in t.columns:
            if str(col).lower() in ("ticker", "symbol"):
                return [_norm(s) for s in t[col].tolist()]
    return []


def _watchlist() -> list:
    if not os.path.exists(WATCHLIST_FILE):
        return []
    out = []
    with open(WATCHLIST_FILE, encoding="utf-8") as fh:
        for line in fh:
            s = line.strip().upper()
            if s and not s.startswith("#"):
                out.append(s)
    return out


def _load_cache() -> dict:
    if os.path.exists(UNIVERSE_CACHE):
        try:
            with open(UNIVERSE_CACHE, encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, ValueError):
            return {}
    return {}


def get_universe(name: str = "ALL", use_cache: bool = True) -> list:
    """Return ticker list for: SP500 / NASDAQ100 / ALL (union) / RUSSELL2000.

    Cached weekly. Falls back to the local watchlist on fetch failure.
    """
    cache = _load_cache()
    fresh = False
    try:
        if cache.get("date"):
            fresh = (date.today() - date.fromisoformat(cache["date"])).days < TTL_DAYS
    except Exception:
        fresh = False

    if not (use_cache and fresh and cache.get("ALL")):
        try:
            sp = _sp500()
            ndx = _nasdaq100()
            cache = {
                "date": date.today().isoformat(),
                "SP500": sp, "NASDAQ100": ndx,
                "ALL": sorted(set(sp) | set(ndx)),
                "RUSSELL2000": [],   # not available free at scale (see module doc)
            }
            with open(UNIVERSE_CACHE, "w", encoding="utf-8") as fh:
                json.dump(cache, fh)
        except Exception as exc:
            print(f"  ! שליפת יקום נכשלה ({exc}); נופל חזרה ל-watchlist")
            wl = _watchlist()
            cache = {"date": date.today().isoformat(), "SP500": wl, "NASDAQ100": wl,
                     "ALL": wl, "RUSSELL2000": []}

    return cache.get(name.upper(), cache.get("ALL", []))
