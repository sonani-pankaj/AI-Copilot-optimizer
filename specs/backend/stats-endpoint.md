# Spec: GET /stats — Metrics Aggregation

## Purpose
Returns aggregate statistics for the dashboard: cache performance, token savings, and
per-user/team breakdowns. Also exposes a time-series history endpoint for charts.

## Inputs
### GET /stats
| Field        | Type   | Required | Description                        |
|--------------|--------|----------|------------------------------------|
| Authorization| header | yes      | Bearer JWT token                   |
| team_id      | query  | no       | Filter by team (admin only)        |

### GET /stats/history
| Field        | Type   | Required | Description                           |
|--------------|--------|----------|---------------------------------------|
| Authorization| header | yes      | Bearer JWT token                      |
| days         | query  | no       | Number of days back (default: 30)     |

## Outputs
### GET /stats
```json
{
  "total_entries": 142,
  "total_requests": 891,
  "cache_hits": 734,
  "cache_misses": 157,
  "hit_ratio": 0.823,
  "tokens_saved": 42300
}
```

### GET /stats/history
```json
[
  { "date": "2026-05-01", "requests": 45, "cache_hits": 38, "tokens_saved": 1140 },
  { "date": "2026-05-02", "requests": 61, "cache_hits": 50, "tokens_saved": 1500 }
]
```

## Behavior / Logic
1. Extract `user_id`, `team_id` from JWT
2. Scope queries to `user_id` (personal stats) OR `team_id` if provided and user belongs to team
3. `total_entries` = COUNT from `cache_entries` for scope
4. `total_requests` = COUNT from `request_logs` for scope
5. `cache_hits` = COUNT from `request_logs` WHERE `cache_hit = true`
6. `cache_misses` = `total_requests - cache_hits`
7. `hit_ratio` = `cache_hits / total_requests` (0.0 if total_requests = 0)
8. `tokens_saved` = SUM of `tokens_saved` from `cache_entries` for scope
9. History: GROUP BY DATE(created_at) for last N days, fill missing days with zeros

## Acceptance Criteria
- [ ] Returns 0-values gracefully when no data exists
- [ ] `hit_ratio` never causes division by zero
- [ ] History endpoint returns one entry per day (no gaps)
- [ ] Scoping by user_id works (user A cannot see user B's stats)
- [ ] JWT missing → 401

## Edge Cases
- No entries yet → return all zeros
- `days=0` → return empty history array
- `days > 365` → cap at 365

## Dependencies
- `models/db.py` (CacheEntry, RequestLog queries)
- `auth/jwt.py`
