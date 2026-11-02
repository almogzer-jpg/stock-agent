"""Old data is never shown as new: a banner when the update failed or the close is old."""
from datetime import date

from dashboard.v4 import home_data as H

MON = date(2026, 11, 2)


def test_old_close_is_flagged_and_a_normal_weekend_is_not():
    assert "לפני 4 ימים" in H.data_warning("29/10/2026", MON)          # Thursday's close on Monday
    assert H.data_warning("30/10/2026", MON) == ""                     # Friday's close on Monday


def test_a_failed_update_is_said_even_when_the_close_looks_recent():
    sync = {"files": ["events.json"], "failed": ["results.csv: HTTP Error 503", "universe.json: timed out"]}
    assert "לא הצלחנו לעדכן" in H.data_warning("30/10/2026", MON, sync)
    assert "לא הצלחנו לעדכן" in H.data_warning("30/10/2026", MON, {"files": [], "failed": ["x"]})
    assert H.data_warning("30/10/2026", MON, {"files": ["results.csv", "universe.json"], "failed": []}) == ""
