"""
test_backend.py — NeuroLearnAI v2
Test suite for backend, db, ai_engine, and adaptive modules.
"""
import sys, os
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import traceback
from backend import evaluate_performance, get_question_set, analyze_pdf_content, SUBJECTS
from db import verify_user, register_user, get_all_users, clear_results
from ai_engine import generate_feedback
from adaptive import get_difficulty, get_difficulty_summary


def _banner(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)

def _run(name, fn):
    _banner(f"TEST: {name}")
    try:
        ok = fn()
        print(f"  [PASS] {name}")
        return True
    except Exception as e:
        print(f"  [FAIL] {name} -> {e}")
        traceback.print_exc()
        return False


# ── Auth tests ────────────────────────────────────────────────────────────────
def test_verify_valid():
    user = verify_user("school_user", "school123")
    assert user is not None, "Valid login should return user dict"
    assert user["role"] == "School"
    return True

def test_verify_invalid():
    user = verify_user("school_user", "wrongpass")
    assert user is None, "Invalid password must return None"
    return True

def test_register_new():
    ok, msg = register_user("test_tmp_user", "test123abc", "College", "Test Temp")
    assert ok, f"Registration failed: {msg}"
    user = verify_user("test_tmp_user", "test123abc")
    assert user is not None
    assert user["role"] == "College"
    return True

def test_register_duplicate():
    register_user("dup_user_xyz", "pass123", "School", "Dup")
    ok, msg = register_user("dup_user_xyz", "pass456", "School", "Dup2")
    assert not ok, "Duplicate username must fail"
    return True

def test_register_empty():
    ok, msg = register_user("", "pass123", "School", "No Name")
    assert not ok, "Empty username must fail"
    return True


# ── Question bank tests ───────────────────────────────────────────────────────
def test_get_questions_school():
    qs = get_question_set("School", "Math", "Algebra", n=5)
    assert len(qs) == 5
    assert all("q" in q and "opts" in q and "ans" in q for q in qs)
    print(f"    Sample: {qs[0]['q'][:50]}...")
    return True

def test_get_questions_college():
    qs = get_question_set("College", "Programming", "Arrays", n=4)
    assert len(qs) == 4
    return True

def test_get_questions_all_subjects():
    total = 0
    for role, subjects in SUBJECTS.items():
        for subj, topics in subjects.items():
            for topic in topics:
                qs = get_question_set(role, subj, topic, n=3)
                assert len(qs) >= 1, f"No questions for {role}/{subj}/{topic}"
                total += len(qs)
    print(f"    Total questions sampled across all topics: {total}")
    return True

def test_get_questions_invalid():
    try:
        get_question_set("School", "Math", "NonExistentTopic", n=3)
        return False  # should have raised
    except ValueError:
        return True


# ── Backend evaluation tests ──────────────────────────────────────────────────
def test_evaluate_high_score():
    result = evaluate_performance(
        data={"Arrays": [True,True,True,True], "Loops": [True,True,False,True]},
        student_name="High Scorer",
        student_level="College",
    )
    assert result["concept_score"] >= 70
    assert result["level"] in ("Intermediate","Advanced")
    print(f"    Score: {result['concept_score']}%, Level: {result['level']}")
    return True

def test_evaluate_low_score():
    result = evaluate_performance(
        data={"Math": [False,False,False,True], "Physics": [False,False,True,False]},
        student_name="Struggling Student",
        student_level="School",
    )
    assert result["concept_score"] < 50
    assert result["level"] == "Beginner"
    assert len(result["weak_concepts"]) > 0
    print(f"    Score: {result['concept_score']}%, Weak: {result['weak_concepts']}")
    return True

def test_evaluate_mixed():
    result = evaluate_performance(
        data={
            "Pointers"  : [True, False, True, False, True],
            "Recursion" : [True, True, False, True, True],
        },
        student_name="Mixed Student",
        student_level="College",
    )
    assert 0 <= result["concept_score"] <= 100
    assert result["retention"] in ("High","Medium","Low")
    assert result["difficulty_summary"]["trend"] in ("Upward","Downward","Mixed")
    return True

def test_evaluate_empty_raises():
    try:
        evaluate_performance({}, student_name="Ghost", student_level="College")
        return False
    except ValueError:
        return True

def test_evaluate_wrong_type_raises():
    try:
        evaluate_performance([True,False], student_name="Ghost", student_level="College")
        return False
    except (ValueError, TypeError):
        return True

def test_evaluate_single_concept():
    result = evaluate_performance(
        data={"Calculus": [True, True, False]},
        student_name="Solo",
        student_level="College",
    )
    assert result is not None
    assert result["concept_score"] > 0
    return True


