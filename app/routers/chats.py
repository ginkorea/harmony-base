# app/routers/chats.py

from fastapi import APIRouter, Request, Response, Depends, HTTPException, Form
from sqlalchemy import select
from ..db import get_db
from ..models import Chat
from .auth import get_current_user, AuthUser
from typing import Optional

router = APIRouter(prefix="/chat", tags=["chats"])

@router.post("/save")
def save_chat(messages_jsonl: str = Form(...),
              title: Optional[str] = Form(None),
              db=Depends(get_db),
              user: AuthUser = Depends(get_current_user)):
    c = Chat(user_id=user.id, title=title, messages_jsonl=messages_jsonl)
    db.add(c); db.commit()
    return {"ok": True, "chat_id": c.id}

@router.get("/list")
def list_chats(db=Depends(get_db), user: AuthUser = Depends(get_current_user)):
    rows = db.execute(select(Chat.id, Chat.title, Chat.created_at)
                      .where(Chat.user_id == user.id)
                      .order_by(Chat.id.desc())).all()
    return [{"id": r.id, "title": r.title, "created_at": r.created_at.isoformat()} for r in rows]

@router.get("/get/{chat_id}")
def get_chat(chat_id: int, db=Depends(get_db), user: AuthUser = Depends(get_current_user)):
    c = db.get(Chat, chat_id)
    if not c or c.user_id != user.id:
        raise HTTPException(404, "Not found")
    return {"id": c.id, "title": c.title, "messages_jsonl": c.messages_jsonl, "created_at": c.created_at.isoformat()}
