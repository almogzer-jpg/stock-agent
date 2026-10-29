# -*- coding: utf-8 -*-
"""Simple mode — the default experience ("Simple by Default, Professional on Demand").

Written for someone with basic market knowledge. Every screen answers one
question in plain Hebrew, and every stock carries the SAME verdict as in the
professional view (verdict.py via stockdata.py). One responsive single-column
layout serves desktop and phone. The full professional analysis is always one
click away and is never removed.
"""
import json
from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import company_search
import glossary
import market
import mywatch
import verdict as V
from dashboard.theme import (BG, CARD, ELEV, BORDER, PRIMARY, POSITIVE, WARNING, NEGATIVE,
                             TEXT, SECONDARY, MUTED, score_color, style_fig)

PAGES = [("today", "🏠", "היום"), ("check", "🔎", "בדיקת מניה"), ("ideas", "💡", "רעיונות"),
         ("mine", "⭐", "המניות שלי"), ("learn", "📖", "מילון")]
TONE = {"positive": POSITIVE, "warning": WARNING, "negative": NEGATIVE, "muted": MUTED}
POPULAR = [("AAPL", "אפל"), ("MSFT", "מיקרוסופט"), ("NVDA", "אנבידיה"), ("AMZN", "אמזון"),
           ("GOOGL", "גוגל"), ("TEVA", "טבע"), ("JPM", "ג'יי פי מורגן"), ("KO", "קוקה קולה")]

CSS = f"""
<style>
  .block-container {{ max-width: 880px !important; padding-top: 1.2rem !important; }}
  .s-hero {{ font-size: 30px; font-weight: 700; letter-spacing: -.3px; margin: 4px 0 2px; }}
  .s-sub {{ color: {MUTED}; font-size: 15px; }}
  .s-h {{ font-size: 21px; font-weight: 700; margin: 26px 0 10px; }}
  .s-card {{ background: {CARD}; border-radius: 18px; padding: 18px 20px; margin: 10px 0; }}
  .s-card.elev {{ background: {ELEV}; }}
  .s-row {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }}
  .s-tk {{ font-size: 20px; font-weight: 800; }}
  .s-nm {{ color: {SECONDARY}; font-size: 14.5px; margin-top: 2px; }}
  .s-why {{ color: {SECONDARY}; font-size: 15.5px; line-height: 1.65; margin-top: 10px; }}
  .s-pill {{ display: inline-flex; align-items: center; gap: 6px; border-radius: 999px;
             padding: 6px 14px; font-weight: 700; font-size: 15px; background: {ELEV}; white-space: nowrap; }}
  .s-pill.big {{ font-size: 20px; padding: 10px 20px; }}
  .s-chip {{ display: inline-block; border-radius: 999px; padding: 4px 11px; font-size: 13px;
             background: {ELEV}; color: {SECONDARY}; margin: 2px 0 2px 6px; }}
  .s-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-top: 14px; }}
  .s-tile {{ background: {ELEV}; border-radius: 14px; padding: 12px 14px; }}
  .s-tile .l {{ color: {MUTED}; font-size: 13px; }}
  .s-tile .v {{ font-size: 22px; font-weight: 700; margin-top: 2px; }}
  .s-tile .x {{ font-size: 13px; margin-top: 2px; color: {SECONDARY}; }}
  .s-list {{ margin: 6px 0 0; padding: 0; list-style: none; }}
  .s-list li {{ font-size: 15.5px; line-height: 1.6; padding: 4px 0; color: {TEXT}; }}
  .s-note {{ color: {MUTED}; font-size: 13.5px; line-height: 1.6; margin-top: 8px; }}
  .term {{ border-bottom: 1px dotted {MUTED}; cursor: help; position: relative; outline: none; }}
  .term:hover::after, .term:focus::after {{
      content: attr(data-tip); position: absolute; bottom: 135%; right: 0; width: 250px;
      background: {ELEV}; color: {TEXT}; padding: 10px 12px; border-radius: 10px; font-size: 13.5px;
      line-height: 1.55; font-weight: 400; z-index: 60; box-shadow: 0 8px 24px rgba(0,0,0,.45);
      white-space: normal; text-align: right; }}
  @media (max-width: 640px) {{
    header[data-testid="stHeader"] {{ display: none; }}
    .block-container {{ padding: .4rem .8rem 110px !important; }}
    .s-hero {{ font-size: 25px; }}
    .s-grid {{ grid-template-columns: repeat(2, 1fr); }}
    .s-pill.big {{ font-size: 18px; }}
  }}
  /* bottom navigation on phones (simple mode) */
  .st-key-snav {{ position: fixed; bottom: 0; left: 0; right: 0; z-index: 999; background: {CARD};
       border-top: 1px solid {BORDER}; padding: 4px 2px calc(6px + env(safe-area-inset-bottom)); margin: 0; }}
  .st-key-snav [role="radiogroup"] {{ display: flex; flex-wrap: nowrap; gap: 0; width: 100%; overflow: hidden; }}
  .st-key-snav [role="radiogroup"] label {{ flex: 1 1 0; min-width: 0; justify-content: center; text-align: center;
       padding: 6px 1px; min-height: 50px; border-radius: 12px; background: transparent !important; }}
  .st-key-snav [role="radiogroup"] label > div:first-child {{ display: none; }}
  .st-key-snav [role="radiogroup"] label p {{ font-size: 12.5px; font-weight: 600; text-align: center; white-space: nowrap; }}
  .st-key-snav div[data-testid="stRadio"] [role="radiogroup"] label:has(input:checked) {{ background: {ELEV} !important; }}
  .st-key-snav div[data-testid="stRadio"] [role="radiogroup"] label:has(input:checked) * {{ color: {PRIMARY} !important; }}
</style>
"""


