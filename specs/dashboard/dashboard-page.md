# Spec: Dashboard Page

## Purpose
Landing page of the React dashboard. Shows high-level cache performance metrics as stat
cards. Auto-refreshes every 30 seconds.

## Inputs
- JWT from localStorage (injected by Axios interceptor)
- API: `GET /stats`

## Outputs
Three stat cards:
| Card             | Value Source             |
|------------------|--------------------------|
| Total Entries    | `stats.total_entries`    |
| Hit Ratio        | `stats.hit_ratio * 100`% |
| Requests Today   | `stats.total_requests`   |

Plus one summary line: "Estimated tokens saved: {stats.tokens_saved}"

## Behavior / Logic
1. On mount: fetch `GET /stats`, show loading spinner
2. Set 30-second auto-refresh interval (clear on unmount)
3. Render three `<StatCard>` components with icon + value + label
4. On 401 response → redirect to `/login`
5. On fetch error → show error banner (non-blocking)

## Acceptance Criteria
- [ ] Stat cards render correct values from `/stats`
- [ ] Loading spinner shown during fetch
- [ ] Auto-refresh updates values without full page reload
- [ ] 401 redirects to `/login`
- [ ] Token savings displayed in human-readable format (e.g., "42,300 tokens")

## Edge Cases
- All-zero stats → render zeros gracefully (no NaN, no divide-by-zero)
- Network offline → show "Unable to connect to backend" banner

## Dependencies
- `src/api/client.ts` (Axios instance)
- `src/components/StatCard.tsx`
- `specs/backend/stats-endpoint.md`
