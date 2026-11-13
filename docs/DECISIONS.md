# Design decisions

## ADR 001 — Structural grading only

Accepted: syntax and a small public, original rubric vocabulary provide deterministic evidence without executing untrusted code. This sacrifices runtime correctness assessment. Resource-bounded separate sandbox work is deferred; there is no unsafe fallback.

## ADR 002 — Database outbox and lease fencing

Accepted: job + history + dispatch intent commit atomically. Publish-before-mark allows duplicate delivery instead of lost work. PostgreSQL claim locks and tokens fence stale writers. A periodic sweep recovers pending/expired jobs; it creates duplicate broker traffic and needs a single available scheduler. Exactly-once execution is not promised.

## ADR 003 — Rubric snapshots

Accepted: jobs preserve the rubric used at submission even if an owner later edits an assignment. Full immutable/versioned assignment records are deferred. Idempotency compares source and assignment identity, so replaying after a rubric edit still returns the original job.

## ADR 004 — Advisory provider abstraction

Accepted: a small Protocol and Pydantic schema keep provider code separate. Mock feedback supports offline CI. Operator opt-in is sufficient only for this personal local demo; per-user consent is future work. Provider output cannot change the deterministic score. LangGraph adds overhead without a branching workflow, so it is omitted.

## ADR 005 — JWT and owner-scoped workspaces

Accepted: Django account creation via management commands plus SimpleJWT keeps the authentication demonstration focused. Users manage their own assignments and jobs; there is no instructor/student organization model. Public signup, SSO, password recovery and revocation are deferred.

## ADR 006 — PostgreSQL correctness, SQLite convenience

Accepted: fast local tests can use SQLite, but concurrency assertions run only against PostgreSQL. CI provisions PostgreSQL. Python dependencies are locked and hash-checked during Docker installation; mutable base image tags require separate image pinning/update policy for a real deployment.
