# -*- coding: utf-8 -*-
"""What actually happened after each decision: the live engine vs the
four-dimension engine, measured on the shadow log (data/shadow_log.jsonl).

Owner brief (01/11/2026): track the new engine over time against the live engine
and against benchmarks. Not only returns: drawdowns, stability of the decisions,
data quality, decision changes, and results by sector and by market regime. No firm
conclusion from a small sample.

Outcomes (need prices, horizons of 21 and 63 trading days):
  - excess return vs three benchmarks: the equal-weight average of all logged stocks
    that day, SPY, and the same-sector average that day (sector-neutral),
  - drawdowns: average worst drop inside the window, its 10th percentile (the bad
    tail), and the share of decisions that fell 15% or more at some point,
  - hit rate, per engine and action, for the disagreements, by price / timing /
    quality label, by sector, and by market regime (SPY above / below its 200-day average).
Every statistic is averaged per day first and its standard error is clustered by
day. Overlapping windows make neighbouring days dependent, so even that overstates
precision. A group with fewer than MIN_DAYS decision days is marked "not enough evidence".

From the log alone (no prices):
  - stability: how often each engine changes its answer for the same stock from one
    logged day to the next, how long a "buy" lasts, and the buy <-> avoid flips,
  - decision changes: the day-to-day transition counts per engine,
  - data quality: coverage, share without data, reliability, profile age per day.

The number of buys is not a quality measure.

Usage:  python research/shadow_eval.py [--out path]
"""
import json
import math
import os
import sys
from collections import Counter
from datetime import datetime, timedelta

import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))
import config                                       # noqa: E402

HORIZONS = (21, 63)
MIN_DAYS = 20          # below this many independent decision days per group: no conclusion
ACTIONS = ("buy", "wait", "avoid")


def load_log(path=config.SHADOW_LOG) -> pd.DataFrame:
    rows = []
    with open(path, encoding="utf-8") as fh:
        for ln in fh:
            if ln.strip():
                rows.append(json.loads(ln))
    df = pd.DataFrame(rows)
    df["day"] = pd.to_datetime(df["d"], format="%d/%m/%Y")      # dates are DD/MM/YYYY
    for col in ("s", "pa", "q", "rel"):
        if col not in df:
            df[col] = None
    return df


def _prices(tickers, start):
    import yfinance as yf
    data = yf.download(sorted(set(tickers) | {"SPY"}), start=(start - timedelta(days=420)).strftime("%Y-%m-%d"),
                       auto_adjust=True, progress=False, threads=True)
    return data["Close"]


def regimes(spy: pd.Series) -> pd.Series:
    """'rising' when SPY closes at or above its 200-day average, else 'falling'."""
    s = spy.dropna()
    return pd.Series((s >= s.rolling(200).mean()).map({True: "rising", False: "falling"}), index=s.index).where(
        s.rolling(200).mean().notna())


def _forward(close, day, h):
    """Return over h trading days from `day` and the worst drop inside the window, or (None, None)."""
    s = close.dropna()
    idx = s.index.searchsorted(day)
    if idx >= len(s) or idx + h >= len(s):
        return None, None
    window = s.iloc[idx: idx + h + 1]
    base = float(window.iloc[0])
    return float(window.iloc[-1]) / base - 1, float(window.min()) / base - 1


def outcomes(log: pd.DataFrame, closes: pd.DataFrame) -> pd.DataFrame:
    reg = regimes(closes["SPY"]) if "SPY" in closes else pd.Series(dtype=object)
    out = []
    for h in HORIZONS:
        spy = {d: _forward(closes["SPY"], d, h)[0] for d in log["day"].unique()} if "SPY" in closes else {}
        for _, r in log.iterrows():
            if r["t"] not in closes:
                continue
            ret, dd = _forward(closes[r["t"]], r["day"], h)
            if ret is None:
                continue
            i = reg.index.searchsorted(r["day"]) if len(reg) else None
            regime = reg.iloc[i] if i is not None and i < len(reg) else None
            out.append({**r.to_dict(), "h": h, "ret": ret, "dd": dd, "spy": spy.get(r["day"]), "regime": regime})
    df = pd.DataFrame(out)
    if len(df):
        df["ew"] = df.groupby(["h", "day"])["ret"].transform("mean")
        df["x_ew"] = df["ret"] - df["ew"]
        df["x_spy"] = df["ret"] - df["spy"]
        sec = df["s"].fillna("?")
        df["x_sec"] = df["ret"] - df.groupby([df["h"], df["day"], sec])["ret"].transform("mean")
    return df


