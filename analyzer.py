"""
analyzer.py — NeuroLearnAI v2
Exam result analyser.

Accepts:
  - CSV files  (structured: concept, score columns)
  - PDF files  (unstructured: text extraction + keyword scoring)
  - Image files (unstructured: OCR via pytesseract if installed)

Outputs per-concept weakness classification with explanations.
"""

import io
import os
import re
import json
from typing import Any, Dict, List, Optional, Tuple


# ── Classification thresholds ────────────────────────────────────────────────
THRESHOLDS = {
    "Critical" : (0,   40),   # < 40%
    "Weak"     : (40,  55),   # 40–54%
    "Moderate" : (55,  70),   # 55–69%
    "Strong"   : (70, 101),   # ≥ 70%
}

# ── Expected CSV column aliases (case-insensitive) ────────────────────────────
_COL_CONCEPT = {"concept", "topic", "subject", "chapter", "area", "name"}
_COL_SCORE   = {"score", "percentage", "percent", "pct", "marks_pct", "score_pct", "accuracy"}
_COL_MARKS   = {"marks", "obtained", "marks_obtained", "got", "scored"}
_COL_MAX     = {"max", "max_marks", "total", "out_of", "maximum", "full_marks"}
_COL_CORRECT = {"correct", "right", "correct_answers"}
_COL_ATTEMPT = {"attempted", "total_questions", "questions", "total_q"}


# ── Internal helpers ──────────────────────────────────────────────────────────

def _find_col(headers: List[str], aliases: set) -> Optional[str]:
    """Find first header that matches any alias (case-insensitive)."""
    for h in headers:
        if h.strip().lower() in aliases:
            return h
    return None


def _pct(value: float, max_val: float) -> float:
    """Safe percentage calculation."""
    if max_val <= 0:
        return 0.0
    return round((value / max_val) * 100, 2)


def _classify(score_pct: float) -> str:
    """Map a percentage to a weakness classification label."""
    for label, (lo, hi) in THRESHOLDS.items():
        if lo <= score_pct < hi:
            return label
    return "Strong"


def _explain_weakness(concept: str, score_pct: float, classification: str) -> str:
    """
    Generate a natural-language explanation for a concept's weakness level.

    Args:
        concept        : Concept name.
        score_pct      : Score percentage.
        classification : One of Critical / Weak / Moderate / Strong.

    Returns:
        Explanation string.
    """
    if classification == "Critical":
        return (
            f"'{concept}' scored {score_pct:.1f}% — this is critically low. "
            "Less than 40% correct indicates the foundational understanding is missing. "
            "This concept must be rebuilt from scratch before any advanced practice."
        )
    elif classification == "Weak":
        return (
            f"'{concept}' scored {score_pct:.1f}% — below the passing threshold. "
            "You understand parts of this topic but key subtopics are unclear. "
            "Targeted revision of specific weak sub-topics is needed."
        )
    elif classification == "Moderate":
        return (
            f"'{concept}' scored {score_pct:.1f}% — approaching competence but not yet reliable. "
            "You likely solve easy problems correctly but struggle with medium/hard variants. "
            "Practice with varied difficulty and edge cases is recommended."
        )
    else:
        return (
            f"'{concept}' scored {score_pct:.1f}% — strong performance. "
            "Maintain this knowledge with periodic revision. "
            "Challenge yourself with advanced/competitive problems to stay sharp."
        )


# ── CSV Parser ────────────────────────────────────────────────────────────────

def parse_csv(file_obj) -> Dict[str, Any]:
    """
    Parse a CSV exam result file and return per-concept analysis.

    Accepted CSV formats (auto-detected):
      Format A: concept, score           (direct percentage)
      Format B: concept, marks, max_marks
      Format C: concept, correct, attempted

    Args:
        file_obj: File-like object from st.file_uploader (or open()).

    Returns:
        dict with:
          - concepts: {concept: {score_pct, classification, explanation}}
          - overall_pct: weighted overall score
          - raw_rows: parsed row list (for debugging)
          - error: str or None
    """
    try:
        import pandas as pd
        content = file_obj.read()
        if isinstance(content, bytes):
            content = content.decode("utf-8", errors="ignore")
        df = pd.read_csv(io.StringIO(content))
        df.columns = [c.strip() for c in df.columns]
    except Exception as e:
        return {"error": f"Could not read CSV: {e}", "concepts": {}}

    headers = list(df.columns)
    col_concept = _find_col(headers, _COL_CONCEPT)
    if not col_concept:
        return {"error": "CSV must have a 'concept' (or 'topic'/'subject') column.", "concepts": {}}

    col_score   = _find_col(headers, _COL_SCORE)
    col_marks   = _find_col(headers, _COL_MARKS)
    col_max     = _find_col(headers, _COL_MAX)
    col_correct = _find_col(headers, _COL_CORRECT)
    col_attempt = _find_col(headers, _COL_ATTEMPT)

    concepts: Dict[str, Dict] = {}
    raw_rows: List[Dict]      = []

    for _, row in df.iterrows():
        name = str(row[col_concept]).strip()
        if not name or name.lower() in ("nan", ""):
            continue

        score_pct: Optional[float] = None

        if col_score and not pd.isna(row.get(col_score)):
            val = float(row[col_score])
            score_pct = val if val <= 1 else val  # assume 0-100 range

        elif col_marks and col_max:
            try:
                marks = float(row[col_marks])
                max_m = float(row[col_max])
                score_pct = _pct(marks, max_m)
            except (ValueError, TypeError):
                pass

        elif col_correct and col_attempt:
            try:
                correct = float(row[col_correct])
                total   = float(row[col_attempt])
                score_pct = _pct(correct, total)
            except (ValueError, TypeError):
                pass

        if score_pct is None:
            continue

        score_pct = round(float(score_pct), 2)
        cls  = _classify(score_pct)
        expl = _explain_weakness(name, score_pct, cls)

        concepts[name] = {
            "score_pct"     : score_pct,
            "classification": cls,
            "explanation"   : expl,
        }
        raw_rows.append({"concept": name, "score_pct": score_pct})

    if not concepts:
        return {"error": "No valid concept rows could be parsed. Check column names.", "concepts": {}}

    overall = round(sum(c["score_pct"] for c in concepts.values()) / len(concepts), 2)
    return {"concepts": concepts, "overall_pct": overall, "raw_rows": raw_rows, "error": None}


