import os, hmac, hashlib
from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from .services.typeform_mapper import extract_response_fields
from .db import get_db
from .init_db import init_db
from .models import Ping, TypeformResponse

app = FastAPI(title="PathNova API")

TYPEFORM_SECRET = os.getenv("TYPEFORM_SECRET")

# Allow your React dev server
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
    # """Typeform sends 'Typeform-Signature: sha256=...'. Verify HMAC if secret configured."""
    # if not TYPEFORM_SECRET:
    #     return True  # skip verification if not using a secret
    # if not signature or not signature.startswith("sha256="):
    #     return False
    # expected = hmac.new(TYPEFORM_SECRET.encode(), payload, hashlib.sha256).hexdigest()
    # provided = signature.split("sha256=")[-1]
    # return hmac.compare_digest(expected, provided)
    return True

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

    # identify the user if you pass hidden fields
    email = hidden.get("email")         # optional
    user_id = hidden.get("user_id")     # optional (UUID string you pass in URL)

    # build the new columns from answers
    fields = extract_response_fields(answers)

    # Upsert by submission_id (idempotent)
    existing = db.query(TypeformResponse).filter(
        TypeformResponse.submission_id == submission_id
    ).first()

    if existing:
        # update the new fields on the existing row
        for k, v in fields.items():
            setattr(existing, k, v)
        # also update optional email link if you have it
        if email and not existing.email:
            existing.email = email
        db.commit()
        return {"ok": True, "updated": True, "submission_id": submission_id}

    # Create new row
    row = TypeformResponse(
        form_id=form_id,
        submission_id=submission_id,
        answers=answers,
        email=email,         # optional convenience
        user_id=None,        # set if you resolve user_id -> users.id
        **fields
    )
    db.add(row)
    db.commit()
    return {"ok": True, "created": True, "submission_id": submission_id}

# Debug 
@app.get("/debug/latest")
def latest(db: Session = Depends(get_db)):
    row = (db.query(TypeformResponse)
           .order_by(TypeformResponse.received_at.desc())
           .first())
    if not row:
        return {"found": False}
    return {
        "found": True,
        "submission_id": row.submission_id,
        "answers": row.answers,
        "mapped": {
            "name": row.name,
            "email": row.email,
            "career_level": row.career_level,
            "career_goal": row.career_goal,
            "industry": row.industry,
            "target_role": row.target_role,
            "skills": row.skills,
            "career_challenges": row.career_challenges,
            "coaching_style": row.coaching_style,
            "target_timeline": row.target_timeline,
            "study_time": row.study_time,
            "pressure_response": row.pressure_response
        }
    }