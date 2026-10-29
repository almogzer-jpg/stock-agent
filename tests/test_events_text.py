# -*- coding: utf-8 -*-
"""Plain-Hebrew event wording + deep-dive fallbacks (no network)."""
import deepdive as dd
from events import days_phrase, grade_he, rating_action_he
import fundamentals.fundamentals as F


def test_days_phrase():
    assert days_phrase(0) == "היום"
    assert days_phrase(1) == "מחר"
    assert days_phrase(5) == "בעוד 5 ימים"
    assert days_phrase(None) == ""


def test_rating_actions_are_hebrew():
    assert grade_he("Overweight") == "משקל-יתר"
    assert grade_he("Some New Grade") == "Some New Grade"        # unknown → kept, never invented
    assert rating_action_he("reit", "Buy", "Buy") == "אישרור דירוג: קנייה"
    assert rating_action_he("main", "Neutral", "Neutral") == "אישרור דירוג: ניטרלי"
    assert rating_action_he("down", "Outperform", "Peer Perform") == "הורדת דירוג: תשואת-יתר ← תשואת-שוק"
    assert rating_action_he("init", "", "Outperform") == "כיסוי חדש: תשואת-יתר"
    # keywords other modules match on stay intact
    assert "שדרוג" in rating_action_he("up", "Hold", "Buy")
    assert "הורדת" in rating_action_he("down", "Buy", "Hold")


def test_overview_line_never_dangling():
    assert dd.he_overview_line("AAPL", dd.NA, None, dd.NA) == "AAPL — פרטי הפעילות של החברה אינם זמינים כרגע."
    assert dd.he_overview_line("Apple", "טכנולוגיה", None, None) == "Apple פועלת בסקטור טכנולוגיה."


def test_daily_snapshot_reads_results_with_english_keys():
    snap = dd.daily_snapshot("AAPL")
    if snap:                                   # artifact present in the repo checkout
        assert snap["Ticker"] == "AAPL" and isinstance(snap.get("Name"), str)
        assert not any(isinstance(v, float) and v != v for v in snap.values())   # no NaN
    assert dd.daily_snapshot("NOSUCHTICKER") == {}


def test_failed_fundamentals_pull_is_not_cached(monkeypatch):
    monkeypatch.setattr(F, "_fetch_raw", lambda s: {k: None for k in F.FIELDS})
    monkeypatch.setattr(F, "_save_cache", lambda c: None)
    F._CACHE.pop("ZZZT", None)
    F.get_fundamentals("ZZZT")
    assert "ZZZT" not in F._CACHE
