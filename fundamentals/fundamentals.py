# -*- coding: utf-8 -*-
"""Fundamental metrics via yfinance (free) with a weekly cache.

Computes a focused quality/valuation set:
    Revenue Growth, EPS Growth, FCF Growth, Operating Margin,
    Debt/Equity, ROIC, PEG, Forward PE  (+ Sector, Market Cap for the app).

.info gives most fields directly; FCF growth and ROIC are derived from the
financial statements (best-effort). Every field is None when unavailable — we
never fabricate. Results are cached for FUNDAMENTALS_TTL_DAYS so daily runs
stay fast (fundamentals only change quarterly).
"""
import json
import os
from datetime import date

try:
    import yfinance as yf
except ImportError:
    yf = None

from config import FUNDAMENTALS_CACHE, FUNDAMENTALS_TTL_DAYS

FIELDS = ["Sector", "MarketCap", "RevenueGrowth", "EPSGrowth", "FCFGrowth",
          "OperatingMargin", "DebtToEquity", "ROIC", "PEG", "ForwardPE"]


def _num(v):
    """Return v if it's a real number, else None."""
    return v if isinstance(v, (int, float)) and v == v else None


def _pct(v):
    """yfinance fractions (0.15) -> percent (15.0)."""
    v = _num(v)
    return round(v * 100, 1) if v is not None else None


def _row(df, *names):
    """First non-NaN value of the first matching row (case-insensitive)."""
    if df is None or getattr(df, "empty", True):
        return None
    idx = {str(i).lower(): i for i in df.index}
    for n in names:
        if n in idx:
            s = df.loc[idx[n]].dropna()
            if len(s):
                return float(s.iloc[0])
    return None


def _fcf_growth(tk):
    """Latest-vs-prior free-cash-flow growth % (best-effort)."""
    try:
        cf = tk.cashflow
        if cf is None or cf.empty:
            return None
        idx = {str(i).lower(): i for i in cf.index}
        series = None
        if "free cash flow" in idx:
            series = cf.loc[idx["free cash flow"]].dropna()
        else:
            ocf = next((cf.loc[idx[k]] for k in idx if "operating cash flow" in k), None)
            cap = next((cf.loc[idx[k]] for k in idx if "capital expenditure" in k), None)
            if ocf is not None and cap is not None:
                series = (ocf + cap).dropna()        # capex is negative
        if series is None or len(series) < 2:
            return None
        latest, prior = float(series.iloc[0]), float(series.iloc[1])
        if prior == 0:
            return None
        return round((latest - prior) / abs(prior) * 100, 1)
    except Exception:
        return None


def _roic(tk):
    """ROIC % = NOPAT / Invested Capital (best-effort from statements)."""
    try:
        fin, bs = tk.financials, tk.balance_sheet
        ebit = _row(fin, "ebit", "operating income")
        pretax = _row(fin, "pretax income")
        tax = _row(fin, "tax provision")
        debt = _row(bs, "total debt")
        equity = _row(bs, "stockholders equity", "total stockholder equity")
        cash = _row(bs, "cash and cash equivalents",
                    "cash cash equivalents and short term investments", "cash financial")
        if ebit is None or debt is None or equity is None:
            return None
        tax_rate = (tax / pretax) if (pretax and tax is not None and pretax != 0) else 0.21
        tax_rate = min(max(tax_rate, 0.0), 0.5)
        invested = debt + equity - (cash or 0)
        if invested <= 0:
            return None
        return round(ebit * (1 - tax_rate) / invested * 100, 1)
    except Exception:
        return None


def _fetch_raw(symbol: str) -> dict:
    out = {k: None for k in FIELDS}
    if yf is None:
        return out
    try:
        tk = yf.Ticker(symbol)
        info = tk.info or {}
    except Exception:
        return out
    out["Sector"] = info.get("sector") or None
    out["MarketCap"] = _num(info.get("marketCap"))
    out["RevenueGrowth"] = _pct(info.get("revenueGrowth"))
    out["EPSGrowth"] = _pct(info.get("earningsGrowth"))
    out["OperatingMargin"] = _pct(info.get("operatingMargins"))
    de = _num(info.get("debtToEquity"))
    out["DebtToEquity"] = round(de / 100, 2) if de is not None else None   # % -> ratio
    peg = _num(info.get("trailingPegRatio")) or _num(info.get("pegRatio"))
    out["PEG"] = round(peg, 2) if peg is not None else None
    fpe = _num(info.get("forwardPE"))
    out["ForwardPE"] = round(fpe, 1) if fpe is not None else None
    out["FCFGrowth"] = _fcf_growth(tk)
    out["ROIC"] = _roic(tk)
    return out


# --- weekly cache ---------------------------------------------------------

def _load_cache() -> dict:
    if os.path.exists(FUNDAMENTALS_CACHE):
        try:
            with open(FUNDAMENTALS_CACHE, encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, ValueError):
            return {}
    return {}


def _save_cache(cache: dict) -> None:
    try:
        with open(FUNDAMENTALS_CACHE, "w", encoding="utf-8") as fh:
            json.dump(cache, fh, ensure_ascii=False)
    except OSError:
        pass


def _fresh(date_str: str) -> bool:
    try:
        d = date.fromisoformat(date_str)
        return (date.today() - d).days < FUNDAMENTALS_TTL_DAYS
    except Exception:
        return False


_CACHE = _load_cache()


def get_fundamentals(symbol: str) -> dict:
    """Cached fundamentals for `symbol` (refetched weekly). Clean dict (no _date)."""
    entry = _CACHE.get(symbol)
    if entry and _fresh(entry.get("_date", "")):
        return {k: entry.get(k) for k in FIELDS}
    data = _fetch_raw(symbol)
    _CACHE[symbol] = {**data, "_date": date.today().isoformat()}
    _save_cache(_CACHE)
    return data
