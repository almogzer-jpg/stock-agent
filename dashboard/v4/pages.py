# -*- coding: utf-8 -*-
"""V4 screens. Home is the first screen built; the rest follow after the owner
approves it, and until then show a clear placeholder (never a half-built screen)."""

import streamlit as st

import config

from dashboard.v4 import home_data as H
from dashboard.v4 import opps_data as O
from dashboard.v4 import shell, ui


def _html(body: str):
    """st.html refuses an empty body. Sections that have nothing to say render nothing."""
    if body:
        st.html(body)


def _nav():
    return st.session_state["v4_pages"]


def _today_line(close):
    d = config.now_local().date()
    return f"יום {H.DAYS_HE[d.weekday()]}, {d:%d/%m/%Y} · לפי סגירת המסחר של {close}"


# ------------------------------------------------------------------ home
HOWTO = ("\"שווה לשקול קנייה\" מופיע לחברה חזקה שהמגמה שלה לא יורדת והסיכון שלה לא גבוה מאוד. "
         "המחיר מוצג כמידע משלים. זה ניתוח מבוסס נתונים, לא ייעוץ השקעות אישי: ההערכות לא מתחשבות במצבך האישי.")


def home():
    d, p = shell.load(), shell.prefs()
    adv = p["mode"] == "pro"
    nav = _nav()
    shell.header("home", "היום", _today_line(d["close"]))
    st.html(ui.hero(H.market_story(d["global"], d["mkt"])))

    if not p.get("howto_hidden"):                            # first: what the cards mean, and that it is not advice
        with st.container(key="v4howto"):
            st.html(f'<h2 class="v4-h3" style="margin-bottom:8px">איך לקרוא את ההערכות</h2><p>{ui.esc(HOWTO)}</p>')
            with st.container(horizontal=True, gap="small"):
                st.page_link(nav["glossary"], label="להסבר המלא", query_params={"q": "הערכת השקעה"})
                st.button("הבנתי, להסתיר", key="v4howto_hide", type="tertiary",
                          on_click=shell.set_pref, args=("howto_hidden", True))

    main, side = st.columns([1.9, 1], gap="large")
    with main:
        pk = H.picks(d["rows"], d["vmap"], limit=5 if adv else 3)
        cards, total = pk["cards"], pk["total"]
        st.html(ui.section_head("מניות שכדאי לבדוק",
                                f"{len(cards)} מתוך {total} המניות בהערכה \"שווה לשקול קנייה\"" if cards else "", "v4-pick-h"))
        if not cards:
            st.html(ui.empty("אין היום מניות בהערכה \"שווה לשקול קנייה\"",
                             "זה קורה כשהשוק חלש או כשאין מספיק נתונים אמינים. אפשר לראות את כל המניות במסך ההזדמנויות."))
        for c in cards:
            with st.container(key=f"v4pick-{c['ticker']}"):
                st.html(ui.pick_card(c, adv))
                st.page_link(nav["company"], label="לניתוח המלא ‹", query_params={"t": c["ticker"]})
        conc = H.concentration(pk)
        if conc:
            st.html(ui.note(conc["text"], conc["detail"] if adv else "", conc["mix"] if adv else None))
        if total:
            with st.container(key="v4more"):
                st.page_link(nav["opps"], label=f"לכל {total} ההזדמנויות ‹")
        if adv:
            cov = O.coverage_text(O.coverage(d["rows"], d["vmap"]), advanced=True)
            st.html('<div class="v4-gap"></div>' + ui.method_note(cov) + ui.market_table(H.market_table(d["global"])))

    with side:
        st.html(ui.week_panel(H.week(d["events"], d["rows"], d["global"], config.now_local().date())))
        if adv:
            _html(ui.sector_panel(H.sector_bars(d["mkt"])))

    st.html(ui.footer(H.footer(d["rel"], d["global"], d["close"])))


