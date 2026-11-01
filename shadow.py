# -*- coding: utf-8 -*-
"""Shadow run of the four-dimension engine (verdict4.py).

Every scanner run: refresh a slice of the company profiles, compute the new verdict
for every stock in the universe next to the live verdict, and record both with
the price of the day. Nothing here is displayed. research/shadow_eval.py later
measures what actually happened after each decision, for both engines, so the
switch is decided on outcomes and not on how many buys each engine gives.

Outputs (committed by the daily bot):
    data/shadow_verdicts.json   latest snapshot, full detail per stock
    data/shadow_log.jsonl       one compact line per stock per day (re-runs replace the day)
"""
import json
import os
import sys
from collections import Counter
from datetime import date

import config
import market
import stockdata
import verdict4 as V4
from fundamentals import profiles as prof


def _profile_age(p):
    try:
        return (date.today() - date.fromisoformat((p or {}).get("_date", ""))).days
    except ValueError:
        return None


def _log_line(t, row, live, v, p):
    d = v["dimensions"]
    return {"d": row.get("Date"), "t": t, "s": (p or {}).get("sector"), "pa": _profile_age(p),
            "px": v["price"], "live": live.get("action"),
            "live_q": live.get("quality"), "new": v["action"], "why": v["reason"],
            "q": d["quality"]["score"], "p": d["price"]["key"], "ps": d["price"]["score"],
            "up": d["price"]["upside"], "tm": d["timing"]["key"], "r": d["risk"]["level"],
            "rel": v["reliability"]["score"], "tier": row.get("_tier")}


def run(sector_scores: dict | None = None, refresh: bool = True) -> dict:
    """Compute and record the shadow verdicts. Returns a short summary."""
    rows = stockdata.load_rows()
    tickers = sorted(rows)
    profiles = prof.refresh(tickers) if refresh else prof.load()
    if sector_scores is None:
        try:
            sector_scores = {s["sector"]: s["score"] for s in market.sector_intelligence()}
        except Exception:
            sector_scores = {}
    ctx = V4.context({t: profiles[t] for t in tickers if t in profiles})
    live = stockdata.verdicts(rows)

    snap, lines, broken = {}, [], {}
    for t in tickers:
        row, p = rows[t], profiles.get(t)
        sec = sector_scores.get(market.SECTOR_EN_TO_HE.get((p or {}).get("sector"), ""), None)
        v = V4.decide(t, row, p, ctx, sector_score=sec, days_to_earnings=row.get("DaysToEarnings"))
        problems = V4.consistency(v) if v["action"] != "nodata" else []
        if problems:
            broken[t] = problems
        snap[t] = {**v, "live": {k: live[t].get(k) for k in ("action", "label", "quality", "why")}}
        lines.append(_log_line(t, row, live[t], v, p))

    day = next((r.get("Date") for r in rows.values() if r.get("Date")), None)
    summary = {"date": day, "stocks": len(tickers), "profiles": sum(1 for t in tickers if t in profiles),
               "new": dict(Counter(v["action"] for v in snap.values())),
               "live": dict(Counter(v["live"]["action"] for v in snap.values())),
               "inconsistent": broken, "median_analyst_upside": round(ctx["median_upside"], 1)}
    with open(config.SHADOW_JSON, "w", encoding="utf-8") as fh:
        json.dump({"summary": summary, "verdicts": snap}, fh, ensure_ascii=False, separators=(",", ":"))

    kept = []
    if os.path.exists(config.SHADOW_LOG):
        with open(config.SHADOW_LOG, encoding="utf-8") as fh:
            kept = [ln for ln in fh if ln.strip() and json.loads(ln).get("d") != day]
    with open(config.SHADOW_LOG, "w", encoding="utf-8") as fh:
        fh.writelines(kept)
        for ln in lines:
            fh.write(json.dumps(ln, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(f"מנוע ארבעת הממדים (צל): {summary['new']} · המנוע החי: {summary['live']}"
          f" · חוסר עקביות: {len(broken)}")
    _weekly_eval()
    return summary


def _weekly_eval():
    """Re-measure outcomes once a week (data/shadow_eval.json). Never fails the run."""
    try:
        with open(config.SHADOW_EVAL, encoding="utf-8") as fh:
            last = json.load(fh).get("as_of")
        d, m, y = (int(x) for x in last.split("/"))
        if (date.today() - date(y, m, d)).days < config.SHADOW_EVAL_EVERY_DAYS:
            return
    except Exception:
        pass                                    # missing or unreadable: measure now
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "research"))
        import shadow_eval
        res = shadow_eval.evaluate(out_path=config.SHADOW_EVAL)
        print("מדידת תוצאות המנוע החדש:", " ".join(res["headline"]))
    except Exception as exc:
        print(f"  ! מדידת התוצאות לא רצה: {exc}")


if __name__ == "__main__":
    import sys
    run(refresh="--no-refresh" not in sys.argv)
