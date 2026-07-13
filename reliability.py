# -*- coding: utf-8 -*-
"""Reliability layer (Step 0) — provenance, freshness, and a reliability score.

Reliability ≠ Confidence: confidence (trust.py) measures signal agreement and
historical validation; RELIABILITY measures whether the underlying DATA is
trustworthy enough to support any conclusion at all — source, freshness,
completeness, cross-source agreement.

Pure functions over file metadata + pipeline stats; run.py persists the report
to data/reliability.json; the dashboard reads it for provenance lines.
"""
import json
import os
from datetime import datetime

import config

PRIMARY_SOURCE = "Yahoo Finance (yfinance)"
STALE_AFTER_DAYS = 3          # business rule: artifacts older than this are stale

ARTIFACTS = {
    "results": config.RESULTS_CSV,
    "market_overview": config.MARKET_JSON,
    "universe": config.UNIVERSE_JSON,
    "global_markets": config.GLOBAL_JSON,
    "alerts": config.ALERTS_CENTER_JSON,
    "events": config.EVENTS_JSON,
    "backtest": getattr(config, "BACKTEST_JSON", os.path.join(config.DATA_DIR, "backtest.json")),
}


def artifact_status(path, now=None, stale_days=STALE_AFTER_DAYS) -> dict:
    """Freshness of one artifact from file mtime. Never raises."""
    try:
        if not os.path.exists(path):
            return {"exists": False, "age_days": None, "status": "missing"}
        now = now or datetime.now()
        age = (now - datetime.fromtimestamp(os.path.getmtime(path))).total_seconds() / 86400
        return {"exists": True, "age_days": round(age, 2),
                "status": "fresh" if age <= stale_days else "stale"}
    except Exception:
        return {"exists": False, "age_days": None, "status": "unknown"}


def reliability_score(freshness_ok, completeness, cross_status, coverage_ok=True, cross_partial=False) -> dict:
    """Deterministic 0-100 reliability score + Hebrew label.

    Factors (documented weights): freshness 35 · completeness 30 ·
    cross-source agreement 25 · coverage 10. A single primary source caps the
    score at 85 — "גבוהה" requires an agreeing second source ("never show High
    Reliability if only one weak source exists").
    """
    comp = completeness if isinstance(completeness, (int, float)) else 0
    score = (35 if freshness_ok else 10) + 30 * max(0, min(100, comp)) / 100
    score += {"ok": 25, "disagreement": 0, "not_completed": 10}.get(cross_status, 10)
    score += 10 if coverage_ok else 4
    # RULE: "גבוהה" is impossible without an agreeing independent second source —
    # a single primary source caps at 74 (בינונית), agreement unlocks the full scale.
    # Partial cross-check coverage (some series had no secondary) caps at 92.
    cap = 74 if cross_status != "ok" else (92 if cross_partial else 100)
    score = round(min(score, cap))
    label = ("גבוהה" if score >= 75 else "בינונית" if score >= 50 else "נמוכה")
    if cross_status == "disagreement":
        label = "נמוכה — מקורות סותרים"
    return {"score": score, "label": label}


def build_report(system_health=None, crosscheck_report=None, now=None) -> dict:
    """Assemble the platform reliability report (pure; caller persists)."""
    sh = system_health or {}
    arts = {name: artifact_status(path, now=now) for name, path in ARTIFACTS.items()}
    fresh_all = all(a["status"] == "fresh" for a in arts.values() if a["exists"])
    missing = [n for n, a in arts.items() if not a["exists"]]
    completeness = sh.get("data_completeness")
    xr = crosscheck_report or {}
    cross_status = xr.get("status", "not_completed")
    cross_partial = bool(xr.get("checks")) and xr.get("compared", 0) < len(xr.get("checks", []))
    rel = reliability_score(fresh_all, completeness, cross_status,
                            coverage_ok=not missing, cross_partial=cross_partial)
    return {
        "generated": (now or datetime.now()).strftime("%d/%m/%Y %H:%M"),
        "primary_source": PRIMARY_SOURCE,
        "stale_after_days": STALE_AFTER_DAYS,
        "artifacts": arts,
        "missing_artifacts": missing,
        "data_completeness": completeness,
        "crosscheck": crosscheck_report or {"status": "not_completed",
                                            "checks": [], "secondary_source": "Stooq (stooq.com)"},
        "reliability": rel,
        "limitations": ["מקור ראשי יחיד (Yahoo) — ציון אמינות מוגבל ל-85 ללא אימות-צולב מוצלח",
                        "חדשות: ניתוח לקסיקון בסיסי", "בקטסט: אות יחיד, מדגמים קטנים"],
    }