# ------------------------------------------------------------------ others
def _placeholder(key, title, what):
    shell.header(key, title, what)
    st.html(ui.empty("המסך הזה יעבור לעיצוב החדש בשלב הבא",
                     "העיצוב שלו כבר מתוכנן. הוא ייבנה אחרי שמסך הבית החדש יאושר."))
    st.page_link(_nav()["home"], label="חזרה למסך היום ‹")


OPP_DEFAULT = {"tab": "buy", "sector": O.ALL, "risk": O.ALL, "sort": "quality", "shown": O.PAGE}


def _opp_state() -> dict:
    """Tab, filters and sort survive a change of detail level or a trip to a company and back."""
    return st.session_state.setdefault("v4_opp", dict(OPP_DEFAULT))


def _opp_set(field, widget_key, conv=lambda v: v):
    def _cb():
        val = st.session_state.get(widget_key)
        if val is not None:
            stt = _opp_state()
            stt[field] = conv(val)
            stt["shown"] = O.PAGE
    return _cb


def _opp_clear():
    st.session_state["v4_opp"] = {**_opp_state(), "sector": O.ALL, "risk": O.ALL, "shown": O.PAGE}


def _opp_more():
    _opp_state()["shown"] += O.PAGE


def opportunities():
    d, p = shell.load(), shell.prefs()
    adv = p["mode"] == "pro"
    nav = _nav()
    s = _opp_state()
    cov = O.coverage(d["rows"], d["vmap"])
    shell.header("opps", "הזדמנויות",
                 f"הערכות ההשקעה של המערכת · {cov['rated']} מתוך {cov['all']} המניות קיבלו הערכת השקעה · סגירה {d['close']}")
    tab = s["tab"] if s["tab"] in O.ACTIONS else "buy"
    sorts = O.SORTS if adv else {k: v for k, v in O.SORTS.items() if k != "reliability"}
    sort = s["sort"] if s["sort"] in sorts else "quality"
    tb = O.table(d["rows"], d["vmap"], tab, s["sector"], s["risk"], sort)

    with st.container(key=f"v4obar-{tab}", horizontal=True, vertical_alignment="center"):
        st.session_state["v4opp_tab"] = tab
        st.segmented_control("סוג החלטה", list(O.ACTIONS), key="v4opp_tab", required=True,
                             format_func=lambda a: f"{O.TAB_LABEL[a]} · {cov[a]}",
                             on_change=_opp_set("tab", "v4opp_tab"), label_visibility="collapsed")
        with st.container(key="v4ofilters", horizontal=True, horizontal_alignment="left", gap="small"):
            sec_opts = [O.ALL] + [x["name"] for x in tb["sectors"]]
            sec_n = {x["name"]: x["n"] for x in tb["sectors"]}
            st.session_state["v4opp_sector"] = tb["sector"]
            st.selectbox("ענף", sec_opts, key="v4opp_sector", on_change=_opp_set("sector", "v4opp_sector"),
                         format_func=lambda x: "ענף: הכול" if x == O.ALL else f"{x} · {sec_n.get(x, 0)}",
                         label_visibility="collapsed")
            st.session_state["v4opp_risk"] = tb["risk"]
            st.selectbox("סיכון", [O.ALL] + tb["risks"], key="v4opp_risk", on_change=_opp_set("risk", "v4opp_risk"),
                         format_func=lambda x: "סיכון: הכול" if x == O.ALL else f"סיכון {x}", label_visibility="collapsed")
            st.session_state["v4opp_sort"] = sort
            st.selectbox("מיון", list(sorts), key="v4opp_sort", on_change=_opp_set("sort", "v4opp_sort"),
                         format_func=lambda k: f"מיון: {sorts[k]}", label_visibility="collapsed")
    st.html('<div class="v4-gap-sm"></div>')

    rows = tb["rows"]
    if not tb["total"]:
        st.html(ui.empty(f"אין היום מניות בהערכה \"{O.TAB_LABEL[tab]}\"",
                         "זה יכול לקרות בשוק חלש, או כשאין מספיק נתונים אמינים. נסו לשונית אחרת."))
    elif not rows:
        st.html(ui.empty("אין מניות שמתאימות לסינון", "נסו ענף אחר או רמת סיכון אחרת."))
        with st.container(horizontal=True, horizontal_alignment="center"):
            st.button("ניקוי הסינון", key="v4oclear", on_click=_opp_clear)
    else:
        shown = rows[:s["shown"]]
        with st.container(key="v4otbl"):
            st.html(ui.opp_head(adv))
            for r in shown:
                with st.container(key=f"v4orow-{r['ticker']}"):
                    st.html(ui.opp_row(r, adv))
                    st.page_link(nav["company"], label=f"לניתוח המלא של {r['name']}", query_params={"t": r["ticker"]})
            with st.container(key="v4ofoot", horizontal=True, vertical_alignment="center"):
                order = "ממוינות לפי " + sorts[sort]
                st.html(f'<div class="v4-muted">{len(shown)} מתוך {len(rows)} · {ui.esc(order)}</div>')
                if len(rows) > len(shown):
                    st.button(f"{min(O.PAGE, len(rows) - len(shown))} הבאות", key="v4omore", on_click=_opp_more)
        st.html(ui.legend())

    st.html('<div class="v4-gap"></div>')
    mix = O.mix(rows)
    lead = (f"איך מתחלקות {len(rows)} המניות בלשונית הזו בין הענפים. המערכת לא מכוונת לפיזור, "
            "ולכן ריכוז בענף אחד משקף את הנתונים של היום.") if rows else ""
    if adv:
        a, b = st.columns(2, gap="large")
        with a:
            _html(ui.mix_panel("פיזור לפי ענף", mix, lead))
        with b:
            st.html(ui.method_note(O.coverage_text(cov, advanced=True)))   # one panel: how chosen, and what is covered
    else:
        top = mix[0] if mix else None
        mix_line = (f" הענף הגדול ברשימה: {top['name']} ({top['n']} מתוך {len(rows)})." if top and len(mix) > 1 else "")
        st.html(ui.note(O.coverage_text(cov) + mix_line))
    st.html(ui.footer(H.footer(d["rel"], d["global"], d["close"])))


