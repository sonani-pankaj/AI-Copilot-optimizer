# Spec: POST /review — PR / Git Diff Code Review

## Purpose
Accepts a git diff string and returns a structured AI code review identifying bugs,
performance issues, and security risks. Used by the pre-push git hook.

## Inputs
| Field          | Type   | Required | Description                            |
|----------------|--------|----------|----------------------------------------|
| diff           | string | yes      | Git diff output (max 4,000 chars)      |
| pr_title       | string | no       | PR title for additional context        |
| pr_description | string | no       | PR description for additional context  |
| Authorization  | header | yes      | Bearer JWT token                       |

## Outputs
```json
{
  "bugs": [
    { "severity": "HIGH", "category": "bug", "description": "Null pointer possible at line 42", "line_hint": "UserService.java:42" }
  ],
  "performance": [
    { "severity": "MEDIUM", "category": "performance", "description": "N+1 query in loop", "line_hint": "OrderRepository.java:78" }
  ],
  "security": [
    { "severity": "HIGH", "category": "security", "description": "SQL query built with string concatenation", "line_hint": "UserDao.java:31" }
  ],
  "summary": "2 bugs, 1 performance issue, 1 security risk found."
}
```

## Behavior / Logic
1. Extract `user_id` from JWT
2. Run `sanitizer.sanitize(diff)` — strip any secrets accidentally in diff
3. Truncate diff to 4,000 chars if longer (silent truncation)
4. Build OpenAI prompt:
   - System: "You are a senior Java code reviewer. Analyze the git diff and return JSON only."
   - System: Provide JSON schema with bugs/performance/security arrays
   - User: diff content + optional PR title/description
5. Call `gpt-4.1-mini` with `response_format: json_object`, `max_tokens=500`
6. Parse response JSON into ReviewResponse schema
7. Return parsed result (do NOT cache review results)

## Acceptance Criteria
- [ ] Diff with SQL concatenation → at least one security issue returned
- [ ] Diff with no issues → empty arrays, summary says "No issues found"
- [ ] Diff > 4000 chars → silently truncated, still returns valid response
- [ ] JWT missing → 401
- [ ] OpenAI JSON parse error → 502 with "Review service unavailable"

## Edge Cases
- Empty diff after sanitization → return empty review with summary "Empty diff provided"
- OpenAI returns malformed JSON → log error (hash only), return 502
- `pr_title` / `pr_description` combined with diff must still fit token limit

## Dependencies
- `services/sanitizer.py`
- `services/openai_service.py`
- `auth/jwt.py`
