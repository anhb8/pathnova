import os, hmac, hashlib, json
from fastapi import FastAPI, Depends, Request, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from .services.typeform_mapper import extract_response_fields
from .services.plan_inputs import build_user_context, signature_for_context
from .services.generate_plan import generate_learning_plan, OPENAI_MODEL
from .db import get_db
from .init_db import init_db
from .schemas import GeneratePlanRequest, LearningPlanResponse
from .models import Ping, TypeformResponse, User, LearningPlan
from pydantic import BaseModel
from typing import Optional, Tuple, Dict, List, Any

app = FastAPI(title="PathNova API")

TYPEFORM_SECRET = os.getenv("TYPEFORM_SECRET")

# Allow React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    init_db()


@app.get("/")
def root():
    return {"status": "running"}

@app.post("/ping")
def create_ping(db: Session = Depends(get_db)):
    row = Ping(note="db-ok")
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "note": row.note}

@app.get("/ping/{pid}")
def read_ping(pid: int, db: Session = Depends(get_db)):
    row = db.get(Ping, pid)
    return {"exists": bool(row), "row": {"id": row.id, "note": row.note} if row else None}


def verify_typeform_signature(payload: bytes, signature: str) -> bool:
    # if not TYPEFORM_SECRET:
    #     return True  # skip verification if not using a secret
    # if not signature or not signature.startswith("sha256="):
    #     return False
    # expected = hmac.new(TYPEFORM_SECRET.encode(), payload, hashlib.sha256).hexdigest()
    # provided = signature.split("sha256=")[-1]
    # return hmac.compare_digest(expected, provided)
    return True

def normalize_email(email: Optional[str]) -> Optional[str]:
    if not email: 
        return None
    e = email.strip().lower()
    return e or None

def extract_name_email_from_answers(answers: List[Dict[str, Any]]) -> Dict[str, Optional[str]]:
    name = None
    email = None

    name_refs  = {"name"}
    email_refs = {"email"}

    for ans in answers or []:
        ref = (ans.get("field", {}) or {}).get("ref")

        if ref in name_refs:
            if "text" in ans and ans["text"]:
                candidate = ans["text"].strip()
                if candidate:
                    name = candidate

        if ref in email_refs:
            if "email" in ans and ans["email"]:
                candidate = ans["email"].strip()
                if candidate:
                    email = candidate

        # if both found
        if name and email:
            break

    return {"name": name, "email": normalize_email(email)}

def get_or_create_user_by_email( db: Session, *, email: Optional[str], name: Optional[str]) -> Tuple[Optional[User], bool, bool]:
    """
    Upserts a user by email. Creates if not found. Updates name if changed.
    Returns the User or None (if no email passed).
    """
    if not email:
        return None, False, False
    
    email = email.strip().lower()

    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email, name=(name.strip() if name else None))
        db.add(user)
        return user, True, False

    # update name if new info comes in
    updated = False
    incoming = (name or "").strip() or None
    if incoming and user.name != incoming:
        user.name = incoming
        updated = True

    return user, False, updated

@app.post("/webhooks/typeform/")
@app.post("/webhooks/typeform")
async def typeform_webhook(request: Request, db: Session = Depends(get_db)):
    raw = await request.body()
    signature = request.headers.get("Typeform-Signature")

    if not verify_typeform_signature(raw, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = await request.json()
    frm = payload.get("form_response", {}) or {}
    form_id = frm.get("form_id")
    submission_id = payload.get("event_id") or frm.get("token")
    answers = frm.get("answers", []) or []
    hidden = frm.get("hidden", {}) or {}

    # Extract name & email from answers    
    who = extract_name_email_from_answers(answers)
    name = who["name"]
    email = who["email"]

    # build the new columns from answers
    fields = extract_response_fields(answers)

    # Upsert user first 
    user = created = updated = None
    if email:
        user, created, updated = get_or_create_user_by_email(db, email=email, name=name)
        db.flush()
        
    resp = db.query(TypeformResponse).filter(
        TypeformResponse.submission_id == submission_id
    ).first()

    if resp:
        if user and resp.user_id != user.id:
            resp.user_id = user.id
        # Update only columns that actually exist on the model
        for k, v in (fields or {}).items():
            if hasattr(TypeformResponse, k):
                setattr(resp, k, v)
        db.commit()
        return {"ok": True, "updated": True, "submission_id": submission_id}

    # Create a new response row
    create_kwargs = {
        "user_id": (user.id if user else None),
        "form_id": form_id,
        "submission_id": submission_id,
        "answers": answers,
        # unpack additional mapped fields
        **{k: v for k, v in (fields or {}).items() if hasattr(TypeformResponse, k)}
    }

    new_resp = TypeformResponse(**create_kwargs)
    db.add(new_resp)

    # Ccommit persists user and response table
    db.commit()
    return {"ok": True, "created": True, "submission_id": submission_id}

# Debug 
@app.get("/debug/latest")
def latest(email: str = Query(...), db: Session = Depends(get_db)):
    # find the user by email
    norm_email = email.strip().lower()
    user = db.query(User).filter(User.email == norm_email).first()
    if not user:
        return {"found": False, "reason": "user_not_found", "email": norm_email}

    # get user's latest response
    row = (
        db.query(TypeformResponse)
          .filter(TypeformResponse.user_id == user.id)
          .order_by(TypeformResponse.received_at.desc())
          .first()
    )
    if not row:
        return {"found": False, "reason": "no_responses_for_user", "user_id": str(user.id), "email": user.email}

    # return raw answers + mapped fields
    return {
        "found": True,
        "user": {
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
        },
        "response": {
            "submission_id": row.submission_id,
            "received_at": row.received_at,
            "answers": row.answers,
            "mapped": {
                "career_level": getattr(row, "career_level", None),
                "career_goal": getattr(row, "career_goal", None),
                "industry": getattr(row, "industry", None),
                "target_role": getattr(row, "target_role", None),
                "skills": getattr(row, "skills", None),
                "career_challenges": getattr(row, "career_challenges", None),
                "coaching_style": getattr(row, "coaching_style", None),
                "target_timeline": getattr(row, "target_timeline", None),
                "study_time": getattr(row, "study_time", None),
                "pressure_response": getattr(row, "pressure_response", None),
            }
        }
    }

# =========LEARNING PLAN===============
# router = APIRouter(prefix="/plan", tags=["plan"])

@app.post("/plan/generate", response_model=LearningPlanResponse)
def generate_plan(req: GeneratePlanRequest = Body(...), db: Session = Depends(get_db)):
    # Build context from user responses
    try:
        built = build_user_context(db, email=req.email)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    user_id = built["user_id"]
    ctx = built["context"]

    # Create input signature to dedupe identical runs
    sig = signature_for_context(ctx)
    if not req.regenerate:
        existing = (db.query(LearningPlan)
                      .filter(LearningPlan.user_id == user_id,
                              LearningPlan.input_signature == sig)
                      .order_by(LearningPlan.created_at.desc())
                      .first())
        if existing:
            return LearningPlanResponse(
                user_id=str(user_id),
                model=existing.model,
                plan=existing.plan
            )

    # call openAI
    plan = generate_learning_plan(ctx)

    row = LearningPlan(
        user_id=user_id,
        input_signature=sig,
        model=OPENAI_MODEL,
        plan=plan
    )
    db.add(row)
    db.commit()

    return LearningPlanResponse(
        user_id=str(user_id),
        model=OPENAI_MODEL,
        plan=plan
    )
