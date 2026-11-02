# -*- coding: utf-8 -*-
"""V4 charts (Plotly), styled from the theme tokens.

Past data is drawn solid. Estimates (the analysts' price target) are drawn
dashed and labelled as estimates, so the two are never confused.
"""
import plotly.graph_objects as go

from dashboard.v4 import tokens as T

RANGES = {"1m": ("חודש", 21), "3m": ("3 חודשים", 63), "6m": ("חצי שנה", 126), "1y": ("שנה", 252), "5y": ("5 שנים", None)}
PHRASE = {"1m": "בחודש האחרון", "3m": "ב-3 החודשים האחרונים", "6m": "בחצי השנה האחרונה", "1y": "בשנה האחרונה",
          "5y": "ב-5 השנים האחרונות"}


def window(hist, key: str):
    """The closes of one range, with the 50 and 200 day averages computed on the full history."""
    c = hist["Close"]
    ma50, ma200 = c.rolling(50).mean(), c.rolling(200).mean()
    n = RANGES.get(key, RANGES["6m"])[1]
    if n:
        c, ma50, ma200 = c.iloc[-n:], ma50.iloc[-n:], ma200.iloc[-n:]
    return c, ma50, ma200


def change(c) -> float | None:
    if c is None or len(c) < 2 or not c.iloc[0]:
        return None
    return round((c.iloc[-1] / c.iloc[0] - 1) * 100, 1)


def price_figure(hist, key: str, theme: str, advanced: bool = False, target: float | None = None,
                 target_low: float | None = None, target_high: float | None = None, support: float | None = None,
                 prefix: str = "$"):
    p = T.palette(theme)
    c, ma50, ma200 = window(hist, key)
    fig = go.Figure()
    fade = "rgba(37,71,201,0.16)" if theme != "dark" else "rgba(143,169,255,0.20)"
    fig.add_trace(go.Scatter(x=c.index, y=c.values, mode="lines", name="מחיר סגירה",
                             line={"color": p["accent"], "width": 2.2, "shape": "spline", "smoothing": 0.3}, fill="tozeroy",
                             fillgradient={"type": "vertical", "colorscale": [[0, "rgba(0,0,0,0)"], [1, fade]]},
                             hovertemplate="%{x|%d/%m/%Y}<br>" + prefix + "%{y:,.2f}<extra></extra>"))
    if len(c):
        fig.add_trace(go.Scatter(x=[c.index[-1]], y=[c.values[-1]], mode="markers", showlegend=False, hoverinfo="skip",
                                 marker={"size": 8, "color": p["accent"], "line": {"color": p["surface"], "width": 2}}))
    if advanced:
        for s, name, dash in ((ma50, "ממוצע 50 יום", "solid"), (ma200, "ממוצע 200 יום", "solid")):
            if s.notna().any():
                fig.add_trace(go.Scatter(x=s.index, y=s.values, mode="lines", name=name,
                                         line={"color": p["text3"] if "200" in name else p["warning"], "width": 1.3, "dash": dash},
                                         hovertemplate=name + ": " + prefix + "%{y:,.2f}<extra></extra>"))
        if support:
            fig.add_hline(y=support, line={"color": p["text3"], "width": 1}, annotation_text=f"תמיכה ${support:,.0f}",
                          annotation_position="bottom left", annotation_font={"color": p["text3"], "size": 11},
                          annotation_bgcolor=p["surface"])
    lo_y = float(min([c.min()] + [x for x in (support if advanced else None, target) if x]))
    hi_y = float(max([c.max()] + [x for x in (target,) if x]))
    if target:
        fig.add_hline(y=target, line={"color": p["text2"], "width": 1.4, "dash": "dash"},
                      annotation_text=f"יעד אנליסטים (הערכה) ${target:,.0f}", annotation_position="top left",
                      annotation_font={"color": p["text2"], "size": 12}, annotation_bgcolor=p["surface"])
    if advanced and target_low and target_high:
        fig.add_hrect(y0=target_low, y1=target_high, fillcolor=p["surface2"], opacity=0.5, line_width=0, layer="below",
                      annotation_text="טווח יעדי האנליסטים", annotation_position="bottom right",
                      annotation_font={"color": p["text3"], "size": 11})
    pad = (hi_y - lo_y) * 0.08 or hi_y * 0.05
    long = key in ("1y", "5y")
    fig.update_layout(
        height=300, margin={"l": 8, "r": 8, "t": 10, "b": 30}, showlegend=advanced,
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.01, "xanchor": "right", "x": 1,
                "font": {"size": 12, "color": p["text2"]}},
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font={"family": T.FONT, "color": p["text2"], "size": 12}, hovermode="x unified",
        hoverlabel={"bgcolor": p["surface"], "bordercolor": p["border"], "font": {"color": p["text"], "family": T.FONT}},
        xaxis={"showgrid": False, "linecolor": p["border"], "tickformat": "%m/%Y" if long else "%d/%m", "fixedrange": True, "automargin": True,
               "tickfont": {"color": p["text3"], "size": 11.5}, "ticks": ""},
        yaxis={"side": "right", "gridcolor": p["border"], "griddash": "dot", "zeroline": False, "tickprefix": prefix, "tickformat": ",.0f",
               "fixedrange": True, "automargin": True, "tickfont": {"color": p["text3"], "size": 11.5},
               "range": [lo_y - pad, hi_y + pad]},
    )
    return fig
