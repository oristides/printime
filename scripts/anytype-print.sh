#!/usr/bin/env bash
# Print an Anytype page by title via printime.
# Usage:
#   anytype-print.sh "I am 021er"
#   anytype-print.sh                    # uses page title from clipboard
# Bind to Ctrl+Shift+P in your desktop environment.

set -euo pipefail

TITLE="${1:-$(xclip -o -selection clipboard 2>/dev/null || true)}"
if [[ -z "$TITLE" ]]; then
  echo "Usage: $0 \"Page title\"" >&2
  echo "   or copy the page title and run without arguments" >&2
  exit 1
fi

EXTRA=()
if [[ "${PRINTIME_YES:-}" == "1" ]]; then
  EXTRA=(--yes)
else
  EXTRA=(--preview)
fi

exec printime anytype print "$TITLE" "${EXTRA[@]}"
