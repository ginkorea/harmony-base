# app/llm/registry.py
from __future__ import annotations
import os, yaml, asyncio
from typing import Dict, Any
from .providers.openai import OpenAIProvider
from .runtimes.llama_cpp_server import LlamaCppServer
from dataclasses import dataclass
from .base import BaseProvider

@dataclass
class ModelEntry:
    name: str
    display_name: str
    type: str
    provider: BaseProvider | None = None
    runtime: object | None = None


class Registry:
    def __init__(self):
        self.models: Dict[str, ModelEntry] = {}
        self.defaults: Dict[str, Any] = {}

    def load(self, path: str = "models.yaml"):
        with open(path, "r") as f:
            data = yaml.safe_load(f) or {}
        self.defaults = (data.get("defaults") or {}).get("llm", {})
        for m in data.get("models", []):
            name = m["name"]
            display = m.get("display_name", name)
            typ = m["type"]

            runtime = None
            if "runtime" in m:
                r = m["runtime"]
                if r.get("kind") == "llama_cpp_server":
                    runtime = LlamaCppServer(
                        bin_path=r["bin"],
                        host=r.get("host","127.0.0.1"),
                        port=int(r.get("port",8080)),
                        args=r.get("args", []),
                    )

            if typ == "openai":
                o = m["openai"]
                prov = OpenAIProvider(
                    name=name,
                    display_name=display,
                    base_url=os.path.expandvars(o["base_url"]),
                    api_key=os.path.expandvars(o.get("api_key","")),
                    model=o["model"],
                    defaults={**self.defaults, **(m.get("llm") or {})},
                )
            else:
                raise ValueError(f"Unknown provider type: {typ}")

            self.models[name] = ModelEntry(
                name=name, display_name=display, type=typ, provider=prov, runtime=runtime
            )

    async def startup(self):
        # start all runtimes first, then providers (if they need it)
        for e in self.models.values():
            if e.runtime:
                await e.runtime.start()
        for e in self.models.values():
            await e.provider.startup()

    async def shutdown(self):
        for e in self.models.values():
            await e.provider.shutdown()
        for e in self.models.values():
            if e.runtime:
                await e.runtime.stop()

    def get(self, model_name: str) -> BaseProvider:
        if model_name not in self.models:
            raise KeyError(f"Model not found: {model_name}")
        return self.models[model_name].provider

registry = Registry()
