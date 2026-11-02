# -*- coding: utf-8 -*-
"""V4 company analysis: HTML sections, styled by dashboard/v4/css.py (.v4c-*).

Reading order: the decision first, then why and what would change it, then the
evidence (price and valuation, the chart, the business, the risks) for whoever
wants to go deeper. Everything from data is escaped. Numbers inside Hebrew
sentences go through ui.text so their sign stays on the right side.
"""
from dashboard.v4.ui import chip, esc, icon, term, text

TONE_MARK = {True: ("positive", "עובר"), False: ("negative", "לא עובר"), None: ("muted", "אין נתון")}


def head(h: dict) -> str:
    sub = " · ".join(esc(x) for x in (h["sector"], h.get("industry"), h.get("country")) if x)
    return (f'<div class="v4c-head"><div class="v4-ini lg" aria-hidden="true">{esc(h["ini"])}</div><div class="v4c-id">'
            f'<h1 class="v4-h1"><span class="nm">{esc(h["name"])}</span></h1>'
            f'<div class="v4c-sub"><span class="v4-num">{esc(h["ticker"])}</span> · {sub}</div></div>'
            f'<div class="v4c-px"><div class="v v4-num">{esc(h["price"])}</div>'
            f'<div class="c"><span class="v4-num t-{h["chg_tone"]}">{esc(h["chg"])}</span> · סגירה {esc(h["close"])}</div></div></div>')


def hero(dc: dict, facts_html: str = "", flag: str = "", stale: str = "") -> str:
    """The decision: label, one-line headline, the live engine's own reason, two answers."""
    answers = "".join(f'<div class="v4c-ans"><span class="q">{esc(a["q"])}</span>'
                      f'<b class="t-{a["tone"]}">{esc(a["a"])}</b></div>' for a in dc["answers"])
    note = ""
    if dc["status"] == "rated":
        note = ('<p class="v4c-lesson"><b>מה קבע את ההערכה:</b> ציון האיכות, המגמה והסיכון. '
                '<b>מידע משלים:</b> יעדי האנליסטים והערכת התמחור (מכפילי הרווח נכנסים לציון האיכות במשקל קטן, '
                'עד כ-4 נקודות מתוך 100). ההערכה היא סיווג לפי כללים קבועים, לא סיכוי שהמניה תעלה.</p>')
    ans = f'<div class="v4c-answers">{answers}</div>' if answers else ""
    if flag:
        ans += (f'<a class="v4c-flag" href="#v4c-price">{icon("info", 16, 2)}<span><b>שימו לב: </b>{text(flag)} '
                'זה לא משנה את הערכת ההשקעה. <u>לפירוט במחיר ותמחור</u></span></a>')
    if stale:
        ans += f'<div class="v4-stale" role="note">{icon("clock", 14, 2.2)}<span>{text(stale)}</span></div>'
    return (f'<section class="v4c-hero" id="v4c-decision" aria-labelledby="v4c-dh"><div class="v4c-hero-main">'
            f'<div class="v4c-eyebrow">הערכת ההשקעה של המערכת {chip(dc["label"], dc["tone"])}</div>'
            f'<h2 id="v4c-dh">{esc(dc["headline"])}</h2><p class="v4c-why">{text(dc["why"])}</p>{ans}{note}</div>'
            f'{facts_html}</section>')


def change_and_hold(dc: dict) -> str:
    """What would change the verdict (the live engine's own conditions) and guidance for holders."""
    if dc["status"] != "rated":
        return ""
    conds = "".join(f"<li>{text(c)}</li>" for c in dc["conditions"]) or "<li>אין תנאי מיוחד מעבר לכללים הקבועים.</li>"
    h = dc["holder"]
    return (f'<div class="v4c-duo"><section aria-labelledby="v4c-ch"><h3 id="v4c-ch">מה ישנה את ההערכה</h3><ul class="v4c-list">{conds}</ul></section>'
            f'<section aria-labelledby="v4c-hh"><h3 id="v4c-hh">מה הנתונים אומרים למי שמחזיק</h3>'
            f'<div><span class="v4-tag t-{h["tone"]} bg-{h["tone"]}">{esc(h["label"])}</span></div>'
            f'<p>{text(h["why"])}</p></section></div>')