def markets():
    from dashboard.v4 import charts as CH
    from dashboard.v4 import markets_data as M
    from dashboard.v4 import markets_ui as MU

    d, p = shell.load(), shell.prefs()
    adv = p["mode"] == "pro"
    g, mkt = d["global"], d["mkt"]
    ok = g.get("status") == "ok"
    age = M.calc_age(mkt)
    shell.header("markets", "שווקים", f"מה השוק עושה ולמה · סגירה {d['close']} · "
                 + (f"נתוני שוק עודכנו {g.get('updated')}" if ok else "נתוני השוק לא אומתו"))
    story = {**H.market_story(g, mkt), "figures": M.gauges(mkt, g)}
    st.html(ui.hero(story, more=False))
    if age["stale"]:
        st.html(ui.note(f"החישובים של המערכת (ציון השוק, חוזק הענפים ורוחב השוק) הם מ-{age['date']}, "
                        "ולא מהיום. הם יתעדכנו בסריקה היומית הבאה."))

    if ok:
        st.html(MU.validation(M.validation(g), adv))
        secs = {s["key"]: s for s in M.sections(g, adv)}
        a, b = st.columns(2, gap="large")
        with a:
            st.html(MU.asset_table(secs["equity"], adv) + MU.asset_table(secs["commodity"], adv))
        with b:
            st.html(MU.asset_table(secs["rates"], adv) + MU.asset_table(secs["crypto"], adv))
    else:
        st.html(ui.error("נתוני השווקים הגלובליים מוסתרים", g.get("message") or "הם לא עברו בדיקת תקינות."))

    a, b = st.columns([1.4, 1], gap="large")
    with a:
        st.html(MU.sectors(M.sectors(mkt), adv, age["date"]))
    with b:
        _html(MU.breadth(M.breadth(mkt), adv))

    if adv:
        hist = shell.market_history(M.HISTORY)
        hrows = M.history(hist, g)
        st.html(MU.history(hrows))
        shown = {r["sym"]: r["name"] for r in hrows if r["status"] == "ok"}
        with st.container(key="v4m-chart"):
            if shown:
                st.html('<section class="v4m-sec"><h2 class="v4-h3">גרף</h2>'
                        '<p class="v4m-sum">מחירי סגירה בפועל, עם הממוצעים של 50 ו-200 יום. רק נכסים שעברו את בדיקת ההתאמה.</p></section>')
                with st.container(horizontal=True, gap="small", key="v4m-pick"):
                    if st.session_state.get("v4m_sym") not in shown:
                        st.session_state["v4m_sym"] = next(iter(shown))
                    sym = st.selectbox("נכס", list(shown), key="v4m_sym", format_func=lambda s: shown[s],
                                       label_visibility="collapsed")
                    st.session_state.setdefault("v4m_rng", "1y")
                    rng = st.segmented_control("טווח זמן", list(CH.RANGES), key="v4m_rng", required=True,
                                               format_func=lambda k: CH.RANGES[k][0], label_visibility="collapsed")
                frame = hist[sym].to_frame("Close")
                chg = CH.change(CH.window(frame, rng)[0])
                if chg is not None and sym not in M.YIELDS:
                    st.html(f'<p class="v4c-p">{ui.text("שינוי " + CH.PHRASE[rng] + ":")} '
                            f'<b class="v4-num t-{H.tone_of(chg)}">{ui.esc(H.pct(chg))}</b></p>')
                st.plotly_chart(CH.price_figure(frame, rng, p["theme"], True, prefix="$" if sym in M.DOLLAR else ""),
                                config={"displayModeBar": False, "responsive": True}, theme=None, key="v4m_fig")
            else:
                st.html('<div class="v4c-missing">ההיסטוריה של הנכסים לא זמינה כרגע, או שלא עברה את בדיקת ההתאמה. '
                        'לא מוצג גרף במקום נתון שלא נבדק.</div>')
        st.html('<div class="v4-gap"></div>' + MU.methods(mkt))
    st.html(ui.footer(H.footer(d["rel"], d["global"], d["close"])))


