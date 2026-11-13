# API examples

All data below is synthetic. Start Compose and create a `demo` account as described in README. Set `TOKEN` to a token returned by `POST /api/token/`.

## Create an assignment

```bash
curl http://localhost:8000/api/assignments/ \
 -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{
  "title":"Normalize labels",
  "description":"Define normalize_labels(values), include a docstring, and avoid imports.",
  "rubric":[
    {"kind":"syntax","points":20},
    {"kind":"function","target":"normalize_labels","points":40},
    {"kind":"docstring","target":"normalize_labels","points":20},
    {"kind":"no_imports","points":20}
  ]
}'
```

Returns 201 with `id` and timestamps. Criterion targets default to an empty string except required function/docstring identifiers.

## Submit

```bash
curl http://localhost:8000/api/jobs/ \
 -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{
  "assignment":1,
  "source":"def normalize_labels(values):\n    \"Normalize labels.\"\n    return [v.strip().lower() for v in values if v.strip()]",
  "idempotency_key":"labels-001"
}'
```

Returns 202. Store the returned UUID. The same key/payload returns 200 with the same job. Different source with the same key returns 409. Keys are scoped to the authenticated user, 1–100 ASCII letters, digits, underscores or hyphens.

```bash
curl http://localhost:8000/api/jobs/JOB_UUID/ -H "Authorization: Bearer $TOKEN"
curl 'http://localhost:8000/api/jobs/?state=COMPLETED&page=1' -H "Authorization: Bearer $TOKEN"
```

Representative completed result (inside the job's `result` field):

```json
{
  "score": 100,
  "breakdown": [
    {"kind":"syntax","target":"","points":20,"earned":20,"passed":true},
    {"kind":"function","target":"normalize_labels","points":40,"earned":40,"passed":true},
    {"kind":"docstring","target":"normalize_labels","points":20,"earned":20,"passed":true},
    {"kind":"no_imports","target":"","points":20,"earned":20,"passed":true}
  ],
  "feedback":"Structural evidence only; runtime correctness is not tested.",
  "mode":"ast-only",
  "advisory":{
    "summary":"Review the structural rubric evidence.",
    "suggestions":["Add independent runtime tests."]
  }
}
```

Syntax/complexity rejection completes with score 0 and an empty breakdown; it is a valid grading outcome, not a worker failure. Infrastructure/domain failures retry and eventually produce FAILED. Advisory failure is represented as `{"status":"unavailable"}`.

## Errors

Handled API exceptions use a consistent envelope:

```json
{"error":{"status":409,"details":{"detail":"Idempotency key already used for a different request"}}}
```

Validation details may be field dictionaries; JWT errors include their standard error code inside `details`. Relevant statuses: 400 validation, 401 authentication, 404 inaccessible/missing object, 409 key conflict, 429 throttled, 500 unexpected failure. Routing-level non-API errors are Django responses. List endpoints return `count`, `next`, `previous`, `results`; default page size is 20. Unknown state filters yield no matches.
