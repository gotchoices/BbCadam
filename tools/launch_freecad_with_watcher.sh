#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT_DEFAULT="$(cd "$SCRIPT_DIR/../.." && pwd)"
# Watcher lives inside the BbCadam package next to this script
WATCHER="$(cd "$SCRIPT_DIR/.." && pwd)/watcher/watch_specs.py"

usage() {
  echo "Usage: $0 [--freecad PATH_TO_GUI] [--project PATH] [--dry-run]"
  echo "  Launch FreeCAD and run the BbCadam watcher."
}

FREECAD_GUI="${FREECAD_GUI:-}"
PROJECT_ROOT="${PROJECT_ROOT:-$PWD}"
DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --freecad)
      shift; FREECAD_GUI="${1:-}" ;;
    --project)
      shift; PROJECT_ROOT="${1:-}" ;;
    --dry-run)
      DRY_RUN=1 ;;
    -h|--help)
      usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage; exit 2 ;;
  esac
  shift || true
done

# Validate watcher path
if [[ ! -f "$WATCHER" ]]; then
  echo "Watcher not found: $WATCHER" >&2; exit 1
fi

if [[ -z "$FREECAD_GUI" ]]; then
  # Try finder script (supports macOS and PATH)
  FC_FIND="$(cd "$SCRIPT_DIR" && pwd)/find_freecad.sh"
  if [[ -x "$FC_FIND" ]]; then
    eval "$($FC_FIND)"
    if [[ -n "${GUI:-}" ]]; then FREECAD_GUI="$GUI"; fi
  fi
  # Fallback to default macOS app
  if [[ -z "$FREECAD_GUI" && -x "/Applications/FreeCAD.app/Contents/MacOS/FreeCAD" ]]; then
    FREECAD_GUI="/Applications/FreeCAD.app/Contents/MacOS/FreeCAD"
  fi
fi

if [[ -z "$FREECAD_GUI" ]]; then
  echo "Provide --freecad /path/to/FreeCAD" >&2; exit 1
fi

echo "Using FreeCAD GUI: $FREECAD_GUI"
echo "Launching watcher: $WATCHER"

# Ensure UTF-8
if [[ "${LANG:-}" == "" || "$LANG" == "C" ]]; then export LANG=en_US.UTF-8; fi
if [[ "${LC_ALL:-}" == "" || "$LC_ALL" == "C" ]]; then export LC_ALL=en_US.UTF-8; fi

if [[ "$DRY_RUN" == "1" ]]; then exit 0; fi

BB_PROJECT_ROOT="$PROJECT_ROOT" "$FREECAD_GUI" "$WATCHER" & disown
echo "FreeCAD started. Watching under project: $PROJECT_ROOT"