def _group_stats(g):
    per_day = g.groupby("day").agg(x=("x_ew", "mean"), s=("x_spy", "mean"), sec=("x_sec", "mean"),
                                   dd=("dd", "mean"), hit=("x_ew", lambda v: (v > 0).mean()))
    n_days = len(per_day)
    se = per_day["x"].std(ddof=1) / math.sqrt(n_days) if n_days > 1 else None
    pct = lambda v: None if v is None or v != v else round(v * 100, 2)
    return {"n": int(len(g)), "days": n_days,
            "excess_vs_avg_%": pct(per_day["x"].mean()), "se_%": pct(se),
            "excess_vs_spy_%": pct(per_day["s"].mean()),
            "excess_vs_sector_%": pct(per_day["sec"].mean()),
            "hit_rate_%": None if per_day["hit"].isna().all() else round(per_day["hit"].mean() * 100, 1),
            "avg_worst_drop_%": pct(per_day["dd"].mean()),
            "worst_drop_p10_%": pct(g["dd"].quantile(0.10)),
            "share_fell_15%_%": round((g["dd"] <= -0.15).mean() * 100, 1),
            "enough_days": n_days >= MIN_DAYS}


def report(df: pd.DataFrame) -> dict:
    res = {}
    for h in HORIZONS:
        d = df[df["h"] == h]
        if d.empty:
            res[h] = "no matured decisions yet"
            continue
        r = {"live": {}, "new": {}, "disagreements": {}}
        for eng in ("live", "new"):
            for a, g in d[d[eng].isin(ACTIONS)].groupby(eng):
                r[eng][a] = _group_stats(g)
        for name, mask in (("new_buy_live_not", (d["new"] == "buy") & (d["live"] != "buy")),
                           ("live_buy_new_not", (d["live"] == "buy") & (d["new"] != "buy")),
                           ("both_buy", (d["live"] == "buy") & (d["new"] == "buy"))):
            if mask.any():
                r["disagreements"][name] = _group_stats(d[mask])
        d = d.assign(qt=pd.cut(pd.to_numeric(d["q"], errors="coerce"), [-1, 44.5, 54.5, 67.5, 101],
                               labels=["poor", "weak", "fair", "strong"]))
        rated = d[d["new"] != "nodata"]
        for dim in ("p", "tm", "qt"):
            r[f"by_{dim}"] = {str(k): _group_stats(g) for k, g in rated.groupby(dim, observed=True)}
        r["by_sector"] = {str(s): {a: _group_stats(g2) for a, g2 in g.groupby("new") if a in ACTIONS}
                          for s, g in rated.groupby(rated["s"].fillna("?"))}
        r["by_regime"] = {str(k): {eng: {a: _group_stats(g2) for a, g2 in g.groupby(eng) if a in ACTIONS}
                                   for eng in ("live", "new")}
                          for k, g in d.groupby(d["regime"].fillna("unknown"))}
        res[h] = r
    return res