# ------------------------------------------------------------------ helpers
def _n(v):
    try:
        f = float(v)
        return f if f == f else None
    except (TypeError, ValueError):
        return None


def _money(v):
    v = _n(v)
    if v is None:
        return "—"
    return f"${v:,.0f}" if v >= 1000 else f"${v:,.2f}"


def term(label, key=None):
    """A professional term with a plain-Hebrew tooltip (hover or tap)."""
    tip = glossary.tip(key or label)
    if not tip:
        return label
    tip = tip.replace('"', "&quot;")
    return f'<span class="term" tabindex="0" data-tip="{tip}">{label}</span>'


_INLINE_TERMS = [("ROIC", "ROIC"), ("מכפיל עתידי", "מכפיל עתידי"), ("רמת התמיכה", "תמיכה"),
                 ("מחיר היעד הממוצע של האנליסטים", "מחיר יעד"), ("הממוצע של 200", "ממוצע נע"),
                 ("מגמת עלייה", "מגמה"), ("מגמת ירידה", "מגמה"), ("רווח תפעולי", "שולי רווח")]


def gloss(text):
    """Add plain-Hebrew tooltips to professional terms inside generated text."""
    out = str(text or "")
    for phrase, key in _INLINE_TERMS:
        if phrase in out:
            out = out.replace(phrase, term(phrase, key), 1)
    return out


def pill(v, big=False):
    col = TONE.get(v.get("tone"), MUTED)
    return (f"<span class='s-pill{' big' if big else ''}' style='color:{col}'>"
            f"{v['emoji']} {v['label']}</span>")


def rel_chip(rel):
    col = POSITIVE if rel["label"] == "גבוהה" else WARNING if rel["label"] == "בינונית" else NEGATIVE
    why = " · ".join(rel.get("reasons", []))
    return (f"<span class='s-chip' title='{why}'>{term('אמינות הנתונים')}: "
            f"<b style='color:{col}'>{rel['label']}</b></span>")


def goto(page, ticker=None):
    st.session_state["s_page"] = page
    if ticker:
        st.session_state["s_ticker"] = ticker
    st.rerun()


def _card(html, elev=False):
    st.markdown(f"<div class='s-card{' elev' if elev else ''}'>{html}</div>", unsafe_allow_html=True)


