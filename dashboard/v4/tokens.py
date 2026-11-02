# -*- coding: utf-8 -*-
"""V4 design tokens: the one source of truth for colour, type, spacing and radii.

Values are the approved round-2 prototypes (docs/v4/prototypes/R2*.dc.html).
Every V4 style and component reads from here, never from literals, so the two
themes stay in step and a change lands everywhere at once.
"""

LIGHT = {
    "bg": "#F6F5F2", "surface": "#FFFFFF", "surface2": "#F3F1EC", "border": "#E6E3DC",
    "text": "#111827", "text2": "#475467", "text3": "#5F6B7C",
    "accent": "#2547C9", "accentSoft": "#EDF1FD", "onAccent": "#FFFFFF",
    "positive": "#0B7A4B", "warning": "#94580A", "negative": "#B42318", "muted": "#5F6B7C",
    "posSoft": "#E8F4EE", "warnSoft": "#FBF1E2", "negSoft": "#FCEDEB", "mutedSoft": "#F3F1EC",
    "warnLine": "rgba(148,88,10,.16)",
    "segOff": "#E6E3DC",
    "shadowSm": "0 1px 2px rgba(17,24,39,.05)",
    "shadowMd": "0 1px 2px rgba(17,24,39,.04), 0 8px 24px rgba(17,24,39,.06)",
}

DARK = {
    "bg": "#0E1218", "surface": "#151B23", "surface2": "#1B222C", "border": "#273141",
    "text": "#E8ECF2", "text2": "#B4BDCA", "text3": "#8E99AA",
    "accent": "#8FA9FF", "accentSoft": "#1D2847", "onAccent": "#0E1218",
    "positive": "#55C795", "warning": "#E2B14E", "negative": "#F38B81", "muted": "#8E99AA",
    "posSoft": "#14261F", "warnSoft": "#241F17", "negSoft": "#2A1C1D", "mutedSoft": "#1B222C",
    "warnLine": "rgba(226,177,78,.28)",
    "segOff": "#33404F",
    "shadowSm": "none", "shadowMd": "none",
}

FONT = "'Heebo', 'Segoe UI', Arial, sans-serif"
FONT_URL = "https://fonts.googleapis.com/css2?family=Heebo:wght@400;500;600;700;800&display=swap"

# Type scale (px): name -> (size, line height, weight)
TYPE = {
    "display": (32, 40, 700), "hero": (30, 40, 800), "h2": (22, 30, 700), "h3": (18, 26, 700),
    "lead": (17, 28, 400), "body": (16, 26, 400), "small": (15, 23, 400), "meta": (14, 21, 400),
    "caption": (13, 20, 400),
}
SPACE = (4, 8, 12, 16, 20, 24, 28, 32, 48)
RADIUS = {"sm": 8, "md": 10, "lg": 14, "xl": 18, "pill": 999}
SIDEBAR_W = 232
PHONE_MAX = 768          # at or below this width the phone layout applies

TONES = ("positive", "warning", "negative", "muted")


def palette(theme: str) -> dict:
    return DARK if theme == "dark" else LIGHT
