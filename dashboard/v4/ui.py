# -*- coding: utf-8 -*-
"""V4 shared components: small HTML builders styled by dashboard/v4/css.py.

Everything that comes from data is escaped. Tones are one of tokens.TONES and
map to the .t-/.bg-/.dot- classes, so colour always carries a word next to it.
"""
import re
from html import escape as _e

ICONS = {
    "check": '<path d="M5 12.5l4.5 4.5L19 7.5"></path>',
    "clock": '<circle cx="12" cy="12" r="8.5"></circle><path d="M12 7.5V12l3 2"></path>',
    "stop": '<circle cx="12" cy="12" r="8.5"></circle><path d="M8.5 15.5l7-7"></path>',
    "info": '<circle cx="12" cy="12" r="8.5"></circle><path d="M12 11v5M12 8h.01"></path>',
    "logo": '<path d="M3 17l5-5 4 4 8-8"></path><path d="M15 8h5v5"></path>',
    "alert": '<path d="M12 4l9 16H3z"></path><path d="M12 10v4M12 17h.01"></path>',
}
TONE_ICON = {"positive": "check", "warning": "clock", "negative": "stop", "muted": "info"}


def esc(x) -> str:
    return _e("" if x is None else str(x))


_NUM = re.compile(r"(?:(?<!\w)[+\-−])?\$?\d(?:[\d,./:]*\d)?(?:%|[KMBT](?![A-Za-z]))?")        # "כ-38": a hyphen after a letter is not a minus


# A Latin phrase with the numbers inside it ("S&P 500", "Q3 2026", "Oil &amp; Gas"): one left to
# right run. Isolating only its number would let the Hebrew around it flip the order
# ("500 S&P"). Runs over escaped text, so "&amp;" is part of the phrase.
_LAT = r"[A-Za-z][A-Za-z0-9&;#.'’/\-]*(?: [A-Za-z0-9&;#.'’/\-]*[A-Za-z0-9;])*"
_RUN = re.compile(f"{_LAT}|{_NUM.pattern}")


def text(x) -> str:
    """Escaped running text with every number and Latin phrase isolated left to right,
    so "+39.1%" never turns into "39.1%+" inside a Hebrew sentence."""
    # quote=False: text content needs no quote entities, and the digits of "&#x27;" would
    # otherwise be wrapped as a number and break the entity on screen.
    return _RUN.sub(lambda m: f'<span class="v4-num">{m.group(0)}</span>', _e("" if x is None else str(x), quote=False))


# Screen labels that name a glossary term in other words. Labels equal to a term or
# one of its aliases are found without being listed here.
TERM_OF = {
    "איכות החברה": "ציון איכות", "סיכון": "רמת סיכון", "יעד אנליסטים ממוצע": "מחיר יעד",
    "צמיחת מכירות (רבעון מול אשתקד)": "צמיחת הכנסות", "צמיחה": "צמיחת הכנסות",
    "רווח תפעולי מהמכירות": "שולי רווח", "רווח נקי מהמכירות": "שולי רווח", "רווחיות": "שולי רווח",
    "תזרים חופשי": "תזרים מזומנים חופשי", "חוב להון": "חוב/הון", "חוב": "חוב/הון",
    "מכפיל רווח עתידי": "מכפיל עתידי", "מכפיל רווח": "מכפיל רווח", "מצב טכני (מומנטום)": "מומנטום",
    "תנודתיות שנתית (שנה אחרונה)": "תנודתיות", "ירידה מקסימלית (שנה אחרונה)": "ירידה מקסימלית",
    "בטא (רגישות לשוק)": "ביתא", "שווי שוק": "שווי שוק", "ענף": "סקטור",
}