AL_TABS = ("all", "critical", "important", "info")


def alerts():
    from dashboard.v4 import alerts_data as A
    from dashboard.v4 import alerts_ui as AU

    d, p = shell.load(), shell.prefs()
    adv = p["mode"] == "pro"
    nav = _nav()
    data = A.build(shell._read_json(config.ALERTS_CENTER_JSON, []), d["rows"], d["vmap"], d["events"],
                   d["mkt"], d["close"], config.now_local().date())
    shell.header("alerts", "התראות", f"מה כדאי לדעת היום · נוצרו בסריקה של {d['close']}")
    st.html(ui.note("ההתראות מכסות את המניות ברשימת המעקב הקבועה של המערכת ואת הענפים, לא את כל 500 המניות. "
                    "מניה שאין עליה התראה לא בהכרח שקטה."))
    if not data["total"]:
        st.html(ui.empty("אין התראות היום", "לא נמצא אירוע חריג במניות שבמעקב או בענפים בסריקה האחרונה."))
    else:
        labels = {"all": "הכול", **{k: l for k, l, _ in A.GROUPS}}
        counts = {"all": data["total"], **data["counts"]}
        st.session_state.setdefault("v4al_tab", "all")
        with st.container(key="v4abar"):
            tab = st.segmented_control("סינון", list(AL_TABS), key="v4al_tab", required=True,
                                       format_func=lambda k: f"{labels[k]} · {counts[k]}", label_visibility="collapsed")
        st.html('<div class="v4-gap-sm"></div>')
        for g, _, _ in A.GROUPS:
            items = [i for i in data["items"] if i["group"] == g]
            if not items or tab not in ("all", g):
                continue
            st.html(AU.group_head(g, len(items)))
            with st.container(key=f"v4alg-{g}"):                # one card per group, a row per alert
                for n, i in enumerate(items):
                    with st.container(key=f"v4al-{g}-{n}"):
                        st.html(AU.card(i, adv))
                        if i["link"] == "company" and i["ticker"]:
                            st.page_link(nav["company"], label="לניתוח המניה ‹", query_params={"t": i["ticker"]})
                        elif i["link"] == "markets":
                            st.page_link(nav["markets"], label="למסך השווקים ‹")
    st.html('<div class="v4-gap"></div>' + AU.rules(adv))
    st.html(ui.footer(H.footer(d["rel"], d["global"], d["close"])))


