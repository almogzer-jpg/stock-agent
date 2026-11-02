# -*- coding: utf-8 -*-
"""V4 application shell: data, navigation, theme and level of detail.

Navigation uses Streamlit's own pages (st.navigation, hidden) with custom
links, so moving between screens keeps the session: the theme, the level of
detail (פשוט / מתקדם) and the open stock survive every switch. The two
preferences are also kept in the visitor's browser (dashboard.localstore).
"""
import os
import subprocess
import sys
import time
from datetime import date

import streamlit as st

import config
from dashboard import localstore as ls
from dashboard.v4 import css, ui

PREFS_DEFAULT = {"theme": "light", "mode": "simple", "howto_hidden": False}
MODES = {"simple": "פשוט", "pro": "מתקדם"}
THEMES = {"light": "בהיר", "dark": "כהה"}


# ------------------------------------------------------------------ data
def _read_json(path, default):
    import json
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


@st.cache_data(ttl=120, show_spinner=False)
def load():
    """Everything the screens read, from the precomputed artifacts. Verdicts are
    the LIVE engine's (stockdata.verdicts), the same ones every screen shows."""
    import globalmkt
    import stockdata
    rows = stockdata.load_rows()
    close = next((r.get("Date") for r in rows.values() if r.get("Date")), None)
    # Scans before 01/11/2026 did not store when the business data was fetched.
    # Where the local cache knows it, use that, so the age is shown and not guessed.
    from datetime import date as _d
    cache = _read_json(config.FUNDAMENTALS_CACHE, {})
    for t, r in rows.items():
        if r.get("_tier") in ("full", "enriched") and not r.get("FundDate") and (cache.get(t) or {}).get("_date"):
            try:
                r["FundDate"] = _d.fromisoformat(cache[t]["_date"]).strftime("%d/%m/%Y")
            except ValueError:
                pass
    return {
        "rows": rows, "vmap": stockdata.verdicts(rows), "close": close or "—",
        "mkt": _read_json(config.MARKET_JSON, {}),
        "global": globalmkt.check(_read_json(config.GLOBAL_JSON, {})),
        "events": _read_json(config.EVENTS_JSON, {}),
        "rel": _read_json(os.path.join(config.DATA_DIR, "reliability.json"), {}),
    }


@st.cache_data(ttl=600, show_spinner=False)
def _profiles() -> dict:
    """Stored company facts (Yahoo statements and ratios, refreshed by the daily bot).
    Raw data only: no conclusion of any engine is read from here."""
    return _read_json(config.PROFILES_JSON, {})


@st.cache_data(ttl=1800, show_spinner=False)
def _live_profile(t: str):
    from fundamentals.profiles import fetch_profile
    try:
        return fetch_profile(t)
    except Exception:
        return None


def profile(t: str) -> dict:
    """The company's stored profile, or one fetched now when it is missing."""
    return _profiles().get(t) or _live_profile(t) or {}


@st.cache_data(ttl=1800, show_spinner=False)
def company_live(t: str) -> dict:
    """Price history and the business description, fetched live (Yahoo), with a
    time limit so a slow answer never freezes the page. Anything missing stays missing."""
    from concurrent.futures import ThreadPoolExecutor
    from datetime import datetime

    def _fetch():
        import yfinance as yf
        tk = yf.Ticker(t)
        out = {"hist": None, "info": {}}
        try:
            h = tk.history(period="5y", auto_adjust=True)
            if h is not None and len(h) and "Close" in h:
                h = h[["Close"]].dropna()
                h.index = h.index.tz_localize(None) if getattr(h.index, "tz", None) else h.index
                out["hist"] = h
        except Exception:
            pass
        try:
            info = tk.info or {}
            keep = ("longName", "shortName", "longBusinessSummary", "industry", "sector", "country",
                    "fullTimeEmployees", "website")
            out["info"] = {k: info.get(k) for k in keep if info.get(k)}
        except Exception:
            pass
        if out["info"].get("longBusinessSummary"):
            from deepdive import translate_he
            out["info"]["summary_he"] = translate_he(out["info"]["longBusinessSummary"])
        return out

    ex = ThreadPoolExecutor(max_workers=1)
    try:
        res = ex.submit(_fetch).result(timeout=25)
    except Exception:
        res = {"hist": None, "info": {}}
    finally:
        ex.shutdown(wait=False)
    res["ok"] = res.get("hist") is not None
    res["fetched"] = datetime.now().strftime("%d/%m/%Y %H:%M") if res["ok"] else None
    return res