def term(label: str, key: str | None = None) -> str:
    """A label with its short glossary explanation, opened by hover, focus or a tap,
    and a link to the full entry. Plain escaped text when the glossary has no entry."""
    import glossary
    e = glossary.lookup(key or TERM_OF.get(label) or label)
    if not e:
        return esc(label)
    from urllib.parse import quote
    return (f'<span class="v4-term" tabindex="0">{esc(label)}<span class="v4-tip" role="tooltip">'
            f'<b>{esc(e["term"])}</b> {text(e["short"])} '
            f'<a href="glossary?q={quote(e["term"], safe="")}" target="_self">במילון ‹</a></span></span>')


def icon(name: str, size: int = 14, stroke: float = 2.6) -> str:
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="{stroke}" aria-hidden="true">{ICONS[name]}</svg>')


def chip(label: str, tone: str) -> str:
    tone = tone if tone in ("positive", "warning", "negative") else "muted"
    return f'<span class="v4-chip t-{tone} bg-{tone}">{icon(TONE_ICON[tone])}{esc(label)}</span>'


def brand() -> str:
    return (f'<div class="v4-brand"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" '
            f'stroke-width="2" aria-hidden="true">{ICONS["logo"]}</svg>Stock Agent</div>')


def page_head(title: str, sub: str) -> str:
    return f'<h1 class="v4-h1">{esc(title)}</h1><div class="v4-sub">{esc(sub)}</div>'


def hero(s: dict, more: bool = True) -> str:
    states = [("positive", "חיובי"), ("neutral", "ניטרלי"), ("negative", "שלילי")]
    tone = {"positive": "positive", "neutral": "warning", "negative": "negative"}.get(s["state"], "muted")
    pills = "".join(
        f'<span class="{"on t-" + tone + " bg-" + tone if k == s["state"] else "off"}">{esc(lbl)}</span>' for k, lbl in states)
    figs = ""
    if s["status"] == "ok":
        rows = "".join(
            f'<div class="v4-fig"><span class="k">{esc(f["name"])}</span><span><span class="v">{text(f["val"])}</span>'
            f'<span class="c v4-num t-{f["tone"]}">{esc(f["chg"])}</span></span></div>' for f in s["figures"])
        more_html = '<span class="more">פירוט מלא במצב מתקדם</span>' if more else ""
        figs = f'<div class="v4-figs">{rows}{more_html}</div>'
    else:
        figs = f'<div class="v4-notice" role="status">{esc(s["message"])}</div>'
    body = f'<p>{esc(s["body"])}</p>' if s["body"] else ""
    return (f'<section class="v4-hero" aria-labelledby="v4-mk-h"><div>'
            f'<div class="v4-hero-k"><span class="v4-eyebrow">מצב השוק</span>'
            f'<div class="v4-states" role="img" aria-label="מצב השוק: {esc(s["label"])}">{pills}</div></div>'
            f'<h2 id="v4-mk-h">{esc(s["headline"])}</h2>{body}</div>{figs}</section>')


def section_head(title: str, sub: str = "", hid: str = "") -> str:
    sub_html = f'<div class="v4-muted">{esc(sub)}</div>' if sub else ""
    return f'<div class="v4-sec"><h2 class="v4-h2" id="{esc(hid)}">{esc(title)}</h2>{sub_html}</div>'


