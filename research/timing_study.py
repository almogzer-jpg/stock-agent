# -*- coding: utf-8 -*-
"""Historical validation of the entry-timing rules used by the verdict engine.

Question: for a stock the system already likes, do the "wait" rules (RSI
overbought, price right under resistance, poor reward/risk to the nearest
levels, long-term downtrend) actually predict worse 3-month outcomes?

Method (reproducible, free data):
  * Universe: current S&P 500 constituents (data/universe.json) — NOTE:
    survivorship bias (today's members only) inflates absolute returns; the
    study therefore compares GROUPS against each other on the same universe,
    which is far less sensitive to that bias than absolute levels.
  * Daily adjusted closes 2014→today from Yahoo (yfinance).
  * Samples every 21 trading days per ticker (≈monthly, limits overlap).
  * Features use only data up to the sample date (no look-ahead), with the
    SAME functions the app uses (technicals.sr_levels, RSI-14, MA50/MA200).
  * Outcomes: 63-trading-day forward return in excess of SPY, the worst
    drawdown inside those 63 days, and the hit rate (excess > 0).
  * Statistics are averaged per sample DATE first, then across dates, so a
    crowded month does not dominate; the ± figure is the standard error across
    dates (≈ a 68% band; 2× ≈ 95%).

Run:  python research/timing_study.py            (≈30 min, network)
      python research/timing_study.py --from-csv samples.csv   (recompute from saved samples;
      set STUDY_SAMPLES_CSV=path on a full run to save them)
Out:  research/timing_study_results.json
"""
import json
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
import yfinance as yf

import config
import technicals as ta
from ranking_engine.score import score_stock
from scanners.breakout import is_breakout

HORIZON = 63
STEP = 21
START = "2014-01-01"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "timing_study_results.json")


def _rsi(close, n=14):
    d = close.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def _download(tickers):
    frames = {}
    for i in range(0, len(tickers), 50):
        chunk = tickers[i:i + 50]
        for attempt in range(3):
            try:
                df = yf.download(chunk, start=START, auto_adjust=True, progress=False,
                                 group_by="ticker", threads=True)
                break
            except Exception:
                time.sleep(5)
        else:
            continue
        for t in chunk:
            try:
                sub = df[t].dropna(how="all")
                if len(sub) > 400:
                    frames[t] = sub
            except Exception:
                pass
        print(f"downloaded {min(i + 50, len(tickers))}/{len(tickers)}", flush=True)
    return frames


def _samples(t, df, spy):
    close = df["Close"]
    ma20, ma50, ma200 = close.rolling(20).mean(), close.rolling(50).mean(), close.rolling(200).mean()
    rsi = _rsi(close)
    hi252 = close.rolling(252).max()
    ret63_back = close / close.shift(63) - 1
    vol = df["Volume"] if "Volume" in df.columns else None
    avgvol = vol.rolling(20).mean() if vol is not None else None
    rows = []
    n = len(close)
    for i in range(260, n - HORIZON, STEP):
        win = df.iloc[max(0, i - 260):i + 1]
        try:
            srl = ta.sr_levels(win)
        except Exception:
            srl = None
        p0, p1 = close.iloc[i], close.iloc[i + HORIZON]
        d0, d1 = close.index[i], close.index[i + HORIZON]
        try:
            s0, s1 = spy.asof(d0), spy.asof(d1)
        except Exception:
            continue
        if not (s0 and s1) or s0 != s0 or s1 != s1:
            continue
        fwd = p1 / p0 - 1
        path = close.iloc[i:i + HORIZON + 1]
        m = {"Price": float(p0), "MA20": float(ma20.iloc[i]), "MA50": float(ma50.iloc[i]),
             "MA200": float(ma200.iloc[i]),
             "RSI14": float(rsi.iloc[i]) if rsi.iloc[i] == rsi.iloc[i] else 50.0,
             "DistFromHigh%": float((hi252.iloc[i] - p0) / hi252.iloc[i] * 100),
             "VolRatio": (float(vol.iloc[i] / avgvol.iloc[i])
                          if vol is not None and avgvol.iloc[i] and avgvol.iloc[i] == avgvol.iloc[i] else 1.0)}
        try:
            tscore, brk = score_stock(m), bool(is_breakout(m))
        except Exception:
            tscore, brk = None, None
        rows.append({
            "t": t, "date": d0.strftime("%Y-%m-%d"),
            "above200": bool(p0 > ma200.iloc[i]), "above50": bool(p0 > ma50.iloc[i]),
            "rsi": float(rsi.iloc[i]) if rsi.iloc[i] == rsi.iloc[i] else None,
            "dist_high": float((hi252.iloc[i] - p0) / hi252.iloc[i] * 100),
            "mom3m": float(ret63_back.iloc[i] * 100) if ret63_back.iloc[i] == ret63_back.iloc[i] else None,
            "status": (srl or {}).get("status"),
            "dist_sup": (srl or {}).get("dist_support_pct"),
            "dist_res": (srl or {}).get("dist_resistance_pct"),
            "rr": (srl or {}).get("risk_reward"),
            "tscore": tscore, "breakout_signal": brk,
            "fwd": fwd * 100, "excess": (fwd - (s1 / s0 - 1)) * 100,
            "dd": float((path.min() / p0 - 1) * 100),
        })
    return rows


