# app/config.py

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List
import json

class Settings(BaseSettings):
    CORS_ORIGINS: List[str] = Field(default_factory=lambda: ["http://localhost:8000","http://127.0.0.1:8000"])
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "lax"

    UPLOADS_DIR: str = "/tmp/pastebox"
    UPLOAD_TTL_SECONDS: int = 2 * 60 * 60
    UPLOAD_MAX_MB: int = 25
    SESSION_CAP_MB: int = 150
    GLOBAL_CAP_GB: int = 50

    DATABASE_URL: str = "sqlite:///./app.db"

    # NEW: auth
    JWT_SECRET: str = "REPLACE_ME_WITH_32PLUS_RANDOM_BYTES"
    JWT_ALGO: str = "HS256"
    ACCESS_TOKEN_DAYS: int = 14

    # password reset token validity (minutes)
    RESET_TOKEN_MINUTES: int = 30

    # llama-server config -- adjust as needed
    LLAMA_SERVER_URL: str = "http://127.0.0.1:8080" # change for production
    LLAMA_MODEL: str = "llama"  # set to your served model name
    LLAMA_API_KEY: str = ""  # if llama-server requires it; else leave blank
    LLAMA_TIMEOUT: float = 60.0

    def parse_origins(self, v):
        if isinstance(v, list): return v
        try: return json.loads(v)
        except Exception: return [s.strip() for s in str(v).split(",") if s.strip()]

    class Config:
        env_file = ".env"

settings = Settings()
