# -*- coding: utf-8 -*-
"""V4 alerts screen: HTML pieces, styled by dashboard/v4/css.py (.v4a-*)."""
from dashboard.v4.alerts_data import GROUPS, RULES
from dashboard.v4.ui import chip, esc, text

TONE = {"critical": "negative", "important": "warning", "info": "muted"}


def group_head(key: str, n: int) -> str:
    label, sub = next((l, s) for k, l, s in GROUPS if k == key)
    return (f'<div class="v4a-gh"><span class="v4-tag t-{TONE[key]} bg-{TONE[key]}">{esc(label)}</span>'
            f'<span class="sub">{esc(sub)} · {n}</span></div>')


def card(i: dict, advanced: bool) -> str:
    meta = " · ".join(esc(x) for x in (i["kind"], i["ticker"], i["date"]) if x)
    tag = chip(i["tag"]["label"], i["tag"]["tone"]) if i.get("tag") and i["tag"].get("label") else ""
    raw = f'<div class="raw">מקור ההתראה: {text(i["raw"])}</div>' if advanced and i["raw"] else ""
    return (f'<div class="v4a-card g-{i["group"]}"><div class="top"><span class="meta">{meta}</span>{tag}</div>'
            f'<h3>{text(i["title"])}</h3><p>{text(i["text"])}</p>{raw}</div>')


def rules(advanced: bool) -> str:
    if advanced:
        rows = "".join(f'<tr><td>{esc(k)}</td><td>{esc(s)}</td><td>{text(r)}</td></tr>' for k, s, r in RULES)
        body = ('<div class="v4c-tblwrap"><table class="v4-tbl"><thead><tr><th>סוג</th><th>חשיבות</th><th>מתי נוצרת</th></tr></thead>'
                f'<tbody>{rows}</tbody></table></div>')
    else:
        body = ''.join(f'<p class="v4c-p"><b>{esc(l)}:</b> {esc(d)}.</p>' for _, l, d in (
            ("", "קריטי", "סיכון גבוה במגמת ירידה, או הורדת המלצה של בית השקעות. כדאי לבדוק היום"),
            ("", "חשוב", "אירוע שיכול להזיז את המחיר, כמו דוחות בשבוע הקרוב או נפח מסחר חריג"),
            ("", "מידע", "רקע: פריצה טכנית, שדרוג או כיסוי חדש, וענפים חזקים וחלשים")))
    return ('<section class="v4m-sec" aria-labelledby="v4a-r-h"><h2 class="v4-h3" id="v4a-r-h">איך מסווגות ההתראות</h2>'
            f'{body}<p class="v4c-fine">התראה היא מידע, לא המלצה. התג שליד כל מניה הוא הערכת ההשקעה הנוכחית שלה, '
            'זהה לזו שבשאר המסכים.</p></section>')
