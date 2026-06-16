# -*- coding: utf-8 -*-
"""Self-contained HTML export for the Company Deep Dive (Phase 18).

Renders the structured report dict from `deepdive.analyze()` into a single dark
RTL HTML page the user can download / open / print-to-PDF. No new dependencies.
"""

NA = "אין נתון זמין"


def _row(label, value):
    return f"<tr><td class='l'>{label}</td><td class='v'>{value}</td></tr>"


def _bar(label, value):
    if not isinstance(value, (int, float)):
        return f"<div class='sb'><span>{label}</span><b>{NA}</b></div>"
    col = "#00E676" if value >= 66 else "#FFC107" if value >= 40 else "#FF5252"
    return (f"<div class='sb'><div class='sbh'><span>{label}</span><b style='color:{col}'>{int(value)}</b></div>"
            f"<div class='sbt'><div class='sbf' style='width:{max(0,min(100,value))}%;background:{col}'></div></div></div>")


def to_html(r: dict) -> str:
    if r.get("error"):
        return f"<html><body><h2>{r['error']}</h2></body></html>"
    o, md, fin = r["overview"], r["market_data"], r["financials"]
    val, sc, th = r["valuation"], r["scores"], r["thesis"]
    op, pc, tech = r["opinion"], r["pros_cons"], r["technicals"]
    rk = r["risk"]

    fin_rows = "".join(_row(k, v) for k, v in [
        ("הכנסות", fin["revenue"]), ("צמיחת הכנסות", fin["revenue_growth"]),
        ("רווח גולמי", fin["gross_profit"]), ("שולי גולמי", fin["gross_margin"]),
        ("רווח תפעולי", fin["operating_income"]), ("שולי תפעול", fin["operating_margin"]),
        ("רווח נקי", fin["net_income"]), ("שולי נטו", fin["net_margin"]),
        ("רווח למניה", fin["eps"]), ("צמיחת רווח למניה", fin["eps_growth"]),
        ("תזרים חופשי (FCF)", fin["fcf"]), ("שולי FCF", fin["fcf_margin"]),
        ("חוב", fin["debt"]), ("מזומן", fin["cash"]),
        ("חוב/הון", fin["debt_to_equity"]), ("ROE", fin["roe"]), ("ROIC", fin["roic"]),
    ])
    val_rows = "".join(_row(k, v) for k, v in [
        ("מכפיל עתידי", val["forward_pe"]), ("מכפיל נוכחי", val["trailing_pe"]),
        ("PEG", val["peg"]), ("מחיר/מכירות", val["price_sales"]),
        ("EV/EBITDA", val["ev_ebitda"]), ("מחיר/FCF", val["price_fcf"]),
        ("סיווג", val["label"]),
    ])
    ret_rows = "".join(_row(k, v) for k, v in [
        ("מחיר", md["price"]), ("שווי שוק", md["market_cap"]),
        ("שיא 52ש'", md["high_52w"]), ("שפל 52ש'", md["low_52w"]),
        ("יומי", md["daily_change"]), ("שבוע", md["ret_1w"]), ("חודש", md["ret_1m"]),
        ("3 ח'", md["ret_3m"]), ("6 ח'", md["ret_6m"]), ("YTD", md["ytd"]),
        ("שנה", md["ret_1y"]), ("3 שנים", md["ret_3y"]),
    ])
    bars = (_bar("ציון סופי v2", sc["final_v2"]["value"]) + _bar("טכני", sc["technical"]["value"])
            + _bar("פונדמנטלי", sc["fundamental"]["value"]) + _bar("סקטור", sc["sector"]["value"])
            + _bar("חדשות", sc["news"]["value"]) + _bar("אמון", sc["trust"]["value"])
            + _bar("שווי", sc["valuation"]["value"]))
    pros = "".join(f"<li>{x}</li>" for x in pc["pros"])
    cons = "".join(f"<li>{x}</li>" for x in pc["cons"])
    sector_risks = "".join(f"<li>{x}</li>" for x in r["regulation_risks"]["sector_risks"])

    return f"""<!DOCTYPE html><html lang="he" dir="rtl"><head><meta charset="utf-8">
<title>ניתוח חברה · {r['ticker']}</title><style>
  body{{margin:0;background:#08111f;color:#E6EDF7;font-family:'Inter','Segoe UI',sans-serif;direction:rtl;padding:26px;line-height:1.6}}
  .wrap{{max-width:900px;margin:0 auto}} h1{{font-size:24px}} h2{{font-size:18px;border-bottom:1px solid #1f3257;padding-bottom:6px;margin-top:26px}}
  .card{{background:linear-gradient(180deg,#16284d,#102040);border:1px solid #1f3257;border-radius:14px;padding:16px;margin:12px 0}}
  table{{width:100%;border-collapse:collapse}} td{{padding:6px 8px;border-bottom:1px solid #1f3257;font-size:14px}}
  td.l{{color:#94A3B8}} td.v{{text-align:left;font-weight:600}}
  .sb{{margin:7px 0}} .sbh{{display:flex;justify-content:space-between;font-size:13px;color:#94A3B8}}
  .sbt{{height:8px;background:#0a1830;border:1px solid #1f3257;border-radius:6px;overflow:hidden}} .sbf{{height:100%;border-radius:6px}}
  .rec{{font-size:22px;font-weight:800;color:#00C2FF}} .muted{{color:#94A3B8;font-size:12px}}
  ul{{padding-right:18px}} .two{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
  .dis{{color:#94A3B8;font-size:12px;margin-top:20px;border-top:1px solid #1f3257;padding-top:10px}}
</style></head><body><div class="wrap">
  <h1>🔎 ניתוח חברה · {o['name']} ({r['ticker']})</h1>
  <div class="muted">{o['sector']} · {o['industry']}</div>

  <h2>1. תיאור החברה</h2>
  <div class="card">{o.get('summary_he') or o.get('he_line') or o['summary']}
    {'<div class="muted" style="margin-top:8px">תורגם אוטומטית מאנגלית</div>' if o.get('summary_he') else ''}</div>

  <h2>2. נתוני שוק</h2><div class="card"><table>{ret_rows}</table></div>
  <h2>3. דוחות כספיים</h2><div class="card"><table>{fin_rows}</table></div>
  <h2>4. תמחור</h2><div class="card"><table>{val_rows}</table></div>

  <h2>5. טכני</h2><div class="card">
    מגמה: <b>{tech['trend']}</b> · מומנטום: <b>{tech['momentum']}</b> · RSI: <b>{tech['rsi']}</b><br>
    {tech['opinion']}</div>

  <h2>6. סיכון</h2><div class="card">
    ביתא {rk['beta']} · תנודתיות {rk['volatility']}% · ירידה מקס׳ {rk['max_drawdown']}% ·
    ציון סיכון {rk['risk_score']} ({rk['category']})</div>

  <h2>7. ציוני Stock Agent</h2><div class="card">{bars}</div>

  <h2>8. תזת השקעה</h2><div class="card">
    <b style="color:#00E676">תרחיש שורי:</b> {th['bull']}<br><br>
    <b style="color:#FFC107">תרחיש בסיס:</b> {th['base']}<br><br>
    <b style="color:#FF5252">תרחיש דובי:</b> {th['bear']}</div>

  <h2>9. בעד / נגד</h2><div class="two">
    <div class="card"><b style="color:#00E676">למה להשקיע</b><ul>{pros}</ul></div>
    <div class="card"><b style="color:#FF5252">למה לא</b><ul>{cons}</ul></div></div>

  <h2>10. סיכוני סקטור <span class="muted">({r['regulation_risks']['label']})</span></h2>
  <div class="card"><ul>{sector_risks}</ul></div>

  <h2>11. דעה סופית</h2><div class="card">
    <div class="rec">{op['recommendation']}</div>
    <div style="margin-top:8px">{op['attractive']}</div>
    <div class="muted" style="margin-top:6px">טווח הקצאה מוצע: <b>{op['allocation_pct']}%</b> ·
      פרופיל משקיע: {op['investor_profile']}</div>
    <div class="muted" style="margin-top:6px">מה ישנה את ההמלצה: {op['what_changes']}</div></div>

  <div class="dis">⚠️ {r['disclaimer']} · עובדות: Yahoo Finance · ציונים: מנועי המערכת ·
    תזה/דעה: מבוססת כללים על נתונים אמיתיים, לא ייעוץ.</div>
</div></body></html>"""
