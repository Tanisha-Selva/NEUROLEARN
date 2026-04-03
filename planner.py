"""
planner.py — NeuroLearnAI v2
Personalized targeted revision plan generator.

Takes concept-level weakness data and generates:
  - Prioritised revision plan (day-by-day)
  - Explained resource recommendations (WHY this resource for THIS concept)
  - Time allocation strategy based on concept severity
  - Actionable micro-goals per concept
"""

import json
import os
from typing import Any, Dict, List, Optional

# ── Load resources ─────────────────────────────────────────────────────────────
_BASE = os.path.dirname(os.path.abspath(__file__))
_RESOURCES_PATH = os.path.join(_BASE, "resources.json")

try:
    with open(_RESOURCES_PATH, "r", encoding="utf-8") as _f:
        _RESOURCES: Dict = json.load(_f)
except Exception:
    _RESOURCES = {}


# ── Priority weights ───────────────────────────────────────────────────────────
_PRIORITY_MAP = {
    "Critical" : {"priority": 1, "label": "URGENT",  "time_pct": 40, "daily_min": 60},
    "Weak"     : {"priority": 2, "label": "HIGH",     "time_pct": 30, "daily_min": 45},
    "Moderate" : {"priority": 3, "label": "MEDIUM",   "time_pct": 20, "daily_min": 30},
    "Strong"   : {"priority": 4, "label": "MAINTAIN", "time_pct": 10, "daily_min": 15},
}

# Day-by-day activity types per severity
_ACTIVITY_PLAN = {
    "Critical": [
        "Watch foundational video lecture from scratch",
        "Read textbook chapter / GeeksforGeeks article — take notes",
        "Solve 10 beginner-level problems; mark every mistake",
        "Review mistakes, re-read unclear sections",
        "Solve 15 mixed-difficulty problems",
        "Take a mini self-test (10 questions) under timed conditions",
        "Review test errors; make flashcards for weak sub-topics",
    ],
    "Weak": [
        "Review notes highlighting gaps; watch concept-clarification video",
        "Solve 10 medium problems — no time limit",
        "Identify subtopics still unclear; deep-dive with examples",
        "Solve 15 medium–hard problems",
        "Write a summary of this concept in your own words",
        "Timed practice (20 questions, exam conditions)",
        "Analyse wrong answers; add to spaced-repetition deck",
    ],
    "Moderate": [
        "Quick revision of core theory (30 min)",
        "Solve 10 medium-hard problems",
        "Attempt 2 past-exam questions on this concept",
        "Review any errors; map to knowledge gaps",
        "Solve 10 application-level / tricky problems",
        "30-min timed mixed test including this concept",
        "Final review of any remaining weak subtopics",
    ],
    "Strong": [
        "20-min revision of key formulas/facts",
        "Solve 5 advanced/competition-level problems",
        "Attempt 1 past-exam question to maintain readiness",
        "Explore one real-world application of this concept",
        "Peer-teach or explain the concept in writing",
        "Optional: explore advanced extension topic",
        "Quick self-test to confirm retention",
    ],
}


# ── Resource lookup ────────────────────────────────────────────────────────────

def _find_resource(concept: str, role: str = "School") -> Optional[str]:
    """Search resources.json for the best matching resource for a concept."""
    level_map = _RESOURCES.get(role, {})
    # Check role-specific subjects first
    for subj_resources in level_map.values():
        if isinstance(subj_resources, dict) and concept in subj_resources:
            return subj_resources[concept]

    # Cross-role fallback
    for bucket in _RESOURCES.values():
        if isinstance(bucket, dict):
            for subj_resources in bucket.values():
                if isinstance(subj_resources, dict) and concept in subj_resources:
                    return subj_resources[concept]

    return None


