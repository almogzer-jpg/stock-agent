"""WCAG AA contrast for V4 text colours on the surfaces they sit on, in both themes."""
from dashboard.v4 import tokens as T


def _lum(hex_):
    r, g, b = (int(hex_[i:i + 2], 16) / 255 for i in (1, 3, 5))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def ratio(a, b):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def test_text_tokens_pass_aa_on_page_and_cards():
    bad = []
    for name, p in (("light", T.LIGHT), ("dark", T.DARK)):
        for fg in ("text", "text2", "text3", "accent", "positive", "warning", "negative"):
            for bg in ("bg", "surface"):
                if ratio(p[fg], p[bg]) < 4.5:
                    bad.append(f"{name} {fg} on {bg}: {ratio(p[fg], p[bg]):.2f}")
    assert not bad, bad