def stability(log: pd.DataFrame) -> dict:
    """Decision changes from one logged day to the next, per engine (no prices needed)."""
    days = sorted(log["day"].unique())
    out = {}
    for eng in ("live", "new"):
        piv = log.pivot_table(index="t", columns="day", values=eng, aggfunc="first")
        trans, changed, compared = Counter(), 0, 0
        for a, b in zip(days, days[1:]):
            both = piv[[a, b]].dropna()
            both = both[both[a].isin(ACTIONS) & both[b].isin(ACTIONS)]
            compared += len(both)
            for x, y in zip(both[a], both[b]):
                trans[f"{x}->{y}"] += 1
                changed += x != y
        runs = []
        for _, row in piv.iterrows():
            n = 0
            for v in row.tolist():
                if v == "buy":
                    n += 1
                elif n:
                    runs.append(n)
                    n = 0
            if n:
                runs.append(n)
        out[eng] = {"day_pairs": len(days) - 1, "compared": compared,
                    "change_rate_%": round(changed / compared * 100, 1) if compared else None,
                    "buy_avoid_flips": trans["buy->avoid"] + trans["avoid->buy"],
                    "avg_buy_run_days": round(sum(runs) / len(runs), 1) if runs else None,
                    "transitions": dict(trans)}
    return out


def data_quality(log: pd.DataFrame) -> list:
    rows = []
    for day, g in log.groupby("day"):
        rel = pd.to_numeric(g["rel"], errors="coerce")
        pa = pd.to_numeric(g["pa"], errors="coerce")
        rows.append({"day": day.strftime("%d/%m/%Y"), "stocks": int(len(g)),
                     "new_nodata_%": round((g["new"] == "nodata").mean() * 100, 1),
                     "live_nodata_%": round((g["live"] == "nodata").mean() * 100, 1),
                     "avg_reliability": None if rel.isna().all() else round(rel.mean(), 1),
                     "with_quality_%": round(pd.to_numeric(g["q"], errors="coerce").notna().mean() * 100, 1),
                     "avg_profile_age_days": None if pa.isna().all() else round(pa.mean(), 1)})
    return rows


def headline(res: dict) -> list:
    """Plain Hebrew lines. Never a verdict before there is enough evidence."""
    lines = [f"יומן הצל: {res['log_days']} ימי החלטה."]
    r21 = (res.get("results") or {}).get(21) if isinstance(res.get("results"), dict) else None
    if not isinstance(r21, dict):
        lines.append("עדיין אין החלטות שהבשילו ל-21 ימי מסחר. אין מה להסיק בשלב זה.")
        return lines
    nb, lb = r21["new"].get("buy"), r21["live"].get("buy")
    for name, s in (("קניות המנוע החדש", nb), ("קניות המנוע החי", lb)):
        if s:
            tag = "" if s["enough_days"] else " (אין עדיין מספיק ימים למסקנה)"
            lines.append(f"{name}: {s['excess_vs_avg_%']:+.2f}% מול הממוצע, ירידה ממוצעת בתוך התקופה "
                         f"{s['avg_worst_drop_%']:.1f}%, על פני {s['days']} ימים{tag}.")
    return lines


def evaluate(log_path=config.SHADOW_LOG, out_path=None, closes=None) -> dict:
    log = load_log(log_path)
    if closes is None:
        closes = _prices(log["t"].unique(), log["day"].min())
    df = outcomes(log, closes)
    res = {"as_of": datetime.now().strftime("%d/%m/%Y"), "log_days": int(log["day"].nunique()),
           "first_day": log["day"].min().strftime("%d/%m/%Y"), "last_day": log["day"].max().strftime("%d/%m/%Y"),
           "matured": {h: int((df["h"] == h).sum()) if len(df) else 0 for h in HORIZONS},
           "min_days_for_conclusion": MIN_DAYS,
           "results": report(df) if len(df) else "no matured decisions yet",
           "stability": stability(log), "data_quality": data_quality(log)}
    res["headline"] = headline(res)
    if out_path:
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(res, fh, ensure_ascii=False, indent=1, default=str)
    return res


def main():
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else config.SHADOW_EVAL
    res = evaluate(out_path=out)
    print("\n".join(res["headline"]))
    print(json.dumps({k: res[k] for k in ("log_days", "matured", "stability")}, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
