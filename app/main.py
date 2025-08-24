from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pathlib import Path
import asyncio

from .config import settings
from .db import Base, engine
from .routers import uploads, chats, auth
from .routers.auth import get_current_user, AuthUser

# --- DB init ---
Base.metadata.create_all(engine)

app = FastAPI(title="Pastebox")

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routers ---
app.include_router(auth.router)     # /auth/*
app.include_router(uploads.router)  # /files/*
app.include_router(chats.router)    # /chat/*

# --- Static & index ---
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def root():
    index = STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    return {"ok": True, "hint": "Place your UI at harmony-base/static/index.html or open /static/index.html"}

@app.get("/favicon.ico")
def favicon():
    fav = STATIC_DIR / "favicon.ico"
    if fav.exists():
        return FileResponse(fav)
    raise HTTPException(status_code=404, detail="favicon not found")

# --- Health ---
@app.get("/healthz")
def health():
    return {"ok": True}

# --- Who am I (used by the UI header) ---
@app.get("/me")
def me(user: AuthUser = Depends(get_current_user)):
    return {"user": user}

# --- Mock generator for UI streaming test ---
# Replace with your real LLM call later.
@app.post("/api/generate")
async def generate(payload: dict, user: AuthUser = Depends(get_current_user)):
    prompt = (payload or {}).get("prompt", "")
    _attachments = (payload or {}).get("attachments", [])

    async def streamer():
        text = f"Echo: {prompt} "
        for ch in text:
            yield ch
            await asyncio.sleep(0.02)
    return StreamingResponse(streamer(), media_type="text/plain")
