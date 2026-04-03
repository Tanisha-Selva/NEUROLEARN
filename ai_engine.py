"""
ai_engine.py — NeuroLearnAI v2
Dynamic AI feedback engine.

Generates personalised, multi-dimensional feedback based on:
  - concept_score   : overall mastery percentage
  - speed           : response speed label
  - retention       : memory retention label
  - weak_concepts   : list of under-performing topics
  - role            : 'School' or 'College' (tunes language complexity)
"""

import os
import random
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

try:
    if GEMINI_API_KEY:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
except Exception as e:
    print(f"[AI] GenAI initialization failed: {e}")
    GEMINI_API_KEY = None


# ── Feedback phrase pools (adds variety across sessions) ─────────────────────

_GREETING_SCHOOL = [
    "Hey {name}! Here's your personalised learning report 🎉",
    "Great effort, {name}! Let's see how you did today 📊",
    "Hello {name}! Your results are ready — let's grow together 🌱",
]

_GREETING_COLLEGE = [
    "Hi {name}! Your performance analysis is ready.",
    "Hello {name}! Here's your detailed academic evaluation.",
    "{name}, your adaptive learning report has been generated.",
]

_MASTERY_HIGH = [
    "🌟 Outstanding! Your concept mastery of {score:.1f}% shows deep understanding.",
    "🏆 Excellent work! {score:.1f}% — you clearly have a strong command of the material.",
    "⭐ Impressive! {score:.1f}% concept mastery. You're operating at an expert level.",
]
_MASTERY_MID = [
    "📘 Good effort! {score:.1f}% — you're on the right path. Focused practice will push you further.",
    "💡 Solid performance at {score:.1f}%. A bit more targeted revision and you'll be excelling.",
    "📈 {score:.1f}% is a respectable score. Consistency is your next milestone.",
]
_MASTERY_LOW_MID = [
    "⚠️ {score:.1f}% — you have a foundation, but key gaps need attention. Let's fix that.",
    "📝 {score:.1f}% shows partial understanding. Break down each weak topic one at a time.",
    "🔄 {score:.1f}% — some concepts haven't clicked yet. More structured revision is needed.",
]
_MASTERY_LOW = [
    "🔴 {score:.1f}% — the fundamentals need more work. Don't worry; a clear plan will get you there.",
    "📉 {score:.1f}% indicates significant gaps. Let's go back to basics and build up step by step.",
    "🌱 {score:.1f}% — every expert starts somewhere. Follow the study plan and you WILL improve.",
]

_SPEED_ADVICE = {
    "Fast": [
        "⚡ Fast response speed! Great agility — just double-check for careless mistakes.",
        "⚡ You answered quickly — superb speed. Review any slip-ups to maintain accuracy.",
    ],
    "Average": [
        "⏱️ Average speed — a healthy, balanced pace. Try timed drills to build further.",
        "⏱️ Steady pace. Gradual speed-building exercises will help you in timed exams.",
    ],
    "Slow": [
        "🐢 Take your time — accuracy first, then speed. Daily timed micro-quizzes will help.",
        "🐢 Slow but steady. Build confidence on each topic and speed will follow naturally.",
    ],
}

_RETENTION_ADVICE = {
    "High": [
        "🧠 Strong retention! Your recent answers show excellent memory consolidation.",
        "🧠 High retention — keep using spaced repetition to lock this in long-term.",
    ],
    "Medium": [
        "📝 Moderate retention. Try active recall: close notes and recall from memory.",
        "📝 Medium retention — Anki flashcards and mind maps will help reinforce concepts.",
    ],
    "Low": [
        "📉 Low retention observed. Try: teach the concept to someone else, use flashcards.",
        "📉 Retention needs work. Spaced repetition (review after 1 day, 3 days, 7 days) is key.",
    ],
}

_CLOSE_HIGH = [
    "🏆 You're doing phenomenally! Challenge yourself with harder problems to stay sharp.",
    "🚀 Top-tier performance! Explore advanced topics and real-world applications.",
]
_CLOSE_MID = [
    "💪 Keep the momentum going! Small daily efforts lead to big breakthroughs.",
    "🌟 You're progressing well — stay consistent and the results will compound.",
]
_CLOSE_LOW = [
    "🌱 Every master was once a beginner. Stick to the plan and you WILL see progress.",
    "💡 Believe in the process. Follow the resources, practice daily, and watch yourself grow.",
]


