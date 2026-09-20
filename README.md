# CodeForge

**Describe what you want to build. Several LLMs write it in parallel, every candidate is validated, and you get a downloadable multi-file project.**

CodeForge is a FastAPI + React app. A request runs through a pipeline: intent analysis → parallel generation across three LLM providers → per-candidate validation → best candidate selected → final validation → downloadable files.

[![Watch the 24-second demo](assets/03-result.png)](assets/codeforge-demo.mp4)

<sub>Click the image to watch the demo (24 s, recorded from a real run: prompt → generation → files → validation).</sub>

| | |
|---|---|
| ![Home](assets/01-home.png) | ![Generating](assets/02-running.png) |
| **Describe the project.** | **Watch the pipeline run** (step 6 of 12 shown). |
| ![Result](assets/03-result.png) | ![Full result](assets/04-full-result.png) |
| **Browse the generated files** with per-file tabs and ZIP download. | **Every step checked, 4/4 validation stages passed.** |

---

## How it works

```
Query ─▶ Intent analysis (Gemini) ─▶ [you confirm if the request is ambiguous]
      ─▶ Parallel generation: Groq + OpenRouter (free models) + Gemini
      ─▶ Validate EVERY candidate ─▶ pick the best valid one
      ─▶ Final validation ─▶ optional self-correction ─▶ optional Docker sandbox ─▶ result
```

**Validation** runs locally on the AST (no API calls) in four stages: syntax, static analysis (bare `except`, print, very long lines), security scan (`eval`, `exec`, `os.system`, `__import__`) and import resolution.

A candidate that fails validation, or that a provider cut off mid-file (`finish_reason=length`), is dropped before the winner is chosen. If no candidate passes, the task fails with the real validation errors instead of shipping broken code.

**Providers** all run at the same time; none is a fallback for another. Each provider only takes part if its API key is set.

| Provider | Role | Model |
|---|---|---|
| Groq | generation | `openai/gpt-oss-120b` |
| OpenRouter | generation | free (`:free`) models only, tried in order on 429/503/404 |
| Gemini | intent analysis + generation | `gemini-3.1-flash-lite` |

---

## Quick start

