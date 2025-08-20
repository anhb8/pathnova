from sqlalchemy.orm import Session
from typing import Dict, Any
from ..models import User, TypeformResponse
from typing import Dict, Any, Optional
from uuid import UUID

def build_user_context(
    db: Session,
    *,
    user_id: Optional[UUID] = None,
    email: Optional[str] = None
) -> Dict[str, Any]:
    if (user_id is None) == (email is None):
        # exactly one must be provided
        raise ValueError("Provide exactly one of user_id or email")
    
    # Resolve user
    if user_id is not None:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User not found for user_id={user_id}")
    else:
        norm_email = email.strip().lower()
        user = db.query(User).filter(User.email == norm_email).first()
        if not user:
            raise ValueError(f"User not found for email={norm_email}")

    # Latest TypeformResponse for this user
    resp = (db.query(TypeformResponse)
              .filter(TypeformResponse.user_id == user.id)
              .order_by(TypeformResponse.received_at.desc())
              .first())
    if not resp:
        raise ValueError("No Typeform submission found for this user")

    ctx = {
        "name": user.name,
        "email": user.email,
        "career_level": getattr(resp, "career_level", None),
        "career_goal": getattr(resp, "career_goal", None),
        "industry": getattr(resp, "industry", None),
        "tech_stack": getattr(resp, "tech_stack", None),
        "target_role": getattr(resp, "target_role", None),
        "skills": getattr(resp, "skills", None),
        "career_challenges": getattr(resp, "career_challenges", None),
        "coaching_style": getattr(resp, "coaching_style", None),
        "target_timeline": getattr(resp, "target_timeline", None),
        "study_time": getattr(resp, "study_time", None),
        # "target_companies": getattr(resp, "companies", None) if hasattr(resp, "companies") else None,
        "pressure_response": getattr(resp, "pressure_response", None),
      
    }
    return {"user_id": str(user.id), "context": ctx}

import json, hashlib
def signature_for_context(ctx: Dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(ctx, sort_keys=True, default=str).encode()).hexdigest()