# ── AI engine tests ───────────────────────────────────────────────────────────
def test_ai_feedback_all_tiers():
    for score, role in [(90,"School"),(65,"College"),(45,"School"),(20,"College")]:
        res = generate_feedback("Student", score, "Average", "Medium", [], role)
        assert "feedback" in res and len(res["feedback"]) > 20
        assert isinstance(res["feedback_parts"], list) and len(res["feedback_parts"]) >= 5
    return True

def test_ai_feedback_weak_concepts():
    res = generate_feedback("Arjun", 50, "Slow", "Low", ["Pointers","Recursion"], "College")
    assert "Pointers" in res["feedback"] or "Focus" in res["feedback"]
    return True


# ── Adaptive tests ────────────────────────────────────────────────────────────
def test_adaptive_all_correct():
    flow = get_difficulty([True]*8)
    assert all(r == "increase level" for r in flow[2:])
    return True

def test_adaptive_all_wrong():
    flow = get_difficulty([False]*6)
    assert all(r == "decrease level" for r in flow)
    return True

def test_adaptive_summary():
    summary = get_difficulty_summary([True,False,True,True,False,True,True,True])
    assert summary["increase_count"] >= summary["decrease_count"]
    assert summary["trend"] == "Upward"
    return True

def test_adaptive_empty_raises():
    try:
        get_difficulty([])
        return False
    except ValueError:
        return True


# ── PDF analysis test ─────────────────────────────────────────────────────────
def test_pdf_analysis_text():
    sample_text = """
    Arrays are fundamental data structures. An array stores elements at contiguous
    memory addresses. Accessing an array element by index takes O(1) time.
    Loops allow iteration over arrays. A for loop iterates over a range.
    Pointers store memory addresses. Dereferencing a pointer gives the value.
    """
    res = analyze_pdf_content(sample_text, "Test Student")
    assert "identified_topics" in res
    assert len(res["identified_topics"]) > 0
    print(f"    Identified: {res['identified_topics'][:3]}")
    return True

def test_pdf_analysis_empty():
    res = analyze_pdf_content("", "Test")
    assert "error" in res
    return True


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("\n" + "#"*60)
    print("  NeuroLearnAI v2 -- Full Test Suite")
    print("#"*60)

    tests = [
        ("Auth: Valid Login",              test_verify_valid),
        ("Auth: Invalid Password",         test_verify_invalid),
        ("Auth: Register New User",        test_register_new),
        ("Auth: Duplicate Username",       test_register_duplicate),
        ("Auth: Empty Username",           test_register_empty),
        ("QB: School Questions",           test_get_questions_school),
        ("QB: College Questions",          test_get_questions_college),
        ("QB: All Topics Have Questions",  test_get_questions_all_subjects),
        ("QB: Invalid Topic Raises",       test_get_questions_invalid),
        ("Eval: High Score College",       test_evaluate_high_score),
        ("Eval: Low Score School",         test_evaluate_low_score),
        ("Eval: Mixed Answers",            test_evaluate_mixed),
        ("Eval: Empty Data Raises",        test_evaluate_empty_raises),
        ("Eval: Wrong Type Raises",        test_evaluate_wrong_type_raises),
        ("Eval: Single Concept",           test_evaluate_single_concept),
        ("AI: Feedback All Score Tiers",   test_ai_feedback_all_tiers),
        ("AI: Feedback Weak Concepts",     test_ai_feedback_weak_concepts),
        ("Adaptive: All Correct",          test_adaptive_all_correct),
        ("Adaptive: All Wrong",            test_adaptive_all_wrong),
        ("Adaptive: Summary Trend",        test_adaptive_summary),
        ("Adaptive: Empty Raises",         test_adaptive_empty_raises),
        ("PDF: Text Analysis",             test_pdf_analysis_text),
        ("PDF: Empty Text Error",          test_pdf_analysis_empty),
    ]

    passed = failed = 0
    for name, fn in tests:
        if _run(name, fn):
            passed += 1
        else:
            failed += 1

    _banner("SUMMARY")
    print(f"  Total  : {len(tests)}")
    print(f"  Passed : {passed} [OK]")
    print(f"  Failed : {failed} [FAIL]")
    if failed == 0:
        print("\n  [ALL CLEAR] NeuroLearnAI v2 backend is fully healthy!")
    else:
        print(f"\n  [WARN] {failed} test(s) failed. Review output above.")
    sys.exit(0 if failed == 0 else 1)

if __name__ == "__main__":
    main()