def _explain_resource(concept: str, resource: Optional[str], classification: str) -> str:
    """
    Generate a natural-language explanation for WHY a specific resource is recommended.

    Args:
        concept        : Concept name.
        resource       : Resource string (URL + description) or None.
        classification : The weakness tier.

    Returns:
        Explanation string.
    """
    reasons = {
        "Critical": (
            f"Since '{concept}' is at a critical level, you need to rebuild understanding "
            f"from fundamentals. "
        ),
        "Weak": (
            f"For '{concept}' at a weak level, structured reading and practice will "
            f"close the specific gaps identified. "
        ),
        "Moderate": (
            f"'{concept}' is nearly there — targeted medium-hard practice will "
            f"solidify your understanding and improve exam reliability. "
        ),
        "Strong": (
            f"'{concept}' is strong — the goal now is maintenance and exposure to "
            f"advanced problems to prevent overconfidence gaps. "
        ),
    }
    base = reasons.get(classification, f"Revision of '{concept}' is recommended. ")

    if resource:
        return base + f"Recommended resource: {resource}"
    else:
        return (
            base
            + f"No pre-mapped resource found for '{concept}'. "
            f"Search on Khan Academy, GeeksforGeeks, or YouTube: '{concept} explained'."
        )


# ── Plan generation ────────────────────────────────────────────────────────────