def facts(rows: list, cls: str = "") -> str:
    body = "".join(f'<div class="f"><span class="k">{term(r["k"])}</span><b>{text(r["v"])}</b></div>' for r in rows)
    return f'<div class="v4c-facts {cls}">{body}</div>'


def section_nav(groups: list) -> str:
    """[(group label, [(anchor, label)])]: what decided the verdict, then supporting information."""
    out = ""
    for g, items in groups:
        links = "".join(f'<a href="#{esc(a)}">{esc(l)}</a>' for a, l in items)
        out += f'<span class="g">{esc(g)}</span>{links}'
    return f'<nav class="v4c-nav" aria-label="חלקי הניתוח">{out}</nav>'


def sec_open(sid: str, title: str, sub: str = "", badge: str = "") -> str:
    b = f'<span class="v4c-badge{" key" if badge.startswith("קובע") else ""}">{esc(badge)}</span>' if badge else ""
    s = f'<p class="v4c-secsub">{esc(sub)}</p>' if sub else ""
    return f'<div class="v4c-sechead" id="{esc(sid)}"><h2 class="v4-h2">{esc(title)}</h2>{b}</div>{s}'


def checks(cs: list, parts: dict | None, advanced: bool) -> str:
    if not cs:
        return ('<p class="v4c-p">המניה לא נכללה היום בניתוח המלא, ולכן אין לה ציון איכות ואין בדיקות להציג. '
                'כשהיא תיכלל בניתוח, כאן יופיעו ארבע הבדיקות שקובעות את ההערכה.</p>')
    rows = ""
    for c in cs:
        tone, word = TONE_MARK[c["ok"]]
        rule = f'<div class="r">{esc(c["rule"])}</div>' if advanced else ""
        rows += (f'<li><span class="m t-{tone} bg-{tone}">{icon({True: "check", False: "stop", None: "info"}[c["ok"]], 13)}{word}</span>'
                 f'<div class="b"><b>{term(c["name"])}</b><span>{esc(c["plain"])}</span>{rule}</div>'
                 f'<span class="val">{text(c["value"])}</span></li>')
    out = f'<ul class="v4c-checks">{rows}</ul>'
    if parts:
        if advanced:
            bars = "".join(f'<div class="v4c-part"><span class="n">{term(p["name"])}</span>'
                           f'<span class="v4-bar"><span class="dot-{"warning" if "מומנטום" in p["name"] else "muted"}" '
                           f'style="width:{max(2, (p["pts"] or 0) / parts["total"] * 100):.0f}%"></span></span>'
                           f'<b class="v4-num">{(p["pts"] or 0):.1f}</b></div>' for p in parts["parts"])
            share = parts["momentum_share"]
            note = (f"כ-{share}% מהציון מגיע ממומנטום (מצב טכני וחוזק הענף), ולא מהעסק עצמו. "
                    "לכן ציון האיכות של המנוע הפעיל מודד גם את התנועה של המניה.")
            out += (f'<div class="v4c-parts"><h3>ממה מורכב ציון האיכות ({parts["total"]:.0f})</h3>{bars}'
                    f'<p class="v4c-fine">{text(note)}</p></div>')
        else:
            note = (f"שימו לב: ציון האיכות משלב נתונים עסקיים ותנועת המחיר של המניה (כ-{parts['momentum_share']}% מהציון). "
                    "הפירוט המלא במצב מתקדם.")
            out += f'<p class="v4c-fine">{text(note)}</p>'

    return out


