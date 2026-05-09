# Spec: POST /query — Semantic Cache Lookup with OpenAI Fallback

## Purpose
Primary endpoint. Returns a cached or freshly generated AI response to a Java code query.
Implements the cache-first strategy: Redis → FAISS → OpenAI.

## Inputs
| Field        | Type        | Required | Description                              |
|--------------|-------------|----------|------------------------------------------|
| query        | string      | yes      | User's code question (max 10,000 chars)  |
| prompt_type  | enum        | no       | QUERY \| GENERATE_TESTS (default: QUERY) |
| context      | string      | no       | Additional file context (max 5,000 chars)|
| language     | string      | no       | Target language hint (default: "java")   |
| Authorization| header      | yes      | Bearer JWT token                         |

## Outputs
```json
{
  "response": "string",
  "cache_hit": true,
  "similarity": 0.94,
  "tokens_used": 0,
  "prompt_type": "QUERY"
}
```

## Behavior / Logic
1. Extract `user_id`, `team_id` from JWT; reject 401 if invalid
2. Run `sanitizer.sanitize(query)` — strip secrets before any processing
3. Compute `query_hash = SHA256(sanitized_query)`
4. **Redis check**: `GET query_hash`
   - IF hit → log `(cache_hit=true, tokens=0)`, return `{response, cache_hit=true, similarity=null}`
5. Embed `sanitized_query` using SentenceTransformers `all-MiniLM-L6-v2`
6. Normalize embedding to unit vector
7. **FAISS search**: top-1, compute cosine similarity
   - IF `similarity >= 0.9` → fetch response from Postgres by stored ID, update Redis TTL, log `(cache_hit=true)`, return
8. **OpenAI fallback**: call `gpt-4.1-mini` with system prompt tuned to `prompt_type`
   - GENERATE_TESTS: include JUnit 5 instructions in system prompt
   - QUERY: concise code-review system prompt
9. Store: call `POST /upsert` internally (non-blocking, background task)
10. Log `(cache_hit=false, tokens_used=N)` to Postgres `request_logs`
11. Return `{response, cache_hit=false, tokens_used=N}`

## Acceptance Criteria
- [ ] Same query sent twice returns `cache_hit: true` on second call
- [ ] JWT missing → 401 response
- [ ] Query with embedded password → sanitized before embedding
- [ ] `prompt_type=GENERATE_TESTS` → response contains JUnit 5 test class
- [ ] Response time < 200ms on cache hit (Redis)
- [ ] Response time < 500ms on FAISS hit

## Edge Cases
- Empty query after sanitization → 422 Unprocessable Entity
- FAISS index empty (first run) → skip FAISS, go directly to OpenAI
- OpenAI API error → 502 with message "LLM unavailable, try again"
- Redis unavailable → skip Redis, fall through to FAISS (degrade gracefully)

## Dependencies
- `services/sanitizer.py`
- `services/faiss_service.py`
- `services/redis_service.py`
- `services/openai_service.py`
- `models/db.py` (RequestLog insert)
- `auth/jwt.py`
