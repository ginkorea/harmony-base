# app/main.py

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from .config import settings
from .db import Base, engine
from .routers import uploads, chats, auth
from .routers.auth import get_current_user, AuthUser
from .routers import generate  # /api/models, /api/generate

# ---- FIX: import the registry (supports either app.llm.registry or app.registry)
try:
    from .llm.registry import registry
except ImportError:
    from .registry import registry  # fallback if your layout is app/registry.py

# --- DB init ---
Base.metadata.create_all(engine)

app = FastAPI(title="WarriorGPT")

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=getattr(settings, "CORS_ORIGINS", ["*"]),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router)     # /auth/*
app.include_router(uploads.router)  # /files/*
app.include_router(chats.router)    # /chat/*
app.include_router(generate.router) # /api/models, /api/generate (proxy via registry)

# --- Static & index ---
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
def root():
    index = STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    return {"ok": True, "hint": "Place your UI at static/index.html or open /static/index.html"}

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

# --- Lifecycle: load models.yaml, start/stop runtimes/providers ---
@app.on_event("startup")
async def _startup():
    # Load model registry (models.yaml at repo root)
    registry.load("models.yaml")
    await registry.startup()

@app.on_event("shutdown")
async def _shutdown():
    await registry.shutdown()
