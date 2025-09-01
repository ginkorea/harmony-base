# app/routers/llm.py
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from ..routers.auth import get_current_user, AuthUser
from ..llm.base import ChatRequest
from ..llm.registry import registry

router = APIRouter(tags=["llm"])

class GenerateIn(BaseModel):
    prompt: str = Field("", description="User prompt")
    system: Optional[str] = Field(None)
    llm_params: Dict[str, Any] = {}

@router.post("/api/generate")
async def generate(
    body: GenerateIn,
    model: str = Query(..., description="Model name from models.yaml"),
    user: AuthUser = Depends(get_current_user),
):
    try:
        provider = registry.get(model)
    except KeyError:
        raise HTTPException(404, f"Unknown model: {model}")

    req = ChatRequest(prompt=body.prompt, system=body.system, llm_params=body.llm_params)

    async def stream():
        async for chunk in provider.stream_chat(req):
            yield chunk

    return StreamingResponse(stream(), media_type="text/plain")
