#!/bin/bash

set -euo pipefail

os_name="$(uname -s)"

found_gui=""
found_cli=""

if [[ "$os_name" == "Darwin" ]]; then
  # macOS defaults
  [[ -x "/Applications/FreeCAD.app/Contents/MacOS/FreeCAD" ]] && found_gui="/Applications/FreeCAD.app/Contents/MacOS/FreeCAD"
  # Some builds install the CLI under Resources/bin as 'freecadcmd'
  if [[ -x "/Applications/FreeCAD.app/Contents/MacOS/FreeCADCmd" ]]; then
    found_cli="/Applications/FreeCAD.app/Contents/MacOS/FreeCADCmd"
  elif [[ -x "/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd" ]]; then
    found_cli="/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd"
  fi
  # Also allow GUI fallback in Resources/bin
  if [[ -z "$found_gui" && -x "/Applications/FreeCAD.app/Contents/Resources/bin/freecad" ]]; then
    found_gui="/Applications/FreeCAD.app/Contents/Resources/bin/freecad"
  fi
fi

# Fallback to PATH
command -v FreeCAD >/dev/null 2>&1 && found_gui="${found_gui:-$(command -v FreeCAD)}"
command -v FreeCADCmd >/dev/null 2>&1 && found_cli="${found_cli:-$(command -v FreeCADCmd)}"

echo "GUI=${found_gui}"
echo "CLI=${found_cli}"

if [[ -z "$found_gui" && -z "$found_cli" ]]; then
  exit 1
fi