def pick_card(c: dict, advanced: bool = False) -> str:
    if c.get("calm") and not advanced:
        # Nothing to flag: one quiet line instead of four green dots. Every answer is still written out.
        answers = " · ".join(f'{esc(d["k"])} {esc(d["v"])}' for d in c["dims"])
        dims_html = (f'<div class="v4-calm" aria-label="ארבע התשובות">{icon("check", 13, 2.6)}'
                     f'<span>{answers}</span></div>')
    else:
        dims = "".join(f'<li><span class="d dot-{d["tone"]}" aria-hidden="true"></span><span class="k">{esc(d["k"])}</span>'
                       f'<b>{esc(d["v"])}</b></li>' for d in c["dims"])
        dims_html = f'<ul class="v4-dims" aria-label="ארבע התשובות">{dims}</ul>'
    meta = ""
    if advanced:
        q = "—" if c.get("quality") is None else f'{c["quality"]:.0f}'
        r = "—" if c.get("reliability") is None else str(c["reliability"])
        meta = (f'<div class="v4-meta">{term("ציון איכות")} {q} מתוך 100 · '
                f'{term("אמינות הנתונים")} {r} מתוך 100</div>')
    return (f'<div class="v4-pick-top"><div class="v4-co"><div class="v4-ini" aria-hidden="true">{esc(c["ini"])}</div>'
            f'<div style="min-width:0"><div class="v4-co-name">{esc(c["name"])}</div>'
            f'<div class="v4-co-tk"><span class="v4-num">{esc(c["ticker"])}</span> · {esc(c.get("sector"))}</div></div></div>'
            f'<div class="v4-pick-px"><div class="v4-px"><div class="v v4-num">{esc(c["price"])}</div>'
            f'<div class="c v4-num t-{c["chg_tone"]}">{esc(c["chg"])}</div></div>{chip(c["label"], c["tone"])}</div></div>'
            f'<p class="v4-why">{text(c["why"])}</p>{stale(c.get("stale"))}{dims_html}{meta}')


def data_banner(text_: str) -> str:
    return (f'<div class="v4-databanner" role="alert">{icon("clock", 16, 2.2)}<span>{text(text_)}</span></div>'
            if text_ else "")


def stale(note: str) -> str:
    return f'<div class="v4-stale" role="note">{icon("clock", 14, 2.2)}<span>{text(note)}</span></div>' if note else ""


def note(body: str, detail: str = "", mix: list | None = None) -> str:
    """A quiet explanatory note (e.g. why the picks share a sector)."""
    d = f'<div class="v4-note-d">{text(detail)}</div>' if detail else ""
    m = ""
    if mix:
        m = '<div class="v4-note-d">' + " · ".join(f'{esc(x["name"])} {x["n"]}' for x in mix) + "</div>"
    return (f'<div class="v4-note" role="note"><span class="v4-note-i">{icon("info", 18, 2)}</span>'
            f'<div><p>{text(body)}</p>{d}{m}</div></div>')


def week_panel(items: list) -> str:
    if not items:
        body = '<div class="v4-empty"><b>אין אירועים מיוחדים השבוע</b>אין דוחות או שינויים חדים בשבוע הקרוב.</div>'
    else:
        body = "".join(f'<div class="v4-wk"><div class="v4-date"><div class="d">{esc(w["day"])}</div><div class="n">{esc(w["date"])}</div></div>'
                       f'<div class="v4-wk-t"><b>{esc(w["title"])}</b><div>{esc(w["text"])}</div></div></div>' for w in items)
    return f'<section class="v4-panel" aria-labelledby="v4-wk-h"><div class="v4-panel-head"><h2 class="v4-h3" id="v4-wk-h">מה חשוב השבוע</h2></div>{body}</section>'


def market_table(rows: list) -> str:
    if not rows:
        return ""
    body = "".join(f'<tr><td>{esc(r["name"])}</td><td class="v4-num">{esc(r["val"])}</td><td class="v4-num t-{r["d1_tone"]}">{esc(r["d1"])}</td>'
                   f'<td class="v4-num">{esc(r["d30"])}</td><td>{esc(r["trend"])}</td></tr>' for r in rows)
    return ('<section class="v4-panel" aria-labelledby="v4-mt-h"><div class="v4-panel-head"><h2 class="v4-h3" id="v4-mt-h">נתוני שוק מלאים</h2></div>'
            '<div style="overflow-x:auto"><table class="v4-tbl"><thead><tr><th>נכס</th><th>ערך</th><th>יומי</th><th>חודש</th><th>מגמה</th></tr></thead>'
            f'<tbody>{body}</tbody></table></div></section>')


