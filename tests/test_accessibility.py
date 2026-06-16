# -*- coding: utf-8 -*-
"""Chart accessibility — WCAG contrast guard for the dark theme.

Fails (warns) if any chart text color drops below WCAG AA on the #08111f
background, or if any data line/marker color is below graphical-AA (3:1).
"""
from dashboard.theme import (contrast_ratio, passes_aa, BG, TEXT, SECONDARY, MUTED,
                             LINE_PRICE, LINE_MA20, LINE_MA50, LINE_MA200,
                             LINE_UP, LINE_DOWN, LINE_RSI, LINE_VOLUME)


def test_known_contrast_anchors():
    assert contrast_ratio("#FFFFFF", "#000000") == 21.0
    assert contrast_ratio(BG, BG) == 1.0


def test_text_colors_pass_wcag_aa_on_bg():
    """Primary / secondary / muted text must all meet AA (>=4.5:1) on the bg."""
    for name, c in (("TEXT", TEXT), ("SECONDARY", SECONDARY), ("MUTED", MUTED)):
        cr = contrast_ratio(c, BG)
        assert passes_aa(c, BG), f"{name} {c} fails WCAG AA on {BG}: {cr}:1 (<4.5)"


def test_muted_is_the_darkest_text_allowed():
    """Requirement: no text is ever darker than #94A3B8 (MUTED is the floor)."""
    floor = contrast_ratio(MUTED, BG)
    for c in (TEXT, SECONDARY):
        assert contrast_ratio(c, BG) >= floor


def test_chart_line_colors_visible():
    """Every accessible data color must clear graphical-AA (>=3:1) on the bg."""
    for c in (LINE_PRICE, LINE_MA20, LINE_MA50, LINE_MA200,
              LINE_UP, LINE_DOWN, LINE_RSI, LINE_VOLUME):
        cr = contrast_ratio(c, BG)
        assert passes_aa(c, BG, large=True), f"line color {c} too low: {cr}:1 (<3.0)"