def stock_card(v, row, key, show_holder=False):
    """Compact list card: verdict, one-line why, price and target."""
    lv = v.get("levels") or {}
    chg = _n(row.get("DailyChange%"))
    chg_html = (f"<span style='color:{POSITIVE if chg >= 0 else NEGATIVE};font-size:13.5px'>"
                f"{chg:+.1f}% היום</span>") if chg is not None else ""
    tgt = (f" · יעד אנליסטים {_money(lv.get('target'))} "
           f"<span style='color:{POSITIVE if (lv.get('upside') or 0) >= 0 else NEGATIVE}'>({lv['upside']:+.0f}%)</span>"
           if lv.get("target") and lv.get("upside") is not None else "")
    holder = (f"<div class='s-note' style='color:{TONE.get(v['holder_tone'], MUTED)}'>"
              f"אם יש לך את המניה: {v['holder_emoji']} {v['holder_label']}</div>") if show_holder else ""
    watch_out = (f"<div class='s-note' style='color:{WARNING}'>⚠️ לשים לב: {v['cons'][0]}</div>"
                 if v["action"] == "buy" and v.get("cons") else "")
    _card(f"<div class='s-row'><div><div class='s-tk'>{v['ticker']}</div>"
          f"<div class='s-nm'>{company_search.display_name(v['ticker'], row.get('Name'))}</div></div>"
          f"<div style='text-align:left'>{pill(v)}</div></div>"
          f"<div class='s-why'>{gloss(v['why'])}</div>"
          f"{watch_out}<div class='s-note'>מחיר {_money(lv.get('price'))} {chg_html}{tgt}</div>{holder}")
    if st.button(f"לפרטים על {v['ticker']} ←", key=key, use_container_width=True):
        goto("check", v["ticker"])


# ---------------------------------------------------------------- pages
def page_today(ctx):
    mkt, rows, vmap = ctx["mkt"], ctx["rows"], ctx["vmap"]
    today = date.today().strftime("%d/%m/%Y")
    st.markdown(f"<div class='s-hero'>מה קורה היום בשוק</div>"
                f"<div class='s-sub'>{today} · הנתונים עודכנו לפי סגירת המסחר האחרונה ({mkt.get('date', '—')})</div>",
                unsafe_allow_html=True)

    # Market in one sentence
    reg = (mkt.get("regime") or {}).get("score")
    fg = mkt.get("fear_greed") or {}
    br = mkt.get("breadth") or {}
    if isinstance(reg, (int, float)):
        mood, mcol = (("חיובי", POSITIVE) if reg >= 60 else ("מעורב", WARNING) if reg >= 40 else ("שלילי", NEGATIVE))
    else:
        mood, mcol = "לא ידוע", MUTED
    idx = {i.get("name"): i for i in mkt.get("indices", [])}
    spx = idx.get("S&P 500") or {}
    fgs = _n(fg.get("score"))
    fg_txt = ("המשקיעים אופטימיים מאוד, ובמצבים כאלה כדאי להיזהר מהתלהבות יתר." if fgs is not None and fgs >= 75 else
              "מצב הרוח של המשקיעים אופטימי." if fgs is not None and fgs >= 55 else
              "מצב הרוח של המשקיעים מאוזן." if fgs is not None and fgs >= 45 else
              "המשקיעים חוששים." if fgs is not None and fgs >= 25 else
              "יש פחד גדול בשוק." if fgs is not None else "")
    lines = []
    if spx.get("change_pct") is not None:
        lines.append(f"מדד {term('S&P 500')} {'עלה' if spx['change_pct'] >= 0 else 'ירד'} "
                     f"{abs(spx['change_pct']):.1f}% ביום המסחר האחרון.")
    if br.get("above200") is not None:
        lines.append(f"{br['above200']:.0f}% מהמניות שהמערכת עוקבת אחריהן נמצאות "
                     f"ב{term('מגמת עלייה', 'מגמה')} ארוכת טווח.")
    if fg_txt:
        lines.append(f"{fg_txt} ({term('פחד/חמדנות')}: {int(fgs)} מתוך 100)")
    _card(f"<div style='font-size:15px;color:{MUTED}'>{term('מצב השוק', 'Risk-On')}</div>"
          f"<div style='font-size:26px;font-weight:800;color:{mcol};margin-top:2px'>{mood}</div>"
          f"<div class='s-why'>{' '.join(lines)}</div>")

    # My stocks first, when something needs attention
    mine = mywatch.items()
    attn = []
    for tk, base in mine.items():
        v = vmap.get(tk)
        if v and (base.get("owned") and v["holder"] in ("review_sell", "caution")):
            attn.append(v)
    if attn:
        st.markdown("<div class='s-h'>⭐ במניות שלך — דורש תשומת לב</div>", unsafe_allow_html=True)
        for v in attn[:3]:
            stock_card(v, rows.get(v["ticker"], {}), f"t_m_{v['ticker']}", show_holder=True)

    import stockdata
    buy = stockdata.ranked(vmap, rows, "buy", limit=3)
    wait = [v for v in stockdata.ranked(vmap, rows, "wait") if v.get("quality_tier") == "strong"][:3]
    avoid = sorted([v for v in stockdata.ranked(vmap, rows, "avoid", tiers=("full",))],
                   key=lambda v: v.get("quality") or 0)[:3]

    st.markdown("<div class='s-h'>🟢 שווה לשקול קנייה</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='s-note'>חברות חזקות שהמניה שלהן במגמה תקינה. "
                f"זו נקודת פתיחה לבדיקה, לא הוראת קנייה.</div>", unsafe_allow_html=True)
    if buy:
        for v in buy:
            stock_card(v, rows.get(v["ticker"], {}), f"t_b_{v['ticker']}")
    else:
        _card("<div class='s-why'>היום אין מניות שעוברות את כל התנאים. לא חייבים לקנות כל יום.</div>")

    if wait:
        st.markdown("<div class='s-h'>🟡 חברות טובות — לחכות לרגע הנכון</div>", unsafe_allow_html=True)
        for v in wait:
            cond = (f"<div class='s-note'>מה לחכות לו: {v['conditions'][0]}</div>" if v.get("conditions") else "")
            stock_card(v, rows.get(v["ticker"], {}), f"t_w_{v['ticker']}")
            if cond:
                st.markdown(cond, unsafe_allow_html=True)

    if avoid:
        st.markdown("<div class='s-h'>🔴 כדאי להיזהר</div>", unsafe_allow_html=True)
        for v in avoid:
            stock_card(v, rows.get(v["ticker"], {}), f"t_a_{v['ticker']}", show_holder=True)

    # Earnings this week, in plain words
    ev = []
    for t, r in rows.items():
        d = _n(r.get("DaysToEarnings"))
        if d is not None and 0 <= d <= 7 and (r.get("_tier") == "full" or t in mine):
            ev.append((int(d), t))
    if ev:
        ev.sort()
        items = "".join(
            f"<li><b>{t}</b> ({company_search.display_name(t, rows[t].get('Name'))}) — "
            f"{'היום' if d == 0 else 'מחר' if d == 1 else f'בעוד {d} ימים'}</li>" for d, t in ev[:6])
        st.markdown("<div class='s-h'>📅 דוחות כספיים השבוע</div>", unsafe_allow_html=True)
        _card(f"<ul class='s-list'>{items}</ul><div class='s-note'>ביום הדוחות המחיר יכול לזוז בחדות. "
              f"מי שרוצה פחות סיכון יכול לחכות לפרסום. {term('מה זה?', 'דוחות רבעוניים')}</div>")