@st.cache_data(ttl=1800, show_spinner=False)
def market_history(symbols: tuple) -> dict:
    """Two years of daily closes for the given symbols (Yahoo), with a time limit.
    Checked against the validated daily values before anything is shown."""
    from concurrent.futures import ThreadPoolExecutor

    def _fetch():
        import yfinance as yf
        df = yf.download(list(symbols), period="2y", auto_adjust=True, progress=False, threads=True)
        close = df["Close"] if "Close" in df else df
        out = {}
        for s in symbols:
            if s in getattr(close, "columns", []):
                col = close[s].dropna()
                col.index = col.index.tz_localize(None) if getattr(col.index, "tz", None) else col.index
                out[s] = col
        return out

    ex = ThreadPoolExecutor(max_workers=1)
    try:
        return ex.submit(_fetch).result(timeout=30)
    except Exception:
        return {}
    finally:
        ex.shutdown(wait=False)


def _sync_browser():
    """Read the visitor's stored display preferences once per run.

    Owner decision 01/11/2026: no personal lists in V4 until visitors can sign in.
    V4 never reads or writes the browser slot that holds the old list, and the slot is
    left as it is, so nothing saved before is lost."""
    stored = ls.sync("v4prefs", default=None)
    if stored is not None and "v4_prefs" not in st.session_state:
        st.session_state["v4_prefs"] = {**PREFS_DEFAULT, **stored}


def prefs() -> dict:
    return st.session_state.get("v4_prefs") or dict(PREFS_DEFAULT)


def set_pref(key, value):
    p = {**prefs(), key: value}
    st.session_state["v4_prefs"] = p
    ls.put("v4prefs", p)


def reset_prefs():
    """Display preferences back to the defaults. Touches only the preferences slot.
    The switches are recreated under new keys: an existing switch would send its old
    value back on the next run and undo the reset."""
    st.session_state["v4_prefs"] = dict(PREFS_DEFAULT)
    st.session_state["v4_ctl_gen"] = st.session_state.get("v4_ctl_gen", 0) + 1
    ls.put("v4prefs", dict(PREFS_DEFAULT))


def _ctl(key: str) -> str:
    return f"{key}-{st.session_state.get('v4_ctl_gen', 0)}"


# ------------------------------------------------------------------ controls
def mode_control(page_key: str):
    """The level-of-detail switch. One widget per page, one shared preference."""
    cur = prefs()["mode"]
    key = _ctl(f"v4mode_{page_key}")

    def _changed():
        val = st.session_state.get(key)
        if val:
            set_pref("mode", {v: k for k, v in MODES.items()}[val])

    st.session_state[key] = MODES[cur]                        # always shows the current preference
    st.segmented_control("רמת פירוט", list(MODES.values()), key=key,
                         on_change=_changed, required=True, label_visibility="collapsed")


def theme_control(key: str):
    cur = prefs()["theme"]
    key = _ctl(key)

    def _changed():
        val = st.session_state.get(key)
        if val:
            set_pref("theme", {v: k for k, v in THEMES.items()}[val])

    st.session_state[key] = THEMES[cur]                       # stored preference may arrive after the first run
    st.segmented_control("ערכת צבעים", list(THEMES.values()), key=key,
                         on_change=_changed, required=True, label_visibility="collapsed")


def header(page_key: str, title: str, sub: str, mode: bool = True):
    """Page title and subtitle, with the detail switch where the page has detail to switch."""
    with st.container(key="v4head"):
        a, b = st.columns([3, 1], vertical_alignment="bottom")
        with a:
            st.html(ui.page_head(title, sub))
        with b:
            if mode:
                with st.container(horizontal=True, horizontal_alignment="left"):
                    mode_control(page_key)


