# app/llm/base.py
from __future__ import annotations
from typing import AsyncIterator, Dict, Any, Optional
from pydantic import BaseModel

class ChatRequest(BaseModel):
    prompt: str
    system: Optional[str] = None
    llm_params: Dict[str, Any] = {}

class BaseProvider:
    name: str
    display_name: str

    async def startup(self) -> None:
        """Optional: start processes or warmups."""
        return None

    async def shutdown(self) -> None:
        """Optional: stop processes."""
        return None

    async def stream_chat(self, req: ChatRequest) -> AsyncIterator[str]:
        """Yield text chunks."""
        raise NotImplementedError