You need Docker and API keys for at least one provider ([Groq](https://console.groq.com/keys), [OpenRouter](https://openrouter.ai/keys), [Gemini](https://aistudio.google.com/apikey); all have free tiers).

```bash
git clone <repo-url> && cd <repo>
cp codeforge/.env.example codeforge/.env      # add your API keys
docker compose up --build
```

Open **http://localhost:5173**. The API is on http://localhost:8000 (interactive docs at `/docs`).

The stack is Postgres + Redis + backend + frontend. Redis is only an intent-analysis cache; the backend still works without it.

### Without Docker

```bash
# backend (Python 3.11+)
cd codeforge
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env                          # keys + DATABASE_URL pointing at your Postgres
uvicorn app.main:app --reload --port 8000

# frontend (Node 18+), in another terminal
cd codeforge-dashboard
npm install && npm run dev                    # http://localhost:5173, proxies /api to :8000
```

Tables are created on startup. You need a running Postgres for `DATABASE_URL`.

---

## API

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/v1/query` | Submit `{"query": "..."}`; starts the pipeline, returns `task_id` |
| `GET` | `/api/v1/query/{id}/status` | Status, files, validation results |
| `POST` | `/api/v1/query/{id}/confirm` | Confirm (or clarify) the analysed intent when asked |
| `GET` | `/api/v1/query/{id}/result` | Final result |
| `WS` | `/api/v1/ws/{id}` | Live progress |
| `GET` | `/health` | Liveness |

```bash
curl -X POST localhost:8000/api/v1/query -H 'content-type: application/json' \
  -d '{"query":"A URL shortener with a FastAPI backend and an HTML frontend"}'
```

Task status runs `pending → intent_analyzing → [awaiting_confirmation → confirmed] → generating → debating → synthesizing → validating → completed | failed` (`debating` is the candidate-selection step; it makes no LLM calls unless `USE_DEBATE_ENGINE=True`).

---

## Configuration

Set in `codeforge/.env` (see `.env.example`).

| Variable | Default | Meaning |
|---|---|---|
| `GROQ_API_KEY` / `OPENROUTER_API_KEY` / `GEMINI_API_KEY` | – | Providers with a key take part in generation |
| `DEFAULT_ENSEMBLE_SIZE` | `2` in code, `3` in `.env.example` | How many providers generate in parallel |
| `MAX_CORRECTION_ATTEMPTS` | `0` | `>0` sends failed validations back to the model to repair (costs extra calls) |
| `USE_DEBATE_ENGINE` | `False` | Extra LLM critique stage |
| `SANDBOX_ENABLED` | `True` in code, `False` in `.env.example` | Execute generated code in Docker (needs Docker access) |
| `DATABASE_URL` / `REDIS_URL` | compose service names | Postgres (required), Redis (optional) |
| `CORS_ORIGINS` | localhost dev origins | Restrict this in production |
| `DEBUG`, `LOG_LEVEL`, `SECRET_KEY` | | Set a real `SECRET_KEY` in production |

API keys are redacted from all log output.

---

## Development

```bash
cd codeforge && . .venv/bin/activate
pytest tests/unit                 # 125 tests, no network or database needed
ruff check app && mypy app        # both still report pre-existing findings
```

Integration tests need Postgres and Redis; point them at yours:

```bash
TEST_DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/codeforge_test \
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/codeforge \
REDIS_URL=redis://localhost:6379/0 pytest tests/integration
```

## Project structure

```
codeforge/                  FastAPI backend
  app/
    api/v1/endpoints/       query, confirmation, generation, status, websocket
    core/                   constants, circuit breaker, exceptions
    models/                 SQLAlchemy models + Pydantic schemas
    prompts/                intent-analysis prompt
    services/               orchestrator, ensemble, model_router, validator,
                            code_extractor, synthesis, self_correction, sandbox, ...
    utils/                  logging (with key redaction)
  tests/                    unit + integration
  Dockerfile  requirements.txt  requirements-dev.txt  .env.example
codeforge-dashboard/        React + Vite + TypeScript UI
assets/                     screenshots and demo video
docker-compose.yml          db + redis + backend + frontend
```

---

## Known limits

- **Validation is not execution.** Passing all four stages means the code parses, its imports resolve and it has no dangerous calls. It does not mean the generated app runs. Generated projects are not executed unless the sandbox is enabled.
- **Made-up packages can slip through.** Import resolution skips unknown single-word names, so a hallucinated dependency in `requirements.txt` is not flagged.
- **Free tiers are flaky.** OpenRouter's free models are often rate-limited or slow, and Gemini returns occasional 503s. A provider that fails is dropped and the others continue; a task can take up to about 2 minutes when OpenRouter is slow.
- **Groq's free tier** limits a request to 8,000 tokens (prompt plus output), so very large projects can be cut off. Such output is detected and discarded.
- **An explicit request wins over the system prompt.** Asking for `eval()` gets you `eval()`, and the validator then blocks the task.
- **Self-correction is off by default.** With `MAX_CORRECTION_ATTEMPTS=0` a validation failure is final.
- **No authentication or rate limiting.** Do not expose it publicly as is. See [Deploying](#deploying).

## Deploying

Before putting this on the internet, add authentication and per-user rate limits; otherwise anyone who finds the URL can spend your provider quota. Then restrict `CORS_ORIGINS`, set a real `SECRET_KEY`, use a managed Postgres, and serve the frontend as a static build (`npm run build`), not the Vite dev server.

The pipeline runs as a FastAPI background task after the HTTP response returns, so choose a host that keeps CPU allocated between requests (an always-on container, or Cloud Run with CPU always allocated and at least one instance).
