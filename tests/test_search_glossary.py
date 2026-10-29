# -*- coding: utf-8 -*-
"""Finding stocks the way people type them + the plain-Hebrew glossary."""
import company_search as cs
import glossary


def test_search_by_hebrew_english_and_ticker():
    assert cs.resolve("אפל") == "AAPL"
    assert cs.resolve("aapl") == "AAPL"
    assert cs.resolve("Microsoft") == "MSFT"
    assert cs.resolve("טבע") == "TEVA"                 # Israeli company listed in the US
    assert cs.resolve("צ'ק פוינט") == "CHKP"
    assert cs.resolve("northern") == "NTRS"


def test_unknown_ticker_passes_through_for_live_lookup():
    assert cs.resolve("ZZZQ") == "ZZZQ"
    assert cs.resolve("") is None
    assert cs.search("") == []


def test_glossary_lookup_by_alias_and_coverage():
    assert glossary.lookup("RSI14")["term"] == "RSI"
    assert glossary.lookup("ציון V2")["term"] == "ציון איכות"
    assert glossary.tip("לא קיים") == ""
    groups = glossary.by_group()
    assert all(groups[g] for g in glossary.GROUPS)
    for e in glossary.TERMS.values():
        assert e["short"] and e["plain"] and e["why"] and e["group"] in glossary.GROUPS
        assert ";" not in e["short"] + e["plain"] + e["why"]   # house style: no semicolons
