# WarriorGPT

**WarriorGPT** is a self-hosted ChatGPT-like system designed for running local large language models with a modern chat interface.
It combines:

* ⚡ A FastAPI backend for authentication, chat persistence, and file uploads.
* 🖥️ A built-in web frontend (dark themed, ChatGPT-style).
* 🧠 Local LLMs (e.g. GPT-OSS, llama.cpp, vLLM) that you can download and serve in your own environment.
* 🔬 Dependencies for model builds (LLVM, Triton) included in `deps/`.

It is intended to be a **general purpose frontend** to any self-hosted model, while remaining lightweight and modular.

---

## Features

* 🔐 **Authentication**

  * Register, login, logout with Argon2 password hashing and JWT cookies.
  * Password reset via signed, short-lived tokens.

* 💬 **Chat**

  * Chat sessions tied to user accounts.
  * Persisted in SQLite (`app.db` by default).
  * Retrieve, reload, and continue past conversations.

* 📎 **File uploads**

  * Paste or drag images (PNG, JPG, WebP, GIF) and PDFs.
  * Session and global quotas.
  * Automatic sweeper task for expired files.

* 🖥️ **Frontend**

  * Single-page UI in `static/` (HTML, CSS, JS).
  * ChatGPT-like design with sticky input, dropzone, thumbnails.
  * Dark theme with responsive layout.

* 🧠 **LLM integration**

  * `/api/generate` streams tokens back to the frontend.
  * Replace the mock echo streamer with your chosen LLM backend.
  * Preconfigured scripts and model folder (`models/`) for GPT-OSS.

---

## Project structure

```
WarriorGPT/
├── app/                # FastAPI backend
│   ├── main.py         # Entrypoint
│   ├── config.py       # Settings (.env)
│   ├── db.py           # SQLAlchemy session/Base
│   ├── models.py       # User, Chat tables
│   └── routers/        # API routes
│       ├── auth.py
│       ├── chats.py
│       ├── uploads.py
│       └── users.py
│
├── static/             # Web UI (served at /)
│   ├── index.html
│   ├── script.js
│   └── style.css
│
├── models/             # Local LLMs
│   └── gpt-oss-20b/
│       ├── config.json
│       ├── model-*.safetensors
│       └── tokenizer.json
│
├── deps/               # Build dependencies (LLVM, Triton, JSON lib, etc.)
├── logs/               # Download & run logs
├── run.sh              # Startup script (convenience)
├── download-gpt-oss.py # Model fetch helper
├── harmony-base.yaml   # Conda environment definition
├── app.db              # SQLite DB (created on first run)
└── README.md
```

---

## Getting started

### 1. Install dependencies

```bash
conda env create -f harmony-base.yaml
conda activate harmony-base
```

### 2. Configure

Create a `.env` in the repo root (or edit `app/config.py` defaults):

```
DATABASE_URL=sqlite:///./app.db
JWT_SECRET=CHANGE_ME_TO_RANDOM_STRING
COOKIE_SECURE=false
CORS_ORIGINS=["http://localhost:8000","http://127.0.0.1:8000"]
```

### 3. Run the backend

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open: [http://localhost:8000](http://localhost:8000)

---

## API overview

* **Auth**
  `/auth/register`, `/auth/login`, `/auth/logout`, `/auth/request_password_reset`, `/auth/reset_password`

* **Users**
  `/u/me`, `/u/me (PATCH)`

* **Chats**
  `/chat/save`, `/chat/list`, `/chat/get/{id}`

* **Files**
  `/files/upload`, `/files/session`, `/files/session/{file_id}`

* **LLM**
  `/api/generate` – replace the mock streamer with your LLM integration

---

## Models

The `models/` folder contains GPT-OSS checkpoints (20B example included).
Use `download-gpt-oss.py` to fetch models.
You can also drop in llama.cpp GGUF, vLLM-ready HF models, or others.

---

## Next steps

* 🔗 Connect `/api/generate` to your model runtime (GPT-OSS, llama.cpp server, vLLM, TGI).
* 📈 Move DB from SQLite → Postgres for multi-user setups.
* 🔒 Harden for production (HTTPS, `COOKIE_SECURE=true`, Redis rate limits).
* 🌐 Serve static UI from nginx and proxy API routes.

---

## License

MIT