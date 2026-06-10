# -*- coding: utf-8 -*-
"""Company-name resolver with a local JSON cache.

Company names come from yfinance's .info, which is slow and occasionally
rate-limited. To keep the daily scan fast we cache resolved names in
data/names_cache.json and only hit the network for tickers we haven't seen.
Falls back to the symbol itself if a name can't be fetched.
"""
import json
import os

try:
    import yfinance as yf
except ImportError:
    yf = None

from config import DATA_DIR

_CACHE_PATH = os.path.join(DATA_DIR, "names_cache.json")


def _load_cache() -> dict:
    """Load the name cache from disk (empty dict on missing/corrupt file)."""
    if os.path.exists(_CACHE_PATH):
        try:
            with open(_CACHE_PATH, encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, ValueError):
            return {}
    return {}


def _save_cache(cache: dict) -> None:
    """Persist the name cache (best-effort)."""
    try:
        with open(_CACHE_PATH, "w", encoding="utf-8") as fh:
            json.dump(cache, fh, ensure_ascii=False, indent=0)
    except OSError:
        pass


# In-memory cache loaded once per process.
_CACHE = _load_cache()


def get_company_name(symbol: str) -> str:
    """Return the company's (English) name for `symbol`, using the cache.

    On a cache miss we fetch via yfinance and store the result. Falls back to
    the symbol itself if the name can't be resolved, so output never breaks.
    """
    if symbol in _CACHE:
        return _CACHE[symbol]

    name = symbol  # safe fallback
    if yf is not None:
        try:
            info = yf.Ticker(symbol).info or {}
            name = info.get("shortName") or info.get("longName") or symbol
        except Exception:
            name = symbol

    _CACHE[symbol] = name
    _save_cache(_CACHE)   # only writes on a genuine miss (new ticker)
    return name
