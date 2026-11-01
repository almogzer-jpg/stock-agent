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


# ---- read-time gate (globalmkt.check): nothing old or unverified shows as current ----
from datetime import datetime, timedelta


def _snap(updated, schema=2, tnx=4.93, tnx_as_of=None):
    up = updated.strftime("%d/%m/%Y %H:%M")
    day = (tnx_as_of or updated).strftime("%d/%m/%Y")
    rows = {"rates": [{"symbol": "^TNX", "name": "10Y", "price": tnx, "d1": -1.2, "d7": 0.1, "d30": -3.0,
                       "trend": "יורדת ↓", "interp": "x", "as_of": day, "suspect": False},
                      {"symbol": "2YY=F", "name": "2Y", "price": 3.9, "d1": 0.1, "d7": 0.1, "d30": 0.1,
                       "trend": "—", "interp": "", "as_of": updated.strftime("%d/%m/%Y"), "suspect": False},
                      {"symbol": "CURVE", "name": "curve", "price": round(tnx - 3.9, 2)}],
            "fx": [{"symbol": "ILS=X", "name": "USD/ILS", "price": 3.11, "d1": -0.5, "d7": 0, "d30": 0,
                    "trend": "—", "interp": "", "as_of": updated.strftime("%d/%m/%Y"), "suspect": False}]}
    g = {"updated": up, "groups": rows, "strip": []}
    if schema is not None:
        g["schema"] = schema
    return g


def test_fresh_valid_snapshot_is_shown():
    now = datetime(2026, 11, 2, 9, 0)
    g = G.check(_snap(now - timedelta(hours=3)), now)
    assert g["status"] == "ok" and g["message"] == ""
    by = {r["symbol"]: r for r in g["strip"]}
    assert by["^TNX"]["price"] == 4.93 and by["ILS=X"]["price"] == 3.11
    assert any(r["symbol"] == "CURVE" for r in g["groups"]["rates"])


def test_file_from_before_the_fix_is_hidden_not_shown():
    """The file committed on 01/11/2026: written by the old build (no schema), 10Y at 0.5."""
    now = datetime(2026, 11, 1, 12, 0)
    g = G.check(_snap(datetime(2026, 10, 30, 9, 0), schema=None, tnx=0.5), now)
    assert g["status"] == "unverified" and "לא עברו בדיקת תקינות" in g["message"]
    assert all(r["price"] is None and r["suspect"] for r in g["strip"])
    assert not any(r["symbol"] == "CURVE" for r in g["groups"]["rates"])


def test_stale_snapshot_after_a_restart_is_hidden():
    now = datetime(2026, 11, 10, 9, 0)
    g = G.check(_snap(datetime(2026, 11, 2, 9, 0)), now)
    assert g["status"] == "stale" and "02/11/2026" in g["message"]
    assert all(r["price"] is None for r in g["strip"])


def test_weekend_gap_is_not_stale():
    friday, monday = datetime(2026, 10, 30, 7, 0), datetime(2026, 11, 2, 6, 30)
    assert G.check(_snap(friday), monday)["status"] == "ok"


def test_out_of_range_value_is_hidden_even_in_a_fresh_file():
    now = datetime(2026, 11, 2, 9, 0)
    g = G.check(_snap(now, tnx=0.49), now)
    by = {r["symbol"]: r for r in g["strip"]}
    assert g["status"] == "ok"
    assert by["^TNX"]["price"] is None and by["^TNX"]["suspect"] and "טווח" in by["^TNX"]["suspect_reason"]
    assert by["ILS=X"]["price"] == 3.11                               # one bad row does not hide the rest
    assert not any(r["symbol"] == "CURVE" for r in g["groups"]["rates"])


def test_row_that_stopped_updating_is_hidden():
    now = datetime(2026, 11, 20, 9, 0)
    g = G.check(_snap(now, tnx_as_of=datetime(2026, 11, 5)), now)
    by = {r["symbol"]: r for r in g["strip"]}
    assert by["^TNX"]["price"] is None and "05/11/2026" in by["^TNX"]["suspect_reason"]


def test_missing_file():
    assert G.check({})["status"] == "missing"


def test_the_file_in_the_repository_right_now_never_shows_a_wrong_yield():
    import json, config
    with open(config.GLOBAL_JSON, encoding="utf-8") as fh:
        g = G.check(json.load(fh))
    tnx = next((r for r in g["strip"] if r["symbol"] == "^TNX"), None)
    assert tnx is None or tnx["price"] is None or 1.0 <= tnx["price"] <= 20.0