def price(ps: dict, advanced: bool) -> str:
    a = ps["analysts"]
    out = ""
    if a:
        pos = a["pos"]
        mark = lambda key, cls, label: (f'<span class="mk {cls}" style="left:{pos[key]}%"><span class="lbl">{label}</span></span>'
                                        if pos.get(key) is not None else "")
        band = (f'<span class="band" style="left:{pos["low"]}%;width:{pos["high"] - pos["low"]}%"></span>'
                if pos.get("low") is not None and pos.get("high") is not None else "")
        n = f' ({a["n"]} אנליסטים)' if a["n"] else ""
        out += (f'<div class="v4c-ptitle"><b>המחיר מול יעד האנליסטים</b><span>{text(a["plain"])}</span></div>'
                f'<div class="v4c-range" role="img" aria-label="מחיר היום {esc(a["price"])}, יעד ממוצע {esc(a["mean"])}, טווח {esc(a["low"])} עד {esc(a["high"])}">'
                f'<div class="track">{band}{mark("mean", "mean", "יעד ממוצע " + esc(a["mean"]))}{mark("price", "now", "היום " + esc(a["price"]))}</div>'
                f'<div class="ends"><span class="v4-num">{esc(a["low"])}</span><span>טווח היעדים{n}</span><span class="v4-num">{esc(a["high"])}</span></div></div>'
                '<details class="v4c-what"><summary>מה זה יעד אנליסטים?</summary><p>המחיר שהאנליסטים שמכסים את החברה מעריכים '
                'שהמניה תגיע אליו בעוד כשנה, בממוצע. זו הערכה חיצונית, לא הבטחה ולא תחזית של המערכת.</p></details>')
    else:
        out += '<div class="v4c-missing">יעדי אנליסטים לא זמינים למניה הזו. לא הצגנו הערכה במקומם.</div>'
    f = ps["facet"]
    if f["tone"] == "muted":
        out += ('<div class="v4c-pfacet"><div><b>ציון התמחור (מידע משלים)</b><span class="v4-tag t-muted bg-muted">לא חושבה</span></div>'
                '<p>המניה לא עברה ניתוח עסקי מלא, ולכן המערכת לא חישבה לה הערכת מחיר. המכפילים כאן הם נתונים גולמיים מ-Yahoo Finance.</p></div>')
    else:
        out += (f'<div class="v4c-pfacet"><div><b>ציון התמחור (מידע משלים)</b><span class="v4-tag t-{f["tone"]} bg-{f["tone"]}">{esc(f["label"])}</span></div>'
                f'<p>{text(f["basis"])}. מוצגת למידע בלבד, ולא משנה את הערכת ההשקעה.</p></div>')
    if ps["conflicts"]:
        first, rest = ps["conflicts"][0], ps["conflicts"][1:]
        out += f'<div class="v4c-conflict" role="note">{icon("alert", 16, 2)}<p><b>נתונים שלא מסתדרים: </b>{text(first)}</p></div>'
        if rest:
            more = "".join(f"<p>{text(c)}</p>" for c in rest)
            out += (f'<details class="v4c-what" {"open" if advanced else ""}><summary>עוד {len(rest)} '
                    f'{"סתירה" if len(rest) == 1 else "סתירות"} בנתוני התמחור</summary>{more}</details>')
    if ps["own_history"]:
        out += f'<p class="v4c-p">{text(ps["own_history"]["plain"])}</p>'
    ms = [m for m in ps["multiples"] if m["raw"] is not None]
    if advanced and ms:
        rows = "".join(f'<tr><td>{esc(m["name"])}</td><td class="v4-num">{esc(m["val"])}</td><td>{esc(m["expl"])}</td></tr>' for m in ps["multiples"])
        out += ('<div class="v4c-tblwrap"><table class="v4-tbl"><thead><tr><th>מכפיל</th><th>היום</th><th>מה הוא מודד</th></tr></thead>'
                f'<tbody>{rows}</tbody></table></div>')
    elif ms:
        main = [m for m in ms if m["key"] in ("fwd_pe", "peg")][:2]
        out += facts([{"k": m["name"], "v": m["val"]} for m in main], "inline")
        out += ('<details class="v4c-what"><summary>מה זה מכפיל רווח?</summary><p>כמה משלמים היום על כל דולר רווח של החברה. '
                'מכפיל גבוה אומר שהשוק מצפה לצמיחה, או שהמניה יקרה. כדאי להשוות לחברות דומות ולהיסטוריה של החברה עצמה.</p></details>')
    return out