# ── PDF Parser ────────────────────────────────────────────────────────────────

# Patterns like: "Algebra: 60%", "Algebra - 12/20", "Algebra 7 out of 10", "Algebra (68%)"
_PDF_PATTERNS = [
    re.compile(r"([A-Za-z &/]+?)\s*[:\-–]\s*(\d+(?:\.\d+)?)\s*%",           re.I),
    re.compile(r"([A-Za-z &/]+?)\s*[:\-–]\s*(\d+)\s*/\s*(\d+)",             re.I),
    re.compile(r"([A-Za-z &/]+?)\s+(\d+(?:\.\d+)?)\s+out\s+of\s+(\d+)",     re.I),
    re.compile(r"([A-Za-z &/]+?)\s*\((\d+(?:\.\d+)?)%?\)",                  re.I),
    re.compile(r"([A-Za-z &/]+?)\s*scored?\s*(\d+(?:\.\d+)?)\s*/\s*(\d+)",  re.I),
]

_TRIVIAL_WORDS = {"the","a","an","and","or","of","in","on","at","to","for",
                  "test","exam","class","student","name","date","subject","total",
                  "marks","score","result","grade","sheet","answer"}


def parse_pdf(file_obj) -> Dict[str, Any]:
    """
    Parse an exam result PDF and extract concept-level scores via pattern matching.

    Args:
        file_obj: File-like object from st.file_uploader.

    Returns:
        Same structure as parse_csv().
    """
    try:
        import PyPDF2
        reader   = PyPDF2.PdfReader(file_obj)
        text     = "\n".join(p.extract_text() or "" for p in reader.pages)
    except Exception as e:
        return {"error": f"PDF read failed: {e}", "concepts": {}}

    if not text.strip():
        return {"error": "No readable text found in PDF. Try uploading a text-layer PDF.", "concepts": {}}

    concepts: Dict[str, Dict] = {}

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        for pattern in _PDF_PATTERNS:
            m = pattern.search(line)
            if not m:
                continue
            groups = m.groups()
            raw_name = groups[0].strip().title()

            # Filter trivial words
            if raw_name.lower() in _TRIVIAL_WORDS or len(raw_name) < 3:
                continue

            if len(groups) == 2:
                score_pct = float(groups[1])
                if score_pct > 100:
                    continue
            elif len(groups) == 3:
                try:
                    score_pct = _pct(float(groups[1]), float(groups[2]))
                except ZeroDivisionError:
                    continue
            else:
                continue

            cls  = _classify(score_pct)
            expl = _explain_weakness(raw_name, score_pct, cls)
            concepts[raw_name] = {
                "score_pct"     : round(score_pct, 2),
                "classification": cls,
                "explanation"   : expl,
            }
            break  # first matching pattern per line

    if not concepts:
        return {
            "error": (
                "No concept scores found in PDF. "
                "Ensure lines follow patterns like: 'Algebra: 72%', 'Geometry - 14/20', etc."
            ),
            "concepts": {},
        }

    overall = round(sum(c["score_pct"] for c in concepts.values()) / len(concepts), 2)
    return {"concepts": concepts, "overall_pct": overall, "raw_rows": [], "error": None}


# ── Image Parser ──────────────────────────────────────────────────────────────

