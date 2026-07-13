# -*- coding: utf-8 -*-
"""Global market indicators (Phase 30) — equities/crypto/FX/commodities/rates.

Real yfinance data only (batched download, cached to data/global_markets.json by
run.py). Deterministic interpretations from calculated changes — never invented.
Missing data → None (UI shows "אין נתון זמין").
"""
from datetime import datetime

import yfinance as yf

import config

# (symbol, Hebrew name, group). ^TNX quotes the 10Y yield ×10.
ASSETS = [
    ("^GSPC", "S&P 500", "equity"), ("^IXIC", "Nasdaq", "equity"),
    ("^DJI", "Dow Jones", "equity"), ("^RUT", "Russell 2000", "equity"),
    ("^VIX", "VIX", "equity"), ("^N225", "Nikkei", "equity"),
    ("^GDAXI", "DAX", "equity"), ("^FTSE", "FTSE", "equity"), ("^HSI", "Hang Seng", "equity"),
    ("BTC-USD", "ביטקוין", "crypto"), ("ETH-USD", "את'ריום", "crypto"),
    ("SOL-USD", "סולאנה", "crypto"), ("XRP-USD", "XRP", "crypto"),
    ("ILS=X", "דולר/שקל", "fx"), ("EURILS=X", "אירו/שקל", "fx"),
    ("GBPILS=X", "ליש\"ט/שקל", "fx"), ("EURUSD=X", "אירו/דולר", "fx"),
    ("GC=F", "זהב", "commodity"), ("SI=F", "כסף", "commodity"),
    ("CL=F", "נפט WTI", "commodity"), ("BZ=F", "ברנט", "commodity"),
    ("NG=F", "גז טבעי", "commodity"),
    ("^TNX", "תשואת אג\"ח 10 שנים", "rates"), ("2YY=F", "תשואת אג\"ח שנתיים", "rates"),
    ("DX-Y.NYB", "מדד הדולר DXY", "rates"),
]
STRIP = ["^GSPC", "^IXIC", "^VIX", "BTC-USD", "ETH-USD", "GC=F", "CL=F", "ILS=X", "DX-Y.NYB", "^TNX"]


def _ret(c, days):
    return round((float(c.iloc[-1]) / float(c.iloc[-1 - days]) - 1) * 100, 2) if len(c) > days else None


def trend_of(d30):
    if not isinstance(d30, (int, float)):
        return "—"
    return "עולה ↑" if d30 > 1 else ("יורדת ↓" if d30 < -1 else "יציבה →")


def interpret(symbol, d1, d30):
    """Deterministic one-liner for the key macro assets (real changes only)."""
    if symbol == "ILS=X" and isinstance(d1, (int, float)):
        return ("התחזקות הדולר מול השקל — לחץ על כוח הקנייה השקלי" if d1 >= 0.3 else
                "היחלשות הדולר מול השקל" if d1 <= -0.3 else "שער הדולר יציב")
    if symbol == "^VIX" and isinstance(d1, (int, float)):
        return ("ירידת VIX תומכת בסנטימנט Risk-On" if d1 <= -2 else
                "עליית VIX — עלייה בשנאת סיכון" if d1 >= 2 else "תנודתיות יציבה")
    if symbol == "^TNX" and isinstance(d30, (int, float)):
        return ("עליית תשואות — לחץ אפשרי על מניות צמיחה" if d30 >= 3 else
                "ירידת תשואות — רוח גבית לנכסי סיכון" if d30 <= -3 else "תשואות יציבות")
    if symbol == "BTC-USD" and isinstance(d30, (int, float)):
        return ("חוזק בקריפטו — תיאבון סיכון גבוה" if d30 >= 10 else
                "חולשה בקריפטו — ירידה בתיאבון הסיכון" if d30 <= -10 else "קריפטו מדשדש")
    if symbol == "GC=F" and isinstance(d30, (int, float)):
        return ("התחזקות זהב — התבצרות דפנסיבית" if d30 >= 5 else
                "היחלשות זהב — נכסי מגן נחלשים" if d30 <= -5 else "זהב יציב")
    return ""


def build() -> dict:
    """Fetch everything in one batch → structured artifact dict."""
    syms = [s for s, _, _ in ASSETS]
    try:
        data = yf.download(syms, period="3mo", auto_adjust=True, progress=False)["Close"]
    except Exception:
        return {"updated": datetime.now().strftime("%d/%m/%Y %H:%M"), "groups": {}, "strip": []}
    rows, by_sym = {}, {}
    for sym, name, grp in ASSETS:
        try:
            c = data[sym].dropna()
        except Exception:
            c = None
        if c is None or len(c) < 2:
            row = {"symbol": sym, "name": name, "price": None, "d1": None, "d7": None,
                   "d30": None, "trend": "—", "interp": "", "source": None}
            # Fallback to the independent secondary source where mapped (Step 0).
            try:
                import crosscheck
                sprice, _sd = crosscheck.fetch_stooq_close(sym)
                if sprice is not None:
                    row["price"] = round(sprice, 3 if "ILS" in sym or sym == "EURUSD=X" else 2)
                    row["source"] = "Stooq (גיבוי)"
            except Exception:
                pass
        else:
            scale = 0.1 if sym == "^TNX" else 1.0
            d1, d7, d30 = _ret(c, 1), _ret(c, 5), _ret(c, 21)
            row = {"symbol": sym, "name": name,
                   "price": round(float(c.iloc[-1]) * scale, 3 if "ILS" in sym or sym == "EURUSD=X" else 2),
                   "d1": d1, "d7": d7, "d30": d30,
                   "trend": trend_of(d30), "interp": interpret(sym, d1, d30),
                   "source": "Yahoo"}
        rows.setdefault(grp, []).append(row)
        by_sym[sym] = row
    # Yield curve 10Y-2Y (only from real values).
    t10, t2 = by_sym.get("^TNX", {}).get("price"), by_sym.get("2YY=F", {}).get("price")
    if isinstance(t10, (int, float)) and isinstance(t2, (int, float)):
        rows["rates"].append({"symbol": "CURVE", "name": "עקום 10ש-2ש", "price": round(t10 - t2, 2),
                              "d1": None, "d7": None, "d30": None,
                              "trend": "הפוך ⚠️" if t10 - t2 < 0 else "תקין",
                              "interp": "עקום הפוך — היסטורית איתות האטה" if t10 - t2 < 0 else ""})
    return {"updated": datetime.now().strftime("%d/%m/%Y %H:%M"), "groups": rows,
            "strip": [by_sym[s] for s in STRIP if s in by_sym]}