def _chart(hist, v):
    if hist is None or "Close" not in getattr(hist, "columns", []):
        return
    c = hist["Close"].dropna().tail(260)
    if len(c) < 20:
        return
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=c.index, y=c.values, mode="lines", line=dict(color=PRIMARY, width=2),
                             name="מחיר", hovertemplate="%{x|%d/%m/%Y}<br>$%{y:.2f}<extra></extra>"))
    lv = v.get("levels") or {}
    for key, name, col in (("support", "תמיכה", POSITIVE), ("resistance", "התנגדות", NEGATIVE),
                           ("target", "יעד אנליסטים", WARNING)):
        y = _n(lv.get(key))
        if y:
            fig.add_hline(y=y, line=dict(color=col, width=1, dash="dot"),
                          annotation_text=f"{name} {_money(y)}", annotation_position="top left",
                          annotation_font=dict(color=col, size=12))
    fig = style_fig(fig, height=300)
    fig.update_layout(showlegend=False, margin=dict(l=8, r=8, t=24, b=8))
    fig.update_xaxes(tickformat="%m/%y")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _analysis_block(t, rep, daily_v):
    v = rep.get("verdict") or V.verdict_for_report(rep)
    o, md = rep.get("overview") or {}, rep.get("market_data") or {}
    lv = v.get("levels") or {}
    chg = md.get("daily_change", "")
    chg_col = NEGATIVE if str(chg).startswith("-") else POSITIVE
    st.markdown(
        f"<div class='s-card'><div class='s-row'><div>"
        f"<div class='s-tk' style='font-size:26px'>{o.get('name') or t}</div>"
        f"<div class='s-nm'>{t} · {o.get('sector_he') if o.get('sector_he') not in (None, '', 'אין נתון זמין') else ''}</div></div>"
        f"<div style='text-align:left'><div style='font-size:28px;font-weight:800'>{md.get('price', '—')}</div>"
        f"<div style='color:{chg_col};font-size:14.5px'>{chg} היום</div></div></div>"
        f"<div style='margin-top:16px'>{pill(v, big=True)}</div>"
        f"<div class='s-why' style='font-size:17px;color:{TEXT}'>{gloss(v['why'])}</div>"
        f"<div style='margin-top:10px'>{rel_chip(v['reliability'])}"
        f"<span class='s-chip'>ציון {term('איכות', 'ציון איכות')}: <b style='color:{score_color(v.get('quality'))}'>"
        f"{int(v['quality']) if v.get('quality') is not None else '—'}</b> מתוך 100</span></div></div>",
        unsafe_allow_html=True)
    if daily_v and daily_v["action"] != v["action"]:
        st.markdown(f"<div class='s-note'>בסריקת הבוקר פסק הדין היה {daily_v['emoji']} {daily_v['label']}. "
                    f"הניתוח כאן מבוסס על המחיר והנתונים העדכניים ביותר.</div>", unsafe_allow_html=True)

    # Key numbers
    up = lv.get("upside")
    dn = lv.get("downside")
    an = lv.get("analysts")
    tiles = [
        ("מחיר נוכחי", _money(lv.get("price")), ""),
        (term("מחיר יעד"), _money(lv.get("target")),
         ((f"<span style='color:{POSITIVE}'>{up:+.1f}% {term('פוטנציאל', 'פוטנציאל עלייה')}</span>" if up >= 0 else
           f"<span style='color:{WARNING}'>המחיר מעל היעד ב-{abs(up):.1f}%</span>")
          + (f" · {int(an)} אנליסטים" if an else "")) if up is not None else "אין יעד אנליסטים"),
        (term("תמיכה"), _money(lv.get("support")),
         f"<span style='color:{NEGATIVE}'>{dn:+.1f}% עד לשם</span>" if dn is not None else ""),
        (term("התנגדות"), _money(lv.get("resistance")),
         (f"{lv['dist_res']:+.1f}% עד לשם" if lv.get("dist_res") is not None else
          "המניה מעל כל השיאים האחרונים" if lv.get("support") else "")),
    ]
    st.markdown("<div class='s-grid'>" + "".join(
        f"<div class='s-tile'><div class='l'>{l}</div><div class='v'>{val}</div><div class='x'>{x}</div></div>"
        for l, val, x in tiles) + "</div>", unsafe_allow_html=True)

    # Why / against
    cols = st.columns(2)
    pros = "".join(f"<li>✅ {gloss(x)}</li>" for x in v["pros"]) or "<li>אין יתרונות בולטים כרגע.</li>"
    cons = "".join(f"<li>⚠️ {gloss(x)}</li>" for x in v["cons"]) or "<li>לא זוהו חסרונות בולטים.</li>"
    with cols[0]:
        _card(f"<div style='font-weight:700;font-size:17px'>מה בעד</div><ul class='s-list'>{pros}</ul>")
    with cols[1]:
        _card(f"<div style='font-weight:700;font-size:17px'>מה נגד</div><ul class='s-list'>{cons}</ul>")

    if v.get("conditions"):
        _card("<div style='font-weight:700;font-size:17px'>מה ישנה את התמונה</div><ul class='s-list'>"
              + "".join(f"<li>• {gloss(c)}</li>" for c in v["conditions"]) + "</ul>")

    hcol = TONE.get(v["holder_tone"], MUTED)
    _card(f"<div style='font-weight:700;font-size:17px'>ואם כבר יש לי את המניה?</div>"
          f"<div style='font-size:18px;font-weight:700;color:{hcol};margin-top:8px'>{v['holder_emoji']} {v['holder_label']}</div>"
          f"<div class='s-why'>{v['holder_why']}</div>", elev=True)

    ev = v.get("evidence")
    if ev:
        _card(f"<div style='font-weight:700;font-size:17px'>מה קרה בעבר במצבים דומים</div>"
              f"<div class='s-why'>בדקנו {ev['n']:,} מקרים שבהם מניות {ev['universe']} היו במצב טכני דומה "
              f"({ev['period']}). בשלושת החודשים שאחרי, המניה ירדה בממוצע בשלב כלשהו "
              f"<b>{abs(ev['avg_drawdown']):.0f}%</b> מתחת למחיר ההתחלה, וב-1 מכל 10 מקרים "
              f"היא סיימה את התקופה בירידה של <b>{abs(ev['p10_return']):.0f}% או יותר</b>.</div>"
              f"<div class='s-note'>המטרה היא להראות כמה תנודות צפויות בדרך, גם במניה טובה. "
              f"הבדיקה כוללת רק מניות שנמצאות היום במדד, ולכן היא אופטימית במקצת. "
              f"זה תיאור של העבר, לא תחזית. {term('איך זה נבדק?', 'בדיקה היסטורית')}</div>")

    _chart(rep.get("_hist"), v)
    st.markdown(f"<div class='s-note'>{v['reliability']['source_note']} · עודכן {v.get('as_of') or ''} · "
                f"מידע בלבד, לא ייעוץ השקעות.</div>", unsafe_allow_html=True)


