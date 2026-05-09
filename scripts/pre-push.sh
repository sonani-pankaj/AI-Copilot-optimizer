#!/usr/bin/env bash
# See: specs/git-hooks/pre-push-review.md
# Sends the staged diff to the AI Copilot Optimizer /review endpoint before push.
# Always exits 0 (advisory only — does not block the push).

BACKEND_URL="${AI_OPTIMIZER_BACKEND:-http://localhost:8000}"
JWT_TOKEN="${AI_OPTIMIZER_JWT:-}"
MAX_DIFF=4000

if [ -z "$JWT_TOKEN" ]; then
  echo "[ai-optimizer] AI_OPTIMIZER_JWT not set — skipping pre-push review."
  exit 0
fi

# Collect diff against the remote tracking branch (HEAD~1 as fallback)
REMOTE="$1"
URL="$2"
DIFF=$(git diff HEAD~1 --unified=3 2>/dev/null | head -c "$MAX_DIFF" || echo "")

if [ -z "$DIFF" ]; then
  echo "[ai-optimizer] No diff found — skipping review."
  exit 0
fi

echo "[ai-optimizer] Sending diff to backend for AI review…"

RESPONSE=$(curl -s -w "\n%{http_code}" \
  -X POST "$BACKEND_URL/review" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d "$(printf '{"diff": %s}' "$(echo "$DIFF" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')" )" \
  2>/dev/null)

HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)

if [ "$HTTP_CODE" != "200" ]; then
  echo "[ai-optimizer] Review request failed (HTTP $HTTP_CODE) — continuing push."
  exit 0
fi

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║       AI Copilot Optimizer — Review      ║"
echo "╚══════════════════════════════════════════╝"
echo "$BODY" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print('Summary:', data.get('summary', 'N/A'))
    for sev in ('security', 'bugs', 'performance'):
        issues = data.get(sev, [])
        if issues:
            print(f'\n{sev.upper()}:')
            for i in issues:
                print(f'  [{i.get(\"severity\",\"?\")}] {i.get(\"description\",\"\")}')
except Exception as e:
    print('Could not parse review response:', e)
" 2>/dev/null || echo "$BODY"

echo ""

# Always allow the push
exit 0
