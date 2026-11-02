# -*- coding: utf-8 -*-
"""V4 glossary and settings: every term, grouped by letter, examples only from real numbers."""
import glossary
from dashboard.v4 import glossary_data as G
from dashboard.v4 import glossary_ui as GU

ROW = {"Ticker": "CVX", "Name": "Chevron Corporation", "Sector": "Energy", "Price": 235.52, "TargetMean": 232.5,
       "AnalystCount": 24, "Support": 197.82, "DistSupport%": -16.0, "Resistance": None, "RiskReward": None,
       "MA200": 191.25, "Beta": -0.63, "RevenueGrowth": 39.1, "RSI14": 72.9, "_tier": "full"}
SAMPLE = {"ticker": "CVX", "row": ROW, "name": "Chevron",
          "v": {"label": "שווה לשקול קנייה", "quality": 90, "reliability": {"score": 85}}}


def test_every_term_is_listed_once_in_letter_order():
    g = G.build("", SAMPLE)
    assert g["count"] == g["total"] == len(glossary.TERMS)
    order = [x["letter"] for x in g["sections"]]
    assert order[-1] == G.LATIN and order[:-1] == sorted(order[:-1])
    assert sum(len(x["items"]) for x in g["sections"]) == g["total"]


def test_search_matches_term_alias_and_definition():
    assert [e["term"] for x in G.build("PEG", SAMPLE)["sections"] for e in x["items"]] == ["PEG"]
    assert any(e["term"] == "ציון אות פנימי" for x in G.build("ביטחון", SAMPLE)["sections"] for e in x["items"])
    assert G.build("zzzz", SAMPLE)["count"] == 0


def test_examples_state_the_real_numbers_and_never_invent():
    assert G.example("מחיר יעד", SAMPLE) == ("ל-Chevron יעד ממוצע של $232.50 לפי 24 אנליסטים, והמחיר $235.52. "
                                             "כלומר המחיר כבר מעל היעד.")
    assert "אין פוטנציאל עלייה" in G.example("פוטנציאל עלייה", SAMPLE)
    assert "מעל כל הרמות" in G.example("התנגדות", SAMPLE)
    assert "הפוך לשוק" in G.example("ביתא", SAMPLE)                # a negative beta is not "less volatile"
    assert "רבעון" in G.example("צמיחת הכנסות", SAMPLE)              # quarterly figure, never called annual
    assert G.example("הערכת השקעה", SAMPLE).endswith("שווה לשקול קנייה.")
    assert G.example("שווי שוק", SAMPLE) is None                     # no MarketCap in the row: no example
    assert G.example("CAGR", SAMPLE) is None and G.example("RSI", None) is None


def test_glossary_html_marks_missing_letters_and_shows_detail_only_in_advanced():
    g = G.build("", SAMPLE)
    abc = GU.letters(g["letters"])
    assert 'href="#v4g-0"' in abc and "<span>ג</span>" in abc
    sec = g["sections"][0]
    idx = [c for c, _ in g["letters"]].index(sec["letter"])
    assert "למה זה חשוב" not in GU.section(sec, idx, False)
    assert "למה זה חשוב" in GU.section(sec, idx, True)


def test_new_terms_match_the_live_engine_gates():
    plain = glossary.TERMS["הערכת השקעה"]["plain"]
    assert "68" in plain and "55" in plain and "גבוה מאוד" in plain
    assert "לא כויל" in glossary.TERMS["ציון אות פנימי"]["plain"]


def test_quotes_in_text_render_as_quotes():
    from dashboard.v4 import ui
    out = ui.text("מקובל כ'מצב השוק' ב-2026")
    assert "&#x27;" not in out and "'מצב השוק'" in out and '<span class="v4-num">2026</span>' in out


def test_latin_phrases_and_signs_keep_their_order():
    from dashboard.v4 import ui
    assert '<span class="v4-num">S&amp;P 500</span>' in ui.text("מעל S&P 500 בחודש")
    assert '<span class="v4-num">-8.01%</span>' in ui.text("חוזק יחסי -8.01%)")
    assert '<span class="v4-num">AT&amp;T</span>' in ui.text("AT&T עלתה")


def test_terms_open_a_short_explanation_with_a_glossary_link():
    from dashboard.v4 import ui
    h = ui.term("חוב להון")
    assert 'class="v4-term"' in h and "glossary?q=" in h and "חוב/הון" in h
    assert ui.term("כותרת שאינה מונח") == "כותרת שאינה מונח"


def test_industries_and_countries_in_hebrew_or_hidden():
    from dashboard.v4 import names_he as NH
    assert NH.industry("Drug Manufacturers - General") == "יצרניות תרופות"
    assert NH.industry("Something New") is None and NH.country("United States") == "ארצות הברית"