def page_check(ctx):
    st.markdown("<div class='s-hero'>בדיקת מניה</div>"
                "<div class='s-sub'>כתבו שם חברה או סימול, בעברית או באנגלית</div>", unsafe_allow_html=True)
    q = st.text_input("חיפוש", key="s_query", placeholder="לדוגמה: אפל, Microsoft, טבע, NVDA",
                      label_visibility="collapsed")
    t = st.session_state.get("s_ticker")
    if q and q.strip() and q != st.session_state.get("_s_last_q"):
        st.session_state["_s_last_q"] = q
        hits = company_search.search(q, extra_names={k: r.get("Name") for k, r in ctx["rows"].items()})
        if len(hits) == 1 or (hits and hits[0]["match"] in ("סימול",) or
                              (len(hits) > 1 and hits[0]["match"] == "שם בעברית")):
            t = hits[0]["ticker"]
            st.session_state["s_ticker"] = t
        elif hits:
            st.session_state["s_ticker"] = None
            t = None
            st.session_state["_s_hits"] = hits
        else:
            guess = company_search.resolve(q)
            st.session_state["s_ticker"] = guess
            t = guess
    hits = st.session_state.get("_s_hits") if not t else None
    if hits:
        st.markdown("<div class='s-note'>למה התכוונתם?</div>", unsafe_allow_html=True)
        cols = st.columns(min(len(hits), 3))
        for i, h in enumerate(hits[:6]):
            if cols[i % len(cols)].button(f"{h['ticker']} · {h['name']}", key=f"hit_{h['ticker']}",
                                          use_container_width=True):
                st.session_state.pop("_s_hits", None)
                goto("check", h["ticker"])
        return
    if not t:
        st.markdown("<div class='s-note'>מניות מוכרות:</div>", unsafe_allow_html=True)
        cols = st.columns(4)
        for i, (tk, he) in enumerate(POPULAR):
            if cols[i % 4].button(f"{he}", key=f"pop_{tk}", use_container_width=True):
                goto("check", tk)
        return

    rep = ctx["analyze"](t)
    if rep.get("error"):
        st.error(f"לא מצאנו נתוני מחיר עבור '{t}'. בדקו את השם או הסימול.")
        return
    _analysis_block(t, rep, ctx["vmap"].get(t))

    mine = mywatch.items()
    c = st.columns(2)
    if t in mine:
        if c[0].button("★ במניות שלי — הסרה", key=f"rm_{t}", use_container_width=True):
            mywatch.remove(t)
            st.rerun()
    else:
        if c[0].button("⭐ שמירה במניות שלי", key=f"add_{t}", use_container_width=True):
            v = rep.get("verdict") or {}
            lv = v.get("levels") or {}
            mywatch.add(t, price=lv.get("price"), score_v2=v.get("quality"),
                        recommendation=v.get("label"), support=lv.get("support"))
            st.rerun()
    if c[1].button("🔬 לניתוח המקצועי המלא", key=f"pro_{t}", use_container_width=True):
        ctx["to_pro"](t)


