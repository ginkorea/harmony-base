from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Response, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from passlib.hash import argon2
from jose import jwt, JWTError
from sqlalchemy import select, update
from collections import defaultdict
from time import time

from ..db import get_db
from ..models import User
from ..config import settings

router = APIRouter(prefix="/auth", tags=["auth"])

# === helpers ===
COOKIE = "access_token"

def hash_pw(pw: str) -> str:
    # Argon2id; passlib handles salt & params
    return argon2.using(rounds=3).hash(pw)

def verify_pw(pw: str, ph: str) -> bool:
    try:
        return argon2.verify(pw, ph)
    except Exception:
        return False

def make_access_token(sub: str) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(days=settings.ACCESS_TOKEN_DAYS)
    payload = {"sub": sub, "iat": int(now.timestamp()), "exp": int(exp.timestamp())}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGO)

def set_cookie(resp: Response, token: str):
    resp.set_cookie(
        COOKIE, token,
        httponly=True, secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE, path="/",
    )

def clear_cookie(resp: Response):
    resp.delete_cookie(COOKIE, path="/")

# --- brute-force throttle (dev-grade; move to Redis in prod) ---
FAILS = defaultdict(list)
MAX_FAILS, WINDOW = 5, 15 * 60

def record_fail(key: str):
    now = time()
    FAILS[key] = [t for t in FAILS[key] if now - t < WINDOW] + [now]

def too_many(key: str) -> bool:
    now = time()
    FAILS[key] = [t for t in FAILS[key] if now - t < WINDOW]
    return len(FAILS[key]) >= MAX_FAILS

# === schemas ===
class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

class PublicUser(BaseModel):
    id: int
    email: EmailStr

class AuthUser(PublicUser):
    pass

# === routes ===
@router.post("/register", response_model=PublicUser, status_code=201)
def register(payload: RegisterIn, db=Depends(get_db)):
    email = payload.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(400, "Email already registered")
    u = User(email=email, password_hash=hash_pw(payload.password))
    db.add(u)
    db.commit()
    db.refresh(u)
    return PublicUser(id=u.id, email=u.email)

@router.post("/login")
def login(
    response: Response,
    request: Request,
    form: Annotated[OAuth2PasswordRequestForm, Depends()],  # username == email
    db=Depends(get_db),
):
    email = form.username.strip().lower()
    key = f"{email}:{request.client.host}"
    if too_many(key):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many attempts, try later")

    u = db.scalar(select(User).where(User.email == email))
    if not u or not verify_pw(form.password, u.password_hash):
        record_fail(key)
        raise HTTPException(401, "Invalid credentials")

    set_cookie(response, make_access_token(str(u.id)))
    return {"ok": True, "user": {"id": u.id, "email": u.email}}

@router.post("/logout")
def logout(response: Response):
    clear_cookie(response)
    return {"ok": True}

# --- guard dependency ---
def get_current_user(request: Request, db=Depends(get_db)) -> AuthUser:
    tok = request.cookies.get(COOKIE)
    if not tok:
        raise HTTPException(401, "Not authenticated")
    try:
        payload = jwt.decode(tok, settings.JWT_SECRET, algorithms=[settings.JWT_ALGO])
        uid = int(payload.get("sub"))
    except JWTError:
        raise HTTPException(401, "Invalid or expired token")
    u = db.get(User, uid)
    if not u:
        raise HTTPException(401, "User not found")
    return AuthUser(id=u.id, email=u.email)

# === password reset (signed, short-lived JWT token) ===
class ResetRequestIn(BaseModel):
    email: EmailStr

class ResetRequestOut(BaseModel):
    ok: bool
    reset_token: Optional[str] = None  # dev convenience; email it in prod
    expires_in_minutes: int

@router.post("/request_password_reset", response_model=ResetRequestOut)
def request_password_reset(payload: ResetRequestIn, db=Depends(get_db)):
    email = payload.email.lower()
    u = db.scalar(select(User).where(User.email == email))
    # Always respond ok; only include token if user exists (avoid user enumeration)
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=settings.RESET_TOKEN_MINUTES)
    if not u:
        return ResetRequestOut(ok=True, reset_token=None, expires_in_minutes=settings.RESET_TOKEN_MINUTES)

    token = jwt.encode(
        {"sub": str(u.id), "typ": "pwd_reset", "iat": int(now.timestamp()), "exp": int(exp.timestamp())},
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGO,
    )
    return ResetRequestOut(ok=True, reset_token=token, expires_in_minutes=settings.RESET_TOKEN_MINUTES)

class ResetPasswordIn(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)

@router.post("/reset_password")
def reset_password(payload: ResetPasswordIn, db=Depends(get_db)):
    try:
        data = jwt.decode(payload.token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGO])
        if data.get("typ") != "pwd_reset":
            raise HTTPException(400, "Invalid token type")
        uid = int(data["sub"])
    except JWTError:
        raise HTTPException(400, "Invalid or expired token")

    db.execute(update(User).where(User.id == uid).values(password_hash=hash_pw(payload.new_password)))
    db.commit()
    return {"ok": True}
