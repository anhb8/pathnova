import os, datetime as dt, uuid, urllib.parse as urlparse, httpx
from fastapi import FastAPI, Depends, Request, HTTPException, Query, Body, Cookie, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from .services.typeform_mapper import extract_response_fields
from .services.plan_inputs import build_user_context, signature_for_context
from .services.generate_plan import generate_learning_plan, OPENAI_MODEL
from .db import get_db
from .init_db import init_db
from .schemas import GeneratePlanRequest, LearningPlanResponse, GoogleTokenIn
from .models import Ping, TypeformResponse, User, LearningPlan, AuthProvider
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from google.oauth2 import id_token
from google.auth.transport import requests as grequests
from pydantic import BaseModel
from typing import Optional, Tuple, Dict, List, Any
import jwt
from dotenv import load_dotenv
load_dotenv()

app = FastAPI(title="PathNova API")
TYPEFORM_SECRET = os.getenv("TYPEFORM_SECRET")

# Allow React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",  # include both to be safe during dev
    ],
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

# ------------ Google Auth helpers & routes ------------
JWT_SECRET = os.getenv("JWT_SECRET", "change_me")
JWT_DAYS = int(os.getenv("JWT_DAYS", "7"))
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")          
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_OAUTH_REDIRECT_URI", "http://localhost:8000/auth/google/callback")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

def make_jwt(uid: str) -> str:
    payload = {
        "uid": uid,
        "jti": str(uuid.uuid4()),
        "exp": dt.datetime.utcnow() + dt.timedelta(days=JWT_DAYS),
        "iat": dt.datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def read_jwt(token: str) -> str:
    data = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    return data["uid"]

def require_user(session: str | None = Cookie(default=None), db: Session = Depends(get_db)) -> User:
    if not session:
        raise HTTPException(status_code=401, detail="No session")
    try:
        uid = read_jwt(session)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid session")
    user = db.get(User, uid)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

@app.post("/auth/google")
def auth_google(body: GoogleTokenIn, response: Response, db: Session = Depends(get_db)):
    # Verify Google ID token
    try:
        claims = id_token.verify_oauth2_token(
            body.id_token, grequests.Request(), GOOGLE_CLIENT_ID
        )
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid Google token")

    sub = claims.get("sub")
    email = (claims.get("email") or "").lower()
    name = claims.get("name") or None
    if not sub:
        raise HTTPException(status_code=400, detail="Missing Google sub")

    # Find existing mapping
    ap = db.query(AuthProvider).filter_by(provider="google", provider_user_id=sub).one_or_none()

    if ap:
        user = db.get(User, ap.user_id)
        ap.last_login_at = dt.datetime.utcnow()
        if not user:
            # dangling mapping (rare) — unlink & create proper user
            db.delete(ap)
            user = None
    else:
        user = db.query(User).filter_by(email=email).one_or_none()
        if not user:
            # create user with generated UUID (from DB default gen_random_uuid())
            # If users.id is generated in DB, you must INSERT via raw SQL or fetch the id after insert
            user = User(email=email, name=name)
            db.add(user)
            db.flush()  
        else:
            if name and user.name != name:
                user.name = name

        ap = AuthProvider(
            provider="google",
            provider_user_id=sub,
            user_id=user.id,
            email_at_link_time=email or None,
        )
        db.add(ap)

    db.commit()

    # Set session cookie
    token = make_jwt(str(user.id))
    response.set_cookie(
        key="session",
        value=token,
        httponly=True,
        secure=False,     # set True in production with HTTPS
        samesite="lax",
        max_age=JWT_DAYS * 24 * 3600,
        path="/",
    )

    return {"ok": True, "user": {"id": str(user.id), "email": user.email, "name": user.name}}

@app.get("/auth/me")
def auth_me(current: User = Depends(require_user)):
    return {"id": str(current.id), "email": current.email, "name": current.name}

@app.post("/auth/logout")
def auth_logout(response: Response):
    # Clear cookie
    response.delete_cookie("session", path="/")
    return {"ok": True}

# redirect user to Google's consent screen
@app.get("/auth/google/start")
def google_start():
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",    
        "prompt": "consent",          
    }
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlparse.urlencode(params)
    return RedirectResponse(url)

# Exchange code for tokens using Google's token endpoint
@app.get("/auth/google/callback")
async def google_callback(request: Request, response: Response, code: str, db: Session = Depends(get_db)):   
    async with httpx.AsyncClient(timeout=10) as client:
        token_res = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    if token_res.status_code != 200:
        raise HTTPException(status_code=401, detail="Token exchange failed")

    token_data = token_res.json()
    id_token_str = token_data.get("id_token")
    if not id_token_str:
        raise HTTPException(status_code=401, detail="No id_token in response")

    # Verify the ID token with Google
    try:
        claims = id_token.verify_oauth2_token(id_token_str, grequests.Request(), GOOGLE_CLIENT_ID)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid Google ID token")

    # Extract identity claims
    sub = claims.get("sub")                   
    email = (claims.get("email") or "").lower()  
    name = claims.get("name") or None
    if not sub:
        raise HTTPException(status_code=400, detail="Missing Google sub")

    # Upsert user & provider mapping
    ap = db.query(AuthProvider).filter_by(provider="google", provider_user_id=sub).one_or_none()
    if ap:
        user = db.get(User, ap.user_id)
        ap.last_login_at = dt.datetime.utcnow()
        if not user:
            db.delete(ap)
            user = None
    else:
        user = db.query(User).filter_by(email=email).one_or_none()
        if not user:
            user = User(email=email, name=name)
            db.add(user)
            db.flush()  
        else:
            if name and user.name != name:
                user.name = name

        ap = AuthProvider(
            provider="google",
            provider_user_id=sub,
            user_id=user.id,
            email_at_link_time=email or None,
        )
        db.add(ap)

    db.commit()

    # Create session cookie
    token = make_jwt(str(user.id))

    # Redirect the user to the Dashboard page as "logged in".
    redirect = RedirectResponse(url=f"{FRONTEND_URL}/plan")
    redirect.set_cookie(
        key="session",
        value=token,
        httponly=True,       
        secure=False,        
        samesite="lax",
        max_age=7 * 24 * 3600,
        path="/",
    )

    return redirect
