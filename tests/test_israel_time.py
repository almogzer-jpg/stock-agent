"""Times and "today" on screen are Israel time, summer and winter, not the server clock."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import config


def test_now_local_is_israel_time():
    now = config.now_local()
    assert now.tzinfo is not None and now.utcoffset().total_seconds() in (7200, 10800)


def test_summer_and_winter_offsets():
    tz = ZoneInfo(config.TIMEZONE)
    assert datetime(2026, 7, 1, 9, 0, tzinfo=timezone.utc).astimezone(tz).strftime("%H:%M") == "12:00"
    assert datetime(2026, 11, 2, 9, 0, tzinfo=timezone.utc).astimezone(tz).strftime("%H:%M") == "11:00"


def test_screens_do_not_read_the_server_clock():
    import pathlib
    for f in pathlib.Path("dashboard/v4").glob("*.py"):
        s = f.read_text(encoding="utf-8")
        assert "date.today()" not in s and "datetime.now()" not in s, f.name