def _stats(df):
    """Date-clustered statistics for one group of samples."""
    if len(df) < 30:
        return {"n": int(len(df)), "insufficient": True}
    g = df.groupby("date").agg(excess=("excess", "mean"), hit=("excess", lambda s: (s > 0).mean()),
                               dd=("dd", "mean"))
    k = len(g)
    se = lambda s: float(s.std(ddof=1) / math.sqrt(k)) if k > 1 else None
    return {
        "n": int(len(df)), "dates": int(k),
        "excess_3m": round(float(g["excess"].mean()), 2), "excess_se": round(se(g["excess"]) or 0, 2),
        "hit_rate": round(float(g["hit"].mean()) * 100, 1), "hit_se": round((se(g["hit"]) or 0) * 100, 1),
        "avg_drawdown": round(float(g["dd"].mean()), 2),
        "p10_return": round(float(np.percentile(df["fwd"], 10)), 2),
        "median_return": round(float(np.median(df["fwd"])), 2),
    }


def _setups(s):
    """Base rates per (trend, RSI band) — the buckets verdict.evidence_for() uses."""
    trend = np.where(~s.above200, "down", np.where(s.above50, "up", "mixed"))
    band = np.where(s.rsi < 50, "lt50", np.where(s.rsi < 70, "50_70", "ge70"))
    s = s.assign(_k=pd.Series(trend, index=s.index) + "|" + pd.Series(band, index=s.index))
    out = {}
    for k, g in s[s.rsi.notna()].groupby("_k"):
        st = _stats(g)
        if not st.get("insufficient"):
            out[k] = {"n": st["n"], "median_return": st["median_return"], "p10_return": st["p10_return"],
                      "avg_drawdown": st["avg_drawdown"], "hit_rate": st["hit_rate"]}
    return out


def build(s, n_tickers):
    up = s[s.above200 & s.above50]
    groups = {
        "all": s,
        # Trend gate
        "uptrend (above MA50 & MA200)": up,
        "below MA200": s[~s.above200],
        "below MA200 and 3m momentum < 0": s[(~s.above200) & (s.mom3m < 0)],
        # Overbought, within uptrends
        "uptrend · RSI < 50": up[up.rsi < 50],
        "uptrend · RSI 50-70": up[(up.rsi >= 50) & (up.rsi < 70)],
        "uptrend · RSI 70-75": up[(up.rsi >= 70) & (up.rsi < 75)],
        "uptrend · RSI >= 75": up[up.rsi >= 75],
        # Proximity to resistance / highs
        "uptrend · breakout (above all pivots)": up[up.status == "breakout"],
        "uptrend · <=2% under resistance": up[(up.status != "breakout") & (up.dist_res <= 2)],
        "uptrend · >2% under resistance": up[(up.status != "breakout") & (up.dist_res > 2)],
        "uptrend · within 3% of 52w high": up[up.dist_high <= 3],
        "uptrend · 3-10% below 52w high": up[(up.dist_high > 3) & (up.dist_high <= 10)],
        "uptrend · >10% below 52w high": up[up.dist_high > 10],
        # Reward/risk to nearest levels
        "uptrend · R/R < 1": up[up.rr < 1],
        "uptrend · R/R 1-2": up[(up.rr >= 1) & (up.rr < 2)],
        "uptrend · R/R >= 2": up[up.rr >= 2],
        # Near support
        "uptrend · within 3% above support": up[up.dist_sup.abs() <= 3],
        "uptrend · 3-8% above support": up[(up.dist_sup.abs() > 3) & (up.dist_sup.abs() <= 8)],
        "uptrend · >8% above support": up[up.dist_sup.abs() > 8],
        # Momentum
        "3m momentum top (>= +20%)": s[s.mom3m >= 20],
        "3m momentum <= -15%": s[s.mom3m <= -15],
    }
    if "tscore" in s.columns:            # model check: the technical score (25% of V2)
        ts = s[s.tscore.notna()]
        for lo, hi in ((0, 35), (35, 50), (50, 65), (65, 80), (80, 101)):
            groups[f"technical score {lo}-{min(hi, 100)}"] = ts[(ts.tscore >= lo) & (ts.tscore < hi)]
        groups["breakout signal (app definition)"] = s[s.breakout_signal == True]  # noqa: E712
        groups["no breakout signal"] = s[s.breakout_signal == False]  # noqa: E712
    return {"meta": {"horizon_days": HORIZON, "step_days": STEP, "start": START,
                     "tickers": int(n_tickers), "samples": int(len(s)),
                     "first_date": s.date.min(), "last_date": s.date.max(),
                     "generated": time.strftime("%Y-%m-%d"),
                     "caveat": "Current S&P 500 members only (survivorship bias); compare groups, not absolute levels."},
            "groups": {k: _stats(v) for k, v in groups.items()},
            "setups": _setups(s)}


def main():
    if len(sys.argv) > 2 and sys.argv[1] == "--from-csv":       # recompute from saved samples
        s = pd.read_csv(sys.argv[2])
        out = build(s, s.t.nunique())
        with open(OUT, "w", encoding="utf-8") as fh:
            json.dump(out, fh, ensure_ascii=False, indent=1)
        return
    with open(config.UNIVERSE_JSON, encoding="utf-8") as fh:
        tickers = sorted({r["Ticker"] for r in json.load(fh)["all"] if r.get("Ticker")})
    print(f"universe: {len(tickers)} tickers", flush=True)
    spy = yf.download("SPY", start=START, auto_adjust=True, progress=False)["Close"]
    spy = spy.iloc[:, 0] if isinstance(spy, pd.DataFrame) else spy
    frames = _download(tickers)
    rows = []
    for j, (t, df) in enumerate(frames.items()):
        rows += _samples(t, df, spy)
        if j % 50 == 0:
            print(f"sampled {j}/{len(frames)}", flush=True)
    s = pd.DataFrame(rows)
    out = build(s, len(frames))
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    if os.environ.get("STUDY_SAMPLES_CSV"):
        s.to_csv(os.environ["STUDY_SAMPLES_CSV"], index=False)
    for k, v in out["groups"].items():
        print(f"{k:45s} {v}")


if __name__ == "__main__":
    main()