def sector_panel(rows: list) -> str:
    if not rows:
        return ""
    body = "".join(f'<div class="v4-row"><span style="flex:0 0 120px">{esc(s["name"])}</span>'
                   f'<span class="v4-bar" style="flex:1" role="img" aria-label="חוזק {s["score"]} מתוך 100"><span class="dot-{s["tone"]}" style="width:{s["w"]}"></span></span>'
                   f'<b class="v4-num" style="flex:0 0 32px;text-align:left">{s["score"]}</b></div>' for s in rows)
    return ('<section class="v4-panel" aria-labelledby="v4-sc-h"><div class="v4-panel-head"><h2 class="v4-h3" id="v4-sc-h">חוזק ענפים</h2></div>'
            '<div class="v4-method" style="margin-bottom:6px">מגמה, מומנטום וחוזק יחסי של תעודות סל ענפיות. אומדן, לא מדידה של תנועות כסף.</div>'
            f'{body}</section>')


def method_note(coverage: str = "") -> str:
    cov = f" {esc(coverage)}" if coverage else ""
    return ('<section class="v4-panel"><h2 class="v4-h3">איך נבחרו המניות</h2><div class="v4-method">'
            'אלה הערכות ההשקעה של המנוע הפעיל: "שווה לשקול קנייה" ניתן לחברה בציון איכות של 68 ומעלה, '
            'כשהמגמה לא יורדת ורמת הסיכון לא גבוהה מאוד. המניות ממוינות לפי ציון האיכות ואז לפי אמינות הנתונים. '
            f'ההערכה זהה בכל המסכים.{cov}</div></section>')


# ------------------------------------------------------------------ opportunities
def _dims_cells(dims: list) -> str:
    return "".join(f'<div class="c"><span class="d dot-{d["tone"]}" aria-hidden="true"></span>'
                   f'<span class="sr">{esc(d["k"])}: </span><b>{esc(d["v"])}</b></div>' for d in dims)


def opp_head(advanced: bool = False) -> str:
    extra = '<div class="c">איכות</div>' if advanced else ""
    tail = '<div class="c">אמינות</div>' if advanced else ""
    return (f'<div class="v4-orow v4-ohead{" adv" if advanced else ""}" aria-hidden="true"><div class="c">מניה</div><div class="c">שער היום</div>{extra}'
            '<div class="c">החברה</div><div class="c">המגמה</div><div class="c">הסיכון</div><div class="c">המחיר (משלים)</div>'
            f'{tail}<div class="c">למה היא כאן</div></div>')


def opp_row(r: dict, advanced: bool = False) -> str:
    """One stock: a table row on desktop and a card on the phone (CSS picks one)."""
    q = "—" if r.get("quality") is None else f'{r["quality"]:.0f}'
    rel = "—" if r.get("reliability") is None else str(r["reliability"])
    co = (f'<div class="v4-ini sm" aria-hidden="true">{esc(r["ini"])}</div><div style="min-width:0">'
          f'<div class="n">{esc(r["name"])}</div><div class="s"><span class="v4-num">{esc(r["ticker"])}</span> · {esc(r["sector"])}</div></div>')
    px = f'<div class="v4-num p">{esc(r["price"])}</div><div class="v4-num ch t-{r["chg_tone"]}">{esc(r["chg"])}</div>'
    extra = f'<div class="c v4-num sc">{q}</div>' if advanced else ""
    tail = f'<div class="c v4-num sc">{rel}</div>' if advanced else ""
    clock = (f'<span class="v4-term v4-stale-i" tabindex="0" aria-label="{esc(r["stale"])}">{icon("clock", 14, 2.2)}'
             f'<span class="v4-tip" role="tooltip">{text(r["stale"])}</span></span>' if r.get("stale") else "")
    co_row = co[:-len("</div>")] + clock + "</div>"           # the clock after the ticker line
    grid = (f'<div class="v4-orow{" adv" if advanced else ""}"><div class="c co">{co_row}</div><div class="c px">{px}</div>{extra}'
            f'{_dims_cells(r["dims"])}{tail}<div class="c why"><span class="wt">{text(r["why"])}</span></div></div>')
    dims = "".join(f'<li><span class="d dot-{d["tone"]}" aria-hidden="true"></span><span class="k">{esc(d["k"])}</span>'
                   f'<b>{esc(d["v"])}</b></li>' for d in r["dims"])
    meta = f'<div class="v4-meta">ציון איכות {q} · אמינות {rel}</div>' if advanced else ""
    card = (f'<div class="v4-ocard"><div class="top"><div class="v4-co">{co}</div><div class="v4-px">{px}</div></div>'
            f'<p>{text(r["why"])}</p>{stale(r.get("stale"))}<ul class="v4-dims">{dims}</ul>{meta}</div>')
    return grid + card


