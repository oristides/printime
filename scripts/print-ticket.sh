#!/usr/bin/env bash
# Print ticket PDF from clipboard path via printime.
# Usage: print-ticket.sh
# Copy a file path (or path as text) to clipboard first.

set -euo pipefail

PDF="$(xclip -o -selection clipboard 2>/dev/null | tr -d '\n' || true)"
if [[ -z "$PDF" || ! -f "$PDF" ]]; then
  echo "Copy a ticket PDF file path to the clipboard first." >&2
  exit 1
fi

EXTRA=()
if [[ "${PRINTIME_YES:-}" == "1" ]]; then
  EXTRA=(--yes)
else
  EXTRA=(--preview)
fi

exec printime print --ticket "$PDF" "${EXTRA[@]}"