def business(b: dict, advanced: bool) -> str:
    if not b["has_any"]:
        return '<div class="v4c-missing">הנתונים העסקיים של החברה לא זמינים כרגע. לא השלמנו אותם בהערכות.</div>'
    lines = "".join(f'<li><span class="d dot-{l["tone"]}" aria-hidden="true"></span><b>{term(l["k"])}</b><span>{text(l["text"])}</span></li>'
                    for l in b["lines"])
    out = f'<ul class="v4c-blines">{lines}</ul>' if lines else ""
    if b.get("note"):
        out += f'<div class="v4c-conflict" role="note">{icon("alert", 16, 2)}<p><b>נתונים שלא מסתדרים: </b>{text(b["note"])}</p></div>'
    if b["hist"]:
        bars = "".join(f'<div class="yr"><span class="y v4-num">{esc(h["year"])}</span><span class="v4-bar thick"><span class="dot-accent" style="width:{h["w"]}"></span></span>'
                       f'<b class="v4-num">{esc(h["rev_txt"])}</b><span class="g v4-num">{esc(h["growth"])}</span></div>' for h in b["hist"])
        out += (f'<div class="v4c-years"><div class="cap">מכירות לפי שנה פיסקלית · דוחות שנתיים שפורסמו (עבר)</div>{bars}</div>')
        if advanced:
            rows = "".join(f'<tr><td class="v4-num">{esc(h["year"])}</td><td class="v4-num">{esc(h["rev_txt"])}</td><td class="v4-num">{esc(h["growth"] or "—")}</td>'
                           f'<td class="v4-num">{esc(h["opm_txt"])}</td><td class="v4-num">{esc(h["eps_txt"])}</td><td class="v4-num">{esc(h["fcf_txt"])}</td></tr>'
                           for h in b["hist"])
            out += ('<div class="v4c-tblwrap"><table class="v4-tbl"><thead><tr><th>שנה</th><th>מכירות</th><th>צמיחה</th><th>רווח תפעולי</th>'
                    f'<th>רווח למניה</th><th>תזרים חופשי</th></tr></thead><tbody>{rows}</tbody></table></div>')
    if advanced:
        out += facts(b["metrics"], "grid")
    if b["date"]:
        out += f'<p class="v4c-fine">נתונים עסקיים מ-Yahoo Finance, נשמרו ב-{esc(b["date"])}. 12 החודשים האחרונים מבוססים על הדוחות האחרונים שפורסמו.</p>'
    return out


def risks(r: dict, advanced: bool) -> str:
    out = (f'<div class="v4c-rlevel"><span>רמת הסיכון של המניה</span>'
           f'<span class="v4-tag t-{r["level_tone"]} bg-{r["level_tone"]}">{esc(r["level"])}</span></div>')
    if r["items"]:
        out += "".join(f'<div class="v4c-risk"><span class="d dot-{i["tone"]}" aria-hidden="true"></span><div><b>{text(i["title"])}</b>'
                       + (f'<p>{text(i["text"])}</p>' if i["text"] else "") + '</div></div>' for i in r["items"])
    else:
        out += '<p class="v4c-p">אין כרגע סימני סיכון מיוחדים בנתונים, מעבר לסיכון הרגיל של השקעה במניה.</p>'
    if advanced:
        out += facts(r["metrics"], "inline")
    if r["sector"]:
        out += (f'<p class="v4c-fine"><b>סיכונים כלליים של הענף</b> (הערכה כללית, לא ניתוח של החברה): '
                f'{esc(", ".join(r["sector"]))}.</p>')
    return out


