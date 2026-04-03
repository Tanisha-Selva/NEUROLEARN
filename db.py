"""
db.py — NeuroLearnAI v2
Database layer: user authentication + result persistence.

Authentication:
  - Passwords stored as sha256 hex digests.
  - Users persisted in users.json (auto-created on first import).
  - Default accounts:
      school_user / school123  (role: School)
      college_user / college123 (role: College)

Results:
  - Saved to student_results.json as a JSON array.
  - Query by student name or retrieve all.
"""

import json
import os
import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

_mongo_client = None
_mongo_db = None
_users_col = None
_results_col = None

try:
    if MONGO_URI:
        from pymongo import MongoClient
        _mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        _mongo_client.admin.command('ping')
        _mongo_db = _mongo_client["neurolearnai"]
        _users_col = _mongo_db["users"]
        _results_col = _mongo_db["results"]
        print("[DB] Connected to MongoDB.")
except Exception as e:
    print(f"[DB] MongoDB connection failed: {e}. Falling back to local JSON.")
    _mongo_client = None

# ── File paths ─────────────────────────────────────────────────────────────────
_BASE = os.path.dirname(os.path.abspath(__file__))
USERS_FILE   = os.path.join(_BASE, "users.json")
RESULTS_FILE = os.path.join(_BASE, "student_results.json")

# ── Internal helpers ──────────────────────────────────────────────────────────

def _hash(password: str) -> str:
    """Return sha256 hex digest of the password string."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _load_json(path: str, default: Any) -> Any:
    """Load JSON from path, returning default if file missing or corrupt."""
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return default


def _write_json(path: str, data: Any) -> None:
    """Persist data as JSON to path."""
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except IOError as e:
        print(f"[DB WARNING] Could not write to {path}: {e}")


def _init_users() -> None:
    """Initialize user storage if it doesn't exist."""
    if _users_col is not None:
        return

    if os.path.exists(USERS_FILE):
        return
    _write_json(USERS_FILE, {"users": []})


# Call on module import so the file is always ready
_init_users()


# ── Authentication API ─────────────────────────────────────────────────────────

def verify_user(username: str, password: str) -> Optional[Dict[str, str]]:
    """
    Verify credentials and return the user record on success.

    Args:
        username : Plain-text username.
        password : Plain-text password.

    Returns:
        User dict (username, name, role) if valid, else None.
    """
    pw_hash = _hash(password)

    if _users_col is not None:
        user = _users_col.find_one({"username": username, "password_hash": pw_hash})
        if user:
            return {
                "username": user["username"],
                "name"    : user.get("name", username),
                "role"    : user.get("role", "School"),
                "class_dept": user.get("class_dept", ""),
                "subject_focus": user.get("subject_focus", ""),
            }
        return None

    data = _load_json(USERS_FILE, {"users": []})
    for user in data.get("users", []):
        if user.get("username") == username and user.get("password_hash") == pw_hash:
            return {
                "username": user["username"],
                "name"    : user.get("name", username),
                "role"    : user.get("role", "School"),
                "class_dept": user.get("class_dept", ""),
                "subject_focus": user.get("subject_focus", ""),
            }
    return None


def register_user(
    username: str,
    password: str,
    role: str,
    name: str,
    class_dept: str = "",
    subject_focus: str = "",
) -> Tuple[bool, str]:
    """
    Register a new user with demographic tracking.
    """
    if not username.strip() or not password.strip():
        return False, "Username and password cannot be empty."

    if role not in ("School", "College"):
        return False, f"Invalid role '{role}'. Must be 'School' or 'College'."

    if _users_col is not None:
        # Check uniqueness
        if _users_col.find_one({"username": {"$regex": f"^{username}$", "$options": "i"}}):
            return False, f"Username '{username}' is already taken. Please choose another."
        _users_col.insert_one({
            "username"     : username,
            "password_hash": _hash(password),
            "role"         : role,
            "name"         : name.strip() or username,
            "class_dept"   : class_dept,
            "subject_focus": subject_focus,
        })
        return True, f"Account created successfully! You can now log in as '{username}'."

    data = _load_json(USERS_FILE, {"users": []})
    users: list = data.get("users", [])

    # Check uniqueness
    if any(u["username"].lower() == username.lower() for u in users):
        return False, f"Username '{username}' is already taken. Please choose another."

    users.append({
        "username"     : username,
        "password_hash": _hash(password),
        "role"         : role,
        "name"         : name.strip() or username,
        "class_dept"   : class_dept,
        "subject_focus": subject_focus,
    })
    _write_json(USERS_FILE, {"users": users})
    return True, f"Account created successfully! You can now log in as '{username}'."


def get_all_users() -> List[Dict]:
    """Return all user records (without password hashes) for admin use."""
    if _users_col is not None:
        return [
            {"username": u["username"], "name": u.get("name"), "role": u.get("role")}
            for u in _users_col.find()
        ]

    data = _load_json(USERS_FILE, {"users": []})
    return [
        {"username": u["username"], "name": u.get("name"), "role": u.get("role")}
        for u in data.get("users", [])
    ]


# ── Results API ────────────────────────────────────────────────────────────────

def save_result(result_data: Dict[str, Any]) -> bool:
    """
    Persist a student result record.

    Required keys in result_data:
        student_name, concept_score, feedback

    Returns:
        True on success, False otherwise.
    """
    required = ("student_name", "concept_score", "feedback")
    missing = [k for k in required if k not in result_data]
    if missing:
        raise ValueError(f"save_result() missing keys: {missing}")

    print(f"\n[DB] Saving result for {result_data['student_name']} "
          f"| Score: {result_data['concept_score']}%")

    record = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        **result_data,
    }

    if _results_col is not None:
        _results_col.insert_one(record)
        return True

    records = _load_json(RESULTS_FILE, [])
    if not isinstance(records, list):
        records = []

    records.append(record)
    _write_json(RESULTS_FILE, records)
    return True


def get_all_results() -> List[Dict]:
    """Return all saved result records."""
    if _results_col is not None:
        return list(_results_col.find({}, {"_id": 0}))

    data = _load_json(RESULTS_FILE, [])
    return data if isinstance(data, list) else []


def get_student_history(student_name: str) -> List[Dict]:
    """Return all records for a specific student (case-insensitive)."""
    name_lower = student_name.lower()
    return [
        r for r in get_all_results()
        if r.get("student_name", "").lower() == name_lower
    ]


def clear_results() -> None:
    """Clear all result records (for testing)."""
    _write_json(RESULTS_FILE, [])
    print("[DB] All results cleared.")


# ── Standalone demo ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== DB Module Demo ===")

    # Auth
    user = verify_user("school_user", "school123")
    print(f"Login test   : {user}")

    bad = verify_user("school_user", "wrongpass")
    print(f"Bad password : {bad}")

    ok, msg = register_user("test_user", "test123", "College", "Test User")
    print(f"Register     : {ok} — {msg}")

    # Results
    save_result({
        "student_name" : "Test User",
        "concept_score": 78.5,
        "feedback"     : "Great effort!",
        "level"        : "Intermediate",
    })
    print(f"History count: {len(get_student_history('Test User'))}")