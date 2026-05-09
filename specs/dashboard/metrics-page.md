# Spec: Metrics Page

## Purpose
Time-series visualization of cache usage and token savings using Recharts.
Gives teams insight into usage trends over time.

## Inputs
- JWT from localStorage
- API: `GET /stats/history?days=30`
- Day range selector: 7 / 14 / 30 days

## Outputs
Two Recharts charts:
1. **Line chart** — Requests vs Cache Hits per day
2. **Bar chart** — Tokens Saved per day

## Behavior / Logic
1. On mount and on range change: fetch `/stats/history?days={selectedDays}`
2. Transform API response into Recharts `data` array format
3. Line chart: two lines — `requests` (blue) and `cache_hits` (green)
4. Bar chart: single bar — `tokens_saved` (orange)
5. Both charts share the same X-axis (date string)
6. Show loading skeleton while fetching

## Acceptance Criteria
- [ ] Line chart renders two distinct lines with legend
- [ ] Bar chart renders tokens saved with correct values
- [ ] Day range selector (7/14/30) triggers new fetch and re-renders
- [ ] Tooltips show exact values on hover
- [ ] Empty data → charts show "No data for selected period" text

## Edge Cases
- All-zero data → charts render flat lines at zero (not blank)
- Single data point → charts still render (no crash)

## Dependencies
- `src/api/client.ts`
- `recharts` library
- `specs/backend/stats-endpoint.md` (history response shape)
