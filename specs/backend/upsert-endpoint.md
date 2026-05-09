# Spec: POST /upsert — Store Cache Entry

## Purpose
Stores a query-response pair into FAISS (vector), Postgres (metadata), and Redis (hot cache).
Called internally after an OpenAI fallback response or externally to seed the cache.

## Inputs
| Field       | Type   | Required | Description                          |
|-------------|--------|----------|--------------------------------------|
| query       | string | yes      | Original (sanitized) query           |
| response    | string | yes      | AI-generated or curated response     |
| tokens_saved| int    | no       | Estimated tokens saved (default: 0)  |
| model_used  | string | no       | Model tag (default: "gpt-4.1-mini")  |
| Authorization| header| yes      | Bearer JWT token                     |

## Outputs
```json
{
  "id": "uuid",
  "query_hash": "sha256hex",
  "message": "Stored successfully"
}
```

## Behavior / Logic
1. Extract `user_id`, `team_id` from JWT
2. Run `sanitizer.sanitize(query)` — always sanitize even if called internally
3. Compute `query_hash = SHA256(sanitized_query)`
4. Check Postgres: if `query_hash` already exists → return existing entry (idempotent)
5. Embed `sanitized_query` → unit-normalized vector
6. Add vector to FAISS index with monotonic integer ID
7. Insert row to `cache_entries` (id, user_id, team_id, query_hash, query, response, tokens_saved, model_used)
8. Call `faiss_service.save()` to persist index to `./data/faiss.index`
9. Store in Redis: `SET query_hash response EX 86400` (24h TTL)
10. Return `{id, query_hash, message}`

## Acceptance Criteria
- [ ] Duplicate query_hash → returns existing entry, no duplicate DB row
- [ ] FAISS index file updated on disk after each upsert
- [ ] Redis key set with 24h TTL
- [ ] Sanitizer called even on internal upsert calls
- [ ] JWT missing → 401

## Edge Cases
- Postgres insert fails → rollback, do NOT write to FAISS or Redis
- FAISS index write fails → return 500, do NOT mark as success
- Very long response (>10k chars) → truncate to 10k before storing

## Dependencies
- `services/sanitizer.py`
- `services/faiss_service.py`
- `services/redis_service.py`
- `models/db.py` (CacheEntry insert)
- `auth/jwt.py`
