#!/usr/bin/env bash
# Print URL from clipboard via printime (blog/article mode).
# Usage: print-url.sh
# Optional: PRINTIME_YES=1 to skip preview confirm

set -euo pipefail

URL="$(xclip -o -selection clipboard 2>/dev/null || true)"
if [[ -z "$URL" ]]; then
  echo "Copy a URL to the clipboard first." >&2
  exit 1
fi

EXTRA=()
if [[ "${PRINTIME_YES:-}" == "1" ]]; then
  EXTRA=(--yes)
else
  EXTRA=(--preview)
fi

exec printime print --url "$URL" --link-qr "${EXTRA[@]}"
