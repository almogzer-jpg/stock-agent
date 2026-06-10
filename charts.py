# -*- coding: utf-8 -*-
"""Tiny price-trend charts (sparklines) for the email report.

Uses matplotlib's non-interactive 'Agg' backend so it works headless (e.g.
under Task Scheduler). Returns PNG bytes that get embedded inline in the email.
"""
import io

import matplotlib
matplotlib.use("Agg")            # headless backend — no display needed
import matplotlib.pyplot as plt


def sparkline_png(closes, width_in: float = 3.0, height_in: float = 0.8) -> bytes:
    """Render a small price line for `closes` and return PNG bytes.

    The line is green when the period ended higher than it started, red
    otherwise. Axes are hidden for a clean 'sparkline' look.
    """
    closes = [float(c) for c in closes if c == c]   # drop NaNs
    if len(closes) < 2:
        closes = closes or [0, 0]

    color = "#1b7f3b" if closes[-1] >= closes[0] else "#b3333b"

    fig = plt.figure(figsize=(width_in, height_in), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])              # fill the whole canvas
    x = range(len(closes))
    ax.plot(x, closes, color=color, linewidth=1.8)
    ax.fill_between(x, closes, min(closes), color=color, alpha=0.12)
    ax.axis("off")

    buf = io.BytesIO()
    fig.savefig(buf, format="png", transparent=True, bbox_inches="tight", pad_inches=0)
    plt.close(fig)
    return buf.getvalue()
