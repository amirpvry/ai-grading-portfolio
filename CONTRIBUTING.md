# Contributing

Use original code and synthetic inputs only. Do not reference private repositories or contribute employer material. Never add secrets, `.env`, datasets, virtual environments or generated databases.

Install with `uv sync --frozen`. Run Ruff, pytest, PostgreSQL concurrency tests, migration drift checks and pip-audit as documented in README. Add regression tests for behavior changes, especially ownership, retries and transaction boundaries. Keep score logic deterministic and separate from provider advice. Do not add a source execution path without a separate threat model and reviewed sandbox service.

Use focused commits explaining the behavior and validation. Update API and design documentation when contracts change. Publication requires repository owner approval; keep this repository private until then.
