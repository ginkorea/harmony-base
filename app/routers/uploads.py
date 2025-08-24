from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request, Response, Depends
from typing import List, Optional
from pathlib import Path
import time, uuid, asyncio, imghdr, os
from ..config import settings
from .auth import get_current_user, AuthUser

router = APIRouter(prefix="/files", tags=["uploads"])

SID_COOKIE = "sid"
ALLOWED_MIME = {"image/png","image/jpeg","image/webp","image/gif","application/pdf"}

BASE = Path(settings.UPLOADS_DIR)
BASE.mkdir(parents=True, exist_ok=True)

def get_sid(req: Request, res: Response) -> str:
    sid = req.cookies.get(SID_COOKIE)
    if not sid:
        sid = uuid.uuid4().hex
        res.set_cookie(SID_COOKIE, sid, httponly=True, secure=settings.COOKIE_SECURE,
                       samesite=settings.COOKIE_SAMESITE, path="/", max_age=60*60*6)
    return sid

def sdir(user_id: int, sid: str) -> Path:
    p = BASE / f"user_{user_id}" / sid
    p.mkdir(parents=True, exist_ok=True)
    return p

def dir_size_bytes(path: Path) -> int:
    total = 0
    for p in path.glob("**/*"):
        if p.is_file():
            total += p.stat().st_size
    return total

def trim_global_cap():
    cap = settings.GLOBAL_CAP_GB * 1024**3
    files = sorted((p for p in BASE.glob("**/*") if p.is_file()), key=lambda p: p.stat().st_mtime)
    total = sum(p.stat().st_size for p in files)
    i = 0
    while total > cap and i < len(files):
        sz = files[i].stat().st_size
        files[i].unlink(missing_ok=True)
        total -= sz
        i += 1

async def sweeper_task():
    while True:
        cutoff = time.time() - settings.UPLOAD_TTL_SECONDS
        for d in BASE.rglob("*"):
            if not d.is_dir():
                continue
            for f in d.iterdir():
                try:
                    if f.is_file() and f.stat().st_mtime < cutoff:
                        f.unlink(missing_ok=True)
                except Exception:
                    pass
            try:
                if d.exists() and not any(d.iterdir()):
                    d.rmdir()
            except Exception:
                pass
        trim_global_cap()
        await asyncio.sleep(600)

@router.on_event("startup")
async def start_sweeper():
    asyncio.create_task(sweeper_task())

@router.post("/upload")
async def upload(req: Request, res: Response,
                 files: List[UploadFile] = File(...),
                 message: Optional[str] = Form(None),
                 user: AuthUser = Depends(get_current_user)):
    sid = get_sid(req, res)
    outdir = sdir(user.id, sid)

    session_cap = settings.SESSION_CAP_MB * 1024**2
    current = dir_size_bytes(outdir)
    saved = []

    for f in files:
        if f.content_type not in ALLOWED_MIME:
            raise HTTPException(415, f"Unsupported type: {f.content_type}")
        ext = {
            "image/png": ".png","image/jpeg": ".jpg","image/webp": ".webp",
            "image/gif": ".gif","application/pdf": ".pdf"
        }.get(f.content_type, "")
        fid = uuid.uuid4().hex
        dest = outdir / (fid + ext)

        maxb = settings.UPLOAD_MAX_MB * 1024**2
        size = 0
        with dest.open("wb") as out:
            while chunk := await f.read(1024 * 1024):
                size += len(chunk)
                if size > maxb:
                    out.close(); dest.unlink(missing_ok=True)
                    raise HTTPException(413, f"File too large. Limit {settings.UPLOAD_MAX_MB} MB")
                if current + size > session_cap:
                    out.close(); dest.unlink(missing_ok=True)
                    raise HTTPException(413, f"Session quota exceeded. Limit {settings.SESSION_CAP_MB} MB")
                out.write(chunk)
        current += size

        if f.content_type.startswith("image/"):
            if imghdr.what(dest) is None:
                dest.unlink(missing_ok=True)
                raise HTTPException(400, "Invalid image data")

        os.utime(dest, None)
        saved.append({"id": fid, "name": f.filename, "stored": dest.name, "type": f.content_type, "size": size})

    trim_global_cap()
    return {"ok": True, "sid": sid, "files": saved, "ttl_seconds": settings.UPLOAD_TTL_SECONDS}

@router.get("/session")
async def list_session(req: Request, res: Response, user: AuthUser = Depends(get_current_user)):
    sid = get_sid(req, res)
    outdir = sdir(user.id, sid)
    items = []
    for fp in outdir.glob("*"):
        st = fp.stat()
        items.append({
            "id": fp.stem, "name": fp.name, "size": st.st_size,
            "modified": int(st.st_mtime),
            "expires_in": max(0, int(st.st_mtime + settings.UPLOAD_TTL_SECONDS - time.time()))
        })
    return {"sid": sid, "files": items}

@router.delete("/session/{file_id}")
async def delete_one(req: Request, res: Response, file_id: str, user: AuthUser = Depends(get_current_user)):
    sid = get_sid(req, res)
    outdir = sdir(user.id, sid)
    hits = list(outdir.glob(file_id + "*"))
    if not hits:
        raise HTTPException(404, "Not found")
    for fp in hits: fp.unlink(missing_ok=True)
    return {"ok": True}