def page_ideas(ctx):
    rows, vmap = ctx["rows"], ctx["vmap"]
    st.markdown("<div class='s-hero'>רעיונות להשקעה</div>"
                "<div class='s-sub'>מניות שהמערכת ניתחה לעומק היום, מסודרות לפי פסק הדין</div>",
                unsafe_allow_html=True)
    import stockdata
    pool = stockdata.ranked(vmap, rows, None)
    secs = sorted({market.SECTOR_EN_TO_HE.get(rows[v["ticker"]].get("Sector"), rows[v["ticker"]].get("Sector"))
                   for v in pool if rows[v["ticker"]].get("Sector")})
    c = st.columns(3)
    show = c[0].selectbox("להציג", ["שווה לשקול קנייה", "קנייה + להמתין", "הכול"], key="s_show")
    risk = c[1].selectbox("רמת סיכון", ["כל הרמות", "נמוכה בלבד", "עד בינונית"], key="s_risk")
    sec = c[2].selectbox("ענף", ["כל הענפים"] + secs, key="s_sec")
    allowed = {"שווה לשקול קנייה": ("buy",), "קנייה + להמתין": ("buy", "wait"),
               "הכול": ("buy", "wait", "avoid")}[show]
    rl = {"כל הרמות": None, "נמוכה בלבד": ("נמוך",), "עד בינונית": ("נמוך", "בינוני")}[risk]
    out = []
    for v in pool:
        r = rows[v["ticker"]]
        if v["action"] not in allowed:
            continue
        if rl and r.get("RiskLevel") not in rl:
            continue
        if sec != "כל הענפים" and market.SECTOR_EN_TO_HE.get(r.get("Sector"), r.get("Sector")) != sec:
            continue
        out.append(v)
    st.markdown(f"<div class='s-note'>{len(out)} מניות · פסק הדין זהה לזה שבתצוגה המקצועית</div>",
                unsafe_allow_html=True)
    if not out:
        _card("<div class='s-why'>אין מניות שמתאימות לסינון הזה. נסו להרחיב את רמת הסיכון או את הענף.</div>")
    for v in out[:25]:
        stock_card(v, rows.get(v["ticker"], {}), f"i_{v['ticker']}")


