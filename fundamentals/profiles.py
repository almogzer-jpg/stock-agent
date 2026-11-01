# -*- coding: utf-8 -*-
"""Company profiles for the whole universe (input to the four-dimension engine).

One profile = one .info call (business ratios, multiples, analyst consensus) plus
the annual statements (revenue, operating margin, diluted EPS, free cash flow) and
the price at each fiscal year end, so the engine can judge business stability and
compare today's P/E with the company's own history.

Profiles live in data/profiles.json and are refreshed on a rolling basis: each run
refetches the stalest PROFILES_PER_RUN tickers. Every field is None when Yahoo does
not provide it — nothing is estimated or filled in.
"""
import json
import math
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date

try:
    import yfinance as yf
except ImportError:
    yf = None

import config

INFO_FIELDS = {
    "sector": "sector", "industry": "industry", "market_cap": "marketCap",
    "roe": "returnOnEquity", "roa": "returnOnAssets",
    "op_margin": "operatingMargins", "profit_margin": "profitMargins",
    "rev_growth": "revenueGrowth", "eps_growth": "earningsGrowth",
    "fcf": "freeCashflow", "revenue": "totalRevenue", "ebitda": "ebitda",
    "total_debt": "totalDebt", "total_cash": "totalCash", "current_ratio": "currentRatio",
    "debt_equity": "debtToEquity", "book_value": "bookValue",
    "fwd_pe": "forwardPE", "trailing_pe": "trailingPE", "ev_ebitda": "enterpriseToEbitda",
    "ps": "priceToSalesTrailing12Months", "trailing_eps": "trailingEps",
    "target_mean": "targetMeanPrice", "target_low": "targetLowPrice",
    "target_high": "targetHighPrice", "analysts": "numberOfAnalystOpinions",
    "price": "currentPrice",
}
PCT = ("roe", "roa", "op_margin", "profit_margin", "rev_growth", "eps_growth")


def _num(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _row(df, *names):
    """Newest-first list of a statement row (None where missing)."""
    if df is None or getattr(df, "empty", True):
        return None
    idx = {str(i).lower(): i for i in df.index}
    for n in names:
        if n in idx:
            return [_num(x) for x in df.loc[idx[n]].tolist()]
    return None


def _history(tk):
    """Annual statement history + P/E at each fiscal year end (best-effort)."""
    out = {"fy_ends": None, "rev_hist": None, "op_margin_hist": None, "eps_hist": None,
           "fcf_hist": None, "pe_hist": None}
    try:
        inc = tk.income_stmt
    except Exception:
        return out
    if inc is None or inc.empty:
        return out
    fy = [c.date() for c in inc.columns]
    rev = _row(inc, "total revenue", "operating revenue")
    opi = _row(inc, "operating income", "ebit")
    eps = _row(inc, "diluted eps", "basic eps")
    out["fy_ends"] = [d.strftime("%d/%m/%Y") for d in fy]
    out["rev_hist"], out["eps_hist"] = rev, eps
    if rev and opi:
        out["op_margin_hist"] = [round(o / r * 100, 1) if o is not None and r else None
                                 for o, r in zip(opi, rev)]
    try:
        cf = tk.cashflow
        out["fcf_hist"] = _row(cf, "free cash flow")
    except Exception:
        pass
    if eps:
        try:
            px = tk.history(period="6y", interval="1mo", auto_adjust=False)["Close"].dropna()
            pes = []
            for d, e in zip(fy, eps):
                before = px[px.index.date <= d]
                p = float(before.iloc[-1]) if len(before) else None
                pes.append(round(p / e, 1) if p and e and e > 0 else None)
            out["pe_hist"] = pes
        except Exception:
            pass
    return out


def fetch_profile(symbol: str) -> dict | None:
    """One company's profile, or None when Yahoo returned nothing usable."""
    if yf is None:
        return None
    try:
        tk = yf.Ticker(symbol)
        info = tk.info or {}
    except Exception as exc:
        if type(exc).__name__ == "YFRateLimitError":
            raise                       # stop the batch: hammering a rate limit only extends it
        return None
    p = {}
    for key, src in INFO_FIELDS.items():
        v = info.get(src)
        p[key] = v if key in ("sector", "industry") else _num(v)
    for k in PCT:
        if p[k] is not None:
            p[k] = round(p[k] * 100, 1)
    if p["debt_equity"] is not None:
        p["debt_equity"] = round(p["debt_equity"] / 100, 2)        # Yahoo gives a percentage
    if p["price"] is None:
        p["price"] = _num(info.get("regularMarketPrice"))
    p["peg"] = _num(info.get("trailingPegRatio")) or _num(info.get("pegRatio"))
    if not any(p.get(k) is not None for k in ("sector", "revenue", "op_margin", "fwd_pe")):
        return None
    p.update(_history(tk))
    p["_date"] = date.today().isoformat()
    return p


def load() -> dict:
    try:
        with open(config.PROFILES_JSON, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def save(profiles: dict) -> None:
    with open(config.PROFILES_JSON, "w", encoding="utf-8") as fh:
        json.dump(profiles, fh, ensure_ascii=False, separators=(",", ":"))


def _age(p) -> int:
    try:
        return (date.today() - date.fromisoformat(p.get("_date", ""))).days
    except Exception:
        return 10 ** 6


def refresh(tickers, limit: int | None = None, workers: int = 4) -> dict:
    """Refetch the stalest profiles (missing first, then oldest), at most `limit`.
    A failed fetch keeps the previous profile. Returns the full profile map."""
    limit = config.PROFILES_PER_RUN if limit is None else limit
    profiles = load()
    stale = [t for t in tickers if _age(profiles.get(t, {})) >= config.PROFILES_TTL_DAYS]
    stale.sort(key=lambda t: -_age(profiles.get(t, {})))
    todo = stale[:limit]
    done = 0
    if todo:
        with ThreadPoolExecutor(workers) as ex:
            try:
                for t, p in zip(todo, ex.map(fetch_profile, todo)):
                    done += 1
                    if p:
                        profiles[t] = p
            except Exception as exc:
                print(f"  ! עדכון פרופילים נעצר ({type(exc).__name__}), נשמר מה שהתקבל")
        save(profiles)
    print(f"פרופילי חברות: נבדקו {done}/{len(todo)}, קיימים {sum(1 for t in tickers if t in profiles)}/{len(tickers)}")
    return profiles