def glossary():
    from dashboard.v4 import glossary_data as G
    from dashboard.v4 import glossary_ui as GU

    d, p = shell.load(), shell.prefs()
    adv = p["mode"] == "pro"
    qp = st.query_params.get("q", "")                     # other screens can link to a term: ?q=...
    if st.session_state.get("v4g_qp") != qp:
        st.session_state["v4g_q"] = st.session_state["v4g_qp"] = qp
    shell.header("glossary", "מילון מונחים", "כל מונח בשפה פשוטה, עם דוגמה מהנתונים האמיתיים")
    with st.container(key="v4gsearch"):
        q = st.text_input("חיפוש מונח", key="v4g_q", placeholder="חיפוש מונח, למשל מכפיל רווח",
                          label_visibility="collapsed")
    s = G.sample(d["rows"], d["vmap"])
    g = G.build(q, s)
    st.html(GU.letters(g["letters"]))
    if not g["sections"]:
        st.html(ui.empty("לא נמצא מונח", "נסו מילה אחרת, או שם באנגלית (למשל PEG או Beta)."))
    for i, (c, _) in enumerate(g["letters"]):
        sec = next((x for x in g["sections"] if x["letter"] == c), None)
        if sec:
            st.html(GU.section(sec, i, adv))
    st.html(GU.count_line(g, d["close"], s and s["name"]))
    st.html(ui.footer(H.footer(d["rel"], d["global"], d["close"])))


def _company_search():
    q = (st.session_state.get("v4c_q") or "").strip()
    if q:
        import company_search
        st.session_state["v4_goto"] = company_search.resolve(q) or q.upper()
        st.session_state["v4c_q"] = ""


