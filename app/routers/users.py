from fastapi import APIRouter, Request, Response, Depends
from pydantic import BaseModel
from sqlalchemy import select, update
from ..db import get_db
from ..models import User
import uuid
from ..config import settings

COOKIE = "uid"

router = APIRouter(prefix="/u", tags=["users"])

class MeOut(BaseModel):
    user_id: str
    display_name: str | None = None

class MeUpdateIn(BaseModel):
    display_name: str | None = None

def ensure_user(req: Request, res: Response, db):
    uid = req.cookies.get(COOKIE)
    if not uid:
        uid = uuid.uuid4().hex
        res.set_cookie(COOKIE, uid, httponly=True, secure=settings.COOKIE_SECURE,
                       samesite=settings.COOKIE_SAMESITE, path="/", max_age=60*60*24*365*5)
    u = db.scalar(select(User).where(User.user_id == uid))
    if not u:
        u = User(user_id=uid)
        db.add(u)
        db.commit()
    return uid

@router.get("/me", response_model=MeOut)
def me(req: Request, res: Response, db=Depends(get_db)):
    uid = ensure_user(req, res, db)
    u = db.scalar(select(User).where(User.user_id == uid))
    return MeOut(user_id=u.user_id, display_name=u.display_name)

@router.patch("/me", response_model=MeOut)
def update_me(payload: MeUpdateIn, req: Request, res: Response, db=Depends(get_db)):
    uid = ensure_user(req, res, db)
    db.execute(update(User).where(User.user_id == uid).values(display_name=payload.display_name))
    db.commit()
    u = db.scalar(select(User).where(User.user_id == uid))
    return MeOut(user_id=u.user_id, display_name=u.display_name)
