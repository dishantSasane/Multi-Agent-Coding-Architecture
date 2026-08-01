# CodeForge

Multi-Agent Coding Orchestrator System - Production-ready code generation with adversarial review, sandbox execution, and multi-stage validation.

## Architecture Overview

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   FastAPI   │────▶│   Celery     │────▶│  PostgreSQL │
│   (REST)    │     │   Workers    │     │  (State)    │
└─────────────┘     └──────────────┘     └─────────────┘
       │                    │
       ▼                    ▼
┌─────────────┐     ┌──────────────┐
│  WebSocket  │     │    Redis     │
│  (Real-time)│     │   (Queue)    │
└─────────────┘     └──────────────┘
                          │
                          ▼
              ┌────────────────────────┐
              │   LLM Router (LiteLLM) │
              ├────────────────────────┤
              │ Claude │ GPT-4 │ Qwen  │
              │ Kimi   │ Gemini│       │
              └────────────────────────┘
                          │
                          ▼
              ┌────────────────────────┐
              │   Docker Sandbox       │
              │   (Execution)          │
              └────────────────────────┘
```

## Features

- **Multi-Model Ensemble**: Parallel dispatch to 3+ LLMs with voting
- **Adversarial Debate**: Models critique each other's solutions
- **Sandbox Execution**: Secure Docker containers with resource limits
- **Multi-Stage Validation**: Syntax, static analysis, security, tests, fuzzing
- **Self-Correction**: Automatic error fixing with exponential backoff
- **Circuit Breakers**: Graceful degradation when LLM APIs fail

## Quick Start

```bash
# Clone and setup
cd codeforge
cp .env.example .env
# Edit .env with your API keys

# Start all services
docker-compose up -d

# Access API
open http://localhost:8000/docs

# Run tests
docker-compose exec app pytest

# Check logs
docker-compose logs -f app
```

## API Endpoints

- `POST /api/v1/query` - Submit coding query
- `GET /api/v1/query/{task_id}/status` - Poll status
- `POST /api/v1/query/{task_id}/confirm` - Confirm intent
- `GET /api/v1/query/{task_id}/result` - Get final result
- `WS /ws/{task_id}` - Real-time updates

## Configuration

See `.env.example` for all configuration options.

### Required Environment Variables

- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `OPENAI_API_KEY` - OpenAI API key
- `ANTHROPIC_API_KEY` - Anthropic API key
- At least one LLM provider key

## Development

```bash
# Install dependencies
pip install -e ".[dev]"

# Run linting
ruff check app/
mypy app/

# Run tests
pytest tests/

# Start development server
uvicorn app.main:app --reload
```

## Security Considerations

- All generated code runs in isolated Docker containers
- No network egress from sandbox
- Resource limits prevent DoS
- Input sanitization prevents prompt injection
- Circuit breakers protect against API failures

## License

MIT