def generate_feedback(
    student_name: str,
    concept_score: float,
    speed: str,
    retention: str,
    weak_concepts: List[str],
    role: str = "School",
) -> Dict[str, Any]:
    """
    Generate personalised AI feedback for a student.

    Args:
        student_name  : Student's full name.
        concept_score : Overall mastery percentage (0–100).
        speed         : Speed tier — 'Fast', 'Average', or 'Slow'.
        retention     : Retention tier — 'High', 'Medium', or 'Low'.
        weak_concepts : List of concept names where student scored < 50%.
        role          : 'School' or 'College' — adjusts language tone.

    Returns:
        dict: student_name, concept_score, speed, retention,
              weak_concepts, feedback (joined string), feedback_parts (list)
    """
    if GEMINI_API_KEY:
        try:
            import google.generativeai as genai
            model = genai.GenerativeModel("gemini-1.5-flash")
            wc_str = ", ".join(weak_concepts) if weak_concepts else "None"
            prompt = (
                f"Act as an encouraging {role} tutor for {student_name}. "
                f"Their overall score is {concept_score:.1f}%. "
                f"Their response speed is {speed} and memory retention is {retention}. "
                f"Weak concepts: {wc_str}. "
                "Write a short, personalised set of 3 to 4 distinct feedback points. "
                "Separate each distinct point with a pipe character (|). "
                "Keep each point brief, actionable, and include relevant emojis."
            )
            response = model.generate_content(prompt)
            raw_text = response.text.replace("\n", " ").strip()
            # Parse the pipe-separated text
            parts = [p.strip() for p in raw_text.split("|") if p.strip()]
            
            if parts:
                return {
                    "student_name"  : student_name,
                    "concept_score" : round(concept_score, 2),
                    "speed"         : speed,
                    "retention"     : retention,
                    "weak_concepts" : weak_concepts,
                    "feedback_parts": parts,
                    "feedback"      : " | ".join(parts),
                }
        except Exception as e:
            print(f"[AI] Gemini API failed: {e}. Falling back to static engine.")

    # ── Fallback: Static Engine ──
    greetings = _GREETING_SCHOOL if role == "School" else _GREETING_COLLEGE
    parts: List[str] = []

    # Greeting
    parts.append(random.choice(greetings).format(name=student_name))

    # Mastery
    if concept_score >= 85:
        parts.append(random.choice(_MASTERY_HIGH).format(score=concept_score))
    elif concept_score >= 65:
        parts.append(random.choice(_MASTERY_MID).format(score=concept_score))
    elif concept_score >= 40:
        parts.append(random.choice(_MASTERY_LOW_MID).format(score=concept_score))
    else:
        parts.append(random.choice(_MASTERY_LOW).format(score=concept_score))

    # Speed
    speed_pool = _SPEED_ADVICE.get(speed, [f"Your speed is: {speed}."])
    parts.append(random.choice(speed_pool))

    # Retention
    ret_pool = _RETENTION_ADVICE.get(retention, [f"Retention level: {retention}."])
    parts.append(random.choice(ret_pool))

    # Weak concepts
    if weak_concepts:
        wc_str = ", ".join(weak_concepts)
        parts.append(
            f"📌 Priority Focus Areas: {wc_str}. "
            "Curated resources for these are included in your study plan."
        )
    else:
        parts.append("✅ No critical weak spots detected! Keep reinforcing all topics evenly.")

    # Motivational close
    if concept_score >= 85:
        parts.append(random.choice(_CLOSE_HIGH))
    elif concept_score >= 55:
        parts.append(random.choice(_CLOSE_MID))
    else:
        parts.append(random.choice(_CLOSE_LOW))

    return {
        "student_name"  : student_name,
        "concept_score" : round(concept_score, 2),
        "speed"         : speed,
        "retention"     : retention,
        "weak_concepts" : weak_concepts,
        "feedback_parts": parts,
        "feedback"      : " | ".join(parts),
    }