def generate_targeted_plan(
    concept_analysis: Dict[str, Dict],
    student_name: str = "Student",
    role: str          = "School",
    timeline_days: int = 7,
) -> Dict[str, Any]:
    """
    Generate a complete targeted revision plan from concept-level analysis.

    Args:
        concept_analysis: Dict from analyzer.py — {concept: {score_pct, classification, explanation}}
        student_name    : Student's display name.
        role            : 'School' or 'College'.
        timeline_days   : Number of days for the plan (default 7).

    Returns:
        Dict containing:
          - student_name, role, timeline_days
          - concept_recommendations: [{concept, score_pct, classification, priority,
                                       daily_minutes, resource, resource_explanation,
                                       micro_goals}]
          - daily_schedule: [{day, tasks: [{concept, activity, minutes}]}]
          - summary: Human-readable overview string
          - total_study_minutes_per_day: int
    """
    if not concept_analysis:
        return {"error": "No concept data provided.", "concept_recommendations": []}

    # Sort by priority (Critical first, then Weak, Moderate, Strong)
    def _sort_key(item):
        return _PRIORITY_MAP.get(item[1].get("classification", "Moderate"), {}).get("priority", 3)

    sorted_concepts = sorted(concept_analysis.items(), key=_sort_key)

    # ── Per-concept recommendations ───────────────────────────────────────────
    recommendations: List[Dict] = []
    for concept, data in sorted_concepts:
        cls          = data.get("classification", "Moderate")
        score_pct    = data.get("score_pct", 0)
        priority_info= _PRIORITY_MAP.get(cls, _PRIORITY_MAP["Moderate"])
        resource     = _find_resource(concept, role)
        res_expl     = _explain_resource(concept, resource, cls)

        # Micro goals: 3 concrete actions for this concept
        day_activities = _ACTIVITY_PLAN.get(cls, _ACTIVITY_PLAN["Moderate"])
        micro_goals    = [
            f"Day 1-2: {day_activities[0]}",
            f"Day 3-4: {day_activities[2]}",
            f"Day 5-7: {day_activities[5]}",
        ]

        recommendations.append({
            "concept"              : concept,
            "score_pct"            : score_pct,
            "classification"       : cls,
            "priority_label"       : priority_info["label"],
            "daily_minutes"        : priority_info["daily_min"],
            "resource"             : resource or f"Search '{concept}' on Khan Academy / YouTube / GeeksforGeeks",
            "resource_explanation" : res_expl,
            "weakness_explanation" : data.get("explanation", ""),
            "micro_goals"          : micro_goals,
        })

    # ── Daily schedule ────────────────────────────────────────────────────────
    # Distribute concepts across the timeline
    # Critical/Weak get more days; Moderate/Strong fewer
    daily_schedule: List[Dict] = []
    for day in range(1, timeline_days + 1):
        tasks: List[Dict] = []
        for rec in recommendations:
            cls        = rec["classification"]
            activities = _ACTIVITY_PLAN.get(cls, _ACTIVITY_PLAN["Moderate"])
            # Choose daily activity (cycle through the 7-day plan)
            activity   = activities[(day - 1) % len(activities)]
            minutes    = rec["daily_minutes"] // (
                4 if cls == "Strong" else 2 if cls == "Moderate" else 1
            )
            minutes = max(15, minutes)  # floor at 15 min

            # Skip Strong concepts on days 2,3,5,6 (less frequent)
            if cls == "Strong" and day in (2, 3, 5, 6):
                continue
            # Skip Moderate on days 3, 6
            if cls == "Moderate" and day in (3, 6):
                continue

            tasks.append({
                "concept" : rec["concept"],
                "priority": rec["priority_label"],
                "activity": activity,
                "minutes" : minutes,
            })

        total_min = sum(t["minutes"] for t in tasks)
        daily_schedule.append({
            "day"        : day,
            "tasks"      : tasks,
            "total_minutes": total_min,
        })

    # ── Summary string ────────────────────────────────────────────────────────
    critical_count  = sum(1 for _, d in sorted_concepts if d.get("classification") == "Critical")
    weak_count      = sum(1 for _, d in sorted_concepts if d.get("classification") == "Weak")
    moderate_count  = sum(1 for _, d in sorted_concepts if d.get("classification") == "Moderate")
    strong_count    = sum(1 for _, d in sorted_concepts if d.get("classification") == "Strong")

    summary_parts = [
        f"Hi {student_name}! Your {timeline_days}-day targeted revision plan is ready.",
        f"Analysed {len(concept_analysis)} concept(s):",
        f"  🔴 Critical ({critical_count}) — must rebuild from scratch",
        f"  🟠 Weak ({weak_count}) — targeted gap-filling needed",
        f"  🟡 Moderate ({moderate_count}) — close to competence; practice to solidify",
        f"  🟢 Strong ({strong_count}) — maintain with light revision",
    ]
    if critical_count > 0:
        critical_names = [c for c, d in sorted_concepts if d.get("classification") == "Critical"]
        summary_parts.append(f"  ⚡ URGENT: Focus first on → {', '.join(critical_names)}")

    summary_parts.append(
        "Each day's schedule is optimised to spend more time on critical/weak concepts "
        "and less on strong ones — maximising revision efficiency."
    )

    avg_daily = round(sum(d["total_minutes"] for d in daily_schedule) / max(len(daily_schedule), 1))

    return {
        "student_name"             : student_name,
        "role"                     : role,
        "timeline_days"            : timeline_days,
        "concept_count"            : len(concept_analysis),
        "concept_recommendations"  : recommendations,
        "daily_schedule"           : daily_schedule,
        "summary"                  : "\n".join(summary_parts),
        "avg_daily_minutes"        : avg_daily,
    }


# ── Standalone demo ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    sample_analysis = {
        "Algebra"   : {"score_pct": 35, "classification": "Critical", "explanation": "Below 40%"},
        "Geometry"  : {"score_pct": 48, "classification": "Weak",     "explanation": "Below 55%"},
        "Arithmetic": {"score_pct": 75, "classification": "Strong",   "explanation": "Above 70%"},
        "History"   : {"score_pct": 62, "classification": "Moderate", "explanation": "55–70% range"},
    }

    plan = generate_targeted_plan(sample_analysis, "Riya Sharma", "School", 7)
    print("=== Revision Plan Summary ===")
    print(plan["summary"])
    print(f"\nAvg daily study: {plan['avg_daily_minutes']} minutes")
    print("\n=== Day 1 Schedule ===")
    for t in plan["daily_schedule"][0]["tasks"]:
        print(f"  [{t['priority']:8s}] {t['concept']:15s} — {t['activity'][:60]} ({t['minutes']} min)")
    print("\n=== Recommendations ===")
    for rec in plan["concept_recommendations"]:
        print(f"\n  [{rec['classification']:8s}] {rec['concept']}")
        print(f"    Resource: {str(rec['resource'])[:80]}")
        print(f"    Why: {rec['resource_explanation'][:100]}...")
