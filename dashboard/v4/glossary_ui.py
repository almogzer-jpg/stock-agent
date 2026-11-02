# -*- coding: utf-8 -*-
"""Glossary and settings screen components (HTML builders styled by css.py)."""
from dashboard.v4.ui import esc, text


def letters(lst: list) -> str:
    out = "".join(f'<a href="#v4g-{i}">{esc(c)}</a>' if on else f'<span>{esc(c)}</span>'
                  for i, (c, on) in enumerate(lst))
    return f'<nav class="v4g-abc" aria-label="אינדקס אותיות">{out}</nav>'


def section(sec: dict, idx: int, advanced: bool) -> str:
    rows = []
    for e in sec["items"]:
        more = ""
        if advanced:
            shown = [a for a in e.get("aliases", []) if "V2" not in a.upper()]   # internal version names stay searchable, not shown
            al = f'<div class="al">נקרא גם: {esc(" · ".join(shown))}</div>' if shown else ""
            more = f'<p class="pl">{text(e["plain"])}</p><p class="wy"><b>למה זה חשוב:</b> {text(e["why"])}</p>{al}'
        ex = (f'<div class="ex"><b>דוגמה:</b> {text(e["example"])}</div>' if e.get("example") else "")
        rows.append(f'<li><div class="t"><h3>{esc(e["term"])}</h3><span>{esc(e["group"])}</span></div>'
                    f'<div class="d"><p>{text(e["short"])}</p>{more}</div>{ex}</li>')
    return (f'<section class="v4g-sec" id="v4g-{idx}"><div class="v4g-l">{esc(sec["letter"])}</div>'
            f'<ul>{"".join(rows)}</ul></section>')


def count_line(g: dict, close: str, sample_name: str | None) -> str:
    src = f" · הדוגמאות מנתוני {esc(close)}, מהמניה {esc(sample_name)}" if sample_name and g["with_example"] else ""
    shown = f'{g["count"]} מתוך {g["total"]} מונחים' if g["count"] != g["total"] else f'{g["total"]} מונחים'
    return f'<div class="v4g-count">{text(shown)} · {text(str(g["with_example"]))} עם דוגמה{src}</div>'


def panel_open(title: str, sub: str = "") -> str:
    s = f'<div class="v4-method">{text(sub)}</div>' if sub else ""
    return f'<h2 class="v4-h3">{esc(title)}</h2>{s}'


def data_table(rows: list) -> str:
    body = "".join(f'<tr><th scope="row">{esc(a)}</th><td>{esc(b)}</td><td>{text(c)}</td></tr>' for a, b, c in rows)
    return f'<table class="v4s-tbl"><tbody>{body}</tbody></table>'