# ------------------------------------------------------------------ shell
def _first_run():
    """No data yet (fresh cloud container): run the pipeline once, showing a loading state."""
    if os.path.exists(config.RESULTS_CSV):
        return
    st.html(ui.page_head("טוען נתונים", "סריקה ראשונה, בדרך כלל פחות מדקה"))
    st.html(ui.skeleton_cards(3))
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    try:
        subprocess.run([sys.executable, "run.py"], cwd=root, timeout=300, capture_output=True,
                       env=dict(os.environ, STOCK_AGENT_DISABLE_EMAIL="1", PYTHONUTF8="1"))
    except Exception:
        pass
    if not os.path.exists(config.RESULTS_CSV):
        st.html(ui.error("הנתונים לא נטענו", "הסריקה הראשונה לא הצליחה. נסו לרענן את הדף בעוד דקה."))
        st.stop()
    st.cache_data.clear()
    st.rerun()


def _html_banner(msg: str):
    if msg:
        st.html(ui.data_banner(msg))


def main():
    from dashboard.v4 import pages as P

    _sync_browser()
    st.html(css.build(prefs()["theme"]))
    _first_run()

    nav = {
        "home": st.Page(P.home, title="היום", icon=":material/home:", url_path="today", default=True),
        "opps": st.Page(P.opportunities, title="הזדמנויות", icon=":material/target:", url_path="opportunities"),
        "company": st.Page(P.company, title="ניתוח חברה", icon=":material/bar_chart:", url_path="company"),
        "markets": st.Page(P.markets, title="שווקים", icon=":material/public:", url_path="markets"),
        "alerts": st.Page(P.alerts, title="התראות", icon=":material/notifications:", url_path="alerts"),
        "glossary": st.Page(P.glossary, title="מילון מונחים", icon=":material/help:", url_path="glossary"),
        "settings": st.Page(P.settings, title="הגדרות", icon=":material/settings:", url_path="settings"),
    }
    st.session_state["v4_pages"] = nav
    current = st.navigation(list(nav.values()), position="hidden")
    cur_key = next((k for k, p in nav.items() if p.url_path == current.url_path), "home")

    goto = st.session_state.pop("v4_goto", None)
    if goto:
        st.switch_page(nav["company"], query_params={"t": goto})

    # Desktop: side navigation.
    with st.sidebar:
        st.html(ui.brand())

        def _search():
            q = (st.session_state.get("v4q") or "").strip()
            if q:
                import company_search
                t = company_search.resolve(q) or q.upper()
                st.session_state["v4_goto"] = t
                st.session_state["v4q"] = ""

        st.text_input("חיפוש חברה", key="v4q", placeholder="חיפוש חברה או סימול", on_change=_search,
                      label_visibility="collapsed")
        for k in ("home", "opps", "company", "markets", "alerts"):
            with st.container(key=f"v4on-{k}" if k == cur_key else f"v4nav-{k}"):
                st.page_link(nav[k], label=nav[k].title, icon=nav[k].icon)
        with st.container(key="v4sidefoot"):
            for k in ("glossary", "settings"):
                with st.container(key=f"v4on-{k}" if k == cur_key else f"v4nav-{k}"):
                    st.page_link(nav[k], label=nav[k].title, icon=nav[k].icon)
            theme_control("v4theme_side")

    # Phone: top app bar (brand, search, help).
    with st.container(key="v4appbar", horizontal=True, vertical_alignment="center"):
        st.html(ui.brand().replace("v4-brand", "v4-brand v4-brand-bar"))
        with st.container(horizontal=True, horizontal_alignment="left", gap=None):
            st.page_link(nav["company"], label="חיפוש", icon=":material/search:")
            st.page_link(nav["alerts"], label="התראות", icon=":material/notifications:")
            st.page_link(nav["glossary"], label="הסבר", icon=":material/help:")

    from dashboard.v4 import home_data as H
    _html_banner(H.data_warning(load()["close"], date.today()))
    current.run()

    # Phone: bottom tab bar.
    tabs = (("home", "היום", ":material/home:"), ("opps", "הזדמנויות", ":material/target:"),
            ("company", "חיפוש", ":material/search:"), ("markets", "שווקים", ":material/public:"),
            ("settings", "עוד", ":material/menu:"))
    with st.container(key="v4tabbar", horizontal=True, gap=None):
        for k, label, ic in tabs:
            with st.container(key=f"v4tab-on-{k}" if k == cur_key else f"v4tab-{k}"):
                st.page_link(nav[k], label=label, icon=ic)
