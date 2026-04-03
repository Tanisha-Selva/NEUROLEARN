"""
adaptive.py — NeuroLearnAI v2
Adaptive difficulty engine.
Analyses answer sequences and recommends difficulty adjustments per answer.
"""

from typing import List, Dict, Any


def get_difficulty(answers: List[bool]) -> List[str]:
    """
    Determine difficulty adjustment recommendation for each answer.
    Uses a 3-answer sliding window:
      - >= 2/3 correct in window -> 'increase level'
      - < 2/3 correct in window -> 'decrease level'

    For the first two answers (no full window yet), uses single-answer rule.

    Args:
        answers: List of booleans (True = correct, False = incorrect).

    Returns:
        List of strings — one recommendation per answer.

    Raises:
        TypeError : If answers is not a list.
        ValueError: If answers is empty.
    """
    if not isinstance(answers, list):
        raise TypeError(f"Expected list, got {type(answers).__name__}.")
    if not answers:
        raise ValueError("answers list must not be empty.")

    flow: List[str] = []

    for i, answer in enumerate(answers):
        answer = bool(answer)
        if i < 2:
            rec = "increase level" if answer else "decrease level"
        else:
            window = [bool(a) for a in answers[i - 2: i + 1]]
            rec = "increase level" if sum(window) >= 2 else "decrease level"
        flow.append(rec)

    return flow


def get_difficulty_summary(answers: List[bool]) -> Dict[str, Any]:
    """
    Produce an aggregated summary of the difficulty flow analysis.

    Returns:
        dict containing flow, total, increase_count, decrease_count, trend, score_pct
    """
    flow = get_difficulty(answers)
    inc  = flow.count("increase level")
    dec  = flow.count("decrease level")
    total = len(flow)
    correct = sum(bool(a) for a in answers)

    if inc > dec:
        trend = "Upward"
    elif dec > inc:
        trend = "Downward"
    else:
        trend = "Mixed"

    return {
        "flow"          : flow,
        "total"         : total,
        "increase_count": inc,
        "decrease_count": dec,
        "trend"         : trend,
        "correct"       : correct,
        "score_pct"     : round((correct / total) * 100, 1) if total else 0,
    }


def get_next_difficulty(answers: List[bool], current_level: str = "Beginner") -> str:
    """
    Recommend the next overall difficulty level based on the full session.

    Args:
        answers       : Full list of boolean answers.
        current_level : The student's current level.

    Returns:
        One of 'Beginner', 'Intermediate', 'Advanced'.
    """
    levels = ["Beginner", "Intermediate", "Advanced"]
    summary = get_difficulty_summary(answers)

    try:
        idx = levels.index(current_level)
    except ValueError:
        idx = 0

    if summary["trend"] == "Upward" and idx < 2:
        return levels[idx + 1]
    elif summary["trend"] == "Downward" and idx > 0:
        return levels[idx - 1]
    return current_level


def analyze_attempt_trend(attempts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Implements the core hackathon constraint:
    Track last 3 attempts.
    If improving → increase difficulty
    If declining → decrease difficulty
    Else → maintain
    """
    # Grab at most the last 3 attempts, chronologically ordered
    recent = attempts[-3:] if len(attempts) >= 3 else attempts
    
    if len(recent) < 2:
        return {
            "difficulty_flow": "maintain",
            "trend_summary": "Not enough attempts to calculate a strict trend. Keep current level."
        }
        
    scores = [a.get("overall_score", 0) for a in recent]
    
    # Check if strictly improving (each score is >= previous and at least one is >)
    is_improving = all(scores[i] <= scores[i+1] for i in range(len(scores)-1)) and scores[0] < scores[-1]
    
    # Check if strictly declining
    is_declining = all(scores[i] >= scores[i+1] for i in range(len(scores)-1)) and scores[0] > scores[-1]
    
    if is_improving:
        flow = "increase difficulty"
        summary = f"Scores improved across recent attempts ({scores}). Ready for a harder challenge."
    elif is_declining:
        flow = "decrease difficulty"
        summary = f"Scores declined across recent attempts ({scores}). Stepping back to reinforce basics."
    else:
        flow = "maintain"
        summary = f"Scores are fluctuating or stagnant ({scores}). Maintaining current difficulty."
        
    return {
        "difficulty_flow": flow,
        "trend_summary": summary
    }

# ── Standalone demo ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    sample = [True, False, True, True, False, True, True, True, False, True]
    summary = get_difficulty_summary(sample)
    print("=== Adaptive Difficulty ===")
    print(f"Answers : {sample}")
    print(f"Flow    : {summary['flow']}")
    print(f"Trend   : {summary['trend']}")
    print(f"Next    : {get_next_difficulty(sample, 'Beginner')}")