# app/llm/runtimes/llama_cpp_server.py
from __future__ import annotations
import asyncio, time, os
from subprocess import Popen
from typing import Optional
from pathlib import Path
import httpx

class LlamaCppServer:
    def __init__(self, bin_path: str, host: str, port: int, args: list[str]):
        self.bin = bin_path
        self.host = host
        self.port = port
        self.args = args
        self.proc: Optional[Popen] = None
        self.log_path = Path("logs/llama_server.log")

    def _preflight(self):
        # binary exists?
        b = Path(self.bin)
        if not b.exists():
            raise FileNotFoundError(f"llama.cpp server binary not found: {b}")
        # model file exists? (naive: look for '-m' and grab the next token)
        if "-m" in self.args:
            try:
                mi = self.args.index("-m")
                mpath = Path(self.args[mi+1])
                if not mpath.exists():
                    raise FileNotFoundError(f"Model GGUF not found: {mpath}")
            except Exception:
                pass

    async def start(self, wait_timeout: float = 180.0) -> None:
        # if already up, don't spawn
        if await self._is_ready(0.1):
            return
        self._preflight()
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        logf = self.log_path.open("ab", buffering=0)  # append binary, unbuffered
        # Keep env; you may set CUDA_VISIBLE_DEVICES externally if needed
        env = os.environ.copy()
        # Spawn with visible logs
        self.proc = Popen([self.bin, *self.args], stdout=logf, stderr=logf, env=env)
        try:
            await self._wait_ready(wait_timeout)
        except Exception:
            # tail last lines into the exception for quick hints
            try:
                with self.log_path.open("rb") as lf:
                    tail = lf.read()[-4096:].decode("utf-8", "ignore")
                raise RuntimeError(
                    "llama.cpp server did not become ready.\n--- llama_server.log tail ---\n"
                    + tail
                )
            finally:
                # Let it keep running if it actually started; otherwise kill
                if self.proc and self.proc.poll() is None:
                    try: self.proc.terminate()
                    except Exception: pass
                self.proc = None

    async def stop(self) -> None:
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=5)
            except Exception:
                try: self.proc.kill()
                except Exception: pass
        self.proc = None

    async def _is_ready(self, timeout: float) -> bool:
        url = f"http://{self.host}:{self.port}/v1/models"
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                r = await client.get(url)
                return r.status_code == 200
        except Exception:
            return False

    async def _wait_ready(self, timeout: float) -> None:
        t0 = time.time()
        while time.time() - t0 < timeout:
            if await self._is_ready(2.0):
                return
            await asyncio.sleep(0.5)
        raise RuntimeError("llama.cpp server did not become ready")