def company():
    from dashboard.v4 import charts as CH
    from dashboard.v4 import company_data as C
    from dashboard.v4 import company_ui as CU

    d, p = shell.load(), shell.prefs()
    adv = p["mode"] == "pro"
    nav = _nav()
    t = (st.query_params.get("t") or "").upper().strip()
    if not t:
        import stockdata
        shell.header("company", "ניתוח חברה", "חפשו חברה לפי שם או סימול, בעברית או באנגלית", mode=False)
        st.text_input("חיפוש חברה", key="v4c_q", placeholder="למשל: אפל, Microsoft, NVDA", on_change=_company_search)
        # Every stock that has an investment assessment today, by assessment, best first.
        cov = O.coverage(d["rows"], d["vmap"])
        st.html('<div class="v4-gap"></div>' + ui.section_head(
            "המניות עם הערכת השקעה", f"{cov['rated']} מתוך {cov['all']} המניות במעקב. כל מניה אחרת זמינה דרך החיפוש."))
        for act in ("buy", "wait", "avoid"):
            vs = stockdata.ranked(d["vmap"], d["rows"], act)
            if not vs:
                continue
            st.html(f'<div class="v4ci-h">{ui.chip(vs[0]["label"], vs[0]["tone"])}<span>{len(vs)}</span></div>')
            with st.container(key=f"v4cidx-{act}", horizontal=True, gap=None):
                for v in vs:
                    nm = H.short_name(d["rows"].get(v["ticker"], {}).get("Name"), v["ticker"])
                    st.page_link(nav["company"], label=f"{v['ticker']} · {nm}", query_params={"t": v["ticker"]})
        st.html(ui.footer(H.footer(d["rel"], d["global"], d["close"])))
        return

    row, v = d["rows"].get(t), d["vmap"].get(t)
    prof = shell.profile(t)
    if not row and not prof:
        live = shell.company_live(t)
        if not live["ok"]:
            shell.header("company", "ניתוח חברה", t)
            st.html(ui.empty(f"לא מצאנו את \"{t}\"",
                             "המערכת עוקבת אחרי מניות מדד S&P 500. בדקו את הסימול, או חפשו לפי שם החברה בתפריט."))
            st.page_link(nav["home"], label="חזרה למסך היום ‹")
            return
    row = row or {}
    info_now = (shell.company_live(t) or {}).get("info") if not row.get("Name") else {}
    hd = C.header(t, row, prof, info_now)
    dc = C.decision(v, row)
    rel = (v or {}).get("reliability") or {}

    # ---- head: identity, price, close date, list, level of detail
    # Same top row as every other screen (the detail switch in the same place), then the
    # company row across the full width, so the price sits at the far edge.
    with st.container(key="v4chead"):
        a, b = st.columns([3, 1], vertical_alignment="bottom")
        with a:
            st.html(f'<div class="v4c-crumb">ניתוח חברה · <span class="v4-num">{ui.esc(t)}</span></div>')
        with b:
            with st.container(horizontal=True, horizontal_alignment="left", gap="small", key="v4cact"):
                shell.mode_control("company")
        st.html(CU.head(hd))

    # ---- the decision, with the key facts beside it
    ev = (d["events"] or {}).get(t) or {}
    ed = C._dmy(ev.get("earnings_date"))
    key_facts = [{"k": "שווי שוק", "v": hd["market_cap"]},
                 {"k": "מהשיא של 52 שבועות", "v": hd["dist_high"]},
                 {"k": "רמת סיכון", "v": row.get("RiskLevel") or "—"},
                 {"k": "אמינות הנתונים", "v": f'{rel["score"]} מתוך 100' if rel.get("score") is not None else "—"},
                 {"k": "דוחות הבאים", "v": ed or "לא ידוע"},
                 {"k": "נתונים עסקיים", "v": (f"רבעון עד {row['LastQuarter']}" if row.get("LastQuarter")
                                              else f"נשלפו {hd['fund_date']}" if hd["fund_date"] else "לא ידוע")}]
    ps = C.price_section(v, row, prof)
    st.html(CU.hero(dc, CU.facts(key_facts, "aside"), ps["flag"] if dc["status"] == "rated" else "", hd["stale"]))
    _html(CU.change_and_hold(dc))

    extra = [("v4c-price", "מחיר ותמחור"), ("v4c-chart", "גרף"), ("v4c-biz", "ביצועים עסקיים"),
             ("v4c-risk", "סיכונים"), ("v4c-about", "על החברה")]
    if adv:
        extra.append(("v4c-src", "מקורות ומתודולוגיה"))
    st.html(CU.section_nav([("קובע את ההערכה", [("v4c-how", "כיצד נקבעה ההערכה?")]), ("מידע משלים", extra)]))

    main, side = st.columns([1.85, 1], gap="large")
    with main:
        with st.container(key="v4cs-how"):
            st.html(CU.sec_open("v4c-how", "כיצד נקבעה ההערכה?",
                                "אלה הבדיקות היחידות שקובעות את ההערכה. כולן צריכות לעבור כדי לקבל \"שווה לשקול קנייה\".",
                                "קובע את ההערכה")
                    + CU.checks(C.checks(v, row), C.score_parts(row), adv))
        with st.container(key="v4cs-price"):
            st.html(CU.sec_open("v4c-price", "מחיר ותמחור",
                                "האם המחיר של היום אטרקטיבי. זו שאלה נפרדת מאיכות החברה.", "מידע משלים, לא חלק מההערכה")
                    + CU.price(ps, adv))

        with st.container(key="v4cs-chart"):
            st.html(CU.sec_open("v4c-chart", "גרף המחיר"))
            ph = st.empty()
            ph.html(ui.skeleton_cards(1))
            live = shell.company_live(t)
            ph.empty()
            if live["ok"]:
                st.session_state.setdefault("v4c_rng", "6m")
                rng = st.segmented_control("טווח זמן", list(CH.RANGES), key="v4c_rng", required=True,
                                           format_func=lambda k: CH.RANGES[k][0], label_visibility="collapsed")
                c, _, _ = CH.window(live["hist"], rng)
                chg = CH.change(c)
                lv = (v or {}).get("levels") or {}
                tgt = lv.get("target") or (prof or {}).get("target_mean")
                if chg is not None:
                    st.html(f'<p class="v4c-p">{ui.text("שינוי במחיר " + CH.PHRASE[rng] + ":")} '
                            f'<b class="v4-num t-{H.tone_of(chg)}">{ui.esc(C.pct1(chg))}</b></p>')
                st.plotly_chart(CH.price_figure(live["hist"], rng, p["theme"], adv, tgt, lv.get("target_low"),
                                                lv.get("target_high"), lv.get("support")),
                                config={"displayModeBar": False, "responsive": True}, theme=None, key="v4c_fig")
                cap = ("קו רציף: מחירי סגירה בפועל (עבר). קו מקווקו: יעד האנליסטים, הערכה חיצונית לשנה קדימה, לא תחזית של המערכת."
                       + (" באפור: ממוצע 200 יום, בכתום: ממוצע 50 יום, ורצועה בהירה: טווח היעדים." if adv else ""))
                st.html(f'<p class="v4c-fine">{ui.esc(cap)} עודכן {ui.esc(live["fetched"])}.</p>')
            else:
                st.html('<div class="v4c-missing">גרף המחיר לא זמין כרגע: מקור הנתונים לא ענה. '
                        f'המחיר האחרון הידוע הוא {ui.esc(hd["price"])}, לפי סגירה {ui.esc(hd["close"])}. נסו לרענן בעוד כמה דקות.</div>')

        with st.container(key="v4cs-biz"):
            st.html(CU.sec_open("v4c-biz", "ביצועים עסקיים", "מה החברה מכרה והרוויחה. נתוני עבר מדוחות שפורסמו.")
                    + CU.business(C.business(prof, row), adv)
                    + CU.diffs(C.diffs(row, prof), C._dmy((prof or {}).get("_date")) or "", adv))

    with side, st.container(key="v4cside"):                   # stays in view beside the longer main column
        with st.container(key="v4cs-risk"):
            st.html(CU.sec_open("v4c-risk", "סיכונים שכדאי להכיר") + CU.risks(C.risks(v, row, d["events"], t), adv))
        with st.container(key="v4cs-about"):
            live_info = (shell.company_live(t) or {}).get("info") or {}
            st.html(CU.sec_open("v4c-about", "על החברה") + CU.about(C.about(t, row, prof, live_info), adv))

    if adv:
        with st.container(key="v4cs-src"):
            st.html(CU.sec_open("v4c-src", "מקורות ומתודולוגיה")
                    + CU.sources(C.sources(row, prof, shell.company_live(t)), rel))

    st.html(ui.footer(H.footer(d["rel"], d["global"], d["close"])))


