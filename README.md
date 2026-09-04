# CodeForge — Multi-Agent Coding Orchestrator

CodeForge is a production-ready AI coding assistant that routes your natural-language request through a **pipeline of multiple LLM agents**, each specialising in a different part of the task, and delivers validated, multi-file code.

## Architecture

```
User Query
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  FastAPI  (port 8000)                                           │
│                                                                 │
│  1. Intent Parser   → understands what you want                 │
│  2. Ensemble        → 1-N models generate code in parallel      │
│  3. Debate Engine   → models critique each other (optional)     │
│  4. Synthesis       → best solution merged & cleaned            │
│  5. Validator       → syntax · static analysis · import check   │
│  6. Sandbox         → executes code in Docker (optional)        │
│  7. Self-Correction → fixes failures automatically              │
└──────────────────────────────┬──────────────────────────────────┘
                               │ WebSocket (real-time progress)
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  React Dashboard  (port 5173)                                   │
│  • Pipeline stage tracker                                       │
│  • Multi-file tab viewer + per-file + ZIP download             │
│  • Model activity cards                                         │
│  • Validation report                                            │
└─────────────────────────────────────────────────────────────────┘

External Services (cloud — no local containers required)
  • Neon         → PostgreSQL database
  • Upstash      → Redis (Celery broker + result backend)
  • Google AI    → Gemini 2.0 Flash Lite (primary LLM)
  • OpenRouter   → fallback LLMs (optional)
```

---

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| Docker + Docker Compose | Option A only |
| conda or Python 3.11 | Option B only |
| Node 18+ | Option B frontend |
| Neon account | Free — [neon.tech](https://neon.tech) |
| Upstash account | Free — [upstash.com](https://upstash.com) |
| Google AI Studio key | Free — [aistudio.google.com](https://aistudio.google.com/app/apikey) |

---

## Option A — Docker (Recommended)

```bash
# 1. Clone
git clone <repo-url>
cd Multi-Agent-Coding-Architecture

# 2. Configure environment
cp codeforge/.env.example codeforge/.env
# Open codeforge/.env and fill in your real API keys and URLs

# 3. Build and start all services
docker compose up --build

# 4. Open the dashboard
#    http://localhost:5173
```

All three services start together:
- **backend** — FastAPI on port 8000
- **celery** — background task worker
- **frontend** — Vite dev server on port 5173

To stop: `docker compose down`  
To rebuild after code changes: `docker compose up --build`

---

## Option B — Manual Setup (conda)

### Backend

```bash
# Create environment
conda create -n codeforge python=3.11 -y
conda activate codeforge

# Install dependencies
pip install -r codeforge/requirements.txt

# Configure environment
cp codeforge/.env.example codeforge/.env
# Edit codeforge/.env with your API keys

# Start the API server
cd codeforge
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Celery Worker (separate terminal)

```bash
conda activate codeforge
cd codeforge
python -m celery -A app.celery_app worker --loglevel=info --pool=solo
```

### Frontend (separate terminal)

```bash
cd codeforge-dashboard
npm install
npm run dev
# Open http://localhost:5173
```

---

## Required API Keys & Services

### 1. Gemini API Key (primary LLM — **required**)
- Sign up at [aistudio.google.com](https://aistudio.google.com/app/apikey)
- Free tier: **500 requests/day** on Gemini 2.0 Flash Lite
- Set `GEMINI_API_KEY` in `.env`

### 2. Neon PostgreSQL (**required**)
- Sign up at [neon.tech](https://neon.tech) — free tier available
- Create a project and copy the **asyncpg connection string**
- Set `DATABASE_URL` — must include `?sslmode=require`

### 3. Upstash Redis (**required**)
- Sign up at [upstash.com](https://upstash.com) — free tier available
- Create a Redis database, copy the **TLS (rediss://) connection string**
- Set `REDIS_URL`, `CELERY_BROKER_URL`, and `CELERY_RESULT_BACKEND`

### 4. OpenRouter (optional fallback)
- Sign up at [openrouter.ai](https://openrouter.ai) — free tier available
- Set `OPENROUTER_API_KEY`, `OPENAI_API_KEY` (same key), and  
  `OPENAI_API_BASE=https://openrouter.ai/api/v1`
- Used automatically when Gemini quota runs out

---

## Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | — | Neon PostgreSQL asyncpg URL |
| `REDIS_URL` | — | Upstash Redis TLS URL |
| `CELERY_BROKER_URL` | — | Same as `REDIS_URL` |
| `CELERY_RESULT_BACKEND` | — | Same as `REDIS_URL` |
| `GEMINI_API_KEY` | — | Google AI Studio key |
| `SANDBOX_ENABLED` | `False` | Enable Docker sandbox (needs Docker-in-Docker) |
| `DEFAULT_ENSEMBLE_SIZE` | `1` | Models to call per query (1 = cheapest) |
| `USE_DEBATE_ENGINE` | `False` | LLM debate stage (extra API calls) |
| `MAX_CORRECTION_ATTEMPTS` | `3` | Self-correction retry limit |
| `DEBUG` | `True` | Show full tracebacks in HTTP responses |
| `SECRET_KEY` | change me | JWT signing key — **change in production** |

---

## Known Issues & Limits

| Symptom | Cause | Fix |
|---------|-------|-----|
| `503 Service Unavailable` from Gemini | Daily quota (500 RPD) exhausted | Wait until quota resets, or configure OpenRouter fallback |
| Each query uses 2 API calls | Intent analysis + code generation | Expected behaviour; set `USE_LOCAL_FOR_INTENT=True` with Ollama to reduce it |
| `SANDBOX_ENABLED=False` required | No Docker-in-Docker in most envs | Leave `False`; code is validated but not executed |
| Celery worker shows `connection refused` | Upstash URL missing or wrong | Check `CELERY_BROKER_URL` in `.env`; must be `rediss://` (TLS) |
| `ValidationError` on import resolution | Generated code uses local imports | Fixed in validator — single-word bare imports are skipped |

---

## Project Structure

```
Multi-Agent-Coding-Architecture/
├── codeforge/                  # FastAPI backend
│   ├── app/
│   │   ├── api/                # Route handlers (query, status, websocket)
│   │   ├── core/               # Circuit breaker, exceptions, security
│   │   ├── models/             # SQLAlchemy ORM + Pydantic schemas
│   │   ├── prompts/            # LLM prompt templates
│   │   └── services/           # Orchestrator, ensemble, validator, sandbox …
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
│
├── codeforge-dashboard/        # React + Vite + TypeScript frontend
│   ├── src/
│   │   ├── components/         # UI components
│   │   ├── hooks/              # useWebSocket, useCodeGeneration
│   │   ├── store/              # Zustand app store
│   │   └── lib/                # API client
│   └── Dockerfile
│
├── docker-compose.yml          # Orchestrates backend + celery + frontend
└── README.md                   # This file
```

---

## Git Commands (after setup)

```bash
# Stage everything
git add .

# Verify .env is excluded (should NOT appear)
git status | grep ".env"

# Commit
git commit -m "Initial CodeForge commit"

# Push
git push origin main
```
