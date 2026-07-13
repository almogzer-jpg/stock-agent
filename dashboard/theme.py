# -*- coding: utf-8 -*-
"""Institutional design system (Phase 23).

One calm, premium design language for every screen: neutral near-black canvas,
flat elevated surfaces (separation by background depth, NOT borders/gradients),
a strict 3-size type scale, and exactly five colors with meaning —
white text · gray secondary · green=positive · red=negative · blue=action ·
yellow=warning. Subtle motion only.

Backwards-compat: every exported name, CSS class and helper from earlier phases
is preserved (pages depend on them) — only their VISUAL VALUES changed.
"""

# --- Core palette (Phase 23 — calm, non-neon) -----------------------------
BG = "#0B0F17"          # app canvas (neutral near-black)
CARD = "#131926"        # primary surface
ELEV = "#1A2233"        # raised surface (hover / secondary elevation)
BORDER = "#232D40"      # hairline (used sparingly; mostly separation-by-depth)
PRIMARY = "#5EA8FF"     # blue — actions / interactive only
POSITIVE = "#34D399"    # green — positive only
WARNING = "#FBBF24"     # yellow — warnings only
NEGATIVE = "#F87171"    # red — negative only
TEXT = "#F4F6F8"        # primary text (soft white — not glaring)
SECONDARY = "#C8D2E0"   # secondary text (WCAG AA on BG)
MUTED = "#94A3B8"       # muted text — contrast floor, never darker

# --- Legacy aliases (all tabs + mobile keep working) ----------------------
GREEN = POSITIVE
AMBER = WARNING
RED = NEGATIVE
BLUE = PRIMARY

# Accessible chart line colors (all ≥3:1 on BG).
LINE_PRICE = "#5EA8FF"
LINE_MA20 = "#FBBF24"
LINE_MA50 = "#B388FF"
LINE_MA200 = "#F1F5F9"
LINE_UP = "#34D399"
LINE_DOWN = "#F87171"
LINE_RSI = "#5EA8FF"
LINE_VOLUME = "#26A69A"

# --- Type scale (Phase 28 — Bloomberg/Koyfin grade) ------------------------
FS_KPI = "40px"         # primary numbers
FS_NUM2 = "28px"        # secondary numbers
FS_TITLE = "20px"       # card titles
FS_BODY = "16px"        # descriptions / normal text
FS_FOOT = "14px"        # footnotes


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
    """Tiny inline-SVG sparkline (no Plotly = fast). '' if not enough data."""
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
        f"<polygon points='{area}' fill='{color}' fill-opacity='0.10'/>"
        f"<polyline points='{line}' fill='none' stroke='{color}' stroke-width='1.5' "
        f"stroke-linejoin='round' stroke-linecap='round'/></svg>"
    )