def page_mine(ctx):
    rows, vmap = ctx["rows"], ctx["vmap"]
    st.markdown("<div class='s-hero'>המניות שלי</div>"
                "<div class='s-sub'>מניות ששמרתם, ומה השתנה מאז. נשמר רק בדפדפן שלכם.</div>",
                unsafe_allow_html=True)
    items = mywatch.items()
    if not items:
        _card("<div class='s-why'>עוד לא שמרתם מניות. בעמוד 'בדיקת מניה' לחצו על ⭐ כדי לשמור מניה, "
              "ומכאן נעדכן אתכם מה השתנה מאז ומה כדאי לעשות.</div>")
        if st.button("🔎 לבדיקת מניה", key="mine_go", use_container_width=True):
            goto("check")
        return
    for tk, base in items.items():
        v = vmap.get(tk)
        r = rows.get(tk, {})
        price_now = _n(r.get("Price"))
        base_p = _n(base.get("price"))
        d = round((price_now / base_p - 1) * 100, 1) if price_now and base_p else None
        since = (f"מאז ששמרתם ({base.get('added', '')}): "
                 f"<b style='color:{POSITIVE if (d or 0) >= 0 else NEGATIVE}'>{d:+.1f}%</b>"
                 if d is not None else f"נשמרה ב-{base.get('added', '')}")
        if v:
            owned = bool(base.get("owned"))
            line = (f"{v['holder_emoji']} {v['holder_label']}" if owned else f"{v['emoji']} {v['label']}")
            col = TONE.get(v["holder_tone"] if owned else v["tone"], MUTED)
            why = v["holder_why"] if owned else v["why"]
            _card(f"<div class='s-row'><div><div class='s-tk'>{tk}</div>"
                  f"<div class='s-nm'>{company_search.display_name(tk, r.get('Name'))}</div></div>"
                  f"<div style='text-align:left;font-weight:700;color:{col}'>{line}</div></div>"
                  f"<div class='s-why'>{why}</div><div class='s-note'>מחיר {_money(price_now)} · {since}</div>")
        else:
            _card(f"<div class='s-tk'>{tk}</div><div class='s-why'>המניה לא נכללת בסריקה היומית. "
                  f"לחצו לפרטים כדי לקבל ניתוח עדכני.</div><div class='s-note'>{since}</div>")
        c = st.columns([2, 2, 1])
        own = c[0].toggle("יש לי את המניה", value=bool(base.get("owned")), key=f"own_{tk}")
        if own != bool(base.get("owned")):
            mywatch.set_owned(tk, own)
            st.rerun()
        if c[1].button("לפרטים ←", key=f"m_go_{tk}", use_container_width=True):
            goto("check", tk)
        if c[2].button("הסרה", key=f"m_rm_{tk}", use_container_width=True):
            mywatch.remove(tk)
            st.rerun()


