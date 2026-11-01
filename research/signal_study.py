# -*- coding: utf-8 -*-
"""Does the technical score predict returns? Does the breakout signal?

A second, stricter study than timing_study.py, written to answer the owner's
question before any weight changes: is the technical score (25% of Score V2)
or the breakout signal a reason to buy?

Method (free data, reproducible):
  * Universe: S&P 500 members today (survivorship bias acknowledged below).
    GICS sectors from the same Wikipedia table, for sector benchmarks.
  * One sample per ticker every 21 trading days, features from data up to that
    day only, computed with the app's own functions (score_stock, is_breakout).
  * Horizons 21, 63 and 126 trading days.
  * Three benchmarks: SPY, the stock's sector ETF (SPDR), and the equal-weight
    cross-section of the same date (return minus that date's average across
    all sampled stocks). The cross-sectional one removes the market and most of
    the level bias that survivorship adds, so it is the primary test.
  * Predictive power: per-date Spearman rank correlation (IC) between the
    signal and the forward return, and the top-minus-bottom quintile spread.
    Means across dates with Newey-West standard errors (overlapping horizons).
  * Stability: three sub-periods and two market regimes (SPY above/below its
    200-day average).
  * Breakout: event study against all stocks on the same date AND against a
    matched control group that meets every breakout condition except the volume
    spike, so the test isolates what the signal adds.
  * Returns are winsorised at the 1st/99th percentile per horizon to keep a few
    extreme moves from driving the averages.

Run:  python research/signal_study.py            (≈10 min, network)
Out:  research/signal_study_results.json
"""
import io
import json
import math
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import pandas as pd
import yfinance as yf

import config
from ranking_engine.score import score_stock
from scanners.breakout import is_breakout
from timing_study import _download, _rsi

HORIZONS = (21, 63, 126)
STEP = 21
START = "2014-01-01"
OUT = os.environ.get("STUDY_OUT") or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                   "signal_study_results.json")
SECTOR_ETF = {
    "Information Technology": "XLK", "Health Care": "XLV", "Financials": "XLF",
    "Consumer Discretionary": "XLY", "Consumer Staples": "XLP", "Energy": "XLE",
    "Industrials": "XLI", "Materials": "XLB", "Utilities": "XLU",
    "Real Estate": "XLRE", "Communication Services": "XLC",
}
PERIODS = (("2015-2018", "2015-01-01", "2018-12-31"), ("2019-2022", "2019-01-01", "2022-12-31"),
           ("2023-2026", "2023-01-01", "2026-12-31"))


def _sectors() -> dict:
    req = urllib.request.Request("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
                                 headers={"User-Agent": "Mozilla/5.0"})
    t = pd.read_html(io.StringIO(urllib.request.urlopen(req, timeout=30).read().decode("utf-8")))[0]
    return {str(s).replace(".", "-").upper(): str(g) for s, g in zip(t["Symbol"], t["GICS Sector"])}


def _close(sym):
    s = yf.download(sym, start=START, auto_adjust=True, progress=False)["Close"]
    return s.iloc[:, 0] if isinstance(s, pd.DataFrame) else s


