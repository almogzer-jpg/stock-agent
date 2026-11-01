# -*- coding: utf-8 -*-
"""What actually happened after each decision: the live engine vs the
four-dimension engine, measured on the shadow log (data/shadow_log.jsonl).

For every logged day and horizon (21 and 63 trading days) it takes the close on
the decision day and the close H days later, and reports per engine and action:
  - excess return vs the equal-weight average of all logged stocks that day
    (and vs SPY), averaged per day first, so each day counts once,
  - a day-clustered standard error (overlapping windows make neighbouring days
    correlated, so the honest unit is the day, and even that overstates precision),
  - hit rate (share beating the day's average) and the average worst drop inside the window.
It also reports the disagreements, where the two engines differ.

The number of buys is not a quality measure. The questions are: do the new
engine's buys do better than its waits and avoids, better than the live buys,
and with shallower drawdowns? Until there are months of data the answer is
"not enough evidence yet", and the script says so.

Usage:  python research/shadow_eval.py [--out research/shadow_eval_results.json]
"""
import json
import math
import os
import sys
from collections import defaultdict
from datetime import datetime

import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))
import config                                       # noqa: E402

HORIZONS = (21, 63)
MIN_DAYS = 20          # below this many independent days per group, no conclusion is printed


def _load_log(path=config.SHADOW_LOG):
    rows = []
    with open(path, encoding="utf-8") as fh:
        for ln in fh:
            if ln.strip():
                rows.append(json.loads(ln))
    df = pd.DataFrame(rows)
    df["day"] = pd.to_datetime(df["d"], format="%d/%m/%Y")      # dates are DD/MM/YYYY
    return df


def _prices(tickers, start):
    import yfinance as yf
    data = yf.download(sorted(set(tickers) | {"SPY"}), start=start.strftime("%Y-%m-%d"),
                       auto_adjust=True, progress=False, threads=True)
    return data["Close"]


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
    out = []
    for h in HORIZONS:
        spy = {d: _forward(closes["SPY"], d, h)[0] for d in log["day"].unique()} if "SPY" in closes else {}
        for _, r in log.iterrows():
            if r["t"] not in closes:
                continue
            ret, dd = _forward(closes[r["t"]], r["day"], h)
            if ret is None:
                continue
            out.append({**r.to_dict(), "h": h, "ret": ret, "dd": dd, "spy": spy.get(r["day"])})
    df = pd.DataFrame(out)
    if len(df):
        df["ew"] = df.groupby(["h", "day"])["ret"].transform("mean")
        df["x_ew"] = df["ret"] - df["ew"]
        df["x_spy"] = df["ret"] - df["spy"]
    return df


def _group_stats(g):
    per_day = g.groupby("day").agg(x=("x_ew", "mean"), s=("x_spy", "mean"), dd=("dd", "mean"),
                                   hit=("x_ew", lambda v: (v > 0).mean()))
    n_days = len(per_day)
    se = per_day["x"].std(ddof=1) / math.sqrt(n_days) if n_days > 1 else None
    return {"n": int(len(g)), "days": n_days,
            "excess_vs_avg_%": round(per_day["x"].mean() * 100, 2),
            "se_%": None if se is None or se != se else round(se * 100, 2),
            "excess_vs_spy_%": round(per_day["s"].mean() * 100, 2),
            "hit_rate_%": round(per_day["hit"].mean() * 100, 1),
            "avg_worst_drop_%": round(per_day["dd"].mean() * 100, 2),
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
            for a, g in d[d[eng].isin(["buy", "wait", "avoid"])].groupby(eng):
                r[eng][a] = _group_stats(g)
        for name, mask in (("new_buy_live_not", (d["new"] == "buy") & (d["live"] != "buy")),
                           ("live_buy_new_not", (d["live"] == "buy") & (d["new"] != "buy")),
                           ("both_buy", (d["live"] == "buy") & (d["new"] == "buy"))):
            if mask.any():
                r["disagreements"][name] = _group_stats(d[mask])
        d = d.assign(qt=pd.cut(d["q"], [-1, 44.5, 54.5, 67.5, 101], labels=["poor", "weak", "fair", "strong"]))
        for dim in ("p", "tm", "qt"):
            r[f"by_{dim}"] = {str(k): _group_stats(g) for k, g in d[d["new"] != "nodata"].groupby(dim, observed=True)}
        res[h] = r
    return res


def main():
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else os.path.join(_HERE, "shadow_eval_results.json")
    log = _load_log()
    print(f"יומן הצל: {log['day'].nunique()} ימים, {len(log)} החלטות, "
          f"{log['day'].min():%d/%m/%Y} עד {log['day'].max():%d/%m/%Y}")
    closes = _prices(log["t"].unique(), log["day"].min())
    df = outcomes(log, closes)
    res = {"as_of": datetime.now().strftime("%d/%m/%Y"), "log_days": int(log["day"].nunique()),
           "matured": {h: int((df["h"] == h).sum()) if len(df) else 0 for h in HORIZONS},
           "min_days_for_conclusion": MIN_DAYS, "results": report(df) if len(df) else "no matured decisions yet"}
    json.dump(res, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(res, ensure_ascii=False, indent=1, default=str)[:3000])


if __name__ == "__main__":
    main()
