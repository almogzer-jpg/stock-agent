# -*- coding: utf-8 -*-
"""Cross-source validation (Step 0 — reliability layer).

Validates our primary source (Yahoo/yfinance) against an independent free
source (Stooq, daily CSV endpoint) for a small set of high-importance series:
major indices and FX. Never blocks the pipeline: any network/parse failure
degrades to status "not_completed" — shown to the user as
"אימות-צולב לא הושלם", never silently treated as verified.

Pure parsing/compare logic is separated from network for unit-testing.
"""
import csv
import io
import urllib.parse
import urllib.request

# Yahoo symbol → Stooq symbol (only series Stooq serves reliably for free).
STOOQ_MAP = {
    "^GSPC": "^spx",
    "^DJI": "^dji",
    "ILS=X": "usdils",
    "EURUSD=X": "eurusd",
}
# Yahoo symbol → ECB (Frankfurter) currency pair — official central-bank fixing.
ECB_MAP = {
    "ILS=X": ("USD", "ILS"),
    "EURUSD=X": ("EUR", "USD"),
}
TOLERANCE_PCT = 1.0          # |diff| above this = material disagreement
ECB_TOLERANCE_PCT = 1.5      # ECB daily fixing vs live market rate — wider window
TIMEOUT_S = 8
_HDRS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json,text/csv;q=0.9,*/*;q=0.8"}


def _stooq_url(sym: str) -> str:
    return f"https://stooq.com/q/l/?s={urllib.parse.quote(sym)}&f=sd2t2ohlcv&h&e=csv"


def parse_stooq_csv(text: str):
    """Parse Stooq single-quote CSV → (close, date_str) or (None, None)."""
    try:
        rows = list(csv.DictReader(io.StringIO(text)))
        if not rows:
            return None, None
        r = rows[0]
        close = r.get("Close")
        if close in (None, "", "N/D"):
            return None, None
        return float(close), r.get("Date")
    except Exception:
        return None, None


def fetch_stooq_close(yahoo_sym: str):
    """Live fetch of the Stooq close for a Yahoo symbol. None on any failure."""
    ssym = STOOQ_MAP.get(yahoo_sym)
    if not ssym:
        return None, None
    try:
        req = urllib.request.Request(_stooq_url(ssym), headers=_HDRS)
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            return parse_stooq_csv(resp.read().decode("utf-8", "replace"))
    except Exception:
        return None, None


def fetch_ecb_rate(yahoo_sym: str):
    """Official ECB fixing via the free Frankfurter API. None on any failure."""
    pair = ECB_MAP.get(yahoo_sym)
    if not pair:
        return None, None
    try:
        import json as _json
        url = f"https://api.frankfurter.app/latest?from={pair[0]}&to={pair[1]}"
        req = urllib.request.Request(url, headers=_HDRS)
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            d = _json.load(resp)
        rate = (d.get("rates") or {}).get(pair[1])
        return (float(rate), d.get("date")) if rate else (None, None)
    except Exception:
        return None, None


def compare(yahoo_price, stooq_price, tolerance_pct=TOLERANCE_PCT):
    """Pure compare → dict {diff_pct, agree} or None when not comparable."""
    if not isinstance(yahoo_price, (int, float)) or not isinstance(stooq_price, (int, float)):
        return None
    if stooq_price <= 0:
        return None
    diff = (yahoo_price / stooq_price - 1) * 100
    return {"diff_pct": round(diff, 2), "agree": abs(diff) <= tolerance_pct}


def run_crosscheck(global_rows_by_symbol: dict) -> dict:
    """Cross-validate the mapped symbols against Stooq.

    global_rows_by_symbol: {yahoo_symbol: row} from globalmkt (needs row["price"]).
    Returns a report — status: ok / disagreement / not_completed.
    """
    checks, fetched = [], 0
    for ysym in set(STOOQ_MAP) | set(ECB_MAP):
        row = global_rows_by_symbol.get(ysym) or {}
        yprice = row.get("price")
        # Prefer the official ECB fixing for FX; Stooq for indices (best-effort).
        sec_name, tol = None, TOLERANCE_PCT
        sprice, sdate = (None, None)
        if ysym in ECB_MAP:
            sprice, sdate = fetch_ecb_rate(ysym)
            if sprice is not None:
                sec_name, tol = "ECB", ECB_TOLERANCE_PCT
        if sprice is None and ysym in STOOQ_MAP:
            sprice, sdate = fetch_stooq_close(ysym)
            if sprice is not None:
                sec_name = "Stooq"
        if sprice is not None:
            fetched += 1
        cmpres = compare(yprice, sprice, tolerance_pct=tol)
        checks.append({"symbol": ysym, "name": row.get("name", ysym),
                       "yahoo": yprice, "stooq": sprice, "stooq_date": sdate,
                       "secondary": sec_name,
                       "diff_pct": cmpres["diff_pct"] if cmpres else None,
                       "agree": cmpres["agree"] if cmpres else None})
    compared = [c for c in checks if c["agree"] is not None]
    if not compared:
        status = "not_completed"
    elif all(c["agree"] for c in compared):
        status = "ok"
    else:
        status = "disagreement"
    return {"status": status, "secondary_source": "ECB (מט\"ח) + Stooq (מדדים, מיטב-מאמץ)",
            "tolerance_pct": TOLERANCE_PCT, "fetched": fetched,
            "compared": len(compared), "checks": checks}