APP_VERSION = "2.0"

# Confidence bands (Phase 0.5) — one verbal scale for the whole platform.
CONF_BANDS = [(93, "Institutional", "אמינות מוסדית"), (80, "High", "אמינות גבוהה"),
              (65, "Moderate", "אמינות בינונית"), (40, "Low", "אמינות נמוכה"),
              (0, "Very Low", "אמינות נמוכה מאוד")]


def conf_band(score) -> dict:
    s = score if isinstance(score, (int, float)) else 0
    for th, en, he in CONF_BANDS:
        if s >= th:
            return {"score": round(s), "band": en, "label_he": he}
    return {"score": 0, "band": "Very Low", "label_he": "אמינות נמוכה מאוד"}


def data_confidence(sources_agreeing=1, fresh=True, source_quality=80,
                    cross_ok=None, fallback_used=False, completeness=100,
                    consistent=True) -> dict:
    """Per-datum/domain Data Confidence Score (0-100) — Phase 0.5 factor model.

    Weights: completeness 30 · freshness 20 · source quality 20 ·
    cross-validation 15 · multi-source 10 · consistency 5.
    Fallback use subtracts 10. Single unvalidated source caps at 79 (never
    'High/Institutional' from one unverified source).
    """
    comp = max(0, min(100, completeness if isinstance(completeness, (int, float)) else 0))
    score = 30 * comp / 100
    score += 20 if fresh else 5
    score += 20 * max(0, min(100, source_quality)) / 100
    score += 15 if cross_ok else (7 if cross_ok is None else 0)
    score += 10 if sources_agreeing >= 2 else 4
    score += 5 if consistent else 0
    if fallback_used:
        score -= 10
    if sources_agreeing < 2 and not cross_ok:
        score = min(score, 79)
    return conf_band(max(0, score))


def quality_gate(confidence_score, fresh=True, critical_missing=(), cross_status="not_completed",
                 min_confidence=45) -> dict:
    """Pre-display gate: verify freshness / min confidence / critical fields /
    cross-validation. Fail → the UI must suppress conclusions (show data only)."""
    reasons = []
    if not fresh:
        reasons.append("הנתונים אינם טריים")
    if isinstance(confidence_score, (int, float)) and confidence_score < min_confidence:
        reasons.append(f"אמינות נתונים נמוכה ({round(confidence_score)}/100)")
    for f in critical_missing:
        reasons.append(f"שדה קריטי חסר: {f}")
    if cross_status == "disagreement":
        reasons.append("מקורות נתונים סותרים")
    return {"pass": not reasons, "reasons": reasons}


DECISION_AUDIT_PATH = os.path.join(config.DATA_DIR, "decision_audit.jsonl")
REC_HISTORY_PATH = os.path.join(config.DATA_DIR, "rec_history.json")


def record_decision_audit(record: dict) -> bool:
    """Append an immutable audit line (reproducibility). Never raises."""
    try:
        record = dict(record, version=APP_VERSION,
                      ts=datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
        with open(DECISION_AUDIT_PATH, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        return True
    except Exception:
        return False


def record_recommendation(ticker, recommendation, confidence, score_v2, target, risk) -> bool:
    """Per-ticker recommendation history (one entry per day). Never raises."""
    try:
        hist = {}
        if os.path.exists(REC_HISTORY_PATH):
            with open(REC_HISTORY_PATH, encoding="utf-8") as fh:
                hist = json.load(fh)
        day = datetime.now().strftime("%d/%m/%Y")
        entries = [e for e in hist.get(ticker, []) if e.get("date") != day][-29:]
        entries.append({"date": day, "recommendation": recommendation,
                        "confidence": confidence, "score_v2": score_v2,
                        "target": target, "risk": risk})
        hist[ticker] = entries
        with open(REC_HISTORY_PATH, "w", encoding="utf-8") as fh:
            json.dump(hist, fh, ensure_ascii=False, indent=1)
        return True
    except Exception:
        return False


def recommendation_history(ticker) -> list:
    try:
        with open(REC_HISTORY_PATH, encoding="utf-8") as fh:
            return json.load(fh).get(ticker, [])
    except Exception:
        return []


def save_report(report: dict) -> bool:
    """Persist to data/reliability.json. Never raises."""
    try:
        with open(config.RELIABILITY_JSON, "w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False