def _fund_date(rows: dict):
    """The business-data fetch date most rated stocks carry (they are fetched in one run)."""
    from collections import Counter
    c = Counter(r.get("FundDate") for r in rows.values()
                if r.get("_tier") in ("full", "enriched") and r.get("FundDate"))
    return c.most_common(1)[0][0] if c else None


def settings():
    from dashboard.v4 import glossary_ui as GU

    d = shell.load()
    nav = _nav()
    f = H.footer(d["rel"], d["global"], d["close"])
    cov = O.coverage(d["rows"], d["vmap"])
    shell.header("settings", "הגדרות", "תצוגה, נתונים ואמינות")

    with st.container(key="v4set-view"):
        st.html(GU.panel_open("תצוגה")
                + '<h3 class="v4s-h">ערכת צבעים</h3><div class="v4-method">בהיר: רקע בהיר, ברירת המחדל. '
                  'כהה: נוח לעיניים בערב ובחושך.</div>')
        shell.theme_control("v4theme_settings")
        st.html('<h3 class="v4s-h">רמת פירוט</h3><div class="v4-method">פשוט: מסקנות והסברים קצרים במילים, מתאים לרוב '
                'המשתמשים. מתקדם: כל המספרים, המקורות, המשקלות ואיך התקבלה כל הערכה.</div>')
        shell.mode_control("settings_body")
        st.html('<div class="v4-method v4s-foot">אפשר לעבור בין פשוט למתקדם בכל מסך. המעבר שומר את המניה והמסך '
                'שבהם אתם נמצאים.</div>')

    fd = _fund_date(d["rows"])
    with st.container(key="v4set-data"):
        st.html(GU.panel_open("נתונים ואמינות") + GU.data_table([
            ("מחירי מניות ומגמות", "Yahoo Finance", f"סגירת המסחר {d['close']}"),
            ("נתונים עסקיים ויעדי אנליסטים", "Yahoo Finance",
             f"נשלפו {fd}, מתעדכנים פעם ביום" if fd else "מועד השליפה לא נשמר בסריקה הזו"),
            ("שווקים גלובליים ומט״ח", "Yahoo Finance, נבדקים מול טווחים סבירים", f["market_updated"]),
            ("הערכות השקעה", "המנוע הפעיל", f"{cov['rated']} מתוך {cov['all']} מניות"),
            ("עדכון אוטומטי", "סריקה יומית", "שני עד שישי, בדרך כלל בסביבות הצהריים (שעון ישראל). GitHub מעכב ריצות מתוזמנות, "
                                              "ולכן השעה המדויקת משתנה."),
        ]) + ui.note(f"מקור יחיד: נתוני המניות מגיעים מ-Yahoo Finance בלבד, בלי אימות מול מקור נוסף. "
                     f"אמינות הנתונים כרגע: {f['rel_label']}. כל מסך מציין את מועד הנתונים שעליהם הוא מבוסס.")
                + f'<div class="v4-method v4s-foot">{ui.text(O.coverage_text(cov))}</div>')
        st.page_link(nav["markets"], label="מצב השווקים ובדיקת הנתונים ‹")

    with st.container(key="v4set-privacy"):
        st.html(GU.panel_open("פרטיות", "האתר לא מציג רשימות מעקב או תיקי השקעות אישיים. ההעדפות שלך "
                                        "(ערכת צבעים ורמת פירוט) נשמרות רק בדפדפן הזה, ולא נשלחות לשום מקום."))
        st.button("איפוס ההעדפות לברירת המחדל", key="v4set_reset", on_click=shell.reset_prefs)

    with st.container(key="v4set-about"):
        st.html(GU.panel_open("אודות")
                + f'<p class="v4s-ver"><b>Stock Agent Pro</b> · גרסה 4 בפיתוח · סורק {ui.text(str(len(d["rows"])))} חברות '
                  'ממדד S&amp;P 500</p>'
                + '<div class="v4-method">המידע במערכת מבוסס נתונים ומחקר, ואינו ייעוץ השקעות אישי. ההערכות לא מתחשבות '
                  'במצבך הכלכלי, ביעדים שלך או ברמת הסיכון שלך. החלטת השקעה היא באחריותך, ולפני החלטה משמעותית כדאי '
                  'להתייעץ עם יועץ השקעות מורשה.</div>')
        with st.container(horizontal=True):
            st.page_link(nav["glossary"], label="איך המערכת קובעת הערכה ‹", query_params={"q": "הערכת השקעה"})
            st.page_link(nav["glossary"], label="מילון מונחים ‹")
    st.html(ui.footer(f))
