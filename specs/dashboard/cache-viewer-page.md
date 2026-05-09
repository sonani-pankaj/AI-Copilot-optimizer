# Spec: Cache Viewer Page

## Purpose
Displays all stored cache entries in a paginated, filterable table. Allows team leads
to inspect what is cached and filter by user or team.

## Inputs
- JWT from localStorage
- API: `GET /cache?page=1&limit=20&user_id=&team_id=`
- Filter inputs: `user_id` (text), `team_id` (text)

## Outputs
Table with columns:
| Column       | Source                      |
|--------------|-----------------------------|
| Query (50ch) | `entry.query` (truncated)   |
| Response     | `entry.response` (truncated)|
| User         | `entry.user_id`             |
| Team         | `entry.team_id`             |
| Tokens Saved | `entry.tokens_saved`        |
| Cached At    | `entry.created_at` (locale) |

## Behavior / Logic
1. On mount: fetch `GET /cache?page=1&limit=20`
2. Filter inputs are debounced (300ms) before triggering new fetch
3. Pagination: Previous / Next buttons; show "Page X of Y"
4. Clicking a row expands full query + response in a modal
5. On 401 → redirect to `/login`

## Acceptance Criteria
- [ ] Table renders all 6 columns
- [ ] Filter by user_id returns only that user's entries
- [ ] Pagination navigates correctly
- [ ] Row click opens modal with full query/response text
- [ ] Empty state shows "No cache entries found"

## Edge Cases
- Response text > 500 chars → truncated in table, full text in modal
- user_id or team_id filter with no matches → show empty state message

## Dependencies
- `src/api/client.ts`
- `specs/backend/upsert-endpoint.md` (cache_entries data shape)
