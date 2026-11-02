# -*- coding: utf-8 -*-
"""V4 global stylesheet, generated from tokens for the active theme.

Two layouts from one page: the desktop layout (side navigation, two columns)
and the phone layout at or below tokens.PHONE_MAX (top app bar, bottom tab bar,
single column, cards instead of tables). Streamlit's own chrome is restyled or
hidden so the product reads as one designed surface.
"""
from dashboard.v4 import tokens as T


def build(theme: str) -> str:
    c = T.palette(theme)
    v = "\n".join(f"  --{k}: {val};" for k, val in c.items())
    ph = T.PHONE_MAX
    return f"""<style>
@import url('{T.FONT_URL}');
:root {{
{v}
  --font: {T.FONT};
  color-scheme: {'dark' if theme == 'dark' else 'light'};
}}

/* ---------- Streamlit chrome ---------- */
.stApp, [data-testid="stAppViewContainer"] {{ background: var(--bg); color: var(--text); direction: rtl; font-family: var(--font); }}
.stApp p, .stApp li, .stApp a, .stApp button, .stApp input, .stApp h1, .stApp h2, .stApp h3 {{ font-family: var(--font); }}
.stApp [data-testid="stIconMaterial"] {{ font-family: 'Material Symbols Rounded' !important; }}
[data-testid="stElementContainer"]:has(iframe[title*="localstore"]) {{ height: 0; overflow: hidden; margin: 0; }}
header[data-testid="stHeader"] {{ display: none; }}
[data-testid="stDecoration"], footer:not(.v4-footer), [data-testid="stStatusWidget"] {{ display: none !important; }}
.block-container, [data-testid="stMainBlockContainer"] {{ max-width: 1196px; padding: 32px 48px 72px !important; }}
[data-testid="stVerticalBlock"] {{ gap: 0; }}
.v4-gap-lg {{ height: 32px; }} .v4-gap {{ height: 20px; }} .v4-gap-sm {{ height: 12px; }}
.stApp a {{ color: var(--accent); text-decoration: none; }}
.stApp a:hover {{ text-decoration: underline; }}
*:focus-visible {{ outline: 2px solid var(--accent) !important; outline-offset: 2px; }}
[data-testid="stElementContainer"]:has(> [data-testid="stHtml"] > style) {{ display: none; }}

/* ---------- side navigation (desktop) ---------- */
/* the collapse control is hidden, so the menu is never collapsed on desktop (Streamlit collapses it
   after a visit at phone width and, in RTL, would leave it over the content) */
section[data-testid="stSidebar"] {{ transform: none !important; max-width: none !important; }}
section[data-testid="stSidebar"] {{ width: {T.SIDEBAR_W}px !important; min-width: {T.SIDEBAR_W}px !important;
  background: var(--surface); border-left: 1px solid var(--border); }}
section[data-testid="stSidebar"] > div {{ padding: 22px 14px; }}
[data-testid="stSidebarHeader"], [data-testid="stSidebarCollapseButton"], [data-testid="stSidebarCollapsedControl"],
[data-testid="stExpandSidebarButton"] {{ display: none !important; }}
.v4-brand-bar {{ padding: 0 !important; }}
.v4-brand {{ display: flex; align-items: center; gap: 10px; padding: 0 8px 18px; font-size: 17px; font-weight: 700; color: var(--text); }}
.v4-navlabel {{ font-size: 12.5px; font-weight: 600; color: var(--text3); padding: 16px 12px 6px; }}
[data-testid="stPageLink"] a {{ display: flex; align-items: center; gap: 12px; min-height: 44px; padding: 0 12px;
  border-radius: {T.RADIUS['sm']}px; color: var(--text2) !important; text-decoration: none !important; background: transparent; }}
[data-testid="stPageLink"] a p, [data-testid="stPageLink"] a span {{ color: inherit !important; font-size: 15px; font-weight: 500; }}
[data-testid="stPageLink"] a:hover {{ background: var(--surface2); }}
[class*="st-key-v4on-"] [data-testid="stPageLink"] a {{ background: var(--accentSoft); color: var(--accent) !important; }}
[class*="st-key-v4on-"] [data-testid="stPageLink"] a p {{ font-weight: 700; }}
section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] > div > [data-testid="stVerticalBlock"] {{ min-height: calc(100vh - 44px); }}
.st-key-v4sidefoot {{ border-top: 1px solid var(--border); padding-top: 14px; }}
[data-testid="stLayoutWrapper"]:has(> .st-key-v4sidefoot) {{ margin-top: auto; padding-top: 20px; }}

/* segmented controls (theme, level of detail) */
[data-testid="stButtonGroup"] {{ background: var(--surface2); border-radius: {T.RADIUS['md']}px; padding: 3px; display: inline-flex; gap: 2px; }}
[data-testid="stButtonGroup"] button {{ border: none !important; background: transparent !important; color: var(--text2) !important;
  min-height: 36px; border-radius: {T.RADIUS['sm']}px !important; padding: 0 14px !important; box-shadow: none !important; }}
[data-testid="stButtonGroup"] button p {{ font-size: 13.5px; font-weight: 600; color: inherit !important; }}
[data-testid="stButtonGroup"] button[kind$="Active"], [data-testid="stButtonGroup"] button[aria-checked="true"] {{
  background: var(--surface) !important; color: var(--text) !important; box-shadow: var(--shadowSm) !important; }}
[data-testid="stWidgetLabel"] {{ display: none; }}

/* buttons */
.stButton button {{ min-height: 44px; border-radius: {T.RADIUS['md']}px; border: 1px solid var(--border); background: var(--surface);
  color: var(--text); font-weight: 600; box-shadow: none; }}
.stButton button:hover {{ border-color: var(--accent); color: var(--accent); }}
.stButton button[kind="primary"] {{ background: var(--accent); color: var(--onAccent); border-color: var(--accent); }}
.stButton button[kind="tertiary"] {{ border: none; background: transparent; color: var(--accent); padding: 0 6px; min-height: 40px; }}

/* search box */
.stTextInput input {{ min-height: 42px; border-radius: {T.RADIUS['md']}px; background: var(--surface) !important; color: var(--text) !important;
  border: 1px solid var(--border) !important; box-shadow: none !important; font-size: 14.5px; direction: rtl; padding: 0 12px; }}
.stTextInput input:focus {{ border-color: var(--accent) !important; box-shadow: 0 0 0 2px var(--accentSoft) !important; }}
.stTextInput [data-baseweb="input"], .stTextInput [data-baseweb="base-input"] {{ background: transparent !important; border: none !important;
  box-shadow: none !important; }}
.stTextInput input::placeholder {{ color: var(--text3) !important; opacity: 1; }}

/* ---------- page header ---------- */
.v4-h1 {{ margin: 0; font-size: 32px; line-height: 40px; font-weight: 800; letter-spacing: -0.015em; color: var(--text); }}
.v4-sub {{ font-size: 14.5px; color: var(--text3); margin-top: 4px; }}
.st-key-v4head {{ margin-bottom: 28px; }}
.st-key-v4head [data-testid="stHorizontalBlock"] {{ align-items: flex-end; }}

/* ---------- shared components ---------- */
.v4-card {{ background: var(--surface); border: 1px solid var(--border); border-radius: {T.RADIUS['lg']}px; padding: 20px 22px; }}
.v4-h2 {{ margin: 0; font-size: 22px; line-height: 30px; font-weight: 800; letter-spacing: -0.01em; color: var(--text); }}
.v4-h3 {{ margin: 0; font-size: 18px; line-height: 26px; font-weight: 700; letter-spacing: -0.005em; color: var(--text); }}
.v4-muted {{ color: var(--text3); font-size: 15px; }}
.v4-chip {{ display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; border-radius: 999px; font-size: 14px; font-weight: 700; white-space: nowrap; }}
.v4-chip svg {{ flex: 0 0 auto; }}
.t-positive {{ color: var(--positive); }} .t-warning {{ color: var(--warning); }} .t-negative {{ color: var(--negative); }} .t-muted {{ color: var(--muted); }}
.bg-positive {{ background: var(--posSoft); }} .bg-warning {{ background: var(--warnSoft); }} .bg-negative {{ background: var(--negSoft); }} .bg-muted {{ background: var(--mutedSoft); }}
.v4c-conflict, .v4c-missing, .v4-notice {{ box-shadow: inset 0 0 0 1px var(--warnLine); }}
.dot-positive {{ background: var(--positive); }} .dot-warning {{ background: var(--warning); }} .dot-negative {{ background: var(--negative); }} .dot-muted {{ background: var(--text3); }}
.v4-num {{ font-variant-numeric: tabular-nums; direction: ltr; unicode-bidi: isolate; }}

/* market hero */
.v4-hero {{ background: var(--surface); border: 1px solid var(--border); border-radius: {T.RADIUS['xl']}px; box-shadow: var(--shadowMd);
  padding: 32px 36px; display: grid; grid-template-columns: minmax(0, 1fr) 300px; gap: 32px; align-items: center; margin-bottom: 32px; }}
.v4-hero-k {{ display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 12px; }}
.v4-eyebrow {{ font-size: 13px; font-weight: 600; color: var(--text3); }}
.v4-states {{ display: flex; gap: 4px; padding: 3px; border-radius: 999px; background: var(--surface2); }}
.v4-states span {{ padding: 3px 11px; border-radius: 999px; font-size: 13px; font-weight: 600; color: var(--text3); }}
.v4-states span.on {{ font-weight: 700; }}
.v4-hero h2 {{ margin: 0 0 12px; font-size: 30px; line-height: 40px; font-weight: 800; letter-spacing: -0.015em; text-wrap: balance; color: var(--text); }}
.v4-hero p {{ margin: 0; max-width: 640px; font-size: 17px; line-height: 28px; color: var(--text2); }}
.v4-figs {{ border-right: 1px solid var(--border); padding-right: 28px; }}
.v4-fig {{ display: flex; justify-content: space-between; align-items: baseline; padding: 10px 0; border-bottom: 1px solid var(--border); }}
.v4-fig .k {{ font-size: 15px; color: var(--text2); }}
.v4-fig .v {{ font-size: 16px; font-weight: 700; color: var(--text); }}
.v4-fig .c {{ font-size: 14px; font-weight: 600; margin-right: 6px; }}
.v4-figs .more {{ display: inline-block; margin-top: 12px; font-size: 14.5px; font-weight: 600; color: var(--accent) !important; }}
[class*="st-key-v4set-"] [data-testid="stPageLink"] a {{ color: var(--accent) !important; padding: 0; min-height: 36px; }}
[class*="st-key-v4set-"] [data-testid="stPageLink"] a p {{ font-weight: 600; }}
[class*="st-key-v4set-"] [data-testid="stPageLink"] a:hover {{ background: transparent; text-decoration: underline !important; }}
.v4-notice {{ border-radius: {T.RADIUS['md']}px; padding: 12px 14px; font-size: 15px; line-height: 23px; background: var(--warnSoft); color: var(--text); }}

/* section heads */
.v4-sec {{ margin-bottom: 14px; }}

/* stock pick card: the keyed container is the card */
[class*="st-key-v4pick-"] {{ position: relative; background: var(--surface); border: 1px solid var(--border); border-radius: {T.RADIUS['lg']}px;
  padding: 20px 22px 8px; margin-bottom: 14px; }}
@media (min-width: {ph + 1}px) {{
  [class*="st-key-v4pick-"] {{ padding-bottom: 10px; }}
  [class*="st-key-v4pick-"] [data-testid="stElementContainer"]:has([data-testid="stPageLink"]) {{ position: absolute; left: 22px; bottom: 8px;
    width: auto !important; }}
  [class*="st-key-v4pick-"] .v4-dims, [class*="st-key-v4pick-"] .v4-calm {{ padding-left: 140px; }}
}}
.v4-pick-top {{ display: flex; justify-content: space-between; align-items: center; gap: 12px; }}
.v4-co {{ display: flex; align-items: center; gap: 12px; min-width: 0; }}
.v4-ini {{ flex: 0 0 44px; height: 44px; border-radius: 12px; background: var(--surface2); display: flex; align-items: center; justify-content: center;
  font-size: 17px; font-weight: 700; color: var(--text2); }}
.v4-co-name {{ font-size: 18px; font-weight: 700; color: var(--text); direction: ltr; text-align: right; }}
.v4-co-tk {{ font-size: 13.5px; color: var(--text3); }}
.v4-pick-px {{ display: flex; align-items: center; gap: 16px; }}
.v4-px {{ text-align: left; }} .v4-px .v {{ font-size: 17px; font-weight: 700; color: var(--text); }} .v4-px .c {{ font-size: 13.5px; font-weight: 600; }}
.v4-why {{ margin: 12px 0; font-size: 16px; line-height: 26px; color: var(--text2); }}
.v4-dims {{ list-style: none; margin: 0; padding: 12px 0 4px; border-top: 1px solid var(--border); display: flex; gap: 8px 20px; flex-wrap: wrap; }}
.v4-dims li {{ display: inline-flex; align-items: center; gap: 7px; font-size: 14px; color: var(--text); }}
.v4-dims .d {{ width: 8px; height: 8px; border-radius: 50%; }}
.v4-dims .k {{ color: var(--text3); }} .v4-dims b {{ font-weight: 600; }}
.v4-meta {{ font-size: 13.5px; color: var(--text3); padding-bottom: 6px; }}
.v4-calm {{ display: flex; align-items: center; gap: 8px; padding: 12px 0 6px; border-top: 1px solid var(--border); font-size: 14px; color: var(--text2); }}
.v4-calm svg {{ flex: 0 0 auto; color: var(--positive); }}
[class*="st-key-v4pick-"] [data-testid="stPageLink"] a {{ min-height: 40px; padding: 0; color: var(--accent) !important; justify-content: flex-start; }}
[class*="st-key-v4pick-"] [data-testid="stPageLink"] a p {{ font-weight: 600; font-size: 14.5px; }}
[class*="st-key-v4pick-"] [data-testid="stPageLink"] a:hover {{ background: transparent; text-decoration: underline !important; }}
[class*="st-key-v4pick-"] [data-testid="stIconMaterial"], .st-key-v4more [data-testid="stIconMaterial"],
.st-key-v4howto [data-testid="stIconMaterial"] {{ display: none; }}
.st-key-v4more [data-testid="stPageLink"] a {{ color: var(--accent) !important; padding: 0; }}
.st-key-v4more [data-testid="stPageLink"] a p, .st-key-v4howto [data-testid="stPageLink"] a p {{ font-weight: 600; }}
.st-key-v4howto [data-testid="stPageLink"] a {{ background: var(--accent); color: var(--onAccent) !important; padding: 0 16px; min-height: 40px; border-radius: {T.RADIUS['md']}px; }}
.st-key-v4howto [data-testid="stPageLink"] a:hover {{ background: var(--accent); text-decoration: none !important; }}

/* ---------- markets ---------- */
.v4m-sec {{ background: var(--surface); border: 1px solid var(--border); border-radius: {T.RADIUS['lg']}px; padding: 22px 24px 24px;
  margin-bottom: 20px; }}
.v4m-sec .v4-h3 {{ font-size: 19px; line-height: 27px; }}
.v4m-sec .v4c-tblwrap {{ border: none; border-radius: 0; margin: 12px -24px 0; border-top: 1px solid var(--border); border-bottom: 1px solid var(--border); }}
.v4m-sec .v4c-tblwrap:last-child {{ border-bottom: none; margin-bottom: -24px; }}
.st-key-v4m-chart {{ background: var(--surface); border: 1px solid var(--border); border-radius: {T.RADIUS['lg']}px; padding: 22px 24px 16px; margin-bottom: 20px; }}
.st-key-v4m-chart .v4m-sec {{ background: none; border: none; padding: 0; margin: 0 0 8px; }}
.v4m-sec .v4m-list {{ border: none; border-radius: 0; background: transparent; }}
.v4m-sec .v4m-list li {{ padding: 10px 0; }}
.v4m-sec .v4m-stats {{ border: none; border-radius: 0; background: transparent; gap: 0; }}
.v4m-sec .v4m-stat {{ padding: 12px 0; background: transparent; }}
.v4m-sec .v4m-stat + .v4m-stat {{ border-top: 1px solid var(--border); }}
.v4m-sum {{ margin: 4px 0 12px; font-size: 15.5px; line-height: 25px; color: var(--text2); }}
.v4m-tbl {{ background: var(--surface); }}
.v4m-tbl td:first-child {{ font-weight: 600; }}
.v4m-tbl tr.na td {{ color: var(--text3); }}
.v4m-tbl .why {{ font-size: 12.5px; font-weight: 400; color: var(--text3); }}
.v4m-tbl .tr {{ color: var(--text2); }}
.v4m-two {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
.v4m-two h3 {{ margin: 0 0 6px; font-size: 15px; font-weight: 700; color: var(--text2); }}
.v4m-list {{ list-style: none; margin: 0; padding: 0; background: var(--surface); border: 1px solid var(--border); border-radius: {T.RADIUS['md']}px; }}
.v4m-list li {{ display: flex; justify-content: space-between; align-items: center; gap: 10px; padding: 10px 14px; font-size: 15px; color: var(--text); }}
.v4m-list li + li {{ border-top: 1px solid var(--border); }}
.v4m-stats {{ display: grid; gap: 1px; background: var(--border); border: 1px solid var(--border); border-radius: {T.RADIUS['md']}px; overflow: hidden; }}
.v4m-stat {{ background: var(--surface); padding: 12px 16px; display: grid; grid-template-columns: 1fr auto; gap: 2px 12px; }}
.v4m-stat .k {{ font-size: 14.5px; color: var(--text); font-weight: 600; }}
.v4m-stat b {{ grid-row: span 2; align-self: center; font-size: 22px; font-weight: 700; color: var(--text); }}
.v4m-stat .t {{ font-size: 13.5px; color: var(--text3); }}
.v4m-valid {{ display: flex; gap: 8px; align-items: flex-start; margin: -12px 0 24px; color: var(--positive); }}
.v4m-valid p {{ margin: 0; font-size: 13.5px; line-height: 21px; color: var(--text3); }}
.v4m-valid p b {{ font-weight: 600; color: var(--text2); }}
.v4m-tbl td.tr.t-positive {{ color: var(--positive); }} .v4m-tbl td.tr.t-negative {{ color: var(--negative); }}
.v4m-valid svg {{ flex: 0 0 auto; margin-top: 3px; }}
.st-key-v4m-chart [data-testid="stButtonGroup"] {{ margin: 0 0 4px; }}
.st-key-v4m-pick {{ flex-wrap: wrap; align-items: center; margin-bottom: 6px; }}
.st-key-v4m-pick .stSelectbox {{ min-width: 190px; }}
.v4m-tbl td.pos {{ min-width: 110px; }}

/* ---------- alerts ---------- */
.v4a-gh {{ display: flex; align-items: center; gap: 10px; margin: 22px 0 10px; }}
.v4a-gh .sub {{ font-size: 14.5px; color: var(--text3); }}
[class*="st-key-v4alg-"] {{ background: var(--surface); border: 1px solid var(--border); border-radius: {T.RADIUS['lg']}px;
  padding: 0 22px; margin-bottom: 8px; }}
[class*="st-key-v4al-"] {{ position: relative; padding: 16px 16px 6px 0; }}
[class*="st-key-v4al-"] + [class*="st-key-v4al-"] {{ border-top: 1px solid var(--border); }}
[class*="st-key-v4al-critical"]::before, [class*="st-key-v4al-important"]::before {{ content: ""; position: absolute; right: 0; top: 20px;
  width: 3px; height: 22px; border-radius: 2px; background: var(--negative); }}
[class*="st-key-v4al-important"]::before {{ background: var(--warning); }}
.v4a-card .top {{ display: flex; justify-content: space-between; align-items: center; gap: 10px; flex-wrap: wrap; }}
.v4a-card .meta {{ font-size: 13px; color: var(--text3); }}
.v4a-card h3 {{ margin: 8px 0 4px; font-size: 17px; line-height: 25px; font-weight: 700; color: var(--text); }}
.v4a-card p {{ margin: 0; font-size: 15px; line-height: 24px; color: var(--text2); }}
.v4a-card .raw {{ margin-top: 6px; font-size: 12.5px; color: var(--text3); }}
[class*="st-key-v4al-"] [data-testid="stPageLink"] a {{ min-height: 40px; padding: 0; color: var(--accent) !important; justify-content: flex-start; }}
[class*="st-key-v4al-"] [data-testid="stPageLink"] a p {{ font-weight: 600; font-size: 14.5px; }}
[class*="st-key-v4al-"] [data-testid="stPageLink"] a:hover {{ background: transparent; text-decoration: underline !important; }}
[class*="st-key-v4al-"] [data-testid="stIconMaterial"] {{ display: none; }}

/* the whole screen may show old data */
.v4-databanner {{ display: flex; gap: 10px; align-items: flex-start; margin: 0 0 18px; padding: 12px 14px; border-radius: {T.RADIUS['md']}px;
  background: var(--warnSoft); box-shadow: inset 0 0 0 1px var(--warnLine); color: var(--warning); font-size: 14.5px; line-height: 22px; }}
.v4-databanner span {{ color: var(--text); }}
.v4-databanner svg {{ flex: 0 0 auto; margin-top: 3px; }}
/* the verdict rests on older business data */
.v4-stale {{ display: flex; gap: 6px; align-items: flex-start; margin: 6px 0 10px; font-size: 13.5px; line-height: 20px; color: var(--warning); }}
.v4-stale svg {{ flex: 0 0 auto; margin-top: 3px; }}
.v4-orow .why .v4-stale {{ margin: 6px 0 0; }}

/* quiet explanatory note */
.v4-note {{ display: flex; gap: 10px; align-items: flex-start; background: var(--surface2); border-radius: {T.RADIUS['md']}px;
  padding: 12px 14px; margin: 2px 0 14px; }}
.v4-note-i {{ color: var(--text3); padding-top: 2px; }}
.v4-note p {{ margin: 0; font-size: 14.5px; line-height: 23px; color: var(--text2); }}
.v4-note-d {{ margin-top: 6px; font-size: 13.5px; line-height: 21px; color: var(--text3); }}

/* opportunities: decision tabs and filters */
[class*="st-key-v4obar-"] {{ justify-content: space-between; flex-wrap: wrap; gap: 12px; }}
[class*="st-key-v4obar-"] [data-testid="stButtonGroup"] button {{ min-height: 40px; padding: 0 16px !important; }}
[class*="st-key-v4obar-"] [data-testid="stButtonGroup"] button p {{ font-size: 14.5px; }}
.st-key-v4obar-buy [data-testid="stButtonGroup"] button[kind$="Active"] {{ color: var(--positive) !important; }}
.st-key-v4obar-wait [data-testid="stButtonGroup"] button[kind$="Active"] {{ color: var(--warning) !important; }}
.st-key-v4obar-avoid [data-testid="stButtonGroup"] button[kind$="Active"] {{ color: var(--negative) !important; }}
.st-key-v4ofilters {{ flex: 0 1 auto; width: auto !important; flex-wrap: wrap; }}
.st-key-v4ofilters [data-testid="stElementContainer"] {{ width: auto !important; }}
.st-key-v4ofilters .stSelectbox {{ min-width: 150px; }}
.stSelectbox [data-baseweb="select"] > div {{ min-height: 40px; border-radius: {T.RADIUS['md']}px; border: 1px solid var(--border) !important;
  background: var(--surface) !important; color: var(--text) !important; font-size: 14px; font-weight: 500; }}
.stSelectbox [data-baseweb="select"] svg {{ color: var(--text3); }}
[data-baseweb="popover"] ul, [data-baseweb="popover"] li {{ background: var(--surface) !important; color: var(--text) !important; font-family: var(--font); }}
[data-baseweb="popover"] li:hover, [data-baseweb="popover"] li[aria-selected="true"] {{ background: var(--surface2) !important; }}

/* opportunities: the table (rows are keyed containers so the whole row is one link) */
.st-key-v4otbl {{ background: var(--surface); border: 1px solid var(--border); border-radius: 14px; overflow-x: auto; overflow-y: hidden; }}
.v4-orow {{ display: grid; grid-template-columns: minmax(200px, 1.6fr) 112px 104px 116px 104px 100px minmax(220px, 2fr);
  align-items: center; min-width: 1000px; min-height: 64px; color: var(--text); }}
.v4-orow.adv {{ grid-template-columns: minmax(190px, 1.5fr) 104px 64px 96px 104px 96px 92px 70px minmax(220px, 1.8fr); min-width: 1100px; }}
.v4-orow .c {{ padding: 10px; display: flex; align-items: center; gap: 7px; font-size: 14.5px; min-width: 0; }}
.v4-orow .c:first-child {{ padding-right: 20px; }} .v4-orow .c:last-child {{ padding-left: 20px; }}
.v4-orow .c b {{ font-weight: 600; }}
.v4-orow .d, .v4-ocard .d {{ flex: 0 0 8px; width: 8px; height: 8px; border-radius: 50%; }}
.v4-orow .co {{ gap: 12px; }}
.v4-orow .n, .v4-ocard .n {{ font-size: 15.5px; font-weight: 700; direction: ltr; text-align: right; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.v4-orow .s, .v4-ocard .s {{ font-size: 13px; color: var(--text3); }}
.v4-orow .px {{ display: block; text-align: right; }}
.v4-orow .px .p, .v4-ocard .p {{ font-size: 15px; font-weight: 600; text-align: right; }}
.v4-orow .px .ch, .v4-ocard .ch {{ font-size: 13px; font-weight: 600; text-align: right; }}
.v4-orow .why {{ display: block; line-height: 21px; color: var(--text2); }}
.v4-orow .why .wt {{ display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }}
.v4-stale-i {{ display: inline-flex; align-items: center; color: var(--warning); margin-inline-start: 6px; vertical-align: middle; }}
.v4-orow .sc {{ font-weight: 600; justify-content: flex-start; }}
.v4-ohead {{ min-height: 0; background: var(--surface2); }}
.v4-ohead .c {{ font-size: 13px; font-weight: 600; color: var(--text2); padding-top: 12px; padding-bottom: 12px; }}
.v4-ini.sm {{ flex: 0 0 36px; height: 36px; border-radius: 10px; font-size: 14px; }}
.sr {{ position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }}
[class*="st-key-v4orow-"] {{ position: relative; border-top: 1px solid var(--border); min-width: 1000px; }}
.st-key-v4otbl:has(.v4-orow.adv) [class*="st-key-v4orow-"], .st-key-v4otbl:has(.v4-orow.adv) .st-key-v4ofoot {{ min-width: 1100px; }}
.st-key-v4otbl [data-testid="stElementContainer"] {{ width: 100% !important; }}
[class*="st-key-v4orow-"]:hover {{ background: var(--surface2); }}
[class*="st-key-v4orow-"] [data-testid="stElementContainer"]:has([data-testid="stPageLink"]) {{ position: absolute; inset: 0; z-index: 2; margin: 0; }}
[class*="st-key-v4orow-"] [data-testid="stPageLink"], [class*="st-key-v4orow-"] [data-testid="stPageLink"] > div {{ height: 100%; }}
[class*="st-key-v4orow-"] [data-testid="stPageLink"] a {{ height: 100%; min-height: 0; border-radius: 0; background: transparent !important; color: transparent !important; }}
[class*="st-key-v4orow-"] [data-testid="stPageLink"] a * {{ color: transparent !important; }}
.v4-ocard {{ display: none; }}
.st-key-v4ofoot {{ justify-content: space-between; border-top: 1px solid var(--border); padding: 8px 20px; min-height: 56px; min-width: 1000px; }}
.st-key-v4ofoot .stButton button {{ min-height: 36px; font-size: 14px; }}
.v4-legend {{ display: flex; gap: 8px 22px; flex-wrap: wrap; font-size: 14px; color: var(--text3); padding-top: 14px; }}
.v4-legend > span {{ display: inline-flex; align-items: center; gap: 7px; }}
.v4-legend .d {{ width: 8px; height: 8px; border-radius: 50%; }}

/* ---------- company analysis ---------- */
.dot-accent {{ background: var(--accent); }}
.v4-ini.lg {{ flex: 0 0 56px; height: 56px; border-radius: 14px; font-size: 22px; }}
.st-key-v4chead {{ margin-bottom: 22px; }}
.st-key-v4cact {{ flex-wrap: wrap; justify-content: flex-end; }}
.st-key-v4cact .stButton button {{ min-height: 40px; padding: 0 14px; font-size: 14px; }}
.v4c-crumb {{ font-size: 13.5px; color: var(--text3); margin-bottom: 10px; }}
.v4c-head {{ display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }}
.v4c-id {{ flex: 1 1 260px; min-width: 0; }}
.v4c-id .v4-h1 {{ font-size: 34px; line-height: 42px; letter-spacing: -0.02em; }}
.v4c-id .nm {{ direction: ltr; unicode-bidi: isolate; }}
.v4c-sub {{ font-size: 15px; color: var(--text3); margin-top: 2px; }}
.v4c-px {{ text-align: left; }}
.v4c-px .v {{ font-size: 30px; line-height: 36px; font-weight: 800; letter-spacing: -0.02em; color: var(--text); }}
.v4c-px .c {{ font-size: 14px; color: var(--text3); }} .v4c-px .c .v4-num {{ font-weight: 600; }}

.v4c-hero {{ background: var(--surface); border: 1px solid var(--border); border-radius: {T.RADIUS['xl']}px; box-shadow: var(--shadowMd);
  padding: 28px 32px; display: grid; grid-template-columns: minmax(0, 1fr) 260px; gap: 32px; margin-bottom: 18px; }}
.v4c-eyebrow {{ display: flex; align-items: center; gap: 10px; flex-wrap: wrap; font-size: 13px; font-weight: 600; color: var(--text3); margin-bottom: 12px; }}
.v4c-hero h2 {{ margin: 0 0 10px; font-size: 28px; line-height: 38px; font-weight: 800; letter-spacing: -0.015em; color: var(--text); text-wrap: balance; }}
.v4c-why {{ margin: 0; font-size: 17px; line-height: 28px; color: var(--text2); max-width: 680px; }}
.v4c-answers {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1px; background: var(--border);
  border: 1px solid var(--border); border-radius: 12px; overflow: hidden; margin-top: 20px; }}
.v4c-ans {{ background: var(--surface2); padding: 12px 16px; display: flex; flex-direction: column; gap: 2px; }}
.v4c-ans .q {{ font-size: 13.5px; color: var(--text3); }} .v4c-ans b {{ font-size: 17px; font-weight: 700; }}
.v4c-lesson {{ margin: 14px 0 0; font-size: 14.5px; line-height: 23px; color: var(--text2); }}
.v4c-facts.aside {{ border-right: 1px solid var(--border); padding-right: 24px; align-self: center; }}
.v4c-facts .f {{ display: flex; justify-content: space-between; align-items: baseline; gap: 10px; padding: 9px 0; border-bottom: 1px solid var(--border); }}
.v4c-facts .f:last-child {{ border-bottom: none; }}
.v4c-facts .k {{ font-size: 14px; color: var(--text2); }} .v4c-facts b {{ font-size: 15px; font-weight: 700; color: var(--text); }}
.v4c-facts.inline {{ display: flex; flex-wrap: wrap; gap: 8px 28px; margin: 12px 0; }}
.v4c-facts.inline .f {{ border: none; padding: 0; gap: 8px; }}
.v4c-facts.grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0 28px; margin-top: 14px; }}

.v4c-duo {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1px; background: var(--border); border: 1px solid var(--border);
  border-radius: {T.RADIUS['lg']}px; overflow: hidden; margin-bottom: 24px; }}
.v4c-duo > section {{ background: var(--surface); padding: 18px 22px; display: flex; flex-direction: column; gap: 8px; }}
.v4c-duo h3, .v4c-parts h3 {{ margin: 0; font-size: 16px; font-weight: 700; color: var(--text); }}
.v4c-duo p {{ margin: 0; font-size: 15px; line-height: 24px; color: var(--text2); }}
.v4c-list {{ margin: 0; padding-inline-start: 18px; display: grid; gap: 6px; font-size: 15px; line-height: 24px; color: var(--text2); }}

.v4c-nav {{ display: flex; gap: 6px; flex-wrap: wrap; padding: 10px 0 16px; margin-bottom: 8px; border-bottom: 1px solid var(--border); }}
.v4c-nav .g {{ align-self: center; font-size: 12.5px; font-weight: 600; color: var(--text3); padding: 0 4px 0 2px; }}
.v4c-nav .g + a {{ margin-inline-start: 0; }}
.v4c-nav a + .g {{ margin-inline-start: 14px; padding-inline-start: 14px; border-inline-start: 1px solid var(--border); }}
.v4c-flag {{ display: flex; gap: 8px; align-items: flex-start; margin-top: 14px; padding: 10px 14px; border-radius: {T.RADIUS['md']}px;
  background: var(--surface2); color: var(--text3) !important; text-decoration: none !important; font-size: 14.5px; line-height: 22px; }}
.v4c-flag span {{ color: var(--text); }} .v4c-flag u {{ color: var(--accent); text-decoration: none; font-weight: 600; white-space: nowrap; }}
.v4c-flag svg {{ flex: 0 0 auto; margin-top: 3px; }}
.v4c-badge.key {{ color: var(--accent); background: var(--accentSoft); border-color: transparent; }}
.v4c-nav a {{ padding: 6px 14px; border-radius: 999px; background: var(--surface); border: 1px solid var(--border); color: var(--text2) !important;
  font-size: 14px; font-weight: 500; text-decoration: none !important; white-space: nowrap; }}
.v4c-nav a:hover {{ border-color: var(--accent); color: var(--accent) !important; }}

[class*="st-key-v4cs-"] {{ background: var(--surface); border: 1px solid var(--border); border-radius: {T.RADIUS['lg']}px;
  padding: 22px 24px 24px; margin-bottom: 16px; }}
.st-key-v4cside {{ position: sticky; top: 16px; }}
.v4c-sechead {{ display: flex; align-items: center; gap: 10px; flex-wrap: wrap; scroll-margin-top: 16px; }}
.v4c-badge {{ font-size: 12.5px; font-weight: 600; color: var(--text2); background: var(--surface2); border: 1px solid var(--border);
  padding: 2px 10px; border-radius: 999px; }}
.v4c-secsub {{ margin: 4px 0 14px; font-size: 15px; line-height: 23px; color: var(--text3); }}
.v4c-h3 {{ margin: 18px 0 0; font-size: 16px; font-weight: 700; color: var(--text); }}
.v4c-p {{ margin: 10px 0; font-size: 15.5px; line-height: 25px; color: var(--text2); }}
.v4c-fine {{ margin: 10px 0 0; font-size: 13.5px; line-height: 21px; color: var(--text3); }}
.v4c-fine b {{ color: var(--text2); }}
.v4c-missing {{ margin-top: 12px; padding: 14px 16px; border-radius: {T.RADIUS['md']}px; background: var(--warnSoft); color: var(--text);
  font-size: 15px; line-height: 23px; }}

.v4c-checks {{ list-style: none; margin: 12px 0 0; padding: 0; display: grid; }}
.v4c-checks li {{ display: grid; grid-template-columns: 96px minmax(0, 1fr) auto; gap: 14px; align-items: center; padding: 12px 0;
  border-top: 1px solid var(--border); }}
.v4c-checks li:first-child {{ border-top: none; }}
.v4c-checks .m {{ display: inline-flex; align-items: center; justify-content: center; gap: 5px; font-size: 13px; font-weight: 700;
  border-radius: 999px; padding: 4px 8px; }}
.v4c-checks .b {{ display: flex; flex-direction: column; gap: 1px; min-width: 0; }}
.v4c-checks .b b {{ font-size: 15.5px; color: var(--text); }} .v4c-checks .b span {{ font-size: 14.5px; color: var(--text2); }}
.v4c-checks .r {{ font-size: 13px; color: var(--text3); }}
.v4c-checks .val {{ font-size: 14.5px; font-weight: 600; color: var(--text); text-align: left; }}
.v4c-parts {{ margin-top: 18px; padding: 16px 18px; border-radius: {T.RADIUS['md']}px; background: var(--surface2); display: grid; gap: 8px; }}
.v4c-part {{ display: grid; grid-template-columns: 170px minmax(0, 1fr) 44px; gap: 12px; align-items: center; font-size: 14px; color: var(--text2); }}
.v4c-part b {{ text-align: left; color: var(--text); }}
.v4-bar.thick {{ height: 10px; border-radius: 5px; }}

.v4c-ptitle {{ display: flex; flex-direction: column; gap: 2px; margin-top: 4px; }}
.v4c-ptitle b {{ font-size: 16px; color: var(--text); }} .v4c-ptitle span {{ font-size: 15px; color: var(--text2); }}
.v4c-range {{ margin: 34px 4px 8px; direction: ltr; }}
.v4c-range .track {{ position: relative; height: 8px; border-radius: 4px; background: var(--segOff); }}
.v4c-range .band {{ position: absolute; top: 0; bottom: 0; border-radius: 4px; background: var(--border); }}
.v4c-range .mk {{ position: absolute; top: 50%; width: 14px; height: 14px; margin-left: -7px; transform: translateY(-50%); border-radius: 50%;
  border: 2px solid var(--surface); }}
.v4c-range .mk.now {{ background: var(--text); z-index: 2; }}
.v4c-range .mk.mean {{ background: var(--text3); }}
.v4c-range .mk .lbl {{ position: absolute; bottom: 16px; left: 50%; transform: translateX(-50%); direction: rtl; white-space: nowrap; font-size: 12.5px; font-weight: 600;
  color: var(--text2); }}
.v4c-range .mk.mean .lbl {{ bottom: auto; top: 16px; font-weight: 500; }}
.v4c-range .ends span {{ direction: rtl; }}
.v4c-range .ends {{ display: flex; justify-content: space-between; margin-top: 26px; font-size: 13px; color: var(--text3); }}
.v4c-pfacet {{ margin-top: 16px; padding-top: 14px; border-top: 1px solid var(--border); }}
.v4c-pfacet > div {{ display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }}
.v4c-pfacet b {{ font-size: 15.5px; color: var(--text); }}
.v4c-pfacet p {{ margin: 6px 0 0; font-size: 14.5px; line-height: 23px; color: var(--text2); }}
.v4c-conflict {{ display: flex; gap: 10px; align-items: flex-start; margin-top: 12px; padding: 12px 14px; border-radius: {T.RADIUS['md']}px;
  background: var(--warnSoft); color: var(--warning); }}
.v4c-conflict p {{ margin: 0; font-size: 14.5px; line-height: 23px; color: var(--text); }}
.v4c-what {{ margin-top: 10px; font-size: 14.5px; color: var(--text2); }}
.v4c-what summary {{ cursor: pointer; color: var(--accent); font-weight: 600; min-height: 32px; display: flex; align-items: center; }}
.v4c-what p {{ margin: 6px 0 0; line-height: 23px; }}
.v4c-tblwrap {{ overflow-x: auto; margin-top: 14px; border: 1px solid var(--border); border-radius: {T.RADIUS['md']}px; background: var(--surface); }}

.v4c-blines {{ list-style: none; margin: 12px 0 0; padding: 0; display: grid; gap: 10px; }}
.v4c-blines li {{ display: grid; grid-template-columns: 10px 72px minmax(0, 1fr); gap: 10px; align-items: baseline; font-size: 15.5px; line-height: 24px; }}
.v4c-blines .d {{ width: 8px; height: 8px; border-radius: 50%; align-self: center; }}
.v4c-blines b {{ color: var(--text); }} .v4c-blines span {{ color: var(--text2); }}
.v4c-years {{ margin-top: 18px; display: grid; gap: 8px; }}
.v4c-years .cap {{ font-size: 13px; color: var(--text3); }}
.v4c-years .yr {{ display: grid; grid-template-columns: 44px minmax(0, 1fr) 76px 56px; gap: 12px; align-items: center; font-size: 14px; color: var(--text2); }}
.v4c-years .yr b {{ text-align: left; color: var(--text); }} .v4c-years .g {{ font-size: 13px; color: var(--text3); text-align: left; }}

.v4c-rlevel {{ display: flex; justify-content: space-between; align-items: center; gap: 10px; margin: 12px 0 10px; font-size: 15px; color: var(--text2); }}
.v4c-risk {{ display: grid; grid-template-columns: 10px minmax(0, 1fr); gap: 10px; padding: 10px 0; border-top: 1px solid var(--border); }}
.v4c-risk .d {{ width: 8px; height: 8px; border-radius: 50%; margin-top: 8px; }}
.v4c-risk b {{ font-size: 15px; line-height: 23px; color: var(--text); font-weight: 600; }}
.v4c-risk p {{ margin: 2px 0 0; font-size: 14px; line-height: 22px; color: var(--text2); }}
[data-testid="stPlotlyChart"] {{ direction: ltr; }}
.st-key-v4cs-chart [data-testid="stButtonGroup"] {{ margin: 12px 0 2px; }}
.v4ci-h {{ display: flex; align-items: center; gap: 8px; margin: 18px 0 8px; font-size: 13.5px; color: var(--text3); }}
[class*="st-key-v4cidx-"] {{ display: grid !important; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 6px; }}
[class*="st-key-v4cidx-"] > div {{ width: auto !important; min-width: 0; }}
[class*="st-key-v4cidx-"] [data-testid="stPageLink"] a {{ border: 1px solid var(--border); background: var(--surface); min-height: 40px;
  border-radius: {T.RADIUS['md']}px; }}
[class*="st-key-v4cidx-"] [data-testid="stPageLink"] a p {{ font-size: 14px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  direction: ltr; text-align: right; }}
[class*="st-key-v4cidx-"] [data-testid="stIconMaterial"] {{ display: none; }}
[class*="st-key-v4cidx-"] [data-testid="stPageLink"] a > div, [class*="st-key-v4cidx-"] [data-testid="stPageLink"] a [data-testid="stMarkdownContainer"] {{ min-width: 0; }}
[class*="st-key-v4cidx-"] [data-testid="stPageLink"] a:hover {{ border-color: var(--accent); background: var(--surface); }}

/* side column panels */
.v4-panel {{ background: var(--surface); border: 1px solid var(--border); border-radius: {T.RADIUS['lg']}px; padding: 20px 22px; margin-bottom: 20px; }}
.v4-panel-head {{ display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 6px; }}
.v4-wk {{ display: flex; gap: 14px; padding: 12px 0; }}
.v4-wk + .v4-wk, .v4-row + .v4-row {{ border-top: 1px solid var(--border); }}
.v4-date {{ flex: 0 0 52px; text-align: center; border-radius: {T.RADIUS['md']}px; background: var(--surface2); padding: 6px 0; align-self: flex-start; }}
.v4-date .d {{ font-size: 12px; color: var(--text3); }} .v4-date .n {{ font-size: 15px; font-weight: 700; color: var(--text); }}
.v4-wk-t {{ font-size: 15px; line-height: 23px; color: var(--text); }} .v4-wk-t b {{ font-weight: 700; }} .v4-wk-t div {{ color: var(--text2); }}
.v4-row {{ display: flex; justify-content: space-between; align-items: center; gap: 10px; min-height: 58px; }}
.v4-row .n {{ font-size: 15px; font-weight: 600; color: var(--text); direction: ltr; text-align: right; }}
.v4-row .c {{ font-size: 13px; }}
.v4-tag {{ padding: 4px 10px; border-radius: 999px; font-size: 13px; font-weight: 600; white-space: nowrap; }}
.st-key-v4howto {{ background: var(--accentSoft); border-radius: {T.RADIUS['lg']}px; padding: 20px 22px 12px; margin-bottom: 20px; }}
.st-key-v4howto p {{ margin: 0; font-size: 15px; line-height: 24px; color: var(--text); }}
.st-key-v4howto [data-testid="stHorizontalBlock"] {{ gap: 8px; }}

/* states */
.v4-empty {{ text-align: center; padding: 20px 8px; color: var(--text2); font-size: 15px; line-height: 23px; }}
.v4-empty b {{ display: block; color: var(--text); font-size: 16px; margin-bottom: 4px; }}
.v4-skel {{ background: linear-gradient(90deg, var(--surface2) 25%, var(--border) 50%, var(--surface2) 75%); background-size: 200% 100%;
  border-radius: 6px; animation: v4shine 1.4s linear infinite; }}
@keyframes v4shine {{ to {{ background-position: -200% 0; }} }}
@media (prefers-reduced-motion: reduce) {{ .v4-skel {{ animation: none; }} }}
/* a term with its short explanation, without leaving the screen */
.v4-term {{ position: relative; border-bottom: 1px dotted var(--text3); cursor: help; }}
.v4-term:focus-visible {{ outline: 2px solid var(--accent); outline-offset: 2px; border-radius: 2px; }}
.v4-tip {{ display: none; position: absolute; top: calc(100% + 8px); inset-inline-start: 0; z-index: 60; width: 280px; max-width: 80vw;
  background: var(--surface); color: var(--text2); border: 1px solid var(--border); border-radius: 10px; box-shadow: 0 8px 24px rgba(17,24,39,.16);
  padding: 10px 12px; font-size: 13.5px; line-height: 21px; font-weight: 400; white-space: normal; text-align: right; cursor: auto; }}
.v4-tip b {{ display: block; color: var(--text); font-size: 14px; font-weight: 700; margin-bottom: 2px; }}
.v4-tip a {{ display: inline-block; margin-top: 4px; font-weight: 600; }}
.v4-term:hover > .v4-tip, .v4-term:focus > .v4-tip, .v4-term:focus-within > .v4-tip {{ display: block; }}
/* glossary */
.v4g-abc {{ display: flex; flex-wrap: wrap; gap: 2px 4px; margin: 14px 0 20px; padding: 6px 0; direction: rtl; position: sticky; top: 0; z-index: 30;
  background: var(--bg); }}
[data-testid="stElementContainer"]:has(> [data-testid="stHtml"] > .v4g-abc) {{ position: sticky; top: 0; z-index: 30; }}
.v4g-abc a, .v4g-abc span {{ min-width: 30px; height: 32px; display: inline-flex; align-items: center; justify-content: center;
  border-radius: 8px; font-size: 15px; font-weight: 700; padding: 0 4px; }}
.v4g-abc a:hover {{ background: var(--accentSoft); }}
.v4g-abc span {{ color: var(--text3); opacity: .45; font-weight: 500; }}
.v4g-sec {{ display: grid; grid-template-columns: 56px minmax(0, 1fr); gap: 8px; background: var(--surface); border: 1px solid var(--border);
  border-radius: {T.RADIUS['lg']}px; padding: 18px 22px; margin-bottom: 16px; scroll-margin-top: 64px; }}
.v4g-l {{ font-size: 24px; font-weight: 800; color: var(--accent); line-height: 30px; white-space: nowrap; direction: ltr; text-align: right; }}
.v4g-sec ul {{ list-style: none; margin: 0; padding: 0; }}
.v4g-sec li {{ display: grid; grid-template-columns: 180px minmax(0, 1fr) minmax(0, 300px); gap: 8px 24px; padding: 14px 0;
  border-bottom: 1px solid var(--border); align-items: start; }}
.v4g-sec li:first-child {{ padding-top: 4px; }}
.v4g-sec li:last-child {{ border-bottom: none; padding-bottom: 2px; }}
.v4g-sec h3 {{ margin: 0; padding: 0; font-size: 16.5px; font-weight: 700; color: var(--text); line-height: 24px; }}
.v4g-sec .t span {{ font-size: 13px; color: var(--text3); }}
.v4g-sec .d p {{ margin: 0; font-size: 15px; line-height: 23px; color: var(--text); }}
.v4g-sec .d .pl, .v4g-sec .d .wy {{ margin-top: 8px; font-size: 14px; line-height: 22px; color: var(--text2); }}
.v4g-sec .d .al {{ margin-top: 6px; font-size: 13px; color: var(--text3); }}
.v4g-sec .ex {{ background: var(--surface2); border-radius: 10px; padding: 10px 14px; font-size: 14px; line-height: 22px; color: var(--text2); }}
.v4g-sec .ex b {{ color: var(--text); }}
.v4g-count {{ font-size: 13.5px; color: var(--text3); padding: 8px 2px 4px; border-top: 1px solid var(--border); margin-top: 8px; }}
/* settings */
[class*="st-key-v4set-"] {{ background: var(--surface); border: 1px solid var(--border); border-radius: {T.RADIUS['lg']}px;
  padding: 20px 22px; margin-bottom: 20px; gap: 10px; }}
.v4s-h {{ font-size: 15px; font-weight: 700; margin: 10px 0 2px; padding: 0; color: var(--text); }}
.v4s-foot {{ margin-top: 4px; font-size: 13.5px; color: var(--text3); }}
.v4s-ver {{ margin: 4px 0 8px; font-size: 15px; color: var(--text); }}
.v4s-tbl {{ width: 100%; border-collapse: collapse; margin: 8px 0 14px; font-size: 14.5px; }}
.v4s-tbl th, .v4s-tbl td {{ text-align: right; padding: 11px 0; border-bottom: 1px solid var(--border); vertical-align: top; }}
.v4s-tbl th {{ font-weight: 600; color: var(--text); width: 34%; padding-left: 16px; }}
.v4s-tbl td {{ color: var(--text2); padding-left: 16px; }}
.v4s-tbl tr:last-child th, .v4s-tbl tr:last-child td {{ border-bottom: none; }}

/* advanced mode */
.v4-adv {{ margin-top: 12px; }}
.v4-tbl {{ width: 100%; border-collapse: collapse; font-size: 14.5px; font-variant-numeric: tabular-nums; }}
.v4-tbl th {{ text-align: right; font-size: 12.5px; font-weight: 600; color: var(--text3); background: transparent; padding: 11px 16px;
  border-bottom: 1px solid var(--border); white-space: nowrap; }}
.v4-tbl td {{ text-align: right; padding: 12px 16px; border-top: 1px solid var(--border); color: var(--text); }}
.v4-tbl tbody tr:first-child td {{ border-top: none; }}
.v4-tbl tbody tr:hover td {{ background: var(--surface2); }}
.v4-tbl td.v4-num, .v4-tbl td .v4-num {{ text-align: right; }}
.v4-tbl td.t-positive {{ color: var(--positive); }} .v4-tbl td.t-negative {{ color: var(--negative); }}
.v4-tbl td.t-warning {{ color: var(--warning); }} .v4-tbl td.t-muted {{ color: var(--text3); }}
.v4-bar {{ height: 6px; border-radius: 3px; background: var(--segOff); position: relative; overflow: hidden; min-width: 80px; }}
.v4-bar span {{ position: absolute; top: 0; bottom: 0; right: 0; border-radius: 3px; }}
.v4-method {{ font-size: 14px; line-height: 22px; color: var(--text2); }}

.v4-footer {{ display: flex; justify-content: space-between; gap: 16px; flex-wrap: wrap; font-size: 13px; line-height: 20px; color: var(--text3);
  border-top: 1px solid var(--border); padding-top: 16px; margin-top: 12px; }}

/* phone-only chrome, hidden on desktop */
.st-key-v4appbar, .st-key-v4tabbar {{ display: none; }}

/* ---------- phone layout ---------- */
@media (max-width: {ph}px) {{
  section[data-testid="stSidebar"] {{ display: none !important; }}
  .block-container, [data-testid="stMainBlockContainer"] {{ padding: 0 16px 104px !important; }}
  .st-key-v4appbar {{ display: flex; position: sticky; top: 0; z-index: 50; margin: 0 -16px 20px; width: calc(100% + 32px) !important;
    min-width: calc(100% + 32px) !important; max-width: none !important; flex: none !important; box-sizing: border-box; height: 56px; padding: 0 8px 0 16px;
    align-items: center; justify-content: space-between; background: var(--surface); border-bottom: 1px solid var(--border); }}
  .st-key-v4appbar [data-testid="stPageLink"] a {{ width: 44px; padding: 0; justify-content: center; }}
  .st-key-v4appbar [data-testid="stPageLink"] a p {{ position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0);
    white-space: nowrap; }}   /* icon only on screen, the name stays for screen readers */
  .st-key-v4tabbar {{ display: flex; position: fixed; bottom: 0; left: 0; right: 0; z-index: 60; height: 68px;
    padding: 6px 4px calc(8px + env(safe-area-inset-bottom, 0px)); background: var(--surface); border-top: 1px solid var(--border);
    justify-content: space-around; align-items: stretch; }}
  .st-key-v4tabbar > div {{ flex: 1 1 0; min-width: 0; }}
  .st-key-v4tabbar [data-testid="stPageLink"] a {{ flex-direction: column; gap: 2px; justify-content: center; padding: 0; min-height: 54px; }}
  .st-key-v4tabbar [data-testid="stPageLink"] a p {{ font-size: 12px; }}
  [class*="st-key-v4tab-on-"] [data-testid="stPageLink"] a {{ color: var(--accent) !important; background: transparent; }}
  [class*="st-key-v4tab-on-"] [data-testid="stPageLink"] a p {{ font-weight: 700; }}
  .v4-h1 {{ font-size: 26px; line-height: 34px; }}
  .v4m-sec {{ margin-bottom: 14px; padding: 18px 16px 20px; border-radius: 16px; }}
  .v4m-sec .v4c-tblwrap {{ margin: 10px -16px 0; }}
  .v4m-sec .v4c-tblwrap:last-child {{ margin-bottom: -20px; }}
  .st-key-v4m-chart {{ padding: 18px 16px 12px; border-radius: 16px; }}
  .v4-sub {{ font-size: 14px; }}
  .st-key-v4head {{ margin-bottom: 20px; }}
  /* the switch sits beside the title, the subtitle keeps the full width under both */
  .st-key-v4head > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] {{ display: block; position: relative; }}
  .st-key-v4head [data-testid="stColumn"]:first-child {{ width: 100% !important; }}
  .st-key-v4head [data-testid="stColumn"]:last-child {{ position: absolute; top: 2px; left: 0; width: auto !important; min-width: 0 !important; }}
  .st-key-v4head [data-testid="stButtonGroup"] button, .st-key-v4chead [data-testid="stButtonGroup"] button {{ min-height: 32px; padding: 0 10px !important; }}
  .st-key-v4head [data-testid="stButtonGroup"] button p, .st-key-v4chead [data-testid="stButtonGroup"] button p {{ font-size: 12.5px; }}
  .v4-hero {{ display: block; padding: 20px 18px; border-radius: 18px; margin-bottom: 24px; }}
  .v4-hero h2 {{ font-size: 22px; line-height: 31px; }}
  .v4-hero p {{ font-size: 15.5px; line-height: 25px; }}
  .v4-hero .v4-states span.off {{ display: none; }}
  .v4-figs {{ border: 1px solid var(--border); padding: 0; margin-top: 14px; border-radius: 12px; overflow: hidden;
    display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 1px; background: var(--border); }}
  .v4-fig {{ display: block; background: var(--surface2); padding: 10px; border: none; }}
  .v4-fig .k {{ display: block; font-size: 12.5px; color: var(--text3); }}
  .v4-fig .v {{ display: block; font-size: 15px; text-align: right; }}
  .v4-fig .c {{ display: block; margin: 0; font-size: 13px; text-align: right; }}
  .v4-figs .more {{ display: none; }}
  [class*="st-key-v4pick-"] {{ padding: 16px 16px 6px; border-radius: 16px; margin-bottom: 12px; }}
  .v4-pick-top {{ flex-wrap: wrap; }}
  .v4-pick-px {{ width: 100%; flex-direction: row-reverse; justify-content: space-between; }}
  .v4-co-name {{ font-size: 17px; }}
  .v4-why {{ font-size: 15px; line-height: 24px; margin: 10px 0; }}
  .v4-dims {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 6px 12px; }}
  .v4-panel {{ border-radius: 16px; padding: 4px 16px; }}
  .v4-panel-head {{ padding-top: 12px; }}
  .v4-tbl {{ font-size: 13.5px; }}
  [class*="st-key-v4obar-"] {{ flex-direction: column; align-items: stretch; }}
  [class*="st-key-v4obar-"] > div {{ flex: 0 0 auto !important; width: 100% !important; }}
  [class*="st-key-v4obar-"] [data-testid="stButtonGroup"] {{ display: block; width: 100%; box-sizing: border-box; }}
  [class*="st-key-v4obar-"] [data-baseweb="button-group"] {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); width: 100%; gap: 2px; }}
  [class*="st-key-v4obar-"] [data-testid="stButtonGroup"] button {{ padding: 0 4px !important; }}
  [class*="st-key-v4obar-"] [data-testid="stButtonGroup"] button {{ min-height: 52px; }}
  [class*="st-key-v4obar-"] [data-testid="stButtonGroup"] button p {{ font-size: 13px; line-height: 17px; white-space: normal; text-align: center; }}
  .st-key-v4ofilters {{ flex-wrap: wrap; width: 100% !important; justify-content: flex-start; gap: 8px !important; }}
  .st-key-v4ofilters > div {{ flex: 1 1 calc(50% - 8px) !important; min-width: 0 !important; width: auto !important; }}
  .st-key-v4ofilters .stSelectbox {{ min-width: 0; }}
  .st-key-v4otbl {{ background: transparent; border: none; border-radius: 0; overflow: visible; }}
  .v4-orow {{ display: none; }}
  [class*="st-key-v4orow-"], .st-key-v4otbl:has(.v4-orow.adv) [class*="st-key-v4orow-"] {{ border: 1px solid var(--border); border-radius: 14px;
    background: var(--surface); margin-bottom: 10px; min-width: 0; }}
  [class*="st-key-v4orow-"] [data-testid="stPageLink"] a {{ border-radius: 14px; }}
  .v4-ocard {{ display: flex; flex-direction: column; gap: 8px; padding: 14px; }}
  .v4-ocard .top {{ display: flex; justify-content: space-between; align-items: center; gap: 10px; }}
  .v4-ocard p {{ margin: 0; font-size: 14.5px; line-height: 22px; color: var(--text2); }}
  .v4-ocard .v4-dims {{ padding-top: 8px; }}
  .st-key-v4ofoot, .st-key-v4otbl:has(.v4-orow.adv) .st-key-v4ofoot {{ border: none; padding: 4px 0; flex-direction: column; align-items: stretch; gap: 8px; min-width: 0; }}
  .st-key-v4ofoot .stButton button {{ width: 100%; min-height: 48px; color: var(--accent); }}
  .v4-legend > span:last-child {{ display: none; }}
  .v4m-tbl .adv, .v4m-tbl .tr {{ display: none; }}
  .v4m-two {{ grid-template-columns: 1fr; gap: 14px; }}
  .v4m-sec .v4-h3 {{ font-size: 19px; }}
  .st-key-v4chead {{ position: relative; }}
  .st-key-v4chead > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] {{ position: absolute; top: 0; left: 0; width: auto !important; z-index: 2; }}
  .st-key-v4chead [data-testid="stColumn"]:first-child {{ display: none; }}
  .st-key-v4chead [data-testid="stColumn"]:last-child, .st-key-v4head [data-testid="stColumn"]:last-child {{ flex: none !important;
    width: max-content !important; min-width: max-content !important; }}
  .st-key-v4cact {{ flex-wrap: nowrap !important; width: max-content !important; }}
  .st-key-v4chead .v4c-id {{ padding-left: 124px; }}
  .st-key-v4cact {{ justify-content: space-between; flex-wrap: nowrap !important; flex-direction: row !important; }}
  .st-key-v4cact > div {{ flex: 0 1 auto !important; width: auto !important; }}
  .v4c-crumb {{ display: none; }}
  .v4c-head {{ gap: 12px; }}
  .v4-ini.lg {{ flex-basis: 44px; height: 44px; font-size: 18px; border-radius: 12px; }}
  .v4c-id {{ flex-basis: 0; flex-grow: 1; }}
  .v4c-id .v4-h1 {{ font-size: 24px; line-height: 31px; }}
  .v4c-sub {{ font-size: 13.5px; }}
  .v4c-px {{ width: 100%; display: flex; align-items: baseline; gap: 10px; text-align: right; }}
  .v4c-px .v {{ font-size: 24px; line-height: 30px; }}
  .v4c-hero {{ display: block; padding: 20px 18px; border-radius: 18px; }}
  .v4c-hero h2 {{ font-size: 22px; line-height: 31px; }}
  .v4c-why {{ font-size: 15.5px; line-height: 25px; }}
  .v4c-answers {{ grid-template-columns: 1fr; }}
  .v4c-facts.aside {{ border: none; padding: 0; margin-top: 16px; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1px;
    background: var(--border); border-radius: 12px; overflow: hidden; }}
  .v4c-facts.aside .f {{ background: var(--surface2); flex-direction: column; gap: 2px; padding: 10px 12px; border: none; }}
  .v4c-facts.aside .f:last-child:nth-child(odd) {{ grid-column: 1 / -1; }}
  .v4c-duo {{ grid-template-columns: 1fr; border-radius: 16px; }}
  .v4c-nav {{ position: sticky; top: 56px; z-index: 40; flex-wrap: nowrap; overflow-x: auto; margin: 0 -16px 4px; padding: 10px 16px;
    background: var(--bg); scrollbar-width: none; }}
  .v4c-nav::-webkit-scrollbar {{ display: none; }}
  .v4c-nav .g {{ display: none; }}
  .v4c-nav a {{ flex: 0 0 auto; margin: 0 !important; }}
  [class*="st-key-v4cs-"] {{ padding: 18px 16px 20px; border-radius: 16px; margin-bottom: 12px; }}
  .st-key-v4cside {{ position: static; }}
  .v4c-sechead {{ scroll-margin-top: 112px; }}
  .v4c-checks li {{ grid-template-columns: 84px minmax(0, 1fr); }}
  .v4c-checks .val {{ grid-column: 2; text-align: right; font-size: 13.5px; color: var(--text2); }}
  .v4c-part {{ grid-template-columns: 120px minmax(0, 1fr) 36px; font-size: 13px; }}
  .v4c-blines li {{ display: block; }}
  .v4c-blines .d {{ display: inline-block; margin-left: 8px; vertical-align: middle; }}
  .v4c-blines b {{ margin-left: 6px; }}
  .v4c-years .yr {{ grid-template-columns: 40px minmax(0, 1fr) 70px; }}
  .v4c-years .g {{ display: none; }}
  .v4c-facts.grid {{ grid-template-columns: 1fr; }}
  [class*="st-key-v4cidx-"] {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
  .v4-term:hover > .v4-tip {{ display: none; }}
  .v4-term:focus > .v4-tip, .v4-term:focus-within > .v4-tip {{ display: block; position: static; width: auto; max-width: none; margin: 6px 0 2px;
    box-shadow: none; background: var(--surface2); }}
  .v4g-sec {{ grid-template-columns: 1fr; padding: 14px 16px; gap: 0; scroll-margin-top: 116px; }}
  .v4g-l {{ font-size: 20px; }}
  .v4g-sec li {{ grid-template-columns: 1fr; gap: 6px; }}
  .v4g-abc {{ flex-wrap: nowrap; overflow-x: auto; margin: 10px -16px 14px; padding: 6px 16px; scrollbar-width: none; top: 56px; }}
  [data-testid="stElementContainer"]:has(> [data-testid="stHtml"] > .v4g-abc) {{ top: 56px; }}
  [class*="st-key-v4set-"] {{ padding: 16px; border-radius: 16px; }}
  .v4s-tbl, .v4s-tbl tbody, .v4s-tbl tr, .v4s-tbl th, .v4s-tbl td {{ display: block; width: auto; }}
  .v4s-tbl tr {{ padding: 10px 0; border-bottom: 1px solid var(--border); }}
  .v4s-tbl th, .v4s-tbl td {{ border: none; padding: 1px 0; }}
}}
</style>"""
