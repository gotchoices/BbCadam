#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FINDER="$SCRIPT_DIR/find_freecad.sh"

usage() {
  echo "Usage: $0 [--project PATH] [--dump-json PATH] <spec.py> [more ...]"
}

CLI="${FREECAD_CMD:-}"
PROJECT=""
DUMP=""

args=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) shift; PROJECT="${1:-}" ;;
    --dump-json) shift; DUMP="${1:-}" ;;
    -h|--help) usage; exit 0 ;;
    *) args+=("$1") ;;
  esac
  shift || true
done

if [[ -z "$CLI" ]]; then
  if [[ -x "$FINDER" ]]; then
    eval "$("$FINDER")"
    if [[ -n "${CLI:-}" ]]; then CLI="$CLI"; fi
  fi
fi

if [[ -z "$CLI" ]]; then
  echo "FreeCADCmd not found. Set FREECAD_CMD or install FreeCADCmd in PATH." >&2
  exit 1
fi

# Build python exec string to run our script with sys.argv
py_argv=("BbCadam/tools/build_headless.py")
if [[ -n "$PROJECT" ]]; then py_argv+=("--project" "$PROJECT"); fi
if [[ -n "$DUMP" ]]; then py_argv+=("--dump-json" "$DUMP"); fi
py_argv+=("${args[@]}")

# Escape argv to Python list literal
py_list="["
for a in "${py_argv[@]}"; do
  # escape backslashes and quotes
  esc="${a//\\/\\\\}"
  esc="${esc//\"/\\\"}"
  py_list+="\"$esc\"," 

done
py_list+="]"

py="import sys, runpy; sys.argv=$py_list; runpy.run_path(\"$SCRIPT_DIR/build_headless.py\", run_name='__main__')"

cmd=("$CLI" -P "$REPO_ROOT" -c "$py")

echo "Running: ${cmd[*]}"
"${cmd[@]}"


