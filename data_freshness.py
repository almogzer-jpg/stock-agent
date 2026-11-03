# -*- coding: utf-8 -*-
"""Is the data on screen current? Used by the daily refresh workflow.

Current means the close the screens show (read the same way the app reads it)
is the last US trading session that has finished. The finished sessions come
from the market itself (SPY daily bars from Yahoo), so weekends, US holidays
and other days without trading need no calendar of our own.

    python data_freshness.py     prints the state and, on GitHub Actions, writes it
                                 to the step outputs (state, close, last, missed)

States: current, behind, open (a US session is in progress, so a scan now would
store part of a day as a close) and unknown (the market could not be reached).
Read only: it never changes the data or the engine.
"""
import os
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
OPEN, DONE = time(9, 30), time(16, 30)        # the daily bar is final a little after the 16:00 close


def data_close() -> date | None:
    """The close date the screens show (as dashboard/v4/shell.load reads it)."""
    import stockdata
    rows = stockdata.load_rows()
    close = next((r.get("Date") for r in rows.values() if r.get("Date")), None)
    try:
        return datetime.strptime(str(close), "%d/%m/%Y").date()
    except ValueError:
        return None


def market_sessions() -> list[date]:
    import yfinance as yf
    h = yf.Ticker("SPY").history(period="15d", interval="1d", auto_adjust=False)
    return sorted({d.date() for d in h.index})


def state(close: date | None, sessions: list[date], now_ny: datetime) -> dict:
    """The decision, from the shown close, the market's session dates and New York time."""
    today = now_ny.date()
    in_session = today in sessions and OPEN <= now_ny.time() < DONE
    done = [d for d in sessions if d < today or (d == today and now_ny.time() >= DONE)]
    last = done[-1] if done else None
    prev = done[-2] if len(done) > 1 else None
    if in_session:
        s = "open"
    elif close is None or last is None:
        s = "unknown"
    else:
        s = "current" if close >= last else "behind"
    # A whole trading day went by without an update (every slot of a day was missed)
    missed = bool(close and prev and close < prev)
    return {"state": s, "close": close, "last": last, "missed": missed}


def main() -> int:
    close = data_close()
    try:
        sessions = market_sessions()
    except Exception:
        sessions = []
    res = state(close, sessions, datetime.now(NY))
    fmt = lambda d: d.strftime("%d/%m/%Y") if d else "-"
    print(f"state={res['state']} close={fmt(res['close'])} last finished session={fmt(res['last'])}"
          f" missed={res['missed']}")
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(f"state={res['state']}\nclose={fmt(res['close'])}\nlast={fmt(res['last'])}\n"
                     f"missed={int(res['missed'])}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
