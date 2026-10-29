# -*- coding: utf-8 -*-
"""Find a stock by what a person actually types: a ticker, an English company
name, or a Hebrew name ("אפל", "אנבידיה", "טבע").

Sources: assets/company_names.json (S&P 500 names, generated from Wikipedia),
a hand-kept Hebrew alias table (popular US names + Israeli companies listed in
the US), and any names already present in the daily scan rows.
"""
import json
import os
import re

_HERE = os.path.dirname(os.path.abspath(__file__))
_NAMES_PATH = os.path.join(_HERE, "assets", "company_names.json")

# Hebrew (and common colloquial) names → ticker.
HE_ALIASES = {
    "AAPL": ["אפל", "אייפון"], "MSFT": ["מיקרוסופט"], "NVDA": ["אנבידיה", "נבידיה", "אנוידיה"],
    "AMZN": ["אמזון"], "GOOGL": ["גוגל", "אלפבית"], "META": ["מטא", "פייסבוק"],
    "TSLA": ["טסלה"], "NFLX": ["נטפליקס"], "INTC": ["אינטל"], "AMD": ["איי אם די", "AMD"],
    "AVGO": ["ברודקום"], "QCOM": ["קוואלקום"], "CSCO": ["סיסקו"], "ORCL": ["אורקל"],
    "IBM": ["איי בי אם"], "CRM": ["סיילספורס"], "ADBE": ["אדובי"], "PYPL": ["פייפאל"],
    "UBER": ["אובר"], "ABNB": ["איירבנב"], "PLTR": ["פלנטיר"], "SHOP": ["שופיפיי"],
    "KO": ["קוקה קולה", "קוקה-קולה"], "PEP": ["פפסי", "פפסיקו"], "MCD": ["מקדונלדס"],
    "NKE": ["נייקי"], "DIS": ["דיסני"], "SBUX": ["סטארבקס"], "WMT": ["וולמארט"],
    "COST": ["קוסטקו"], "HD": ["הום דיפו"], "PG": ["פרוקטר אנד גמבל", "פרוקטר"],
    "V": ["ויזה"], "MA": ["מאסטרקארד"], "JPM": ["ג'יי פי מורגן", "גיי פי מורגן", "JP מורגן"],
    "BAC": ["בנק אוף אמריקה"], "GS": ["גולדמן זאקס", "גולדמן"], "BRK-B": ["ברקשייר", "באפט"],
    "PFE": ["פייזר", "פפייזר"], "JNJ": ["ג'ונסון אנד ג'ונסון", "גונסון"], "LLY": ["אלי לילי", "לילי"],
    "MRK": ["מרק"], "UNH": ["יונייטד הלת'", "יונייטד הלת"], "XOM": ["אקסון", "אקסון מוביל"],
    "CVX": ["שברון"], "BA": ["בואינג"], "CAT": ["קטרפילר"], "VZ": ["וריזון", "וורייזון"],
    "T": ["איי טי אנד טי"], "NOW": ["סרוויס נאו"], "ASML": ["אי אס אם אל"],
    # Israeli companies traded in the US
    "TEVA": ["טבע"], "CHKP": ["צ'ק פוינט", "צק פוינט", "צ׳ק פוינט"], "NICE": ["נייס"],
    "WIX": ["וויקס", "ויקס"], "MNDY": ["מאנדיי", "מנדיי"], "ESLT": ["אלביט", "אלביט מערכות"],
    "TSEM": ["טאואר"], "DOX": ["אמדוקס"], "MBLY": ["מובילאיי"], "GLBE": ["גלובל אי"],
    "FVRR": ["פייבר"], "INMD": ["אינמוד"], "SEDG": ["סולאראדג'", "סולאראדג"], "FROG": ["ג'יי פרוג", "גיי פרוג"],
    "LMND": ["למונייד", "לימונייד"], "ICL": ["כיל", "איי סי אל"], "NVMI": ["נובה"],
    "CAMT": ["קמטק"], "ORA": ["אורמת"], "CYBR": ["סייברארק"], "PAYO": ["פאיוניר"],
}

