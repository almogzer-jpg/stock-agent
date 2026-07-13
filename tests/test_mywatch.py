# -*- coding: utf-8 -*-
"""Personal watchlist (V3) — snapshot/enrich logic."""
import mywatch as mw


def test_watchlist_roundtrip_and_enrich(tmp_path, monkeypatch):
    monkeypatch.setattr(mw, "WATCHLIST_PATH", str(tmp_path / "w.json"))
    assert mw.add("AAA", price=100.0, score_v2=70, recommendation="Buy", support=95.0)
    assert mw.is_watched("AAA") and not mw.is_watched("BBB")
    uni = {"all": [{"Ticker": "AAA", "Price": 89.0, "ScoreV2": 58.0}]}   # fell below support, score -12
    rows = mw.enrich(uni, [])
    r = rows[0]
    assert r["price_now"] == 89.0 and r["d_price"] == -11.0
    assert r["d_score"] == -12.0
    assert any("תמיכה" in a for a in r["attention"])          # broke saved support
    assert any("ציון" in a for a in r["attention"])            # material score change
    # not-scanned ticker is honest
    mw.add("ZZZ", price=10.0, score_v2=50)
    rows2 = mw.enrich(uni, [])
    z = next(x for x in rows2 if x["ticker"] == "ZZZ")
    assert z["scanned"] is False and z["price_now"] is None
    assert mw.remove("AAA") and not mw.is_watched("AAA")


def test_watchlist_stable_when_no_changes(tmp_path, monkeypatch):
    monkeypatch.setattr(mw, "WATCHLIST_PATH", str(tmp_path / "w.json"))
    mw.add("AAA", price=100.0, score_v2=70, support=90.0)
    uni = {"all": [{"Ticker": "AAA", "Price": 101.0, "ScoreV2": 72.0}]}
    r = mw.enrich(uni, [])[0]
    assert r["attention"] == []                                # +1%, +2 score → calm
