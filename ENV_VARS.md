# Environment variables

Reference for `shopagent_v2` runtime configuration. The
authoritative source is `backend/.env.example` — this doc explains what each
group is for and which are required vs optional.

> Quick start: copy `backend/.env.example` to `backend/.env` and fill in the
> blanks marked **Required**. Defaults are sensible for local development.

## Project

| Variable | Required | Default | Description |
|---|---|---|---|
| `PROJECT_NAME` | optional | `shopagent_v2` | Used in logs, OpenAPI title, email templates |
| `DEBUG` | optional | `true` | When `true`, FastAPI returns full tracebacks |
| `ENVIRONMENT` | optional | `local` | Free-form tag: `local` / `staging` / `production` |
| `TIMEZONE` | optional | `Asia/Shanghai` | IANA TZ name (e.g. `Europe/Warsaw`) |
| `BACKEND_URL` | optional | `http://localhost:8000` | Used by frontend BFF + email link generation |
| `FRONTEND_URL` | optional | `http://localhost:3000` | Used by password-reset / magic-link emails |

## Auth & secrets

| Variable | Required | Default | Description |
|---|---|---|---|
| `SECRET_KEY` | **required in prod** | (generated) | JWT signing key. Rotating invalidates all tokens |
| `API_KEY` | **required in prod** | (generated) | Static admin/service-to-service key for `X-API-Key` header |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | optional | `30` | JWT access token lifetime |
| `REFRESH_TOKEN_EXPIRE_MINUTES` | optional | `10080` | JWT refresh token lifetime (7 days) |

## Database
| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | **required** | `postgresql+asyncpg://...` | Full async connection string |
| `DB_POOL_SIZE` | optional | `5` | Number of long-lived connections |
| `DB_MAX_OVERFLOW` | optional | `10` | Burst capacity above pool size |

## LLM / AI

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | **required** | — | Key for the configured OpenAI-compatible provider (DeepSeek in this project) |
| `OPENAI_BASE_URL` | optional | `https://api.deepseek.com/v1` | OpenAI-compatible API base URL |
| `AI_MODEL` | optional | `deepseek-flash` | Default model used by agent |
| `LOGFIRE_TOKEN` | optional | — | When set, ships traces to Logfire (logfire.pydantic.dev) |

## RAG (pgvector)

| Variable | Required | Default | Description |
|---|---|---|---|
| `EMBEDDING_PROVIDER` | optional | `fastembed` | `fastembed` for local ONNX or `openai` for an API |
| `EMBEDDING_MODEL` | optional | `BAAI/bge-small-zh-v1.5` | 512-d Chinese semantic embedding model |
| `RAG_HYBRID_SEARCH` | optional | `true` | Enable BM25 + vector RRF retrieval |

## Redis

| Variable | Required | Default | Description |
|---|---|---|---|
| `REDIS_URL` | **required** | `redis://localhost:6379/0` | Used by cache, Celery broker, rate-limiter, session store |

## Prometheus

| Variable | Required | Default | Description |
|---|---|---|---|
| `PROMETHEUS_METRICS_PATH` | optional | `/metrics` | URL path where metrics are exposed |
| `PROMETHEUS_AUTH_TOKEN` | optional (off if empty) | — | When set, `/metrics` requires `Authorization: Bearer <token>` |

## Frontend (`frontend/.env.local`)

Separate from the backend `.env` above — `frontend/README.md` has the full table.
The two that decide whether a deployment works at all:

| Variable | Read by | Description |
|---|---|---|
| `NEXT_PUBLIC_WS_URL` | browser | WebSocket origin for chat. Inlined at **build** time, so it needs a rebuild to change, and it must be an address the browser can reach — not a Docker service name |
| `COOKIE_SECURE` | server | `Secure` flag on the auth cookies. Unset follows `NODE_ENV`. A browser drops a `Secure` cookie served over plain `http://`, which makes every request after login return 401 — set `false` only for `http://` on a trusted network |

## Validation

```bash
# Confirm settings load without errors:
cd backend && uv run python -c "from app.core.config import settings; print(settings.model_dump_json(indent=2))"
```

If any **Required** var is missing, FastAPI raises `pydantic_settings.SettingsError` on startup — check the message for which field.