EXTRA_NAMES = {
    "TEVA": "Teva Pharmaceutical", "CHKP": "Check Point Software", "NICE": "NICE Ltd.",
    "WIX": "Wix.com", "MNDY": "monday.com", "ESLT": "Elbit Systems", "TSEM": "Tower Semiconductor",
    "DOX": "Amdocs", "MBLY": "Mobileye", "GLBE": "Global-e Online", "FVRR": "Fiverr",
    "INMD": "InMode", "SEDG": "SolarEdge", "FROG": "JFrog", "LMND": "Lemonade", "ICL": "ICL Group",
    "NVMI": "Nova Ltd.", "CAMT": "Camtek", "ORA": "Ormat Technologies", "CYBR": "CyberArk",
    "PAYO": "Payoneer", "ASML": "ASML Holding", "SHOP": "Shopify",
}

_TICKER_RE = re.compile(r"^[A-Za-z]{1,5}([.\-][A-Za-z])?$")


def _norm(s: str) -> str:
    s = str(s or "").strip().lower()
    s = s.replace("׳", "'").replace("’", "'").replace('"', "").replace("״", "")
    s = re.sub(r"[.,()]", " ", s)
    s = re.sub(r"\b(inc|corp|corporation|co|company|ltd|plc|holdings?|group|the|class [a-c])\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _load_names() -> dict:
    try:
        with open(_NAMES_PATH, encoding="utf-8") as fh:
            d = json.load(fh)
    except Exception:
        d = {}
    return {**d, **EXTRA_NAMES}


NAMES = _load_names()


def display_name(ticker: str, fallback: str | None = None) -> str:
    t = str(ticker or "").upper()
    return fallback or NAMES.get(t) or t


def search(query: str, extra_names: dict | None = None, limit: int = 6) -> list[dict]:
    """Ranked candidates [{ticker, name, match}] for free text. Exact ticker
    first, then Hebrew alias, then English name prefix/contains."""
    q = str(query or "").strip()
    if not q:
        return []
    names = {**NAMES, **{k: v for k, v in (extra_names or {}).items() if v}}
    nq = _norm(q)
    scored = {}

    def add(t, score, how):
        t = t.upper()
        if score > scored.get(t, (0, ""))[0]:
            scored[t] = (score, how)

    if _TICKER_RE.match(q):
        tq = q.upper().replace(".", "-")
        if tq in names or tq in HE_ALIASES:
            add(tq, 100, "סימול")
    for t, aliases in HE_ALIASES.items():
        for a in aliases:
            na = _norm(a)
            if nq == na:
                add(t, 95, "שם בעברית")
            elif len(nq) >= 2 and na.startswith(nq):
                add(t, 80, "שם בעברית")
            elif len(nq) >= 3 and nq in na:
                add(t, 60, "שם בעברית")
    for t, n in names.items():
        nn = _norm(n)
        if not nn:
            continue
        if nq == nn:
            add(t, 90, "שם החברה")
        elif len(nq) >= 2 and nn.startswith(nq):
            add(t, 75, "שם החברה")
        elif len(nq) >= 3 and re.search(r"\b" + re.escape(nq), nn):
            add(t, 65, "שם החברה")
        elif len(nq) >= 4 and nq in nn:
            add(t, 50, "שם החברה")
    ranked = sorted(scored.items(), key=lambda kv: (-kv[1][0], kv[0]))[:limit]
    return [{"ticker": t, "name": display_name(t, names.get(t)), "match": how} for t, (s, how) in ranked]


def resolve(query: str, extra_names: dict | None = None) -> str | None:
    """Best single ticker for the query, or the cleaned query itself when it
    looks like a ticker we don't know (the live lookup will validate it)."""
    hits = search(query, extra_names, limit=1)
    if hits:
        return hits[0]["ticker"]
    q = str(query or "").strip()
    return q.upper().replace(".", "-") if _TICKER_RE.match(q) else None
