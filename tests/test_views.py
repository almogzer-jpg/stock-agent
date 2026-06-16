# -*- coding: utf-8 -*-
"""Opportunities / Sector view helpers (presentation shaping over artifacts)."""
import dashboard.views as v

UNI = {
    "rankings": {"opportunities": ["DOV", "TRV", "EMR"], "momentum": ["ARM", "DOV"]},
    "opportunities": [
        {"Ticker": "DOV", "Name": "Dover Corporation", "Sector": "Industrials", "ScoreV2": 84, "RiskLevel": "נמוך"},
        {"Ticker": "TRV", "Name": "The Travelers Companies", "Sector": "Financial Services", "ScoreV2": 78, "RiskLevel": "בינוני"},
        {"Ticker": "EMR", "Name": "Emerson Electric", "Sector": "Industrials", "ScoreV2": 72, "RiskLevel": "נמוך"},
    ],
    "all": [
        {"Ticker": "ARM", "ScoreV2": 60, "RiskLevel": "גבוה"},
        {"Ticker": "DOV", "ScoreV2": 84, "RiskLevel": "נמוך"},
    ],
}
MKT = {"sectors": [{"sector": "תעשייה", "score": 72, "momentum": 46, "rs": 1.65},
                   {"sector": "פיננסים", "score": 66, "momentum": 58, "rs": 4.78}]}


def test_ranking_rows_full_fields():
    rows = v.ranking_rows(UNI, "opportunities", nc={})
    assert rows[0] == {"ticker": "DOV", "name": "Dover Corporation",
                       "sector": "Industrials", "score_v2": 84, "risk": "נמוך"}


def test_name_fallback_cache_then_unknown():
    rows = v.ranking_rows(UNI, "momentum", nc={"ARM": "Arm Holdings"})
    arm = next(r for r in rows if r["ticker"] == "ARM")
    assert arm["name"] == "Arm Holdings"          # from cache (not enriched)
    bare = v.ranking_rows({"rankings": {"x": ["ZZZ"]}, "all": [], "opportunities": []}, "x", nc={})
    assert bare[0]["name"] == "Unknown Company"   # nothing known → never blank


def test_badges_and_bands():
    assert v.risk_badge("נמוך")[2] == "Low Risk" and v.risk_badge("גבוה מאוד")[2] == "Very High Risk"
    assert v.score_band_color(85) == "#22c55e" and v.score_band_color(30) == "#ef4444"
    assert v.momentum_emoji(229) == "🚀" and v.momentum_emoji(-15) == "📉" and v.momentum_emoji(5) == "➡️"


def test_kpi_highlights():
    h = v.kpi_highlights(UNI, MKT)
    assert h["high_score"]["Ticker"] == "DOV"        # ScoreV2 84
    assert h["strongest"]["sector"] == "Industrials"  # highest sector score


def test_sector_intel_aggregates():
    rows = v.sector_intel(UNI, MKT)
    ind = next(r for r in rows if r["sector"] == "Industrials")
    assert ind["n"] == 2 and ind["top"] == "DOV" and ind["avg_score"] == 78
    assert ind["momentum"] == 46 and ind["reco"] in ("Overweight", "Neutral", "Underweight")
    assert rows[0]["rank"] == 1                   # ranked by sector score desc


def test_sector_summary_headlines():
    s = v.sector_summary(v.sector_intel(UNI, MKT))
    assert s["most"]["sector"] == "Industrials"   # 2 opportunities
    assert s["strongest"]["sector_score"] >= s["weakest"]["sector_score"]
    assert s["best_avg"]["avg_score"] >= 78
