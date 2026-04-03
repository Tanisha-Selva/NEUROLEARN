"""
tracker.py — NeuroLearnAI v2
Progress tracking across multiple test attempts.

Saves per-student session history, computes concept-level trends,
and identifies improving vs declining areas over time.
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

_BASE      = os.path.dirname(os.path.abspath(__file__))
_PROG_FILE = os.path.join(_BASE, "student_progress.json")


# ── I/O helpers ───────────────────────────────────────────────────────────────

def _load() -> Dict[str, List]:
    if not os.path.exists(_PROG_FILE):
        return {}
    try:
        with open(_PROG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, IOError):
        return {}


def _save(data: Dict) -> None:
    try:
        with open(_PROG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except IOError as e:
        print(f"[TRACKER WARNING] Could not save progress: {e}")


# ── Public API ────────────────────────────────────────────────────────────────

def save_attempt(
    student_name  : str,
    test_name     : str,
    concept_scores: Dict[str, float],   # {concept: score_pct}
    overall_score : float,
    role          : str = "School",
    source        : str = "upload",     # 'upload' | 'quiz'
) -> None:
    """
    Persist a test attempt for a student.

    Args:
        student_name  : Student's display name.
        test_name     : Name/label for this test (e.g. 'Math Test 1').
        concept_scores: Per-concept score percentages.
        overall_score : Overall weighted score.
        role          : 'School' or 'College'.
        source        : How this attempt was recorded.
    """
    data = _load()
    key  = student_name.strip().lower()

    attempt = {
        "test_name"     : test_name,
        "timestamp"     : datetime.utcnow().isoformat() + "Z",
        "role"          : role,
        "source"        : source,
        "overall_score" : round(overall_score, 2),
        "concept_scores": {k: round(v, 2) for k, v in concept_scores.items()},
    }

    data.setdefault(key, [])
    data[key].append(attempt)
    _save(data)
    print(f"[TRACKER] Saved attempt '{test_name}' for '{student_name}' (overall: {overall_score:.1f}%)")


def get_attempts(student_name: str) -> List[Dict]:
    """Return all recorded attempts for a student, oldest first."""
    data = _load()
    return data.get(student_name.strip().lower(), [])


def get_concept_trend(student_name: str, concept: str) -> Dict[str, Any]:
    """
    Compute the trend for a single concept across all attempts.

    Returns:
        {
            concept     : str,
            scores      : [float, ...],    # chronological
            trend       : 'Improving' | 'Declining' | 'Stable' | 'Insufficient Data',
            change_pct  : float,           # latest - first
            avg_score   : float,
            explanation : str,
        }
    """
    attempts = get_attempts(student_name)
    scores = [
        a["concept_scores"][concept]
        for a in attempts
        if concept in a.get("concept_scores", {})
    ]

    if len(scores) < 2:
        return {
            "concept"    : concept,
            "scores"     : scores,
            "trend"      : "Insufficient Data",
            "change_pct" : 0,
            "avg_score"  : scores[0] if scores else 0,
            "explanation": (
                f"Only {len(scores)} attempt(s) recorded for '{concept}'. "
                "At least 2 are needed to compute a trend. Keep taking tests!"
            ),
        }

    change = scores[-1] - scores[0]
    avg    = round(sum(scores) / len(scores), 2)

    # Use last-half vs first-half average for robustness
    mid   = len(scores) // 2
    first_half_avg  = sum(scores[:mid]) / max(mid, 1)
    second_half_avg = sum(scores[mid:]) / max(len(scores) - mid, 1)
    delta = second_half_avg - first_half_avg

    if delta >= 5:
        trend = "Improving"
        expl  = (
            f"'{concept}' is improving: your average in recent attempts "
            f"({second_half_avg:.1f}%) is higher than earlier ({first_half_avg:.1f}%). "
            f"Change since first test: +{change:.1f}pp. Keep it up!"
        )
    elif delta <= -5:
        trend = "Declining"
        expl  = (
            f"'{concept}' is declining: your average in recent attempts "
            f"({second_half_avg:.1f}%) is lower than earlier ({first_half_avg:.1f}%). "
            f"Change: {change:.1f}pp. This concept needs immediate attention."
        )
    else:
        trend = "Stable"
        expl  = (
            f"'{concept}' is stable at ~{avg:.1f}%. "
            f"{'Push harder with advanced practice to improve.' if avg < 70 else 'Maintain with periodic revision.'}"
        )

    return {
        "concept"    : concept,
        "scores"     : scores,
        "trend"      : trend,
        "change_pct" : round(change, 2),
        "avg_score"  : avg,
        "explanation": expl,
    }


def progress_summary(student_name: str) -> Dict[str, Any]:
    """
    Full progress report across all attempts and all concepts.

    Returns:
        {
            student_name, total_attempts, overall_trend,
            concept_trends: {concept: get_concept_trend(...)},
            improving: [concepts],
            declining: [concepts],
            stable: [concepts],
            overall_scores: [float, ...],   # chronological
            test_names: [str, ...],
        }
    """
    attempts = get_attempts(student_name)

    if not attempts:
        return {
            "student_name"  : student_name,
            "total_attempts": 0,
            "message"       : "No test attempts recorded yet. Upload exam results to start tracking.",
        }

    # Collect all concept names across all attempts
    all_concepts = set()
    for a in attempts:
        all_concepts.update(a.get("concept_scores", {}).keys())

    concept_trends: Dict[str, Dict] = {}
    improving: List[str] = []
    declining: List[str] = []
    stable   : List[str] = []

    for concept in sorted(all_concepts):
        ct = get_concept_trend(student_name, concept)
        concept_trends[concept] = ct
        if ct["trend"] == "Improving":
            improving.append(concept)
        elif ct["trend"] == "Declining":
            declining.append(concept)
        elif ct["trend"] == "Stable":
            stable.append(concept)

    overall_scores = [a.get("overall_score", 0) for a in attempts]
    test_names     = [a.get("test_name", f"Test {i+1}") for i, a in enumerate(attempts)]

    # Overall trend across sessions
    if len(overall_scores) >= 2:
        delta = overall_scores[-1] - overall_scores[0]
        if delta >= 5:
            overall_trend = "Improving"
        elif delta <= -5:
            overall_trend = "Declining"
        else:
            overall_trend = "Stable"
    else:
        overall_trend = "Insufficient Data"

    return {
        "student_name"  : student_name,
        "total_attempts": len(attempts),
        "overall_trend" : overall_trend,
        "overall_scores": overall_scores,
        "test_names"    : test_names,
        "concept_trends": concept_trends,
        "improving"     : improving,
        "declining"     : declining,
        "stable"        : stable,
        "all_concepts"  : sorted(all_concepts),
    }


def compare_attempts(student_name: str, idx1: int = -2, idx2: int = -1) -> Dict[str, Any]:
    """
    Compare two test attempts and highlight per-concept changes.

    Args:
        student_name : Student name.
        idx1, idx2   : Attempt indices (default: last two).

    Returns:
        Dict with per-concept comparison and delta scores.
    """
    attempts = get_attempts(student_name)
    if len(attempts) < 2:
        return {"error": "Need at least 2 attempts for comparison."}

    try:
        a1 = attempts[idx1]
        a2 = attempts[idx2]
    except IndexError:
        return {"error": "Invalid attempt indices."}

    s1 = a1.get("concept_scores", {})
    s2 = a2.get("concept_scores", {})
    all_concepts = set(s1.keys()) | set(s2.keys())

    comparison: List[Dict] = []
    for concept in sorted(all_concepts):
        v1    = s1.get(concept)
        v2    = s2.get(concept)
        delta = None
        direction = "N/A"

        if v1 is not None and v2 is not None:
            delta     = round(v2 - v1, 2)
            direction = "Improved" if delta >= 2 else ("Declined" if delta <= -2 else "No Change")

        comparison.append({
            "concept"  : concept,
            "test1"    : v1,
            "test2"    : v2,
            "delta"    : delta,
            "direction": direction,
        })

    return {
        "test1_name": a1.get("test_name", "Earlier Test"),
        "test2_name": a2.get("test_name", "Latest Test"),
        "test1_overall": a1.get("overall_score"),
        "test2_overall": a2.get("overall_score"),
        "comparison": comparison,
    }


def clear_progress(student_name: str) -> None:
    """Clear all progress records for a student (for testing)."""
    data = _load()
    key  = student_name.strip().lower()
    if key in data:
        del data[key]
        _save(data)
        print(f"[TRACKER] Cleared progress for '{student_name}'.")


# ── Standalone demo ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    name = "Demo Student"
    clear_progress(name)

    save_attempt(name, "Test 1", {"Algebra": 38, "Geometry": 55, "History": 72}, 55.0)
    save_attempt(name, "Test 2", {"Algebra": 52, "Geometry": 61, "History": 70}, 61.0)
    save_attempt(name, "Test 3", {"Algebra": 64, "Geometry": 58, "History": 74}, 65.3)

    summary = progress_summary(name)
    print("=== Progress Summary ===")
    print(f"Attempts  : {summary['total_attempts']}")
    print(f"Overall   : {summary['overall_scores']}")
    print(f"Trend     : {summary['overall_trend']}")
    print(f"Improving : {summary['improving']}")
    print(f"Declining : {summary['declining']}")

    comp = compare_attempts(name, -2, -1)
    print(f"\n=== Comparison: {comp['test1_name']} vs {comp['test2_name']} ===")
    for c in comp["comparison"]:
        print(f"  {c['concept']:12s}  {c['test1']}% -> {c['test2']}%  ({c['direction']})")
