#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

usage() {
  echo "Usage: $0 <spec.py> [--project PATH] [--out PATH]"
}

SPEC=""
PROJECT=""
OUT=""

args=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) shift; PROJECT="${1:-}" ;;
    --out) shift; OUT="${1:-}" ;;
    -h|--help) usage; exit 0 ;;
    *) args+=("$1") ;;
  esac
  shift || true
done

if [[ ${#args[@]} -lt 1 ]]; then usage; exit 2; fi
SPEC="${args[0]}"

# Default project root: walk up to 'specs' folder
if [[ -z "$PROJECT" ]]; then
  start="$(cd "$(dirname "$SPEC")" && pwd)"
  cur="$start"
  for i in 1 2 3 4 5; do
    if [[ -d "$cur/specs" ]]; then PROJECT="$cur"; break; fi
    parent="$(cd "$cur/.." && pwd)"
    [[ "$parent" == "$cur" ]] && break
    cur="$parent"
  done
  [[ -z "$PROJECT" ]] && PROJECT="$start"
fi

# Default output path: <repo>/kwave/build/debug/<name>.json
if [[ -z "$OUT" ]]; then
  base="$(basename "$SPEC" .py)"
  OUT="$PROJECT/build/debug/${base}.json"
fi

mkdir -p "$(dirname "$OUT")"

bash "$SCRIPT_DIR/build_headless.sh" --project "$PROJECT" --dump-json "$OUT" "$SPEC"

echo "$OUT"

