# -*- coding: utf-8 -*-
"""Institutional dark theme (Phase 17).

A premium "investment terminal" design system: deep-navy canvas, elevated cards,
strong visual hierarchy, large KPI typography, color-coded scores, and tasteful
micro-interactions (hover lift, fade-in, animated progress fills, native
tooltips). Centralizes ALL styling so the dashboard reads like a financial
product without scattering CSS across the app.

Backwards-compat: the legacy color names (GREEN/AMBER/RED/BLUE/CARD/MUTED/TEXT)
are kept but remapped to the new palette, so every existing tab — and the mobile
UI — inherits the new look automatically; only the Home dashboard is re-laid-out.
"""

# --- New institutional palette (Phase 17) --------------------------------
BG = "#08111f"          # app background
CARD = "#102040"        # card surface
BORDER = "#1f3257"      # hairline borders
PRIMARY = "#00C2FF"     # brand / interactive accent
POSITIVE = "#00E676"    # bullish / good
WARNING = "#FFC107"     # caution
NEGATIVE = "#FF5252"    # bearish / bad
TEXT = "#E6EDF7"        # primary text
MUTED = "#94A3B8"       # secondary text
ELEV = "#16284d"        # slightly elevated surface (gradients/hover)

# --- Legacy aliases (so existing tabs + mobile.py keep working) ----------
GREEN = POSITIVE
AMBER = WARNING
RED = NEGATIVE
BLUE = PRIMARY


def score_color(v):
    """Color for a 0-100 score (higher = better)."""
    if v is None:
        return MUTED
    return POSITIVE if v >= 66 else (WARNING if v >= 40 else NEGATIVE)


def regime_color(score):
    """Color for the market-regime score."""
    if not isinstance(score, (int, float)):
        return WARNING
    return POSITIVE if score >= 60 else (NEGATIVE if score < 40 else WARNING)


