#!/bin/bash

set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "Usage: $(basename "$0") <generated_src.py> <target_py>" >&2
  exit 2
fi

SRC="$1"
DST="$2"

if [[ ! -f "$SRC" ]]; then
  echo "[bbcadam] Source not found: $SRC" >&2
  exit 1
fi

mkdir -p "$(dirname "$DST")"

if [[ ! -f "$DST" ]]; then
  cp "$SRC" "$DST"
  echo "[bbcadam] Installed new script: $DST"
  exit 0
fi

# Parse simplified status header (first 40 lines): '# status: <value>'
STATUS_LINE="$(head -n 40 "$DST" | grep -i '^# *status:')" || true
STATUS="$(echo "$STATUS_LINE" | cut -d: -f2- | xargs | tr '[:upper:]' '[:lower:]')"

if [[ "$STATUS" == draft* ]]; then
  cp "$SRC" "$DST"
  echo "[bbcadam] Overwrote draft script: $DST"
  exit 0
fi

ALT="${DST%.py}.ai.py"
cp "$SRC" "$ALT"
echo "[bbcadam] Target protected (status=${STATUS:-unknown}). Wrote: $ALT" >&2
exit 3


