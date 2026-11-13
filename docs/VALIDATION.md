# Validation and release audit

Executed in the task workspace on 2026-11-13 using Python 3.12.14 and PostgreSQL 17. This records observed results, not a certification.

| Check | Observed result |
|---|---|
| PostgreSQL pytest suite | **31 passed**, no skips or warnings; **91%** grading-package statement coverage |
| Concurrency | Four concurrent same-key submissions produce one job; four concurrent worker deliveries claim one attempt |
| Retry/security regressions | JWT, ownership, source bounds, nonexecution, rubric validation/snapshots, duplicate delivery, outbox failure, expired leases, attempt exhaustion and stale-worker fencing passed |
| Provider tests | Mock, consent gate, timeout retry and schema rejection tested; no real OpenAI requests made |
| Live integration | Real Gunicorn + JWT + HTTP API + PostgreSQL + Beat + Redis + prefork Celery worker completed a job, persisted score/history and replayed idempotently |
| Ruff | Lint and formatting checks passed |
| Django checks | System checks passed; migration drift check reported no changes |
| Migrations | Applied to a real PostgreSQL database successfully; test database created/destroyed successfully |
| Docker | Application image built successfully with hash-verified dependencies |
| Compose | Full startup **not validated**: host VFS storage exhausted while creating app containers; project test artifacts removed and storage recovered |
| Dependency advisories | `pip-audit -r requirements.txt`: **no known vulnerabilities found** at audit time |
| GitHub Actions | GitHub Actions run [43480573981](https://github.com/amirpvry/ai-grading-portfolio/actions/runs/43480573981) **completed successfully**; PostgreSQL-backed tests, Redis smoke test, lint, migration checks and dependency audit passed |

The first SQLite run passed 23 tests and skipped two PostgreSQL-only tests. An early PostgreSQL run passed but exposed test connection cleanup warnings, which were fixed. A later database rerun failed at setup due to host storage exhaustion, not an application assertion; storage recovery enabled the clean final run above. A first live smoke attempt collided with a platform port; the script now uses 18080 and the final run passed.

## Files and provenance

This project began as a new local repository with fresh, focused commits and no imported parents; it has since been pushed to GitHub. Only connected account/repository metadata was checked. No employer repository files, source, history, documents or contracts were opened, cloned, modified or reused. Application code and synthetic samples were authored independently in this workspace. This provenance process supports the originality statement; no automated scanner can establish legal ownership.

Tracked files and the full fresh Git history were inspected. No virtualenv, database, cache, private dataset, employer branding, private endpoint or actual API credential is tracked. Package URLs resolve to public PyPI hosts. The only external application API is the explicitly opt-in, fixed OpenAI endpoint. Git author uses the owner's GitHub noreply address.

`detect-secrets` was run over project files and tracked files. Findings were manually reviewed: `.env.example` URL placeholders, synthetic CI credentials/signing key, example password text, synthetic test passwords, and the smoke script's runtime-generated random password assignment. The real locally generated `.env` is ignored by Git and excluded from Docker builds; the initial all-files scan correctly flagged its local database URL. No scanner result is treated as proof that all secrets are absent. A final snapshot scan also covers each commit in the fresh history.

## Remaining release concerns

- Dynamic execution is unavailable; AST scores do not establish functional correctness.
- Full Compose health/startup still needs a run on a host with adequate Docker storage. Docker host resource limits were not enforced in this environment; no sandbox safety claim is made.
- No real external provider request or provider data-retention review was performed.
- Rate limits use local process memory; no token revocation, per-user external-data consent or data-retention system exists.
- OS/container image CVE scanning and public deployment hardening remain outstanding. Python advisory results are a point-in-time check, not a container audit.
- The repository was subsequently pushed to [GitHub](https://github.com/amirpvry/ai-grading-portfolio) and is now public with the owner's approval. The initial GitHub Actions run completed successfully. This does **not** constitute production deployment approval or a comprehensive security certification.

Resume wording supported by executed evidence:

> Built an independent Django/DRF backend for asynchronous AST-based code grading using PostgreSQL, Redis and Celery; implemented JWT authorization, rubric snapshots, transactional dispatch, idempotency and lease-fenced worker recovery, with 31 passing PostgreSQL-backed tests and a verified live API-to-worker workflow.
