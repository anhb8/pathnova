import os, hmac, hashlib
from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

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

    data = await request.json()

    # Typeform structure: data["form_response"] {...}
    frm = data.get("form_response", {})
    form_id = frm.get("form_id")
    submission_id = data.get("event_id") or frm.get("token")
    answers = frm.get("answers", [])
    hidden = frm.get("hidden", {})  # contains user_id if you passed it in URL


    existing = db.query(TypeformResponse).filter(TypeformResponse.submission_id == submission_id).first()
    if not existing:
        row = TypeformResponse(
            user_id=None,  # populate later if have users
            form_id=form_id,
            submission_id=submission_id,
            answers=answers
        )
        db.add(row)
        db.commit()

    return {"ok": True}