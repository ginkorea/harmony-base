# app/llm/providers/openai.py
from __future__ import annotations
from typing import AsyncIterator, Dict, Any, Optional, List
import os, json, httpx
from ..base import BaseProvider, ChatRequest

class OpenAIProvider(BaseProvider):
    def __init__(self, name: str, display_name: str, base_url: str, api_key: str, model: str, defaults: Dict[str, Any]):
        self.name = name
        self.display_name = display_name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or ""
        self.model = model
        self.defaults = defaults or {}

    async def startup(self) -> None:
        return None

    async def shutdown(self) -> None:
        return None

    async def stream_chat(self, req: ChatRequest) -> AsyncIterator[str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        # Build messages
        messages: List[Dict[str, str]] = []
        if req.system:
            messages.append({"role": "system", "content": req.system})
        messages.append({"role": "user", "content": req.prompt})

        # Merge defaults + request overrides
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            **self.defaults,
            **(req.llm_params or {}),
        }

        url = f"{self.base_url}/chat/completions"
        timeout = float(self.defaults.get("timeout", 300))

        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    if line.startswith("data:"):
                        data = line[5:].strip()
                    else:
                        data = line.strip()
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
                            yield content
