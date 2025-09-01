# app/routers/generate.py (new)
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from ..llm.registry import registry
from ..llm.base import ChatRequest
# If you want auth: from .auth import get_current_user, AuthUser

router = APIRouter(tags=["llm"])

@router.get("/api/models")
def list_models():
    return [
        {"name": e.name, "display_name": e.display_name, "type": e.type}
        for e in registry.models.values()
    ]

@router.post("/api/generate")
async def generate(
    req: ChatRequest,
    model: str | None = Query(default=None, description="Model name from /api/models"),
    # user: AuthUser = Depends(get_current_user)  # uncomment if you want auth
):
    # choose provider
    try:
        provider_name = model or next(iter(registry.models.keys()))
        provider = registry.get(provider_name)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

    async def stream():
        async for chunk in provider.stream_chat(req):
            yield chunk

    return StreamingResponse(stream(), media_type="text/plain")