def page_learn(ctx):
    st.markdown("<div class='s-hero'>מילון מונחים</div>"
                "<div class='s-sub'>כל מונח מקצועי במערכת, בשפה פשוטה, ולמה הוא חשוב לכם</div>",
                unsafe_allow_html=True)
    q = st.text_input("חיפוש מונח", key="s_gq", placeholder="לדוגמה: תמיכה, RSI, מכפיל",
                      label_visibility="collapsed").strip()
    for g, entries in glossary.by_group().items():
        hits = [e for e in entries if not q or q.lower() in (e["term"] + " " + " ".join(e.get("aliases", []))).lower()
                or q in e["plain"]]
        if not hits:
            continue
        st.markdown(f"<div class='s-h'>{g}</div>", unsafe_allow_html=True)
        for e in hits:
            with st.expander(e["term"] + (f"  ·  {', '.join(e['aliases'][:2])}" if e.get("aliases") else "")):
                st.markdown(f"<div class='s-why' style='margin-top:0'>{e['plain']}</div>"
                            f"<div class='s-note'><b>למה זה חשוב:</b> {e['why']}</div>", unsafe_allow_html=True)
    st.markdown("<div class='s-h'>איך המערכת מחליטה</div>", unsafe_allow_html=True)
    _card("<ul class='s-list'>"
          "<li>1. <b>האם החברה טובה?</b> ציון איכות 0–100 שמשקלל נתונים עסקיים, מגמה, ענף, חדשות וסיכון.</li>"
          "<li>2. <b>האם זה רגע טוב?</b> בודקים מגמה וכללי תזמון שנבדקו על נתוני עבר אמיתיים.</li>"
          "<li>3. <b>כמה אפשר לסמוך על הנתונים?</b> כשהנתונים לא מספיקים, המערכת לא נותנת המלצה.</li>"
          "</ul><div class='s-note'>מכאן יוצא פסק דין אחד: 🟢 שווה לשקול קנייה · 🟡 להמתין להזדמנות · "
          "🔴 לא עכשיו · ⚪ אין מספיק מידע. אותו פסק דין מופיע בכל מקום במערכת.</div>")


# ---------------------------------------------------------------- shell
def render(ctx, mobile: bool):
    st.markdown(CSS, unsafe_allow_html=True)
    st.session_state.setdefault("s_page", "today")
    keys = [p[0] for p in PAGES]
    labels = {p[0]: f"{p[1]} {p[2]}" for p in PAGES}
    cur = st.session_state["s_page"] if st.session_state["s_page"] in keys else "today"

    if mobile:
        with st.container(key="snav"):
            sel = st.radio("ניווט", keys, index=keys.index(cur), format_func=lambda k: labels[k],
                           horizontal=True, label_visibility="collapsed", key=f"snav_r_{cur}")
    else:
        st.sidebar.markdown(f"<div style='font-size:22px;font-weight:800;margin:4px 0 2px'>Stock Agent</div>"
                            f"<div style='color:{MUTED};font-size:13.5px;margin-bottom:12px'>מצב פשוט</div>",
                            unsafe_allow_html=True)
        sel = st.sidebar.radio("ניווט", keys, index=keys.index(cur), format_func=lambda k: labels[k],
                               label_visibility="collapsed", key=f"snav_d_{cur}")
        st.sidebar.divider()
        if st.sidebar.button("🔬 מעבר לתצוגה מקצועית", use_container_width=True, key="to_pro_side"):
            ctx["to_pro"](None)
        st.sidebar.caption("התצוגה המקצועית כוללת את כל הניתוחים, הגרפים והנתונים המלאים.")
    if sel != cur:
        st.session_state["s_page"] = sel
        if sel == "check":
            st.session_state.pop("_s_hits", None)
        st.rerun()

    {"today": page_today, "check": page_check, "ideas": page_ideas,
     "mine": page_mine, "learn": page_learn}[cur](ctx)

    st.divider()
    c = st.columns([3, 2])
    c[0].markdown(f"<div class='s-note'>Stock Agent מציג מידע ופסקי דין מבוססי נתונים. "
                  f"זה לא ייעוץ השקעות אישי, וההחלטה הסופית שלכם.</div>", unsafe_allow_html=True)
    if mobile and c[1].button("🔬 לתצוגה המקצועית", key="to_pro_foot", use_container_width=True):
        ctx["to_pro"](None)
