#!/usr/bin/env bash
set -euo pipefail
python - <<'PY'
import os, sys
from pathlib import Path
if not Path(".env").exists() and Path(".env.example").exists():
    import shutil; shutil.copyfile(".env.example", ".env")
print("Using .env:", Path(".env").resolve())
PY

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