def analyze_exam_llm(raw_text: str, student_name: str, role: str, class_dept: str = "", subject_focus: str = "", file_bytes: bytes = None, mime_type: str = None) -> Dict[str, Any]:
    """
    Directly analyze raw exam text or images/PDFs using Gemini and map to the exact JSON schema requested.
    """
    if not GEMINI_API_KEY:
        return {"error": "Native AI analysis requires a valid GEMINI_API_KEY. Please configure your .env file."}

    try:
        import google.generativeai as genai
        import json
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        system_instruction = f"""
You are NeuroLearnAI, an AI tutor for school and college students. 
Your task is to analyze uploaded exam results and answer sheets, identify weak and strong concepts, and generate personalized, adaptive feedback.

STEPS:
1. Identify the student domain:
   - Student Role: {role}
   - Class/Department: {class_dept}
   - Major/Subject Focus: {subject_focus}
2. Extract all concepts mentioned in the text dynamically. (NO hardcoded fallback mapping, detect accurately based on the domain provided).
3. DISTINGUISH BETWEEN:
   - ANSWER SHEET/RESULT (marked): Calculate performance (0-100%).
   - QUESTION PAPER / STUDY NOTES / SYLLABUS (no marks): Set 'is_question_paper' to true and 'overall_score' to 0. Focus ONLY on extracting concepts and building a preparation plan. Do NOT penalize the student for not having marks on a question paper.
4. Calculate performance per concept (for Answer Sheets). Handle fractions like 30/30 as 100%. Convert any raw marks to percentages. Identify weak concepts (<70%) and strong concepts (>=70%).
5. EXPLANATIONS (CRITICAL): Provide exact reasoning for why each concept is flagged or why specific resources are recommended.
6. Feedback message: Contain an empowering tone with relevant emojis. If it's a question paper/notes, say 'Excellent material for preparation! Identified key topics for your study plan.'

Output EXACTLY as valid JSON. Ensure 'is_question_paper' is a boolean. Ensure 'overall_score' and concept percentages are numeric floats.
Example:
{
  "student_name": "{student_name}",
  "domain": "{role}",
  "is_question_paper": true,
  "text_summary": "This is a History question paper containing sections on modern India...",
  "overall_score": 0,
  "level": "Intermediate",
  "weak_concepts": ["Lord Rippon", "Prime Minister"],
  "strong_concepts": [],
  "resources": ["Read Indian History Part 2"],
  "plan": ["Prepare notes on Modern History topics", "Solve mock questions on these IDs"],
  "concept_explanations": [
    {"concept": "Lord Rippon", "reason_weak": "N/A - Preparation Topic", "resource": "Indian History Part 2", "reason_resource": "Detailed chapter on colonial administration."}
  ],
  "difficulty_flow": ["maintain level"],
  "feedback": "Great study material! I've extracted the core syllabus for your next exam."
}
        """

        prompt_parts = [system_instruction]
        if raw_text:
            prompt_parts.append(f"\n\nExam Text Data:\n{raw_text}")
        
        if file_bytes and mime_type:
            prompt_parts.append({
                "mime_type": mime_type,
                "data": file_bytes
            })

        response = model.generate_content(
            prompt_parts,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json"
            )
        )
        
        data = json.loads(response.text)
        
        # Post-Processing: If score is 0 but concepts exist, it's likely a study guide/notes
        is_qp = data.get("is_question_paper", False)
        concepts_found = len(data.get("weak_concepts", [])) + len(data.get("strong_concepts", []))
        if data.get("overall_score", 0) == 0 and concepts_found > 0:
            is_qp = True

        # Normalize structure for _show_results and frontend expectations
        return {
            "student_name"   : data.get("student_name", student_name),
            "domain"         : data.get("domain", role),
            "is_question_paper": is_qp,
            "text_summary"   : data.get("text_summary", ""),
            "concept_score"  : data.get("overall_score", 0),  # Maps to UI expectations
            "level"          : data.get("level", "Beginner"),
            "retention"      : "Medium",                      # Heuristic default for static upload
            "speed"          : "Average",                     # Heuristic default for static upload
            "weak_concepts"  : data.get("weak_concepts", []),
            "strong_concepts": data.get("strong_concepts", []),
            "resources"      : data.get("resources", []),
            "plan"           : data.get("plan", []),
            "concept_explanations": data.get("concept_explanations", []),
            "difficulty_flow": data.get("difficulty_flow", []),
            "difficulty_summary": {
                "trend": "Upward" if "increase" in str(data.get("difficulty_flow", "")) else "Stable",
                "increase_count": str(data.get("difficulty_flow", [])).count("increase"),
                "decrease_count": str(data.get("difficulty_flow", [])).count("decrease")
            },
            "feedback"       : data.get("feedback", "Excellent material for preparation! Identified key topics for your study plan." if is_qp else "Analysis complete."),
            "next_level"     : data.get("next_level", data.get("level", "Beginner")),
            "error"          : None
        }
            
    except Exception as e:
        return {"error": f"LLM parsing failed: {e}"}

# ── Standalone demo ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    result = generate_feedback(
        student_name="Anika Patel",
        concept_score=72.5,
        speed="Average",
        retention="Medium",
        weak_concepts=["Pointers", "Recursion"],
        role="College",
    )
    print("=== AI Feedback ===")
    for i, part in enumerate(result["feedback_parts"], 1):
        print(f"  {i}. {part}")