# app/routers/llama.py
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from typing import Any, Dict, List
from ..config import settings
from .auth import get_current_user, AuthUser
import httpx, json

router = APIRouter(tags=["llm"])

def _to_messages(payload: Dict[str, Any]) -> List[Dict[str, str]]:
    # Support either {messages:[...]} or {prompt, system}
    if isinstance(payload.get("messages"), list):
        return payload["messages"]
    prompt = (payload or {}).get("prompt", "") or ""
    system = payload.get("system") or payload.get("systemPrompt")
    msgs: List[Dict[str, str]] = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    return msgs

@router.post("/api/generate")
async def generate(payload: Dict[str, Any], user: AuthUser = Depends(get_current_user)):
    url = settings.LLAMA_SERVER_URL.rstrip("/") + "/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    if settings.LLAMA_API_KEY:
        headers["Authorization"] = f"Bearer {settings.LLAMA_API_KEY}"

    body: Dict[str, Any] = {
        "model": settings.LLAMA_MODEL,
        "messages": _to_messages(payload),
        "stream": True,
    }

    # Allow extra llm params pass-through (temperature, top_p, etc.)
    if isinstance(payload.get("llm_params"), dict):
        body.update(payload["llm_params"])

    async def stream():
        try:
            async with httpx.AsyncClient(timeout=settings.LLAMA_TIMEOUT) as client:
                async with client.stream("POST", url, headers=headers, json=body) as resp:
                    if resp.status_code != 200:
                        detail = (await resp.aread()).decode("utf-8", "ignore")
                        raise HTTPException(status_code=resp.status_code, detail=detail or "llama-server error")
                    async for line in resp.aiter_lines():
                        if not line:
                            continue
                        if not line.startswith("data:"):
                            continue
                        data = line[5:].strip()
                        if data == "[DONE]":
                            break
                        try:
                            obj = json.loads(data)
                        except Exception:
                            continue
                        for choice in obj.get("choices", []):
                            delta = (choice or {}).get("delta") or {}
                            content = delta.get("content")
                            if content:
                                # stream raw text so the existing frontend keeps working
                                yield content
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=502, detail=str(e))

    return StreamingResponse(stream(), media_type="text/plain")
