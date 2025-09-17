#!/usr/bin/env python3
"""
preview_test: Launch FreeCAD GUI to preview the part built by a given test file.

Usage:
  python tests/preview_test.py tests/test_sketch_arcs_pad.py

This extracts the `build_part(ctx)` function from the provided file, writes a
minimal abbreviated script into build/preview/, and starts FreeCAD to build and
display the part. Files persist for debugging.

Notes:
- To visualize the Sketcher object, ensure your script uses sketch(..., visible=True).
- This does not run under pytest and is intended for manual inspection only.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path


def _find_freecad_gui() -> str | None:
    candidates = [
        "/Applications/FreeCAD.app/Contents/MacOS/FreeCAD",
        "/Applications/FreeCAD.app/Contents/Resources/bin/FreeCAD",
        "/usr/bin/freecad",
        "/usr/local/bin/freecad",
    ]
    for p in candidates:
        if Path(p).exists():
            return p
    # PATH lookup
    import shutil
    exe = shutil.which("FreeCAD") or shutil.which("freecad")
    return exe


def _extract_build_part(fn: Path) -> str:
    text = fn.read_text(encoding="utf-8", errors="ignore")
    # Find the first top-level def build_part(ctx): block
    m = re.search(r"^def\s+build_part\s*\(ctx\)\s*:\n([\s\S]*?)\n(?=def\s|if\s+__name__|\Z)", text, re.M)
    if not m:
        raise SystemExit(f"No build_part(ctx) found in {fn}")
    body = m.group(0)
    return body


def main() -> None:
    parser = argparse.ArgumentParser(description="Preview a test's build_part in FreeCAD GUI")
    parser.add_argument("file", help="Path to a test file containing build_part(ctx)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging in FreeCAD Report view")
    args = parser.parse_args()

    src_path = Path(args.file).resolve()
    if not src_path.exists():
        raise SystemExit(f"File not found: {src_path}")

    repo_root = Path(__file__).resolve().parents[1]
    freecad = _find_freecad_gui()
    if not freecad:
        raise SystemExit("FreeCAD GUI not found. Please install FreeCAD or add it to PATH.")

    build_part_src = _extract_build_part(src_path)

    # Persistent preview directory so FreeCAD can load files reliably
    preview_dir = (repo_root / "build" / "preview").resolve()
    preview_dir.mkdir(parents=True, exist_ok=True)
    script_py = preview_dir / "preview_part.py"
    runner_py = preview_dir / "runner_preview.py"

    script_py.write_text(build_part_src)

    lines = []
    lines.append("import sys, traceback\n")
    lines.append(f"sys.path.insert(0, {repr(str(repo_root))})\n")
    lines.append("from pathlib import Path\n")
    lines.append("import FreeCAD as App\n")
    lines.append("\n")
    lines.append("try:\n")
    lines.append("    from bbcadam.builder import build_part_script\n")
    lines.append(f"    App.Console.PrintMessage('[preview] repo_root: {str(repo_root)}\\n')\n")
    lines.append(f"    App.Console.PrintMessage('[preview] script: {str(script_py)}\\n')\n")
    lines.append(f"    build_part_script(Path({repr(str(repo_root))}), Path({repr(str(script_py))}))\n")
    lines.append("    try:\n")
    lines.append("        import FreeCADGui as Gui\n")
    lines.append("        for d in App.listDocuments().values():\n")
    lines.append("            try:\n")
    lines.append("                Gui.activateDocument(d.Name)\n")
    lines.append("                v = Gui.ActiveDocument.ActiveView\n")
    lines.append("                if v: v.viewAxonometric(); v.fitAll()\n")
    lines.append("                break\n")
    lines.append("            except Exception:\n")
    lines.append("                pass\n")
    lines.append("    except Exception:\n")
    lines.append("        pass\n")
    lines.append("except Exception as e:\n")
    lines.append("    App.Console.PrintError('[preview] ERROR: %s\\n' % e)\n")
    lines.append("    App.Console.PrintError(traceback.format_exc())\n")

    runner_py.write_text(''.join(lines))

    env = os.environ.copy()
    cmd = [freecad, str(runner_py)]
    print(f"Launching FreeCAD GUI: {' '.join(cmd)}")
    print(f"[preview] runner: {runner_py}")
    print(f"[preview] script: {script_py}")
    try:
        subprocess.Popen(cmd, env=env)
    except Exception as e:
        raise SystemExit(f"Failed to launch FreeCAD: {e}")


if __name__ == "__main__":
    main()


