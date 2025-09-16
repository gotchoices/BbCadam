"""Internal runner executed inside FreeCADCmd to build scripts.

Reads context from environment variables:
- BB_PROJECT_ROOT
- BB_BUILD_DIR
- BB_SCRIPTS (os.pathsep-separated list of script paths)
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path


def _classify(py_path: Path) -> str:
    try:
        text = py_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return "part"
    if re.search(r"def\s+build_assembly\s*\(", text):
        return "assembly"
    if re.search(r"def\s+build_part\s*\(", text):
        return "part"
    return "part"


def main() -> None:
    from bbcadam.builder import build_part_script, build_assembly_script

    project_root = Path(os.environ.get("BB_PROJECT_ROOT", ".")).resolve()
    build_dir = Path(os.environ.get("BB_BUILD_DIR", project_root / "build")).resolve()
    scripts_env = os.environ.get("BB_SCRIPTS", "")
    if not scripts_env:
        print("[bbcadam] No scripts specified (BB_SCRIPTS empty)")
        sys.exit(2)

    scripts = [Path(p) for p in scripts_env.split(os.pathsep) if p]

    status = 0
    for script in scripts:
        kind = _classify(script)
        try:
            if kind == "assembly":
                print(f"[bbcadam] Running build_assembly_script: {script}")
                build_assembly_script(project_root, script)
            else:
                print(f"[bbcadam] Running build_part_script: {script}")
                build_part_script(project_root, script)
        except Exception as exc:
            status = 1
            import traceback
            print(f"[bbcadam] Build failed for {script}: {exc}\n{traceback.format_exc()}", file=sys.stderr)

    sys.exit(status)


if __name__ == "__main__":
    main()


