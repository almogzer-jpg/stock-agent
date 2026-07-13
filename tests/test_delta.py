# -*- coding: utf-8 -*-
"""Delta Engine (Morning Terminal) — pure diff/classify/action logic."""
import delta as dl


def _snap(date, **tickers):
    return {"date": date, "tickers": tickers}


def test_diff_scores_with_causes():
    prev = _snap("10/07/2026",
                 AAA={"ScoreV2": 75, "Price": 100.0, "RiskLevel": "נמוך",
                      "ContribFund": 28.0, "ContribNews": 5.0, "Name": "A"},
                 GONE={"ScoreV2": 50, "Price": 10.0})
    cur = _snap("13/07/2026",
                AAA={"ScoreV2": 68, "Price": 99.0, "RiskLevel": "בינוני",
                     "ContribFund": 28.0, "ContribNews": 0.0, "Name": "A", "Group": "watch"},
                NEW={"ScoreV2": 80, "Price": 50.0})
    d = dl.diff_scores(prev, cur)
    assert d["available"] and d["new"] == ["NEW"] and d["removed"] == ["GONE"]
    it = next(x for x in d["items"] if x["ticker"] == "AAA")
    assert any("75→68" in c for c in it["changes"])            # score change shown
    assert any("חדשות -5.0" in c for c in it["causes"])        # measurable cause
    assert any("סיכון" in c for c in it["changes"])            # risk level change
    # no snapshots → honest unavailable
    assert dl.diff_scores(None, cur)["available"] is False


def test_breakout_and_materiality_ranking():
    prev = _snap("a", X={"ScoreV2": 60, "Breakout": False, "Price": 10.0},
                 Y={"ScoreV2": 60, "Price": 10.0})
    cur = _snap("b", X={"ScoreV2": 61, "Breakout": True, "Price": 10.0},
                Y={"ScoreV2": 64, "Price": 10.0, "ContribFund": 0.0})
    d = dl.diff_scores(prev, cur)
    assert d["items"][0]["ticker"] == "X"                      # breakout outranks +4 score
    assert any("פריצה" in c for c in d["items"][0]["changes"])


def test_action_mapping():
    assert dl.action_for(80, "positive", 2)["icon"] == "📈"
    assert dl.action_for(60, "watch", 10)["icon"] == "🔍"
    assert dl.action_for(60, "watch", -9)["icon"] == "⚠️"
    assert dl.action_for(40, "avoid", 0)["icon"] == "❌"
    assert dl.action_for(70, "positive", 1)["icon"] == "⭐"
    assert dl.action_for(50, "watch", 0)["icon"] == "⏳"


def test_environment_classifier():
    env = dl.classify_environment({"score": 82}, {"price": 13.0}, {"above50": 70},
                                  [{"sector": "טכנולוגיה"}, {"sector": "פיננסים"}])
    assert "Risk-On" in env["labels"] and "תנודתיות נמוכה" in env["labels"]
    assert any("VIX" in w for w in env["why"])
    env2 = dl.classify_environment({"score": 30}, {"price": 31.0}, {},
                                   [{"sector": "שירותים ציבוריים"}, {"sector": "בריאות"}])
    assert "Risk-Off" in env2["labels"] and "תנודתיות גבוהה" in env2["labels"]
    assert "רוטציה דפנסיבית" in env2["labels"]


def test_asset_flows_labeled_trends():
    g = {"equity": [{"symbol": "^GSPC", "d30": 5.0}, {"symbol": "^N225", "d30": -4.0}],
         "crypto": [{"symbol": "BTC-USD", "d30": 12.0}],
         "commodity": [{"symbol": "GC=F", "d30": 1.0}]}
    rows = dl.asset_flows(g)
    by = {r["asset"]: r for r in rows}
    assert "↑" in by["קריפטו"]["trend"] and "↓" in by["מניות בינלאומיות"]["trend"]
    assert "→" in by["זהב (מגן)"]["trend"]
