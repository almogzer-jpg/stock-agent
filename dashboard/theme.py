# -*- coding: utf-8 -*-
"""Dark professional theme: CSS for Streamlit + a Plotly layout helper.

Centralizes all styling so the dashboard looks like a financial-intelligence
platform (dark navy, card layout, RTL) without scattering CSS across the app.
"""

# Status palette (kept consistent with ranking_engine.interpret).
GREEN = "#36d399"
AMBER = "#fbbd23"
RED = "#f87272"
BLUE = "#60a5fa"
BG = "#0e1726"
CARD = "#16213a"
BORDER = "#233456"
TEXT = "#e6eefb"
MUTED = "#9fb3d1"

DARK_CSS = f"""
<style>
  /* Base dark canvas + RTL */
  .stApp {{ background:{BG}; color:{TEXT}; direction:rtl; }}
  section.main > div {{ padding-top: 0.5rem; }}
  h1,h2,h3,h4,p,span,label,div[data-testid="stMarkdownContainer"] {{
      direction:rtl; text-align:right; color:{TEXT};
  }}
  /* Hide default Streamlit chrome for a cleaner app look */
  #MainMenu, footer, header[data-testid="stHeader"] {{ visibility:hidden; }}

  /* Sidebar */
  section[data-testid="stSidebar"] {{ background:{CARD}; border-left:1px solid {BORDER}; }}
  section[data-testid="stSidebar"] * {{ color:{TEXT}; }}

  /* KPI metric cards */
  div[data-testid="stMetric"] {{
      background:{CARD}; border:1px solid {BORDER}; border-radius:12px;
      padding:16px 18px;
  }}
  div[data-testid="stMetricLabel"] p {{ color:{MUTED}; font-size:13px; }}
  div[data-testid="stMetricValue"] {{ color:{TEXT}; font-weight:800; }}

  /* Generic card wrapper (use with st.container or markdown) */
  .card {{
      background:{CARD}; border:1px solid {BORDER}; border-radius:12px;
      padding:16px 18px; margin-bottom:14px;
  }}
  /* Top bar */
  .topbar {{
      background:#0b1220; border:1px solid {BORDER}; border-radius:12px;
      padding:12px 18px; margin-bottom:16px; display:flex;
      justify-content:space-between; align-items:center;
  }}
  .pill {{ background:#10331f; color:{GREEN}; border-radius:20px;
           padding:3px 12px; font-size:13px; }}
  .mk b {{ color:#cfe0f5; }}
  /* Spacing & typography */
  .block-container {{ padding-top:1.2rem; padding-bottom:2rem; max-width:1500px; }}
  h2,h3,h4,h5 {{ margin-top:0.5rem; margin-bottom:0.4rem; font-weight:800; }}
  p {{ margin-bottom:0.4rem; }}

  /* Metric cards — consistent, RTL */
  div[data-testid="stMetric"] {{ text-align:right; }}
  div[data-testid="stMetricValue"] {{ font-size:1.6rem; }}

  /* Cards — consistent rhythm */
  .card {{ box-shadow:0 1px 3px rgba(0,0,0,.25); }}

  /* Tables — RTL, bordered, readable, zebra */
  div[data-testid="stDataFrame"] {{
      background:{CARD}; border:1px solid {BORDER}; border-radius:10px; direction:rtl;
  }}
  div[data-testid="stDataFrame"] * {{ font-size:13px; }}

  /* Tabs / expanders / inputs — RTL */
  .stTabs [data-baseweb="tab-list"] {{ gap:4px; direction:rtl; }}
  details summary {{ direction:rtl; text-align:right; }}
  .stSelectbox label, .stSlider label, .stRadio label {{ text-align:right; }}
  .stPlotlyChart {{ margin-bottom:6px; }}
  .stButton button {{ border-radius:8px; font-weight:600; }}

  /* Mobile responsiveness */
  @media (max-width:640px) {{
    .block-container {{ padding:0.5rem !important; }}
    div[data-testid="stMetricValue"] {{ font-size:1.2rem; }}
    .card {{ padding:12px 14px; }}
    .topbar {{ flex-direction:column; gap:6px; align-items:flex-start; }}
    h2 {{ font-size:1.3rem; }} h3 {{ font-size:1.1rem; }}
    div[data-testid="stDataFrame"] * {{ font-size:11px; }}
  }}
</style>
"""


def style_fig(fig, height: int = 300):
    """Apply the dark theme to a Plotly figure."""
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=CARD,
        plot_bgcolor=CARD,
        font=dict(family="Arial", color=TEXT, size=12),
        margin=dict(l=10, r=10, t=30, b=10),
        height=height,
        legend=dict(orientation="h", y=-0.2),
    )
    return fig
