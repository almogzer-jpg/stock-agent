# -*- coding: utf-8 -*-
"""Market-wide opportunity discovery engine (Phase 14, Part 5).

Two-phase scan so a market-wide universe completes in minutes on free data:

  Phase A (cheap, ALL tickers): one batched yf.download of OHLCV, then per-ticker
    technical score, risk (beta/vol/maxDD), momentum (1m/3m) and breakout —
    all from prices, vectorised. Ranks the whole universe.
  Phase B (deep, top-N only): fundamentals (weekly-cached), valuation, sector
    score, composite Final Score v2, and a signal backtest (historical success).

Produces discovery rankings (opportunities / undervalued / momentum / quality /
turnarounds), per-opportunity detail, a sector distribution and timing — saved
to data/universe.json for the dashboard's Market Scanner tab.

Run:  python scanner.py [SP500|NASDAQ100|ALL] [limit]
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import yfinance as yf

import config
import universe
import market
import technicals as technicals_mod
import risk as risk_engine
import decisions as decision_engine
from indicators.technical import rsi
from scanners.breakout import is_breakout
from ranking_engine.score import score_stock
from ranking_engine.composite import composite_score
from ranking_engine.factor_scores import fundamental_score
from fundamentals.fundamentals import get_fundamentals
from backtesting.backtester import backtest_signal
from names import get_company_name


def _download(tickers, period="2y", chunk=80):
    """Batched OHLCV download → {ticker: DataFrame}. Robust to multi/flat cols."""
    frames = {}
    for i in range(0, len(tickers), chunk):
        batch = tickers[i:i + chunk]
        try:
            data = yf.download(batch, period=period, auto_adjust=True,
                               progress=False, group_by="ticker", threads=True)
        except Exception:
            continue
        if data is None or data.empty:
            continue
        multi = isinstance(data.columns, pd.MultiIndex)
        for t in batch:
            try:
                sub = data[t] if multi else data
                if "Close" in sub and sub["Close"].notna().any():
                    frames[t] = sub
            except Exception:
                pass
    return frames


def _metrics(close, vol):
    """Price-only metrics for one ticker (None if too little history)."""
    c = close.dropna()
    if len(c) < 210:
        return None
    v = vol.reindex(c.index)
    price = float(c.iloc[-1])
    high52 = float(c.tail(252).max())
    m = {
        "Price": round(price, 2),
        "MA20": float(c.rolling(20).mean().iloc[-1]),
        "MA50": float(c.rolling(50).mean().iloc[-1]),
        "MA200": float(c.rolling(200).mean().iloc[-1]),
        "RSI14": round(float(rsi(c, 14).iloc[-1]), 1),
        "AvgVol20": float(v.rolling(20).mean().iloc[-1]) if v.notna().any() else 0,
        "CurVol": float(v.iloc[-1]) if v.notna().any() else 0,
        "High52w": round(high52, 2),
        "DistFromHigh%": round((high52 - price) / high52 * 100, 2) if high52 > 0 else 0,
        "DailyChange%": round((c.iloc[-1] / c.iloc[-2] - 1) * 100, 2) if len(c) >= 2 else 0,
        "Ret1m": round((c.iloc[-1] / c.iloc[-22] - 1) * 100, 2) if len(c) > 22 else None,
        "Ret3m": round((c.iloc[-1] / c.iloc[-64] - 1) * 100, 2) if len(c) > 64 else None,
    }
    m["VolRatio"] = round(m["CurVol"] / m["AvgVol20"], 2) if m["AvgVol20"] > 0 else 0.0
    # 60-day reclaim flag for turnarounds: was below 200-MA recently, now > 50-MA.
    below200_recent = bool((c.tail(60) < c.rolling(200).mean().tail(60)).any())
    m["_reclaim"] = below200_recent and price > m["MA50"] and price > m["MA200"]
    return m


def scan_universe(name=None, limit=None, top_enrich=None) -> dict:
    name = name or config.SCAN_UNIVERSE
    top_enrich = top_enrich or config.SCAN_TOP_ENRICH
    t0 = time.time()
    tickers = universe.get_universe(name)
    if limit:
        tickers = tickers[:limit]
    print(f"סורק יקום {name}: {len(tickers)} מניות...")

    mkt_df = _download(["^GSPC"], period="2y", chunk=1).get("^GSPC")
    mkt_close = mkt_df["Close"] if mkt_df is not None else None
    sectors = market.sector_intelligence()

    frames = _download(tickers, period="2y")
    print(f"הורדו נתונים ל-{len(frames)} מניות תוך {time.time()-t0:.0f}s")

    # ---- Phase A: cheap technical/risk/momentum for ALL ----
    recs = []
    for t, df in frames.items():
        m = _metrics(df["Close"], df["Volume"])
        if m is None:
            continue
        m["Ticker"] = t
        m["Breakout"] = is_breakout(m)
        m["Score"] = score_stock(m)
        rp = risk_engine.risk_profile(df["Close"], mkt_close)
        m["RiskScore"] = rp["risk_score"] if rp["risk_score"] is not None else 50
        m["RiskLevel"] = rp["category"]
        m["Beta"], m["Volatility"], m["MaxDrawdown"] = rp["beta"], rp["volatility"], rp["max_drawdown"]
        # Support/Resistance levels (Phase 24) — real swing pivots + 52w extremes.
        srl = technicals_mod.sr_levels(df)
        m["Support"] = srl["support"] if srl else None
        m["Resistance"] = srl["resistance"] if srl else None
        m["DistSupport%"] = srl["dist_support_pct"] if srl else None
        m["DistResistance%"] = srl["dist_resistance_pct"] if srl else None
        m["RiskReward"] = srl["risk_reward"] if srl else None
        m["enriched"] = False
        m["ScoreV2"] = m["Score"]            # provisional until enriched
        recs.append(m)

    recs.sort(key=lambda x: x["Score"], reverse=True)

    # ---- Phase B: deep-enrich the top N ----
    for m in recs[:top_enrich]:
        t = m["Ticker"]
        fund = get_fundamentals(t)
        m["Name"] = get_company_name(t)
        m["Sector"] = fund.get("Sector")
        m["MarketCap"] = fund.get("MarketCap")
        m["ScoreFundamental"] = fundamental_score(fund)
        m["Valuation"] = decision_engine.valuation_score(fund)
        m["SectorScore"] = market.sector_score_for(m["Sector"], sectors)
        comp = composite_score(technical=m["Score"], fundamental=m["ScoreFundamental"],
                               sector=m["SectorScore"], news=50, risk=m["RiskScore"])
        m["ScoreV2"] = comp["final"] if comp else m["Score"]
        bt = backtest_signal(frames[t], mkt_close)
        m["HistWinRate"] = bt.get("win_rate") if bt else None
        m["Confidence"] = bt.get("confidence") if bt else "נמוך"
        # Discovery tags
        tags = []
        if m["Breakout"]:
            tags.append("פריצה")
        if (m.get("Ret3m") or 0) >= 15 and m["Price"] > m["MA50"]:
            tags.append("מומנטום חזק")
        if (m.get("Valuation") or 0) >= 65:
            tags.append("מוערך בחסר")
        if (m.get("ScoreFundamental") or 0) >= 70:
            tags.append("איכות גבוהה")
        if (fund.get("EPSGrowth") or 0) >= 20:
            tags.append("האצת רווחים")
        if m.get("_reclaim"):
            tags.append("תפנית (Turnaround)")
        if (m.get("SectorScore") or 0) >= 70:
            tags.append("רוטציה סקטוריאלית")
        if m["ScoreV2"] >= 70 and m["Confidence"] != "נמוך":
            tags.append("הזדמנות בביטחון גבוה")
        m["tags"] = tags

    enriched = [m for m in recs if m.get("enriched") is False and "Name" in m]
    for m in recs:
        m.pop("_reclaim", None)

    # ---- Rankings ----
    def top(seq, key, n=10, reverse=True):
        vals = [x for x in seq if x.get(key) is not None]
        return [x["Ticker"] for x in sorted(vals, key=lambda x: x[key], reverse=reverse)[:n]]

    rankings = {
        "opportunities": top(enriched, "ScoreV2"),
        "undervalued": top(enriched, "Valuation"),
        "momentum": top(recs, "Ret3m"),                       # whole universe
        "high_quality": top(enriched, "ScoreFundamental"),
        "turnarounds": [m["Ticker"] for m in sorted(
            [x for x in enriched if "תפנית (Turnaround)" in x.get("tags", [])],
            key=lambda x: x["ScoreV2"], reverse=True)[:10]],
    }

    # Sector distribution of enriched opportunities
    sec_dist = {}
    for m in enriched:
        s = m.get("Sector") or "לא ידוע"
        sec_dist[s] = sec_dist.get(s, 0) + 1

    payload = {
        "universe": name, "scanned": len(recs), "enriched": len(enriched),
        "opportunities": [m for m in recs if "Name" in m],   # enriched detail
        "all": recs,                                          # full universe (for filters)
        "rankings": rankings, "sector_distribution": dict(sorted(sec_dist.items(),
                                                          key=lambda kv: -kv[1])),
        "elapsed_sec": round(time.time() - t0, 1),
    }
    return payload


def save_universe(payload):
    with open(config.UNIVERSE_JSON, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False)


def _report(p):
    print("=" * 56)
    print(f"יקום: {p['universe']} · נסרקו: {p['scanned']} · הועשרו: {p['enriched']} "
          f"· זמן: {p['elapsed_sec']}s")
    print("הזדמנויות מובילות:", ", ".join(p["rankings"]["opportunities"][:10]))
    print("מומנטום:", ", ".join(p["rankings"]["momentum"][:10]))
    print("התפלגות סקטורים:", p["sector_distribution"])
    print("=" * 56)


if __name__ == "__main__":
    uni = sys.argv[1] if len(sys.argv) > 1 else config.SCAN_UNIVERSE
    lim = int(sys.argv[2]) if len(sys.argv) > 2 else None
    payload = scan_universe(uni, limit=lim)
    save_universe(payload)
    _report(payload)
