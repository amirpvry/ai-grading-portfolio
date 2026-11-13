# AI Grading Portfolio

An independently designed Django backend demonstrating asynchronous, **AST-only** Python code grading. It combines deterministic structural rubric scores with optional, schema-validated advisory feedback. It is an original portfolio demonstration, not an employer application.

**What a score means:** a submission can score 100 while returning the wrong answer. This project measures syntax and selected structural evidence, not functional correctness. Submitted code is never executed.

## Technical highlights

- Python 3.12+, Django 5.2, DRF and short-lived JWT access tokens.
- PostgreSQL transactions, user-scoped resources and per-user idempotency keys.
- Redis/Celery delivery with a transactional outbox, expiring worker leases and fenced completion writes.
- Immutable submission/rubric snapshots, four job states and timestamped state history.
- Pure AST scoring, bounded source size, original synthetic examples and no executable-code path.
- Provider abstraction: deterministic mock or explicit opt-in OpenAI advisory feedback. Provider failures never change scores.
- Locked dependencies, Ruff, pytest, PostgreSQL concurrency tests, Docker Compose and GitHub Actions.

## Architecture

```mermaid
flowchart LR
  Client -->|JWT| API[Django REST API]
  API -->|atomic submission + snapshot + outbox| DB[(PostgreSQL)]
  Beat[Celery Beat / outbox dispatcher] --> DB
  Beat -->|at least once| Redis[(Redis)]
  Redis --> Worker[Celery worker]
  Worker -->|claim lease / fence completion| DB
  Worker --> AST[Pure AST grader]
  Worker --> Mock[Mock feedback]
  Worker -. explicit consent .-> LLM[OpenAI advisory provider]
  Sandbox[Future separate sandbox service - NOT implemented]
```

`grading/api` handles HTTP validation and ownership; `grading/domain` contains scoring rules; `grading/services.py` owns submission transactions; `grading/tasks.py` owns delivery and job lifecycle; `grading/infrastructure` integrates feedback and logging.

## Run with Docker Compose

Install Docker with Compose. No API key is needed.

```bash
cp .env.example .env
# Replace both password placeholders with the SAME random password.
# Generate DJANGO_SECRET_KEY: python -c 'import secrets; print(secrets.token_urlsafe(48))'
docker compose up --build -d
docker compose exec api python manage.py createsuperuser --username demo
docker compose exec api python manage.py seed_demo demo
docker compose ps
curl http://localhost:8000/health/
```

The API binds to localhost only. PostgreSQL and Redis have no published ports. The one-shot `migrate` service must finish before API, worker and Beat start. Keep exactly one Beat instance. Jobs normally start within a dispatcher interval (10 seconds).

```bash
docker compose logs -f api worker beat
docker compose down           # retain data
# docker compose down -v       # deliberately deletes local demo data
```

## Local development and tests

Install Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --frozen
uv run pytest --cov=grading --cov-report=term-missing
uv run ruff check .
uv run ruff format --check .
uv run python manage.py makemigrations --check --dry-run --settings=config.test_settings
uv run pip-audit -r requirements.txt
```

The fast test default is SQLite, with PostgreSQL concurrency tests explicitly skipped. To exercise row locks, supply a dedicated PostgreSQL database whose user can create test databases:

```bash
DATABASE_URL=postgresql://grader:password@localhost:5432/grader uv run pytest
```

For a disposable local PostgreSQL/Redis instance, export the normal app variables and run `uv run python scripts/smoke.py` to start real Gunicorn, Celery and Beat processes, exercise the HTTP lifecycle, and clean up synthetic data. The smoke script uses port 18080 and must not run against a shared broker or production database.

Tests select `config.test_settings`; production configuration requires `DATABASE_URL` and `DJANGO_SECRET_KEY`. Normal Django commands do not read `.env` automatically; Compose injects it. For running outside Docker, export your variables, run migrations, then start Gunicorn, a Celery worker and one Beat process separately.

## API

| Method | Endpoint | Behavior |
|---|---|---|
| POST | `/api/token/` | Username/password → access and refresh tokens |
| POST | `/api/token/refresh/` | Refresh → access token |
| GET, POST | `/api/assignments/` | Paginated own assignments / create |
| GET, PUT, PATCH | `/api/assignments/{id}/` | Read or edit own assignment/rubric |
| POST | `/api/jobs/` | Submit code with an idempotency key; returns 202 |
| GET | `/api/jobs/?state=COMPLETED&page=1` | Paginated own jobs; optional state filter |
| GET | `/api/jobs/{uuid}/` | Result, attempts, timestamps and state history |
| GET | `/health/` | Database readiness; 200 or 503 |

Assignments and submissions belong to the authenticated user. There is no public registration endpoint; create local accounts through Django management commands. Assignment deletion and submission editing are deliberately unavailable. Rubric kinds are `syntax`, `function`, `docstring`, `no_imports`; function/docstring criteria require a target identifier. Between 1 and 10 criteria must total 100 points.

```bash
curl -s http://localhost:8000/api/token/ -H 'Content-Type: application/json' \
  -d '{"username":"demo","password":"YOUR_LOCAL_PASSWORD"}'
