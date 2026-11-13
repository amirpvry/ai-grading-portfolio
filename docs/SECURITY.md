# Security model

## Threats and implemented controls

- **Untrusted Python:** source is limited to 20,000 UTF-8 bytes; ASTs exceeding 5,000 nodes are rejected. Parsing errors and recursion limits become deterministic zero-score feedback. No source execution, import, bytecode compilation or shell invocation exists in the grader. Parsing itself still consumes CPU/memory; Celery process deadlines and deployment limits are defense in depth, not a proof of safety.
- **Cross-user access:** every resource queryset and submission assignment lookup is owner-filtered. Cross-owner requests return 404. JWTs expire after 15 minutes; refresh lifetime is one day. Signing keys come from environment variables. There is no public account creation.
- **Duplicate jobs/races:** PostgreSQL row locks, unique idempotency constraints, transaction-local history and lease fencing protect results. Application database credentials remain privileged to modify its own tables; history is audit-friendly, not immutable.
- **Data leakage:** logs contain event names and job IDs, not source or authorization headers. Generic API 500 responses do not expose exception details. Local database contents are not encrypted by the app. Operators must manage retention and backups.
- **External feedback:** mock is default. OpenAI requires explicit operator consent plus provider/model/key configuration. The destination is fixed HTTPS, redirects are disabled, the request has a timeout and bounded network retries, and outputs reject unexpected schema fields including scores. HTTP errors or invalid output become unavailable advice, not score changes. No real-provider call is required for CI. Prompt injection remains possible in advice; never treat advice as executable instructions or render it as unsanitized HTML.

## Dynamic execution policy

Dynamic execution is **not implemented and cannot be enabled with an environment flag**. This project has no dynamic runner. A high AST score is not evidence of correctness or safety. Import detection is a rubric criterion, not a sandbox or security allowlist.

Before implementing a runner, require a separate service with no API/broker/database credentials and no host Docker socket; enforce a narrowly defined input/output protocol. Use a microVM or independently evaluated isolation runtime, non-root UID, all capabilities dropped, mandatory syscall policy, disabled network, read-only base filesystem, bounded ephemeral scratch storage, CPU/memory/PID/output limits, wall-clock termination and cleanup on disconnect. Validate limits on the actual host and test hostile payloads. Docker alone is insufficient. The task environment's Docker daemon reports no cgroup enforcement, so it is unsuitable evidence for dynamic execution safety.

## Before public deployment

Configure TLS and proxy limits, strong key management/rotation, shared rate limiting, refresh-token revocation, user quotas, retention/deletion, dependency/image monitoring, PostgreSQL backups and restore tests. DRF throttling currently uses the per-process local-memory cache; it is not reliable abuse protection across workers. Compose binds API to loopback and does not expose DB/Redis ports, but service networks allow trusted application containers to talk to them. Redis has no password in this local demo. The platform has no multi-tenant isolation guarantees.

Do not put secrets in `.env.example`; `.env` is ignored and excluded from image builds. Do not log provider HTTP bodies or exceptions containing source. Do not submit employer or other private material. Report a vulnerability privately to the repository owner; avoid posting credentials or exploit payloads in a public issue.

See [VALIDATION](VALIDATION.md) for the executed audit and its limits. Automated scans cannot establish legal ownership; provenance here is the independently authored creation process with no employer repository access.
