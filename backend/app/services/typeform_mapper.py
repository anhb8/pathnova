from typing import Any, Dict, List, Optional

# Map Typeform question refs -> DB column names
REF_TO_COLUMN = {
    "name": "name",
    "email": "email",
    "career_level": "career_level",
    "career_goal": "career_goal",
    "industry": "industry",
    "tech_stack" : "tech_stack",
    "target_role": "target_role",
    "skills": "skills",
    "career_challenges": "career_challenges",
    "coaching_style": "coaching_style",
    "target_timeline": "target_timeline",
    "study_time": "study_time",
    "pressure_response": "pressure_response"
}

def _get_text(a: Dict[str, Any]) -> Optional[str]:
    return a.get("text") or a.get("string") or a.get("email")

def _get_choice(a: Dict[str, Any]) -> Optional[str]:
    return (a.get("choice") or {}).get("label")

def _get_choices(a: Dict[str, Any]) -> List[str]:
    return (a.get("choices") or {}).get("labels", [])

def _get_number(a: Dict[str, Any]) -> Optional[int]:
    return a.get("number")

def extract_response_fields(answers: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Convert Typeform answers[] into a dict of columns for TypeformResponse.
    Handles text, single choice, multiple choices, and number types.
    """
    out: Dict[str, Any] = {
        "name": None,
        "career_level": None,
        "career_goal": None,
        "industry": None,
        "tech_stack": None,
        "target_role": None,
        "skills": None,               
        "career_challenges": None,   
        "coaching_style": None,
        "target_timeline": None,
        "study_time": None,
        "pressure_response": None,
    }

    for a in answers:
        ref = (a.get("field") or {}).get("ref")
        if not ref:
            continue

        col = REF_TO_COLUMN.get(ref)
        if not col:
            continue

        a_type = a.get("type")
        val = None

        if a_type in ("text", "email"):                 
            val = _get_text(a)
        elif a_type in ("choice",):
            val = _get_choice(a)
        elif a_type in ("choices",):                   
            val = _get_choices(a)
        elif a_type in ("number",):
            val = _get_number(a)

        # Multi-selection
        if col in ("skills", "career_challenges"):
            if isinstance(val, list):
                out[col] = val
            elif isinstance(val, str) and val.strip():
                out[col] = [s.strip() for s in val.split(",")]
            else:
                out[col] = None
        else:
            out[col] = val

    return out