def about(a: dict, advanced: bool) -> str:
    out = f'<p class="v4c-p">{esc(a["line"])}</p>'
    if a["summary_he"]:
        out += (f'<details class="v4c-what" {"open" if advanced else ""}><summary>תיאור הפעילות</summary><p>{esc(a["summary_he"])}</p>'
                '<p class="v4c-fine">תרגום אוטומטי של התיאור שהחברה מסרה ל-Yahoo Finance.</p></details>')
    elif a["summary_en"]:
        out += (f'<details class="v4c-what"><summary>תיאור הפעילות (באנגלית)</summary><p dir="ltr" style="text-align:left">{esc(a["summary_en"])}</p></details>')
    else:
        out += '<p class="v4c-fine">תיאור מפורט של הפעילות לא זמין כרגע מהמקור.</p>'
    if a["employees"]:
        out += f'<p class="v4c-fine">עובדים: <span class="v4-num">{esc(a["employees"])}</span></p>'
    return out


def diffs(ds: list, date_txt: str, advanced: bool) -> str:
    if not ds:
        return ""
    if not advanced:
        return ('<p class="v4c-fine">חלק מהנתונים העסקיים התעדכנו אחרי הסריקה שעליה נשענת ההערכה. '
                'כאן מוצגים נתוני הסריקה, וההבדלים מפורטים במצב מתקדם.</p>')
    rows = "".join(f'<tr><td>{esc(x["name"])}</td><td class="v4-num">{esc(x["scan"])}</td><td class="v4-num">{esc(x["newer"])}</td></tr>' for x in ds)
    return ('<h3 class="v4c-h3">נתונים שהתעדכנו אחרי ההערכה</h3>'
            f'<div class="v4c-tblwrap"><table class="v4-tbl"><thead><tr><th>נתון</th><th>בסריקה (בסיס ההערכה)</th><th>עדכון {esc(date_txt)}</th></tr></thead>'
            f'<tbody>{rows}</tbody></table></div><p class="v4c-fine">ההערכה תתעדכן בסריקה היומית הבאה, לפי הכללים הקבועים.</p>')


def sources(src: list, rel: dict) -> str:
    rows = "".join(f'<tr><td>{esc(s["what"])}</td><td>{esc(s["src"])}</td><td class="v4-num">{esc(s["date"])}</td>'
                   f'<td>{"" if s["ok"] else "לא זמין"}{esc(s.get("note") or "")}</td></tr>' for s in src)
    reasons = " · ".join(esc(x) for x in rel.get("reasons") or [])
    return ('<div class="v4c-tblwrap"><table class="v4-tbl"><thead><tr><th>מה</th><th>מקור</th><th>תאריך</th><th>הערה</th></tr></thead>'
            f'<tbody>{rows}</tbody></table></div>'
            f'<p class="v4c-fine"><b>אמינות הנתונים {esc(rel.get("score") if rel.get("score") is not None else "—")} מתוך 100.</b> {reasons}</p>'
            '<p class="v4c-fine"><b>כיצד נקבעת הערכת ההשקעה?</b> "שווה לשקול קנייה" ניתן כשציון האיכות הוא 68 ומעלה, '
            'המחיר לא מתחת לממוצע של 200 יום, רמת הסיכון לא "גבוה מאוד", ואמינות הנתונים לפחות 55. '
            'ציון האיכות משקלל נתונים עסקיים 35%, מצב טכני 25%, חוזק ענף 20%, חדשות 10% וסיכון 10%. '
            'כללי תזמון נוספים נבדקו במחקר ההיסטורי ולא שיפרו תוצאות, ולכן אינם פעילים. '
            'מנוע ארבעת הממדים רץ במקביל במעקב בלבד, ואינו מוצג כאן.</p>')
