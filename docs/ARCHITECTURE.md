# Architecture

## Boundaries

The REST layer handles transport concerns and limits reads/writes to the caller. The domain grader has no Django dependency and never executes source. Submission creation is an application service. Persistence models encode ownership, immutable submission snapshots and unique per-user idempotency keys. Infrastructure provides feedback adapters and JSON log formatting. Celery orchestrates the lifecycle; Redis is a transport, PostgreSQL is authoritative.

## Consistency

A user-row lock serializes first-use idempotency keys, avoiding a check-then-create race. The assignment is locked while copying the rubric; updates to an assignment cannot mutate existing job snapshots. A unique database constraint is a second line of defense. These guarantees depend on PostgreSQL, not SQLite.

The outbox is committed alongside the job. The dispatcher publishes before marking sent, so a crash can cause duplicate delivery. A concurrent dispatcher can also publish duplicates. Pending jobs are redispatched as a recovery sweep, including when a broker loses an acknowledged message. This simple bounded sweep may publish extra messages for a backlog; throughput and fairness are not claimed. Use a single Beat instance.

Workers lock jobs only for transitions. A 90-second lease exceeds the 60-second hard task deadline. Duplicate delivery during an active lease exits. Expired jobs can be reclaimed. Each attempt gets a random fencing token: an older worker cannot overwrite a newer attempt. Both success and failure transitions check that token. At most three attempts can be claimed. A crash after result commit but before broker acknowledgement is harmless on redelivery.

Transient domain failures move to PENDING and ask Celery to retry with exponential delay. The periodic sweep is a fallback and can schedule earlier than that delay. Feedback failures are intentionally nonfatal. Lease recovery depends on Beat running and approximately synchronized clocks. There is no automatic retry of terminal FAILED jobs; use a fresh submission key for a deliberate new job.

## Data and operations

Assignments contain a JSON rubric. Jobs store source, rubric snapshot, score breakdown, advisory feedback, attempts and timestamps. History captures state transitions, not a tamper-proof audit log. There are no source-update or history-edit API endpoints; database administrators can still modify rows. IDs are ordered only by creation time for presentation.

Compose runs separate API, migration, worker, Beat, database and broker processes. Application containers use a non-root UID, read-only root filesystem, writable temporary directory, dropped capabilities and no privilege escalation. These settings protect ordinary service processes; they do not authorize dynamic submission execution. The API health check verifies DB reachability. Worker health checks use Celery control ping. Beat availability requires operator supervision; no claim of full distributed readiness is made.

## Growth path

Replace the bounded pending sweep with scheduled publication attempts and explicit retry timestamps at larger backlogs. Add queue age metrics, per-user quotas, observability and rubric versions. Partition or archive history only when measurements justify it. A sandbox requires a distinct credential-free service, never Docker-in-worker.
