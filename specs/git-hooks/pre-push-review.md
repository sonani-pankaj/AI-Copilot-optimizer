# Spec: Git Hook — pre-push Review

## Purpose
Intercepts every `git push`, captures the diff of commits being pushed, sends it to the
`/review` endpoint, and prints a structured review to the terminal. Non-blocking: push
proceeds regardless of review findings.

## Inputs
| Source         | Value                                    |
|----------------|------------------------------------------|
| git            | `git diff origin/HEAD HEAD --unified=3`  |
| env            | `AI_OPTIMIZER_JWT` — Bearer token        |
| env            | `AI_OPTIMIZER_URL` — backend URL (default: http://localhost:8000) |

## Outputs
Terminal output format:
```
═══════════════════════════════════════════
  AI Copilot Optimizer — Pre-Push Review
═══════════════════════════════════════════
🐛 BUGS (2)
  [HIGH]   UserService.java:42 — Null pointer possible
  [MEDIUM] OrderService.java:15 — Unhandled exception

⚡ PERFORMANCE (1)
  [MEDIUM] OrderRepository.java:78 — N+1 query detected

🔐 SECURITY (1)
  [HIGH]   UserDao.java:31 — SQL string concatenation

Summary: 2 bugs, 1 performance, 1 security issue found.
═══════════════════════════════════════════
```

## Behavior / Logic
1. Get current diff: `git diff origin/$(git rev-parse --abbrev-ref HEAD) HEAD --unified=3`
2. Truncate diff to 4000 chars
3. If diff is empty → print "No changes to review." and exit 0
4. If `AI_OPTIMIZER_JWT` not set → print warning and exit 0 (non-blocking)
5. POST diff to `{AI_OPTIMIZER_URL}/review` with `Authorization: Bearer {JWT}`
6. Parse JSON response
7. Print formatted output to stderr (so it appears in terminal without affecting git)
8. Always `exit 0` — hook NEVER blocks the push

## Acceptance Criteria
- [ ] Empty diff → skips review, push proceeds normally
- [ ] Missing JWT → prints warning, push proceeds
- [ ] Backend offline → prints "Review skipped: backend unreachable", push proceeds
- [ ] Review result printed before git push output
- [ ] Exit code always 0

## Edge Cases
- `curl` not available → fall back to `python3 -c "import urllib..."` or skip
- Backend returns non-200 → print "Review failed: HTTP {status}" and continue

## Dependencies
- `scripts/install-hooks.sh` (installs this hook)
- `specs/backend/review-endpoint.md`