def _samples(t, df, bench, sector):
    close = df["Close"]
    vol = df["Volume"] if "Volume" in df.columns else None
    ma20, ma50, ma200 = (close.rolling(n).mean() for n in (20, 50, 200))
    rsi = _rsi(close)
    hi252 = close.rolling(252).max()
    avgvol = vol.rolling(20).mean() if vol is not None else None
    spy, etf = bench["SPY"], bench.get(SECTOR_ETF.get(sector or ""))
    rows, n, H = [], len(close), max(HORIZONS)
    for i in range(260, n - H, STEP):
        p0 = float(close.iloc[i])
        d0 = close.index[i]
        if not (ma200.iloc[i] == ma200.iloc[i]):
            continue
        m = {"Price": p0, "MA20": float(ma20.iloc[i]), "MA50": float(ma50.iloc[i]),
             "MA200": float(ma200.iloc[i]),
             "RSI14": float(rsi.iloc[i]) if rsi.iloc[i] == rsi.iloc[i] else 50.0,
             "DistFromHigh%": float((hi252.iloc[i] - p0) / hi252.iloc[i] * 100),
             "VolRatio": (float(vol.iloc[i] / avgvol.iloc[i])
                          if vol is not None and avgvol.iloc[i] and avgvol.iloc[i] == avgvol.iloc[i] else 1.0)}
        r = {"t": t, "date": d0.strftime("%Y-%m-%d"), "sector": sector,
             "tscore": score_stock(m), "breakout": bool(is_breakout(m)),
             "above50": p0 > m["MA50"], "above200": p0 > m["MA200"],
             "near_high": m["DistFromHigh%"] <= config.NEAR_HIGH_PCT,
             "rsi_ok": config.RSI_MIN <= m["RSI14"] <= config.RSI_MAX,
             "vol_spike": m["VolRatio"] >= config.VOLUME_SPIKE,
             "spy_up": None}
        try:
            s0 = float(spy.asof(d0))
            ma_spy = spy.loc[:d0].tail(200).mean()
            r["spy_up"] = bool(s0 > ma_spy)
        except Exception:
            continue
        for h in HORIZONS:
            d1 = close.index[i + h]
            fwd = float(close.iloc[i + h]) / p0 - 1
            r[f"fwd{h}"] = fwd * 100
            try:
                r[f"xs_spy{h}"] = (fwd - (float(spy.asof(d1)) / s0 - 1)) * 100
            except Exception:
                r[f"xs_spy{h}"] = None
            try:
                e0, e1 = float(etf.asof(d0)), float(etf.asof(d1))
                r[f"xs_sec{h}"] = (fwd - (e1 / e0 - 1)) * 100 if e0 == e0 and e1 == e1 else None
            except Exception:
                r[f"xs_sec{h}"] = None
        path = close.iloc[i:i + 64]
        r["dd63"] = float((path.min() / p0 - 1) * 100)
        rows.append(r)
    return rows


def _nw_se(x, lags):
    """Newey-West standard error of the mean of a time series."""
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    T = len(x)
    if T < 8:
        return None
    e = x - x.mean()
    s = (e @ e) / T
    for L in range(1, min(lags, T - 1) + 1):
        w = 1 - L / (lags + 1)
        s += 2 * w * (e[L:] @ e[:-L]) / T
    return math.sqrt(max(s, 0) / T)


