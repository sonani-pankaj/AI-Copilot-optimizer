#!/usr/bin/env bash
# See: specs/git-hooks/pre-push-review.md
# Installs pre-push hook into the current repository's .git/hooks directory.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOK_SRC="$SCRIPT_DIR/pre-push.sh"
HOOK_DEST="$(git rev-parse --show-toplevel)/.git/hooks/pre-push"

if [ ! -f "$HOOK_SRC" ]; then
  echo "ERROR: pre-push.sh not found at $HOOK_SRC" >&2
  exit 1
fi

cp "$HOOK_SRC" "$HOOK_DEST"
chmod +x "$HOOK_DEST"

echo "✓ pre-push hook installed at $HOOK_DEST"