def sparkline_svg(values, w=120, h=34, up=POSITIVE, down=NEGATIVE):
    """Tiny inline-SVG sparkline from a list of numbers (no Plotly = fast).

    Color reflects net direction; an area fill gives it weight. Returns '' if
    there isn't enough data.
    """
    vals = [v for v in (values or []) if isinstance(v, (int, float)) and v == v]
    if len(vals) < 2:
        return ""
    lo, hi = min(vals), max(vals)
    rng = (hi - lo) or 1.0
    n = len(vals)
    pts = [(i / (n - 1) * (w - 2) + 1, h - 2 - (v - lo) / rng * (h - 4)) for i, v in enumerate(vals)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    color = up if vals[-1] >= vals[0] else down
    area = f"1,{h-1} " + line + f" {w-1},{h-1}"
    return (
        f"<svg width='{w}' height='{h}' viewBox='0 0 {w} {h}' preserveAspectRatio='none' class='spark'>"
        f"<polygon points='{area}' fill='{color}' fill-opacity='0.12'/>"
        f"<polyline points='{line}' fill='none' stroke='{color}' stroke-width='1.6' "
        f"stroke-linejoin='round' stroke-linecap='round'/></svg>"
    )


def score_bar(label, value, maxv=100, color=None):
    """One labeled progress bar (number + animated fill + color)."""
    if value is None or (isinstance(value, float) and value != value):
        return (f"<div class='sbar'><div class='sbar-h'><span>{label}</span>"
                f"<b style='color:{MUTED}'>—</b></div>"
                f"<div class='sbar-t'><div class='sbar-f' style='width:0%;background:{MUTED}'></div></div></div>")
    col = color or score_color(value)
    pct = max(0, min(100, value / maxv * 100))
    return (
        f"<div class='sbar'><div class='sbar-h'><span>{label}</span>"
        f"<b style='color:{col}'>{int(round(value))}</b></div>"
        f"<div class='sbar-t'><div class='sbar-f' style='width:{pct:.0f}%;background:{col}'></div></div></div>"
    )


INSTITUTIONAL_CSS = f"""
<style>
  /* ---------- Base canvas + typography ---------- */
  :root {{
    --bg:{BG}; --card:{CARD}; --border:{BORDER}; --primary:{PRIMARY};
    --pos:{POSITIVE}; --warn:{WARNING}; --neg:{NEGATIVE}; --text:{TEXT}; --muted:{MUTED};
  }}
  .stApp {{ background:{BG}; color:{TEXT}; direction:rtl;
            font-size:15px; line-height:1.55;
            font-family:'Inter','Segoe UI',Arial,sans-serif; }}
  h1,h2,h3,h4,h5,p,span,label,li,div[data-testid="stMarkdownContainer"] {{
      direction:rtl; text-align:right; color:{TEXT}; }}
  h2 {{ font-size:22px; font-weight:800; letter-spacing:-.2px; }}
  h3 {{ font-size:18px; font-weight:800; }}
  h4 {{ font-size:16px; font-weight:700; }}
  #MainMenu, footer, header[data-testid="stHeader"] {{ visibility:hidden; }}
  .block-container {{ padding-top:1rem; padding-bottom:2.4rem; max-width:1560px; }}
  ::selection {{ background:{PRIMARY}33; }}

  /* ---------- Sidebar ---------- */
  section[data-testid="stSidebar"] {{
      background:linear-gradient(180deg,#0b1830,#0a1426);
      border-left:1px solid {BORDER}; }}
  section[data-testid="stSidebar"] * {{ color:{TEXT}; }}
  .stRadio [role="radiogroup"] label {{ padding:7px 8px; border-radius:9px; transition:background .15s; }}
  .stRadio [role="radiogroup"] label:hover {{ background:{ELEV}; }}

  /* ---------- Generic elevated card (.card kept for back-compat across tabs) ---------- */
  .card {{
      background:linear-gradient(180deg,{ELEV},{CARD});
      border:1px solid {BORDER}; border-radius:14px; padding:16px 18px;
      margin-bottom:14px; box-shadow:0 4px 16px rgba(0,0,0,.26);
      animation:fadeUp .4s ease both; }}
  .ic-card {{
      background:linear-gradient(180deg,{ELEV},{CARD});
      border:1px solid {BORDER}; border-radius:16px; padding:18px 20px;
      margin-bottom:16px; box-shadow:0 6px 20px rgba(0,0,0,.28);
      animation:fadeUp .4s ease both; }}
  .ic-card:hover {{ border-color:{PRIMARY}55; }}
  .ic-title {{ font-size:16px; font-weight:800; display:flex; align-items:center; gap:8px; }}
  .ic-sub {{ color:{MUTED}; font-size:13px; }}

  /* ---------- KPI grid ---------- */
  .kpi-grid {{ display:grid; grid-template-columns:repeat(6,1fr); gap:14px; margin-bottom:18px; }}
  .kpi {{
      background:linear-gradient(180deg,{ELEV},{CARD});
      border:1px solid {BORDER}; border-top:3px solid var(--ac,{PRIMARY});
      border-radius:16px; padding:16px 16px 14px; position:relative;
      box-shadow:0 6px 18px rgba(0,0,0,.26); transition:transform .18s, box-shadow .18s, border-color .18s;
      animation:fadeUp .45s ease both; cursor:default; }}
  .kpi:hover {{ transform:translateY(-3px); box-shadow:0 12px 26px rgba(0,0,0,.4); }}
  .kpi .k-ico {{ font-size:20px; }}
  .kpi .k-lab {{ color:{MUTED}; font-size:13px; font-weight:600; margin-top:2px; }}
  .kpi .k-val {{ font-size:38px; font-weight:800; line-height:1.05; letter-spacing:-1px;
                 color:var(--ac,{TEXT}); margin:2px 0; }}
  .kpi .k-sub {{ color:{MUTED}; font-size:12px; line-height:1.4; }}
  .kpi .k-dot {{ position:absolute; top:16px; left:16px; width:9px; height:9px; border-radius:50%;
                 background:var(--ac,{PRIMARY}); box-shadow:0 0 0 4px var(--ac,#0000)22; }}

  /* ---------- Score / progress bars ---------- */
  .sbar {{ margin:7px 0; }}
  .sbar-h {{ display:flex; justify-content:space-between; font-size:13px; color:{MUTED}; margin-bottom:3px; }}
  .sbar-h b {{ font-size:13px; }}
  .sbar-t {{ height:8px; background:#0a1830; border:1px solid {BORDER}; border-radius:6px; overflow:hidden; }}
  .sbar-f {{ height:100%; border-radius:6px; animation:grow .7s cubic-bezier(.2,.8,.2,1) both; }}

  /* ---------- Badges / pills ---------- */
  .badge {{ display:inline-flex; align-items:center; gap:5px; font-size:12px; font-weight:700;
            padding:3px 10px; border-radius:999px; border:1px solid currentColor; }}
  .b-crit {{ color:{NEGATIVE}; background:{NEGATIVE}1a; }}
  .b-high {{ color:{NEGATIVE}; background:{NEGATIVE}14; }}
  .b-med  {{ color:{WARNING}; background:{WARNING}1a; }}
  .b-low  {{ color:{PRIMARY}; background:{PRIMARY}1a; }}
  .pill {{ background:{POSITIVE}1f; color:{POSITIVE}; border-radius:999px; padding:3px 12px; font-size:13px; }}

  /* ---------- Action cards (What should I do today) ---------- */
  .act {{ background:linear-gradient(180deg,{ELEV},{CARD}); border:1px solid {BORDER};
          border-right:5px solid var(--ac,{PRIMARY}); border-radius:14px; padding:14px 16px;
          height:100%; box-shadow:0 4px 14px rgba(0,0,0,.25); animation:fadeUp .5s ease both; }}
  .act .a-pr {{ font-size:12px; font-weight:800; color:var(--ac,{PRIMARY}); letter-spacing:.4px; }}
  .act .a-ti {{ font-size:16px; font-weight:800; margin:3px 0 8px; }}
  .act .a-row {{ font-size:13px; color:{MUTED}; margin:3px 0; }}
  .act .a-row b {{ color:{TEXT}; font-weight:600; }}

  /* ---------- Opportunity card ---------- */
  .opp {{ background:linear-gradient(180deg,{ELEV},{CARD}); border:1px solid {BORDER};
          border-right:5px solid var(--ac,{PRIMARY}); border-radius:16px; padding:16px 18px;
          margin-bottom:6px; box-shadow:0 6px 18px rgba(0,0,0,.28);
          transition:transform .18s, border-color .18s; animation:fadeUp .5s ease both; }}
  .opp:hover {{ transform:translateY(-2px); border-color:{PRIMARY}55; }}
  .opp .o-tick {{ font-size:20px; font-weight:800; }}
  .opp .o-co {{ color:{MUTED}; font-weight:400; font-size:14px; }}
  .opp .o-rec {{ font-weight:800; }}
  .opp .o-meta {{ display:flex; gap:18px; flex-wrap:wrap; font-size:13px; color:{MUTED}; margin:8px 0; }}
  .opp .o-meta b {{ color:{TEXT}; }}
  .opp .o-cols {{ display:grid; grid-template-columns:1fr 1fr 1fr; gap:16px; font-size:13px; margin-top:6px; }}
  .opp .o-cols ul {{ margin:4px 0; padding-right:16px; color:{MUTED}; }}
  .spark {{ display:block; }}

  /* ---------- Tables ---------- */
  div[data-testid="stDataFrame"] {{ background:{CARD}; border:1px solid {BORDER};
      border-radius:12px; direction:rtl; }}
  div[data-testid="stDataFrame"] * {{ font-size:13px; }}

  /* ---------- KPI metric (st.metric) ---------- */
  div[data-testid="stMetric"] {{ background:linear-gradient(180deg,{ELEV},{CARD});
      border:1px solid {BORDER}; border-radius:14px; padding:14px 16px; text-align:right; }}
  div[data-testid="stMetricLabel"] p {{ color:{MUTED}; font-size:13px; }}
  div[data-testid="stMetricValue"] {{ color:{TEXT}; font-weight:800; font-size:1.7rem; }}

  /* ---------- Top bar ---------- */
  .topbar {{ background:linear-gradient(90deg,#0b1830,#0a1426); border:1px solid {BORDER};
      border-radius:14px; padding:13px 20px; margin-bottom:16px; display:flex;
      justify-content:space-between; align-items:center; box-shadow:0 4px 14px rgba(0,0,0,.25); }}

  /* ---------- Buttons / tabs / inputs ---------- */
  .stButton button {{ border-radius:10px; font-weight:700; border:1px solid {BORDER};
      background:{ELEV}; color:{TEXT}; transition:all .15s; min-height:40px; }}
  .stButton button:hover {{ border-color:{PRIMARY}; color:{PRIMARY}; transform:translateY(-1px); }}
  .stTabs [data-baseweb="tab-list"] {{ gap:6px; direction:rtl; }}
  .stTabs [data-baseweb="tab"] {{ font-size:14px; font-weight:700; padding:8px 14px; }}
  details summary {{ direction:rtl; text-align:right; font-weight:700; }}
  .stPlotlyChart {{ margin-bottom:6px; }}

  /* ---------- Loading skeleton ---------- */
  .skeleton {{ background:linear-gradient(90deg,{CARD} 25%,{ELEV} 37%,{CARD} 63%);
      background-size:400% 100%; animation:shimmer 1.4s ease infinite; border-radius:10px; }}

  /* ---------- Keyframes ---------- */
  @keyframes fadeUp {{ from {{ opacity:0; transform:translateY(10px); }} to {{ opacity:1; transform:none; }} }}
  @keyframes grow {{ from {{ width:0 !important; }} }}
  @keyframes shimmer {{ 0% {{ background-position:100% 0; }} 100% {{ background-position:0 0; }} }}

  /* ---------- Responsive ---------- */
  @media (max-width:1100px) {{ .kpi-grid {{ grid-template-columns:repeat(3,1fr); }}
                               .opp .o-cols {{ grid-template-columns:1fr; }} }}
  @media (max-width:640px) {{ .kpi-grid {{ grid-template-columns:repeat(2,1fr); }}
      .block-container {{ padding:.5rem !important; }} .kpi .k-val {{ font-size:30px; }}
      h2 {{ font-size:19px; }} }}
</style>
"""

# Legacy name kept so app.py's `from dashboard.theme import DARK_CSS` still works.
DARK_CSS = INSTITUTIONAL_CSS


def style_fig(fig, height: int = 300):
    """Apply the institutional dark theme to a Plotly figure."""
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, Arial", color=TEXT, size=12),
        margin=dict(l=10, r=10, t=34, b=10),
        height=height,
        hoverlabel=dict(bgcolor=CARD, bordercolor=BORDER, font_size=12),
        legend=dict(orientation="h", y=-0.2),
        transition=dict(duration=350, easing="cubic-in-out"),
    )
    fig.update_xaxes(gridcolor=BORDER, zerolinecolor=BORDER)
    fig.update_yaxes(gridcolor=BORDER, zerolinecolor=BORDER)
    return fig