def _summary(series, h):
    lags = max(1, h // STEP - 1)
    x = pd.Series(series).dropna()
    se = _nw_se(x.values, lags)
    mean = float(x.mean()) if len(x) else None
    return {"mean": round(mean, 4) if mean is not None else None,
            "se": round(se, 4) if se else None,
            "t": round(mean / se, 2) if se else None,
            "share_positive": round(float((x > 0).mean()) * 100, 1) if len(x) else None,
            "dates": int(len(x))}


def _ic_and_spread(df, col, h, ret):
    ics, spreads = [], []
    for _, g in df.groupby("date"):
        g = g[[col, ret]].dropna()
        if len(g) < 40 or g[col].nunique() < 5:
            continue
        ics.append(g[col].rank().corr(g[ret].rank()))
        q = pd.qcut(g[col].rank(method="first"), 5, labels=False)
        spreads.append(g[ret][q == 4].mean() - g[ret][q == 0].mean())
    return {"ic": _summary(ics, h), "top_minus_bottom_pct": _summary(spreads, h)}


def _event(df, mask_event, mask_control, h, ret):
    diffs = []
    for _, g in df.groupby("date"):
        a, b = g[mask_event.loc[g.index]][ret].dropna(), g[mask_control.loc[g.index]][ret].dropna()
        if len(a) >= 1 and len(b) >= 5:
            diffs.append(a.mean() - b.mean())
    out = _summary(diffs, h)
    out["events"] = int(mask_event.loc[df.index].sum())
    return out


def analyse(s: pd.DataFrame) -> dict:
    s = s.copy()
    for h in HORIZONS:
        for base in ("fwd", "xs_spy", "xs_sec"):
            c = f"{base}{h}"
            if c in s:
                lo, hi = s[c].quantile([0.01, 0.99])
                s[c] = s[c].clip(lo, hi)
        s[f"xs_ew{h}"] = s[f"fwd{h}"] - s.groupby("date")[f"fwd{h}"].transform("mean")
    res = {"technical_score": {}, "breakout": {}, "risk_by_score": {}}
    for h in HORIZONS:
        res["technical_score"][f"{h}d"] = {
            "vs_equal_weight": _ic_and_spread(s, "tscore", h, f"xs_ew{h}"),
            "vs_sector_etf": _ic_and_spread(s, "tscore", h, f"xs_sec{h}"),
            "sub_periods": {name: _ic_and_spread(s[(s.date >= a) & (s.date <= b)], "tscore", h, f"xs_ew{h}")["ic"]
                            for name, a, b in PERIODS},
            "regimes": {k: _ic_and_spread(s[s.spy_up == v], "tscore", h, f"xs_ew{h}")["ic"]
                        for k, v in (("spy_above_200d", True), ("spy_below_200d", False))},
        }
        brk = s.breakout
        control = s.above50 & s.above200 & s.near_high & s.rsi_ok & ~s.vol_spike
        res["breakout"][f"{h}d"] = {
            "vs_all_same_date": _event(s, brk, ~brk, h, f"xs_ew{h}"),
            "vs_matched_no_volume_spike": _event(s, brk, control, h, f"xs_ew{h}"),
            "vs_sector_etf_mean": _summary(s[brk][f"xs_sec{h}"], h),
            "sub_periods": {name: _event(s[(s.date >= a) & (s.date <= b)], brk, control, h, f"xs_ew{h}")
                            for name, a, b in PERIODS},
        }
    q = pd.qcut(s.tscore.rank(method="first"), 5, labels=["Q1 (נמוך)", "Q2", "Q3", "Q4", "Q5 (גבוה)"])
    res["risk_by_score"] = {str(k): {"avg_drawdown_63d": round(float(g.dd63.mean()), 2),
                                     "p10_fwd63": round(float(np.percentile(g.fwd63, 10)), 2),
                                     "n": int(len(g))}
                            for k, g in s.groupby(q, observed=True)}
    return res


def main():
    if len(sys.argv) > 2 and sys.argv[1] == "--from-csv":
        s = pd.read_csv(sys.argv[2])
    else:
        with open(config.UNIVERSE_JSON, encoding="utf-8") as fh:
            tickers = sorted({r["Ticker"] for r in json.load(fh)["all"] if r.get("Ticker")})
        if os.environ.get("STUDY_LIMIT"):
            tickers = tickers[:int(os.environ["STUDY_LIMIT"])]
        sectors = _sectors()
        bench = {"SPY": _close("SPY")}
        for etf in set(SECTOR_ETF.values()):
            try:
                bench[etf] = _close(etf)
            except Exception:
                pass
        frames = _download(tickers)
        rows = []
        for j, (t, df) in enumerate(frames.items()):
            rows += _samples(t, df, bench, sectors.get(t))
            if j % 100 == 0:
                print(f"sampled {j}/{len(frames)}", flush=True)
        s = pd.DataFrame(rows)
        if os.environ.get("STUDY_SAMPLES_CSV"):
            s.to_csv(os.environ["STUDY_SAMPLES_CSV"], index=False)
    out = {"meta": {"samples": int(len(s)), "tickers": int(s.t.nunique()), "first_date": s.date.min(),
                    "last_date": s.date.max(), "horizons": list(HORIZONS), "step": STEP,
                    "generated": time.strftime("%Y-%m-%d"),
                    "breakout_events": int(s.breakout.sum()),
                    "caveat": "Survivorship: today's S&P 500 members only. Cross-sectional (equal-weight) "
                              "tests are primary because they remove most of the level bias."},
           "results": analyse(s)}
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(json.dumps(out["meta"], ensure_ascii=False))


if __name__ == "__main__":
    main()