# Set TOKEN to the returned access token.
curl http://localhost:8000/api/jobs/ -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"assignment":1,"source":"def normalize_labels(values):\n    \"Normalize labels.\"\n    return [v.strip().lower() for v in values if v.strip()]","idempotency_key":"demo-001"}'
```

The response includes `id`, `state: "PENDING"`, empty `result`, and the initial history event. Poll the detail endpoint until `COMPLETED` or `FAILED`. Completion includes a score, per-criterion earned points and advisory feedback. Full copyable examples: [API_EXAMPLES](docs/API_EXAMPLES.md).

## Lifecycle and guarantees

1. Validate JWT, ownership, input bounds and rubric.
2. In one transaction, serialize submissions for the user, snapshot the rubric, and create job/history/outbox rows.
3. Return 202; replaying the same key and payload returns the same job with 200. A changed payload returns 409.
4. Beat publishes outbox entries to Redis before marking them sent. Unsent entries survive broker outages.
5. A worker locks the job, claims a 90-second lease and increments its attempt counter. Active or terminal jobs are ignored on duplicate delivery.
6. AST grading and optional feedback happen outside the transaction. A completion write must match the current lease token.
7. Expired leases and pending jobs are redispatched. Three failed/abandoned attempts lead to FAILED. State changes append history in the same transaction.

Delivery is at least once; this is not an exactly-once claim. See [architecture](docs/ARCHITECTURE.md) and [decisions](docs/DECISIONS.md) for failure windows and trade-offs.

## Security and limitations

Dynamic execution is disabled by design: there is no `exec`, `eval`, subprocess runner, or Docker socket mounted into application services. Docker alone is not a complete isolation boundary. A future sandbox needs an independently reviewed service boundary, stronger isolation, enforced CPU/memory/PID limits, strict deadlines, disabled networking, read-only filesystem, ephemeral storage and unprivileged execution. See [SECURITY](docs/SECURITY.md).

Code is stored as plaintext in the local database. Do not submit private or sensitive code. External feedback requires `LLM_PROVIDER=openai`, `LLM_SEND_CODE_CONSENT=true`, `OPENAI_API_KEY` and `OPENAI_MODEL`. This is an operator opt-in for a personal local demo, not a per-user consent system. Leave it off for multi-user use. Provider output is untrusted text, schema-validated and separate from scores.

This is not a hardened public service: add TLS, shared rate limiting, request limits at the reverse proxy, token revocation, retention/deletion policy, monitoring, backups and deployment-specific threat review before Internet exposure. Logs omit source and tokens. The health endpoint checks the database, not the entire pipeline.

## Future work

- Dedicated sandbox service with a microVM or independently reviewed gVisor deployment and adversarial testing.
- Per-submission external-provider consent and data deletion workflows.
- Authenticated operational metrics, outbox backoff, fairness and per-user storage quotas.
- Versioned rubric records, more structural criteria and reviewable human overrides.
- Shared Redis rate limiting, refresh-token revocation and deployment hardening.

LangGraph is intentionally omitted: this bounded linear pipeline does not benefit from a graph runtime.

## Portfolio and provenance

All application code, synthetic assignments and documentation were created independently in a fresh repository. No employer source, history, assets or internal contracts were accessed or reused. MIT-licensed original project code; dependencies retain their own licenses. See [validation evidence](docs/VALIDATION.md), [contributing](CONTRIBUTING.md), and [GitHub setup](docs/GITHUB_SETUP.md).