def legend() -> str:
    items = [("positive", "חיובי"), ("warning", "שווה תשומת לב"), ("negative", "שלילי")]
    dots = "".join(f'<span><span class="d dot-{t}" aria-hidden="true"></span>{esc(l)}</span>' for t, l in items)
    return (f'<div class="v4-legend">{dots}<span>החברה, המגמה והסיכון קובעים את ההערכה. המחיר מידע משלים.</span>'
            '<span>לחיצה על שורה פותחת את הניתוח המלא</span></div>')


def mix_panel(title: str, rows: list, text: str = "") -> str:
    if not rows:
        return ""
    body = "".join(f'<div class="v4-row"><span style="flex:0 0 120px">{esc(s["name"])}</span>'
                   f'<span class="v4-bar" style="flex:1" role="img" aria-label="{s["n"]} מניות"><span class="dot-muted" style="width:{s["w"]}"></span></span>'
                   f'<b class="v4-num" style="flex:0 0 32px;text-align:left">{s["n"]}</b></div>' for s in rows)
    t = f'<div class="v4-method" style="margin-bottom:6px">{esc(text)}</div>' if text else ""
    return (f'<section class="v4-panel"><div class="v4-panel-head"><h2 class="v4-h3">{esc(title)}</h2></div>{t}{body}</section>')


def footer(f: dict) -> str:
    tone = {"גבוהה": "positive", "בינונית": "warning", "נמוכה": "negative"}.get(f["rel_label"], "muted")
    return (f'<footer class="v4-footer"><span>אמינות הנתונים: <b class="t-{tone}">{esc(f["rel_label"])}</b> · '
            f'סגירת המסחר {esc(f["close"])} · נתוני שוק עודכנו {esc(f["market_updated"])} · מקור יחיד: Yahoo Finance, בלי אימות צולב</span>'
            '<span>ניתוח מבוסס נתונים, לא ייעוץ השקעות אישי.</span></footer>')


# ------------------------------------------------------------------ states
def empty(title: str, text: str) -> str:
    return f'<div class="v4-card v4-empty"><b>{esc(title)}</b>{esc(text)}</div>'


def error(title: str, text: str) -> str:
    return (f'<div class="v4-card" role="alert" style="display:flex;gap:12px;align-items:flex-start">'
            f'<span class="t-negative">{icon("alert", 20, 2)}</span><div><b>{esc(title)}</b>'
            f'<div class="v4-muted">{esc(text)}</div></div></div>')


def skeleton_cards(n: int = 3) -> str:
    one = ('<div class="v4-card" style="margin-bottom:14px" aria-hidden="true"><div style="display:flex;gap:12px;align-items:center">'
           '<div class="v4-skel" style="width:44px;height:44px;border-radius:12px"></div><div style="flex:1">'
           '<div class="v4-skel" style="width:40%;height:16px;margin-bottom:8px"></div><div class="v4-skel" style="width:20%;height:12px"></div></div></div>'
           '<div class="v4-skel" style="width:90%;height:14px;margin:16px 0 8px"></div><div class="v4-skel" style="width:70%;height:14px"></div></div>')
    return '<div role="status" aria-label="טוען">' + one * n + '</div>'
