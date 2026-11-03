"""The refresh workflow's freshness check: current means the last finished US session."""
from datetime import date, datetime

from data_freshness import NY, state

# Trading days around Thanksgiving 2026 (Thursday 26/11 closed), as Yahoo lists them
SESSIONS = [date(2026, 11, d) for d in (19, 20, 23, 24, 25, 27, 30)]


def at(y, m, d, hh, mm):
    return datetime(y, m, d, hh, mm, tzinfo=NY)


def test_monday_morning_wants_fridays_close():
    s = state(date(2026, 11, 20), SESSIONS[:2], at(2026, 11, 23, 2, 0))
    assert s["state"] == "current" and s["last"] == date(2026, 11, 20)
    assert state(date(2026, 11, 19), SESSIONS[:2], at(2026, 11, 23, 2, 0))["state"] == "behind"


def test_a_us_holiday_is_not_a_missing_day():
    # Friday morning after Thanksgiving: Wednesday's close is the latest there is
    s = state(date(2026, 11, 25), SESSIONS[:5], at(2026, 11, 27, 1, 0))
    assert s["state"] == "current" and not s["missed"]


def test_no_scan_while_a_session_is_in_progress():
    assert state(date(2026, 11, 20), SESSIONS[:3], at(2026, 11, 23, 11, 0))["state"] == "open"
    # after the close the day counts as finished
    assert state(date(2026, 11, 20), SESSIONS[:3], at(2026, 11, 23, 17, 0))["state"] == "behind"


def test_a_whole_missed_day_is_flagged():
    s = state(date(2026, 11, 19), SESSIONS[:3], at(2026, 11, 24, 2, 0))
    assert s["state"] == "behind" and s["missed"]


def test_no_market_answer_is_unknown_not_current():
    assert state(date(2026, 11, 20), [], at(2026, 11, 23, 2, 0))["state"] == "unknown"