def score_bar(label, value, maxv=100, color=None):
    """One labeled progress bar (number + fill + semantic color)."""
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
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
  /* ================= Base canvas & type scale (Phase 28) ================= */
  :root {{
    --bg:{BG}; --card:{CARD}; --elev:{ELEV}; --border:{BORDER}; --primary:{PRIMARY};
    --pos:{POSITIVE}; --warn:{WARNING}; --neg:{NEGATIVE}; --text:{TEXT}; --muted:{MUTED};
  }}
  .stApp {{ background:{BG}; color:{TEXT}; direction:rtl;
            font-size:{FS_BODY}; line-height:1.7; font-weight:400; letter-spacing:.1px;
            font-family:'Inter','IBM Plex Sans','Segoe UI',Arial,sans-serif; }}
  h1,h2,h3,h4,h5,p,span,label,li,div[data-testid="stMarkdownContainer"] {{
      direction:rtl; text-align:right; color:{TEXT}; }}
  h1 {{ font-size:36px; font-weight:700; letter-spacing:-.4px; }}
  h2, h3 {{ font-size:30px; font-weight:700; letter-spacing:-.3px;
      margin-top:2.2rem; margin-bottom:.8rem; }}
  h4, h5 {{ font-size:23px; font-weight:600; letter-spacing:-.2px;
      margin-top:2.2rem; margin-bottom:.8rem; }}
  p {{ margin-bottom:.6rem; }}
  div[data-testid="stCaptionContainer"] p {{ font-size:{FS_FOOT}; }}
  #MainMenu, footer, header[data-testid="stHeader"] {{ visibility:hidden; }}
  .block-container {{ padding-top:1.6rem; padding-bottom:3.4rem; max-width:1460px; }}
  ::selection {{ background:{PRIMARY}33; }}
  hr {{ border-color:{BORDER}; opacity:.5; margin:2rem 0; }}

  /* horizontal chip rows (performance etc.) */
  .chiprow {{ display:flex; gap:10px; overflow-x:auto; padding:6px 0 10px; white-space:nowrap;
              scrollbar-width:none; }}
  .chiprow::-webkit-scrollbar {{ display:none; }}
  .chip {{ flex:0 0 auto; background:{CARD}; border-radius:14px; padding:12px 18px;
           text-align:center; min-width:86px; }}
  .chip .cl {{ color:{MUTED}; font-size:{FS_FOOT}; font-weight:500; }}
  .chip .cv {{ font-size:18px; font-weight:600; margin-top:2px; }}

  /* ================= Sidebar ================= */
  section[data-testid="stSidebar"] {{ background:{CARD}; border-left:1px solid {BORDER}; }}
  section[data-testid="stSidebar"] * {{ color:{TEXT}; }}
  /* a11y: visible focus ring everywhere (keyboard navigation) */
  button:focus-visible, a:focus-visible, [role="radio"]:focus-visible,
  input:focus-visible, [tabindex]:focus-visible {{
      outline:2px solid {PRIMARY} !important; outline-offset:2px; border-radius:6px; }}
  /* hide the nav widget's label ("תצוגה") — nav needs no caption */
  section[data-testid="stSidebar"] label[data-testid="stWidgetLabel"],
  section[data-testid="stSidebar"] div[data-testid="stWidgetLabel"] {{ display:none; }}
  /* Sidebar radio → institutional NAV (no radio circles, active accent bar) */
  section[data-testid="stSidebar"] .stRadio div[data-testid="stWidgetLabel"] {{ display:none; }}
  section[data-testid="stSidebar"] .stRadio [role="radiogroup"] label > div:first-child {{ display:none; }}
  section[data-testid="stSidebar"] .stRadio [role="radiogroup"] label {{
      padding:12px 14px; border-radius:10px; font-size:15.5px; font-weight:600;
      margin-bottom:3px; width:100%; transition:background .15s;
      border-right:3px solid transparent; }}
  section[data-testid="stSidebar"] .stRadio [role="radiogroup"] label:hover {{ background:{ELEV}; }}
  section[data-testid="stSidebar"] .stRadio [role="radiogroup"] label:has(input:checked) {{
      background:{ELEV}; border-right:3px solid {PRIMARY}; }}
  section[data-testid="stSidebar"] .stRadio [role="radiogroup"] label:has(input:checked) p {{ color:{PRIMARY}; }}
  .stRadio [role="radiogroup"] label {{ padding:7px 10px; border-radius:8px; transition:background .15s; }}
  .stRadio [role="radiogroup"] label:hover {{ background:{ELEV}; }}

  /* ================= Surfaces (flat, borderless, depth by bg) ================= */
  .card, .ic-card {{
      background:{CARD}; border:none; border-radius:16px; padding:24px 26px;
      margin-bottom:20px; box-shadow:none; animation:fadeUp .35s ease both;
      transition:box-shadow .18s; }}
  .ic-title {{ font-size:{FS_TITLE}; font-weight:600; display:flex; align-items:center; gap:8px; }}
  .ic-sub {{ color:{SECONDARY}; font-size:{FS_BODY}; line-height:1.7; }}

  /* ================= KPI (Apple-widget structure) ================= */
  .kpi-grid {{ display:grid; grid-template-columns:repeat(6,1fr); gap:16px; margin:8px 0 28px; }}
  .kpi {{ background:{CARD}; border:none; border-radius:16px; padding:20px 22px 18px;
      position:relative; transition:background .15s, box-shadow .18s; animation:fadeUp .35s ease both; }}
  .kpi:hover {{ background:{ELEV}; box-shadow:0 6px 22px rgba(0,0,0,.28); }}
  .kpi .k-ico {{ font-size:14px; opacity:.7; }}
  .kpi .k-val {{ font-size:{FS_KPI}; font-weight:700; line-height:1.06; letter-spacing:-1.2px;
                 color:var(--ac,{TEXT}); margin:6px 0 3px; }}
  .kpi .k-lab {{ color:{SECONDARY}; font-size:{FS_BODY}; font-weight:500; }}
  .kpi .k-sub {{ color:{MUTED}; font-size:{FS_FOOT}; }}
  .kpi .k-dot {{ position:absolute; top:18px; left:18px; width:7px; height:7px; border-radius:50%;
                 background:var(--ac,{MUTED}); }}

  /* ================= Score bars ================= */
  .sbar {{ margin:9px 0; }}
  .sbar-h {{ display:flex; justify-content:space-between; font-size:{FS_BODY}; color:{SECONDARY}; margin-bottom:4px; }}
  .sbar-h b {{ font-size:{FS_BODY}; }}
  .sbar-t {{ height:6px; background:{BG}; border:none; border-radius:4px; overflow:hidden; }}
  .sbar-f {{ height:100%; border-radius:4px; animation:grow .6s cubic-bezier(.2,.8,.2,1) both; }}

  /* ================= Badges / pills ================= */
  .badge, .tbadge, .secbadge {{ display:inline-flex; align-items:center; gap:6px;
      font-size:13.5px; font-weight:600; padding:5px 14px; border-radius:999px;
      background:{ELEV}; border:none; letter-spacing:.1px; }}
  .b-crit, .b-high {{ color:{NEGATIVE}; }}
  .b-med {{ color:{WARNING}; }}
  .b-low {{ color:{PRIMARY}; }}
  .pill {{ background:{ELEV}; color:{POSITIVE}; border-radius:999px; padding:3px 12px; font-size:12.5px; }}

  /* ================= Action / opportunity cards ================= */
  .act {{ background:{CARD}; border:none; border-right:3px solid var(--ac,{PRIMARY});
          border-radius:12px; padding:16px 18px; height:100%; animation:fadeUp .4s ease both; }}
  .act .a-pr {{ font-size:12.5px; font-weight:700; color:var(--ac,{PRIMARY}); letter-spacing:.3px; }}
  .act .a-ti {{ font-size:{FS_TITLE}; font-weight:700; margin:4px 0 8px; }}
  .act .a-row {{ font-size:{FS_BODY}; color:{SECONDARY}; margin:3px 0; }}
  .act .a-row b {{ color:{TEXT}; font-weight:600; }}

  .opp {{ background:{CARD}; border:none; border-right:3px solid var(--ac,{PRIMARY});
          border-radius:14px; padding:18px 20px; margin-bottom:10px;
          transition:background .15s; animation:fadeUp .4s ease both; }}
  .opp:hover {{ background:{ELEV}; }}
  .opp .o-tick {{ font-size:{FS_TITLE}; font-weight:700; }}
  .opp .o-co {{ color:{MUTED}; font-weight:400; font-size:{FS_BODY}; }}
  .opp .o-rec {{ font-weight:700; }}
  .opp .o-meta {{ display:flex; gap:18px; flex-wrap:wrap; font-size:{FS_BODY}; color:{SECONDARY}; margin:10px 0; }}
  .opp .o-meta b {{ color:{TEXT}; }}
  .opp .o-cols {{ display:grid; grid-template-columns:1fr 1fr 1fr; gap:18px; font-size:{FS_BODY}; margin-top:8px; }}
  .opp .o-cols ul {{ margin:4px 0; padding-right:16px; color:{SECONDARY}; }}
  .spark {{ display:block; }}

  /* ================= Tables ================= */
  div[data-testid="stDataFrame"] {{ background:{CARD}; border:1px solid {BORDER};
      border-radius:12px; direction:rtl; }}
  div[data-testid="stDataFrame"] * {{ font-size:14px; }}

  div[data-testid="stMetric"] {{ background:{CARD}; border:none; border-radius:12px;
      padding:14px 16px; text-align:right; }}
  div[data-testid="stMetricLabel"] p {{ color:{SECONDARY}; font-size:{FS_BODY}; }}
  div[data-testid="stMetricValue"] {{ color:{TEXT}; font-weight:700; font-size:1.7rem; }}

  /* ================= Top bar ================= */
  .topbar {{ background:{CARD}; border:none; border-radius:12px; padding:13px 20px;
      margin-bottom:20px; display:flex; justify-content:space-between; align-items:center; }}

  /* ================= Buttons / tabs / inputs ================= */
  .stButton button {{ border-radius:9px; font-weight:600; border:1px solid {BORDER};
      background:transparent; color:{SECONDARY}; transition:all .15s; min-height:40px; }}
  .stButton button:hover {{ border-color:{PRIMARY}; color:{PRIMARY}; background:transparent; }}
  button[kind="primary"], button[data-testid="stBaseButton-primary"] {{
      background:{PRIMARY} !important; color:#0B1220 !important; border:none !important; font-weight:700; }}
  .stTabs [data-baseweb="tab-list"] {{ gap:6px; direction:rtl; }}
  .stTabs [data-baseweb="tab"] {{ font-size:{FS_BODY}; font-weight:600; padding:8px 14px; }}
  details summary {{ direction:rtl; text-align:right; font-weight:600; color:{SECONDARY}; }}
  .stPlotlyChart {{ margin-bottom:10px; }}
  [data-testid="stForm"] {{ background:{CARD}; border:none; border-radius:14px; padding:18px 20px; }}
  [data-testid="stForm"] label {{ font-weight:500; color:{SECONDARY}; }}

  /* ================= Ranking cards / sector table ================= */
  .rcard {{ background:{CARD}; border:none; border-right:3px solid var(--ac,{MUTED});
            border-radius:10px; padding:9px 12px; margin-bottom:7px; transition:background .12s; }}
  .rcard:hover {{ background:{ELEV}; }}
  .rtk {{ font-weight:700; font-size:{FS_BODY}; }}
  .rco {{ color:{MUTED}; font-size:12.5px; margin-right:6px; }}
  .rmeta {{ font-size:12.5px; color:{SECONDARY}; margin-top:2px; }}
  .rmeta b {{ font-size:12.5px; }}
  .sectbl {{ width:100%; border-collapse:collapse; font-size:14px; }}
  .sectbl th {{ text-align:right; color:{MUTED}; font-weight:600; font-size:12.5px;
                padding:10px 12px; border-bottom:1px solid {BORDER}; white-space:nowrap; }}
  .sectbl td {{ padding:11px 12px; border-bottom:1px solid {BORDER}; color:{TEXT}; }}
  .sectbl tr:hover td {{ background:{ELEV}; }}
  .miniprog {{ height:5px; background:{BG}; border:none; border-radius:4px; overflow:hidden; min-width:70px; }}
  .miniprog > div {{ height:100%; border-radius:4px; }}

  /* ================= Rich opportunity cards ================= */
  .ocard {{ background:{CARD}; border:none; border-radius:14px; padding:18px 20px;
            margin-bottom:10px; transition:background .15s; position:relative; }}
  .ocard:hover {{ background:{ELEV}; }}
  .oc-head {{ display:flex; gap:12px; align-items:center; }}
  .oc-av {{ width:38px; height:38px; border-radius:10px; display:flex; align-items:center; justify-content:center;
            font-weight:700; font-size:13px; color:#0B1220; flex:none; }}
  .oc-tk {{ font-size:{FS_TITLE}; font-weight:700; line-height:1.1; }}
  .oc-name {{ color:{SECONDARY}; font-size:{FS_BODY}; margin-top:1px; }}
  .oc-badges {{ display:flex; gap:6px; flex-wrap:wrap; margin:12px 0 10px; }}
  .oc-reason {{ color:{SECONDARY}; font-size:{FS_BODY}; line-height:1.65; margin-top:4px; }}
  .oc-metric {{ display:flex; justify-content:space-between; font-size:{FS_BODY}; color:{SECONDARY}; margin:4px 0; }}
  .oc-metric b {{ font-size:{FS_BODY}; }}
  .info {{ color:{MUTED}; font-size:11px; cursor:help; border:1px solid {BORDER}; border-radius:50%;
           padding:0 5px; margin-right:3px; }}
  .pitem {{ background:{CARD}; border:none; border-right:3px solid var(--ac,{MUTED});
            border-radius:10px; padding:10px 12px; margin-bottom:8px; }}
  .pi-tk {{ font-size:{FS_BODY}; font-weight:700; }}
  .pi-name {{ color:{MUTED}; font-size:12.5px; margin-top:1px; }}

  /* ================= Performance ================= */
  .perf-grid {{ display:grid; grid-template-columns:repeat(7,1fr); gap:10px; margin:8px 0 16px; }}
  .pcard {{ background:{CARD}; border:none; border-top:2px solid var(--ac,{MUTED});
            border-radius:12px; padding:12px 8px; text-align:center; }}
  .pcard .pl {{ color:{MUTED}; font-size:12.5px; font-weight:500; }}
  .pcard .pv {{ font-size:{FS_TITLE}; font-weight:700; color:var(--ac); margin-top:4px; white-space:nowrap; }}
  .cmp {{ margin:10px 0; }}
  .cmp .cl {{ display:flex; justify-content:space-between; font-size:{FS_BODY}; margin-bottom:4px; }}
  .cmptrack {{ height:12px; background:{BG}; border:none; border-radius:6px; overflow:hidden; }}
  .cmpfill {{ height:100%; border-radius:6px; transition:width .5s cubic-bezier(.2,.8,.2,1); }}

  /* ================= Scenario cards / confidence ================= */
  .scen {{ border:none; border-right:3px solid var(--ac); border-radius:14px; padding:20px 22px; height:100%;
           background:{CARD}; direction:rtl; text-align:right; animation:fadeUp .35s ease both; }}
  .scen .s-ti {{ font-size:{FS_TITLE}; font-weight:700; color:var(--ac); display:flex; gap:8px; align-items:center; }}
  .scen .s-lbl {{ font-size:12.5px; color:{MUTED}; margin-top:12px; }}
  .scen .s-prob {{ font-size:{FS_NUM2}; font-weight:600; color:var(--ac); line-height:1.1; }}
  .scen .s-tgt {{ font-size:{FS_NUM2}; font-weight:600; color:{TEXT}; line-height:1.1; }}
  .scen .pill {{ display:inline-block; font-size:12.5px; font-weight:600; padding:3px 12px;
                 border-radius:999px; margin-top:5px; }}
  .scen .s-sum {{ font-size:{FS_BODY}; font-weight:400; color:{SECONDARY}; line-height:1.65; margin:14px 0 8px; }}
  .scen ul {{ list-style:none; padding:0; margin:4px 0; }}
  .scen li {{ font-size:{FS_BODY}; color:{SECONDARY}; line-height:1.65; margin:3px 0; }}
  .confmeter {{ background:{CARD}; border:none; border-radius:14px; padding:16px 20px; margin-top:14px; }}
  .confmeter .ct {{ font-size:{FS_BODY}; font-weight:600; display:flex; justify-content:space-between; }}
  .conftrack {{ height:8px; background:{BG}; border:none; border-radius:5px; overflow:hidden; margin-top:10px; }}
  .conffill {{ height:100%; border-radius:5px; transition:width .6s cubic-bezier(.2,.8,.2,1); }}

  /* ================= Skeleton & motion ================= */
  .skeleton {{ background:linear-gradient(90deg,{CARD} 25%,{ELEV} 37%,{CARD} 63%);
      background-size:400% 100%; animation:shimmer 1.4s ease infinite; border-radius:10px; }}
  @keyframes fadeUp {{ from {{ opacity:0; transform:translateY(6px); }} to {{ opacity:1; transform:none; }} }}
  @keyframes grow {{ from {{ width:0 !important; }} }}
  @keyframes shimmer {{ 0% {{ background-position:100% 0; }} 100% {{ background-position:0 0; }} }}

  /* ================= Responsive ================= */
  @media (max-width:1100px) {{ .kpi-grid {{ grid-template-columns:repeat(3,1fr); }}
                               .opp .o-cols {{ grid-template-columns:1fr; }} }}
  @media (max-width:640px) {{ .kpi-grid {{ grid-template-columns:repeat(2,1fr); }}
      .block-container {{ padding:.5rem !important; }} .kpi .k-val {{ font-size:26px; }}
      .perf-grid {{ grid-template-columns:repeat(3,1fr); }}
      [data-testid="stHorizontalBlock"] {{ flex-wrap:wrap; }}
      [data-testid="stHorizontalBlock"] > [data-testid="column"] {{ flex:1 1 100% !important; min-width:100% !important; }} }}
</style>
"""

# Legacy name kept so `from dashboard.theme import DARK_CSS` still works.
DARK_CSS = INSTITUTIONAL_CSS


def _rel_luminance(hex_color):
    """WCAG relative luminance of a #RRGGBB color."""
    h = hex_color.lstrip("#")
    rgb = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    lin = [(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4) for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast_ratio(fg, bg=BG):
    """WCAG contrast ratio between two #RRGGBB colors (1.0–21.0)."""
    l1, l2 = _rel_luminance(fg), _rel_luminance(bg)
    hi, lo = max(l1, l2), min(l1, l2)
    return round((hi + 0.05) / (lo + 0.05), 2)


def passes_aa(fg, bg=BG, large=False):
    """True if fg/bg meets WCAG AA (4.5:1 normal text, 3:1 large/graphical)."""
    return contrast_ratio(fg, bg) >= (3.0 if large else 4.5)


def style_fig(fig, height: int = 300):
    """Apply the institutional theme to a Plotly figure (WCAG-AA text)."""
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=BG,
        plot_bgcolor=BG,
        font=dict(family="Inter, Segoe UI, Arial", color=TEXT, size=13),
        title=dict(font=dict(color=TEXT, size=15)),
        margin=dict(l=14, r=14, t=42, b=14),
        height=height,
        hoverlabel=dict(bgcolor=CARD, bordercolor=BORDER, font=dict(color=TEXT, size=12.5)),
        legend=dict(orientation="h", y=-0.2, font=dict(color=TEXT, size=12.5),
                    bgcolor="rgba(19,25,38,0.85)", bordercolor=BORDER, borderwidth=1),
        transition=dict(duration=250, easing="cubic-in-out"),
    )
    axis = dict(showgrid=True, gridcolor=BORDER, zerolinecolor=BORDER,
                linecolor=BORDER, tickfont=dict(color=SECONDARY, size=12),
                title=dict(font=dict(color=SECONDARY, size=12.5)))
    fig.update_xaxes(**axis)
    fig.update_yaxes(**axis)
    fig.update_annotations(font=dict(color=TEXT))
    return fig
