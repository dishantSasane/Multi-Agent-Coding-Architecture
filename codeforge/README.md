# CodeForge — Multi-Agent Coding Orchestrator

CodeForge is a multi-agent system that takes a natural-language coding request, breaks it into
sub-tasks, routes each sub-task to the most suitable LLM, merges the results with an optional
debate/ensemble step, optionally executes the generated code in an isolated sandbox, and streams
real-time progress to a React dashboard via WebSocket.

---

## Architecture

| Layer | Technology |
|-------|-----------|
| API server | FastAPI + uvicorn |
| Task queue | Celery (pool=solo on Windows) |
| ORM / DB driver | SQLAlchemy 2 async + asyncpg |
| Database | Neon cloud Postgres (serverless) |
| Broker / cache | Upstash cloud Redis (TLS `rediss://`) |
| LLM gateway | LiteLLM → Groq / OpenRouter / Anthropic |
| Sandbox | Docker-in-Docker (optional) |
| Frontend | React 18 + Vite + TypeScript |
| Real-time | WebSocket (FastAPI native) |

### Pipeline stages

```
Intent Analysis → Task Decomposition → Model Routing →
  Parallel Generation → (Debate / Ensemble) → Validation →
    (Sandbox Execution) → Result Merge → Response
```

---

## Prerequisites

| Requirement | Version |
|-------------|---------|
| Python | 3.11 |
| Node.js | 18 + |
| conda | any recent |
| Groq API key | minimum required LLM key |
| Docker Desktop | only if `SANDBOX_ENABLED=true` or using Docker Compose |

---

## Manual Setup (no Docker)

### 1. Clone and create the conda environment

```bash
conda create -n codeforge python=3.11 -y
conda activate codeforge
```

### 2. Install Python dependencies

```bash
pip install -r codeforge/requirements.txt
```

### 3. Install frontend dependencies

```bash
cd codeforge-dashboard
npm install
cd ..
```

### 4. Configure environment variables

```bash
cp codeforge/.env.example codeforge/.env
# Open codeforge/.env and fill in DATABASE_URL, REDIS_URL,
# CELERY_BROKER_URL, CELERY_RESULT_BACKEND, and at least GROQ_API_KEY
```

### 5. Start the backend API

```bash
cd codeforge
uvicorn app.main:app --reload
```

### 6. Start the Celery worker (separate terminal)

```bash
cd codeforge
python -m celery -A app.celery_app worker --loglevel=info --pool=solo
```

> **Windows note:** `--pool=solo` is required on Windows because the default prefork pool
> does not work there.

### 7. Start the frontend (separate terminal)

```bash
cd codeforge-dashboard
npm run dev
```

Open **http://localhost:5173** in your browser.

---

## Docker Setup

Prerequisites: Docker Desktop installed and running.

1. Copy `.env.example` to `.env` and fill in all required values
2. From the **project root** (not the `codeforge/` subdirectory):
   ```bash
   docker compose up --build
   ```
3. Open **http://localhost:5173** in your browser
4. Backend API available at **http://localhost:8000**

### What runs in Docker

| Service | Port | Description |
|---------|------|-------------|
| backend | 8000 | FastAPI + uvicorn |
| worker | — | Celery worker (pool=solo) |
| frontend | 5173 | Built React app (static) |

No local Postgres or Redis containers are started — the app uses your Neon and Upstash
cloud instances via `DATABASE_URL` and `REDIS_URL` in `.env`.

### Sandbox (Docker-in-Docker)

Sandbox code execution requires Docker socket access. On Windows Docker Desktop this
usually works automatically. If sandbox tasks fail, set `SANDBOX_ENABLED=false` in `.env`.

### Stopping

```bash
docker compose down
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | ✅ | Neon Postgres asyncpg connection string |
| `REDIS_URL` | ✅ | Upstash Redis TLS URL (`rediss://`) |
| `CELERY_BROKER_URL` | ✅ | Celery broker — same Redis, db `/0` |
| `CELERY_RESULT_BACKEND` | ✅ | Celery results — same Redis, db `/1` |
| `GROQ_API_KEY` | ✅ | Primary LLM key |
| `GROQ_MODEL` | optional | Groq model slug (default `openai/gpt-oss-120b`) |
| `OPENAI_API_KEY` | optional | OpenAI or OpenRouter key |
| `OPENAI_API_BASE` | optional | Override base URL (e.g. OpenRouter) |
| `ANTHROPIC_API_KEY` | optional | Anthropic direct key |
| `OPENROUTER_API_KEY` | optional | OpenRouter key |
| `KIMI_API_KEY` | optional | Kimi (Moonshot) key |
| `QWEN_API_KEY` | optional | Qwen key |
| `LITELLM_MASTER_KEY` | optional | Internal LiteLLM proxy key |
| `USE_DEBATE_ENGINE` | optional | `true` = run ensemble debate (more quality, more tokens) |
| `USE_LOCAL_FOR_INTENT` | optional | `true` = use Ollama for intent parsing |
| `USE_LOCAL_FOR_CORRECTION` | optional | `true` = use Ollama for correction |
| `MAX_CORRECTION_ATTEMPTS` | optional | Retry limit for correction loop (default `0`) |
| `DEFAULT_ENSEMBLE_SIZE` | optional | Number of models per ensemble (default `3`) |
| `SANDBOX_ENABLED` | optional | `false` = skip Docker sandbox (default `false`) |
| `SANDBOX_TIMEOUT` | optional | Sandbox execution timeout in seconds (default `30`) |
| `SANDBOX_MEMORY_LIMIT` | optional | Container memory cap (default `512m`) |
| `SANDBOX_CPU_LIMIT` | optional | Container CPU quota (default `1.0`) |
| `CIRCUIT_BREAKER_FAILURE_THRESHOLD` | optional | Failures before circuit opens (default `5`) |
| `CIRCUIT_BREAKER_RECOVERY_TIMEOUT` | optional | Seconds before circuit half-opens (default `60`) |
| `SECRET_KEY` | ✅ | Random string ≥ 32 chars for signing |
| `DEBUG` | optional | `true` = verbose logging (default `false`) |
| `CORS_ORIGINS` | optional | JSON array of allowed origins |

---

## Known Issues

- **Groq provider errors** — check the configured model and account limits.
- **Model ID drift** — strings in `app/core/constants.py` (e.g. `gemini-3.6-flash`,
  `claude-sonnet-5`) may not match the provider's current API names. Update them if
  you receive "model not found" errors.
- **Sandbox on Windows** — if Docker socket mount fails, set `SANDBOX_ENABLED=false` in
  `.env` and remove the `volumes` entries from the backend and worker services in
  `docker-compose.yml`.
- **Celery prefork** — always use `--pool=solo` on Windows; the default prefork pool
  does not work on Windows.
