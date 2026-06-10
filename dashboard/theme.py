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
  /* Dataframe tweaks */
  div[data-testid="stDataFrame"] {{ background:{CARD}; border-radius:10px; }}
  .stTabs [data-baseweb="tab-list"] {{ gap:4px; }}
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
