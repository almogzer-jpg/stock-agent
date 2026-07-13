# -*- coding: utf-8 -*-
"""Reliability layer (Step 0): freshness, scoring, cross-check parsing/compare."""
import os
import time
from datetime import datetime, timedelta

import crosscheck as xc
import reliability as rel


def test_stooq_csv_parse_and_compare():
    csv_ok = "Symbol,Date,Time,Open,High,Low,Close,Volume\n^SPX,2026-07-10,22:00,7500,7560,7490,7543.64,0\n"
    price, date = xc.parse_stooq_csv(csv_ok)
    assert price == 7543.64 and date == "2026-07-10"
    assert xc.parse_stooq_csv("Symbol,Close\n^SPX,N/D\n") == (None, None)
    assert xc.parse_stooq_csv("garbage") == (None, None)

    c = xc.compare(7543.64, 7540.0)
    assert c["agree"] is True and abs(c["diff_pct"]) < 0.1
    assert xc.compare(100.0, 90.0)["agree"] is False        # 11% gap
    assert xc.compare(None, 90.0) is None                   # not comparable → None, not fake


def test_crosscheck_report_statuses():
    rows = {s: {"price": 100.0, "name": s} for s in xc.STOOQ_MAP}
    # offline: fetch returns None → not_completed (never silently "verified")
    orig_s, orig_e = xc.fetch_stooq_close, xc.fetch_ecb_rate
    def _patch(stooq, ecb):
        xc.fetch_stooq_close = lambda s: stooq
        xc.fetch_ecb_rate = lambda s: ecb
    try:
        _patch((None, None), (None, None))          # offline → not_completed, never "verified"
        rep = xc.run_crosscheck(rows)
        assert rep["status"] == "not_completed" and rep["compared"] == 0
        _patch((100.2, "2026-07-10"), (100.3, "2026-07-10"))   # agreeing secondaries → ok
        rep = xc.run_crosscheck(rows)
        assert rep["status"] == "ok" and rep["compared"] >= 2
        _patch((150.0, "2026-07-10"), (150.0, "2026-07-10"))   # material disagreement flagged
        assert xc.run_crosscheck(rows)["status"] == "disagreement"
    finally:
        xc.fetch_stooq_close, xc.fetch_ecb_rate = orig_s, orig_e


def test_artifact_freshness(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("{}")
    st = rel.artifact_status(str(p))
    assert st["exists"] and st["status"] == "fresh"
    old = datetime.now() - timedelta(days=10)
    os.utime(p, (time.mktime(old.timetuple()),) * 2)
    assert rel.artifact_status(str(p))["status"] == "stale"
    assert rel.artifact_status(str(tmp_path / "missing.json"))["status"] == "missing"


def test_reliability_score_rules():
    # single-source cap: without an agreeing second source, never "high" ≥ ... capped at 85
    r = rel.reliability_score(True, 100, "not_completed")
    assert r["score"] <= 74 and r["label"] != "גבוהה"   # single source can NEVER be גבוהה
    # cross-check ok can exceed the cap
    assert rel.reliability_score(True, 100, "ok")["score"] > 74
    # disagreement forces the warning label
    assert "סותרים" in rel.reliability_score(True, 100, "disagreement")["label"]
    # stale data hits hard
    assert rel.reliability_score(False, 100, "ok")["score"] < rel.reliability_score(True, 100, "ok")["score"]


def test_build_report_shape():
    rep = rel.build_report(system_health={"data_completeness": 92},
                           crosscheck_report={"status": "ok", "checks": [], "compared": 4,
                                              "secondary_source": "Stooq"})
    assert rep["primary_source"] and rep["generated"]
    assert "artifacts" in rep and "reliability" in rep
    assert rep["reliability"]["score"] > 0


def test_conf_bands_and_data_confidence():
    assert rel.conf_band(95)["band"] == "Institutional"
    assert rel.conf_band(85)["band"] == "High"
    assert rel.conf_band(70)["band"] == "Moderate"
    assert rel.conf_band(45)["band"] == "Low"
    assert rel.conf_band(20)["band"] == "Very Low"
    # single unvalidated source can never reach High/Institutional
    d = rel.data_confidence(sources_agreeing=1, cross_ok=None, completeness=100)
    assert d["score"] <= 79
    # cross-validated + multi-source unlocks the top bands
    d2 = rel.data_confidence(sources_agreeing=2, cross_ok=True, completeness=100)
    assert d2["score"] > d["score"]
    # fallback usage costs confidence
    assert rel.data_confidence(fallback_used=True)["score"] < rel.data_confidence()["score"]


def test_quality_gate():
    ok = rel.quality_gate(80, fresh=True, critical_missing=(), cross_status="ok")
    assert ok["pass"]
    bad = rel.quality_gate(30, fresh=False, critical_missing=("מחיר",), cross_status="disagreement")
    assert not bad["pass"] and len(bad["reasons"]) >= 3


def test_recommendation_history_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(rel, "REC_HISTORY_PATH", str(tmp_path / "h.json"))
    assert rel.record_recommendation("TST", "Buy", 70, 80, 120.0, "נמוך")
    assert rel.record_recommendation("TST", "Buy", 75, 82, 125.0, "נמוך")  # same day → replaces
    h = rel.recommendation_history("TST")
    assert len(h) == 1 and h[-1]["confidence"] == 75
    assert rel.recommendation_history("NONE") == []


def test_decision_audit_append(tmp_path, monkeypatch):
    monkeypatch.setattr(rel, "DECISION_AUDIT_PATH", str(tmp_path / "a.jsonl"))
    assert rel.record_decision_audit({"ticker": "TST", "recommendation": "Buy"})
    import json
    line = json.loads(open(tmp_path / "a.jsonl", encoding="utf-8").read().splitlines()[0])
    assert line["ticker"] == "TST" and line["version"] and line["ts"]
