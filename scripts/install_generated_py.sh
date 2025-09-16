#!/bin/bash

set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "Usage: $(basename "$0") <generated_src.py> <target_py>" >&2
  exit 2
fi

SRC="$1"
DST="$2"

update_hash() {
  local TARGET="$1"
  # Look for header like: '# AI-generated from <path>; hash: ...'
  local HEADER
  HEADER="$(head -n 40 "$TARGET" | grep -i '^# *AI-generated from .*; *hash:')" || return 0
  # Extract md path (could be relative)
  local MDREL
  MDREL="$(echo "$HEADER" | sed -E 's/^# *AI-generated from[[:space:]]+([^;]+);.*$/\1/i')"
  # Resolve path relative to target dir if not absolute
  local MDPATH
  if [[ "$MDREL" = /* ]]; then
    MDPATH="$MDREL"
  else
    MDPATH="$(dirname "$TARGET")/$MDREL"
  fi
  if [[ -f "$MDPATH" ]]; then
    local HASH
    HASH="$(shasum -a 256 "$MDPATH" | awk '{print $1}')"
    # Replace hash value in the header within the first 40 lines
    local TMP
    TMP="$(mktemp)"
    sed -E "1,40{s|^(# *AI-generated from[^;]*;[[:space:]]*hash:).*$|\\1 ${HASH}|;}" "$TARGET" > "$TMP" && mv "$TMP" "$TARGET"
  fi
}

if [[ ! -f "$SRC" ]]; then
  echo "[bbcadam] Source not found: $SRC" >&2
  exit 1
fi

mkdir -p "$(dirname "$DST")"

if [[ ! -f "$DST" ]]; then
  cp "$SRC" "$DST"
  update_hash "$DST"
  echo "[bbcadam] Installed new script: $DST"
  exit 0
fi

# Parse simplified status header (first 40 lines): '# status: <value>'
STATUS_LINE="$(head -n 40 "$DST" | grep -i '^# *status:')" || true
STATUS="$(echo "$STATUS_LINE" | cut -d: -f2- | xargs | tr '[:upper:]' '[:lower:]')"

if [[ "$STATUS" == draft* ]]; then
  cp "$SRC" "$DST"
  update_hash "$DST"
  echo "[bbcadam] Overwrote draft script: $DST"
  exit 0
fi

ALT="${DST%.py}.ai.py"
cp "$SRC" "$ALT"
update_hash "$ALT"
echo "[bbcadam] Target protected (status=${STATUS:-unknown}). Wrote: $ALT" >&2
exit 3