def parse_image(file_obj) -> Dict[str, Any]:
    """
    OCR an image exam sheet and extract concept scores.

    Requires: pytesseract + Tesseract-OCR binary installed on system.
    Falls back gracefully with a helpful error message if unavailable.

    Args:
        file_obj: File-like object from st.file_uploader.

    Returns:
        Same structure as parse_csv().
    """
    try:
        import pytesseract
        from PIL import Image
        img  = Image.open(file_obj)
        text = pytesseract.image_to_string(img)
    except ImportError:
        return {
            "error": (
                "Image OCR requires 'pytesseract' and 'Pillow' libraries, plus "
                "Tesseract-OCR installed on your system.\n"
                "Install: pip install pytesseract Pillow\n"
                "Then: https://github.com/tesseract-ocr/tesseract\n\n"
                "Alternatively, convert your image to PDF and upload that."
            ),
            "concepts": {},
        }
    except Exception as e:
        return {"error": f"Image processing failed: {e}", "concepts": {}}

    if not text.strip():
        return {"error": "OCR found no text. Ensure the image is clear and high-resolution.", "concepts": {}}

    # Reuse PDF pattern matching on OCR text
    import io
    mock_pdf_file = io.StringIO(text)
    concepts: Dict[str, Dict] = {}

    for line in text.splitlines():
        line = line.strip()
        for pattern in _PDF_PATTERNS:
            m = pattern.search(line)
            if not m:
                continue
            groups = m.groups()
            raw_name = groups[0].strip().title()
            if raw_name.lower() in _TRIVIAL_WORDS or len(raw_name) < 3:
                continue
            try:
                if len(groups) == 2:
                    score_pct = float(groups[1])
                else:
                    score_pct = _pct(float(groups[1]), float(groups[2]))
            except:
                continue
            cls  = _classify(score_pct)
            expl = _explain_weakness(raw_name, score_pct, cls)
            concepts[raw_name] = {"score_pct": round(score_pct, 2), "classification": cls, "explanation": expl}
            break

    if not concepts:
        return {"error": "OCR succeeded but no concept scores found. Check image quality.", "concepts": {}}

    overall = round(sum(c["score_pct"] for c in concepts.values()) / len(concepts), 2)
    return {"concepts": concepts, "overall_pct": overall, "raw_rows": [], "error": None}


# ── Unified entry point ───────────────────────────────────────────────────────

def analyze_upload(file_obj, file_name: str, student_name: str = "Student", role: str = "School", class_dept: str = "", subject_focus: str = "") -> Dict[str, Any]:
    """
    Auto-detect file type, extract raw text, and dispatch to LLM (if configured) or fallback to local python heuristic parser.
    """
    ext = os.path.splitext(file_name.lower())[1]
    raw_text = ""

    import io
    # Extract raw text depending on file type for the LLM
    file_bytes = file_obj.read()
    file_obj.seek(0)
    
    mime_type = None
    if ext == ".pdf": mime_type = "application/pdf"
    elif ext in (".png", ".jpg", ".jpeg"): mime_type = "image/jpeg" # simplified
    elif ext == ".csv": mime_type = "text/csv"

    if ext == ".csv":
        try:
            import pandas as pd
            content = file_bytes.decode("utf-8", errors="ignore")
            df = pd.read_csv(io.StringIO(content))
            raw_text = df.to_csv(index=False)
        except Exception:
            raw_text = ""
    elif ext == ".pdf":
        try:
            import PyPDF2
            reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
            raw_text = "\n".join(p.extract_text() or "" for p in reader.pages)
        except Exception:
            raw_text = ""
    elif ext in (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"):
        try:
            # Only try local OCR if Gemni isn't configured later
            raw_text = "" 
        except Exception:
            raw_text = ""
    else:
        return {"error": f"Unsupported file type '{ext}'. Upload CSV, PDF, or image.", "concepts": {}}

    # Try passing the raw text or the file to the GEMINI engine directly
    from ai_engine import analyze_exam_llm, GEMINI_API_KEY
    if GEMINI_API_KEY:
        print("[ANALYZER] Routing to Gemini LLM Vision for multimodal analysis.")
        # Pass bytes for ANY image/pdf to ensure the LLM sees the original source for quality
        payload_bytes = file_bytes if mime_type in ("application/pdf", "image/jpeg") else None
        
        llm_result = analyze_exam_llm(
            raw_text, student_name, role, class_dept, subject_focus, 
            file_bytes=payload_bytes, mime_type=mime_type
        )
        if not llm_result.get("error"):
            llm_result["file_name"] = file_name
            llm_result["is_llm"] = True
            return llm_result
        else:
            print(f"[ANALYZER] Gemini LLM failed fallback to local ({llm_result.get('error')})")

    # ── Fallback local heuristics ──
    print("[ANALYZER] Using fallback python heuristic parser.")
    if ext == ".csv":
        result = parse_csv(file_obj)
    elif ext == ".pdf":
        result = parse_pdf(file_obj)
    elif ext in (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"):
        result = parse_image(file_obj)
    
    result["file_name"] = file_name
    result["is_llm"] = False
    return result


# ── Standalone demo ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Simulate a CSV file
    csv_content = (
        "concept,marks,max_marks\n"
        "Algebra,12,20\n"
        "Geometry,6,16\n"
        "Arithmetic,18,24\n"
        "Physics,8,20\n"
        "History,15,20\n"
    )
    result = parse_csv(io.StringIO(csv_content))
    print("=== CSV Analysis ===")
    print(f"Overall: {result.get('overall_pct')}%")
    for concept, data in result["concepts"].items():
        print(f"  {concept:15s} {data['score_pct']:5.1f}%  [{data['classification']:8s}]")
        print(f"    -> {data['explanation'][:80]}...")
