# -*- coding: utf-8 -*-
"""Suspicious market data is flagged, never shown as verified (no network)."""
import globalmkt as G


def test_yield_in_percent_passes_and_scaled_yield_fails():
    assert G.validate("^TNX", "rates", [4.99, 5.04, 4.93], 4.93)[:2] == (False, False)
    bad_price, bad_change, why = G.validate("^TNX", "rates", [0.499, 0.504, 0.493], 0.493)
    assert bad_price and bad_change and "טווח" in why


def test_one_day_spike_in_fx_flags_the_change_not_the_level():
    # USD/ILS as Yahoo printed it around 28/10/2026: 3.0833 → 3.0226 → 3.1226
    bad_price, bad_change, why = G.validate("ILS=X", "fx", [3.0833, 3.0226, 3.1226], 3.1226)
    assert not bad_price and bad_change and "קפיצה" in why


def test_normal_moves_pass_and_vix_has_its_own_limits():
    assert G.validate("ILS=X", "fx", [3.10, 3.11, 3.108], 3.108) == (False, False, "")
    assert G.validate("^VIX", "equity", [16.91, 17.20, 19.42], 19.42) == (False, False, "")
    assert G.validate("^GSPC", "equity", [7700, 7720, 6500], 6500)[1]       # −15.8% in a day


def test_non_positive_price_is_suspect():
    assert G.validate("GC=F", "commodity", [4000, 4010], 0)[0]
