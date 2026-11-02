# -*- coding: utf-8 -*-
"""V4 markets screen: HTML sections, styled by dashboard/v4/css.py (.v4m-*)."""
from dashboard.v4.ui import esc, icon, text

STATUS = {"verify": ("warning", "דורש אימות"), "missing": ("muted", "אין נתון")}


def asset_table(sec: dict, advanced: bool) -> str:
    head = ('<tr><th>נכס</th><th>שער</th><th>היום</th>'
            + ('<th class="adv">שבוע</th><th class="adv">חודש</th><th class="adv">נכון ל-</th>' if advanced else "")
            + '<th class="tr">מגמה</th></tr>')
    body = ""
    for r in sec["rows"]:
        if r["status"] != "ok":
            tone, word = STATUS[r["status"]]
            why = f'<div class="why">{esc(r["why"])}</div>' if advanced and r["why"] else ""
            span = 6 if advanced else 3
            body += (f'<tr class="na"><td>{esc(r["name"])}{why}</td><td colspan="{span}">'
                     f'<span class="v4-tag t-{tone} bg-{tone}">{esc(word)}</span></td></tr>')
            continue
        body += (f'<tr><td>{esc(r["name"])}</td><td class="v4-num">{esc(r["val"])}</td>'
                 f'<td class="t-{r["d1_tone"]}">{text(r["d1"])}</td>'
                 + (f'<td class="v4-num adv">{esc(r["d7"])}</td><td class="v4-num adv">{esc(r["d30"])}</td>'
                    f'<td class="v4-num adv">{esc(r["as_of"])}</td>' if advanced else "")
                 + f'<td class="tr t-{r.get("trend_tone", "muted")}">{esc(r["trend"] or "—")}</td></tr>')
    note = f'<p class="v4c-fine">{text(sec["note"])}</p>' if sec["note"] else ""
    bp = ('<p class="v4c-fine">בתשואות האג״ח השינוי מוצג בנקודות בסיס (נ״ב): מאית של נקודת אחוז. '
          'ירידה של 6 נ״ב היא ירידה מ-4.99% ל-4.93%.</p>' if sec["has_bp"] and advanced else "")
    return (f'<section class="v4m-sec" aria-labelledby="v4m-{sec["key"]}"><h2 class="v4-h3" id="v4m-{sec["key"]}">{esc(sec["title"])}</h2>'
            f'<p class="v4m-sum">{text(sec["summary"])}</p><div class="v4c-tblwrap"><table class="v4-tbl v4m-tbl">'
            f'<thead>{head}</thead><tbody>{body}</tbody></table></div>{note}{bp}</section>')


def sectors(s: dict, advanced: bool, date_txt: str) -> str:
    li = lambda r: (f'<li><span>{esc(r["name"])}</span><span class="v4-tag t-{r["tone"]} bg-{r["tone"]}">{esc(r["word"])}</span></li>')
    up = "".join(li(r) for r in (s["up"] if advanced else s["up"][:4])) or "<li><span>אין ענף חזק במיוחד כרגע</span></li>"
    down = "".join(li(r) for r in s["down"]) or "<li><span>אין ענף חלש במיוחד כרגע</span></li>"
    out = (f'<section class="v4m-sec" aria-labelledby="v4m-sec-h"><h2 class="v4-h3" id="v4m-sec-h">ענפים חזקים וחלשים</h2>'
           '<p class="v4m-sum">חוזק הענפים לפי מגמה ומומנטום של תעודות סל ענפיות. אומדן של המערכת, לא מדידה של תנועות כסף.</p>'
           f'<div class="v4m-two"><div><h3>החזקים כרגע</h3><ul class="v4m-list">{up}</ul></div>'
           f'<div><h3>החלשים כרגע</h3><ul class="v4m-list">{down}</ul></div></div>')
    if advanced and s["all"]:
        rows = "".join(f'<tr><td>{esc(r["name"])}</td><td class="v4-num">{esc(r["etf"])}</td><td class="v4-num">{r["score"]:.0f}</td>'
                       f'<td class="v4-num">{esc(r["d1"])}</td><td class="v4-num">{esc(r["m1"])}</td><td class="v4-num">{esc(r["m3"])}</td>'
                       f'<td class="v4-num">{esc(r["rs"])}</td><td>{esc(r["trend"])}</td></tr>' for r in s["all"] if r["score"] is not None)
        out += ('<div class="v4c-tblwrap"><table class="v4-tbl"><thead><tr><th>ענף</th><th>תעודת סל</th><th>ציון</th><th>היום</th>'
                '<th>חודש</th><th>3 חודשים</th><th>חוזק יחסי</th><th>מגמה</th></tr></thead>'
                f'<tbody>{rows}</tbody></table></div>'
                '<p class="v4c-fine">ציון 0 עד 100 מחושב מהמגמה, המומנטום והחוזק היחסי של תעודת הסל מול S&amp;P 500. '
                'חוזק יחסי: התשואה של הענף פחות התשואה של המדד.</p>')
    out += f'<p class="v4c-fine">חישוב של המערכת מ-{esc(date_txt)}.</p></section>'
    return out


def breadth(b: dict | None, advanced: bool) -> str:
    if not b:
        return ""
    items = "".join(f'<div class="v4m-stat"><span class="k">{esc(i["k"])}</span><b class="v4-num">{esc(i["v"])}</b>'
                    f'<span class="t">{text(i["text"])}</span></div>' for i in b["items"])
    base = f"מתוך {b['n']} המניות שהמערכת עוקבת אחריהן מקרוב" if b["n"] else "מתוך המניות שהמערכת עוקבת אחריהן מקרוב"
    m = f'<p class="v4c-fine">{text(b["method"])}</p>' if advanced and b["method"] else ""
    return (f'<section class="v4m-sec" aria-labelledby="v4m-br-h"><h2 class="v4-h3" id="v4m-br-h">כמה מניות משתתפות</h2>'
            f'<p class="v4m-sum">{esc(base)}. מדגם קטן, ולכן זה סימן כללי בלבד ולא מדידה של כל השוק.</p>'
            f'<div class="v4m-stats">{items}</div>{m}</section>')


def validation(v: dict, advanced: bool) -> str:
    if v["status"] != "ok":
        return ""
    issues = v["issues"]
    if not issues:
        body = "כל הנתונים במסך עברו בדיקת תקינות."
    else:
        names = " · ".join(f'{esc(i["name"])} ({"דורש אימות" if i["status"] == "verify" else "אין נתון"})' for i in issues)
        body = f"{v['ok']} נתונים עברו בדיקת תקינות. לא אומתו: {names}."
    extra = ""
    if advanced:
        extra = ('<p class="v4c-fine">הבדיקה: הקובץ עודכן בארבעת הימים האחרונים, כל ערך בטווח סביר לנכס שלו, '
                 'וכל ערך התעדכן עד 5 ימים לפני העדכון. ערך שלא עבר מוצג "דורש אימות", וערך שהמקור לא החזיר מוצג "אין נתון", '
                 'אף פעם לא כמספר.</p>')
    return (f'<div class="v4m-valid" role="note">{icon("check", 16, 2.4)}<div><p><b>נתוני שוק עודכנו {esc(v["updated"])}. </b>'
            f'{body} מקור: Yahoo Finance.</p>{extra}</div></div>')


def history(rows: list) -> str:
    body = ""
    for r in rows:
        if r["status"] != "ok":
            tone, word = STATUS.get(r["status"], ("muted", "אין נתון"))
            body += (f'<tr class="na"><td>{esc(r["name"])}<div class="why">{esc(r["why"])}</div></td>'
                     f'<td colspan="5"><span class="v4-tag t-{tone} bg-{tone}">{esc(word)}</span></td></tr>')
            continue
        bar = (f'<span class="v4-bar" role="img" aria-label="{r["pos"]}% מהטווח"><span class="dot-accent" style="width:{max(3, r["pos"])}%"></span></span>'
               if r["pos"] is not None else "—")
        body += (f'<tr><td>{esc(r["name"])}</td><td class="v4-num">{esc(r["val"])}</td><td>{text(r["m3"])}</td><td>{text(r["y1"])}</td>'
                 f'<td>{text(r["lo"] + " עד " + r["hi"])}</td><td class="pos">{bar}</td></tr>')
    return ('<section class="v4m-sec" aria-labelledby="v4m-hist-h"><h2 class="v4-h3" id="v4m-hist-h">השוואה היסטורית</h2>'
            '<p class="v4m-sum">איפה כל נכס עומד היום ביחס לשלושה חודשים, לשנה ולטווח של 52 השבועות האחרונים. נתוני עבר בלבד.</p>'
            '<div class="v4c-tblwrap"><table class="v4-tbl v4m-tbl"><thead><tr><th>נכס</th><th>היום</th><th>3 חודשים</th><th>שנה</th>'
            f'<th>טווח 52 שבועות</th><th>מיקום בטווח</th></tr></thead><tbody>{body}</tbody></table></div>'
            '<p class="v4c-fine">שליפה חיה של מחירי סגירה מ-Yahoo Finance. נכס מוצג רק כשההיסטוריה תואמת, עד 1% באותו יום, '
            'לערך היומי שעבר את בדיקת התקינות. בתשואות אג״ח השינוי בנקודות בסיס. מיקום בטווח: 0% בשפל השנתי, 100% בשיא.</p></section>')


def methods(mkt: dict) -> str:
    reg, fg = mkt.get("regime") or {}, mkt.get("fear_greed") or {}
    return ('<section class="v4m-sec" aria-labelledby="v4m-me-h"><h2 class="v4-h3" id="v4m-me-h">איך מחושבים המדדים של המערכת</h2>'
            '<p class="v4c-p"><b>ציון השוק</b> (0 עד 100): 40 נקודות אם S&amp;P 500 מעל הממוצע של 200 יום, '
            '30 נקודות אם הוא מעל הממוצע של 50 יום, ועד 30 נקודות לפי מדד הפחד (VIX): מלא מתחת ל-15, אפס מעל 30. '
            '70 ומעלה חיובי, 40 עד 70 ניטרלי, מתחת ל-40 שלילי.'
            f' היום: {esc(reg.get("score"))}.</p>'
            f'<p class="v4c-p"><b>פחד וחמדנות</b>: {text(fg.get("method") or "")}</p>'
            '<p class="v4c-fine">אלה חישובים של המערכת מנתונים אמיתיים, לא מדדים רשמיים. '
            'מדד הפחד והחמדנות של המערכת אינו המדד של CNN.</p></section>')
