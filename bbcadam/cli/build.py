#!/usr/bin/env python3
"""
bbcadam-build: Build CAD models using abbreviated format (kwave-style).
"""

import os
import sys
import subprocess
from pathlib import Path


def find_freecad_cmd():
    """Find FreeCADCmd executable."""
    # Check common FreeCAD locations
    freecad_cmd_paths = [
        "/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd",
        "/usr/bin/freecadcmd",
        "/usr/local/bin/freecadcmd",
    ]
    
    for path in freecad_cmd_paths:
        if Path(path).exists():
            return path
    
    # Check PATH
    import shutil
    freecad_cmd = shutil.which("FreeCADCmd") or shutil.which("freecadcmd")
    if freecad_cmd:
        return freecad_cmd
    
    return None


def main():
    """Main entry point for bbcadam-build."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Build CAD models using abbreviated format (kwave-style)"
    )
    parser.add_argument(
        "scripts",
        nargs="+",
        help="Python script files to build"
    )
    parser.add_argument(
        "--project",
        help="Project root directory (default: current directory)"
    )
    parser.add_argument(
        "--build-dir",
        help="Directory for build outputs (default: build/ in project root)"
    )
    parser.add_argument(
        "--dump-json",
        help="Dump JSON debug info to file"
    )
    parser.add_argument(
        "--freecad-cmd",
        help="Path to FreeCADCmd executable"
    )
    
    args = parser.parse_args()
    
    # Determine project root
    project_root = Path(args.project) if args.project else Path.cwd()
    project_root = project_root.resolve()
    
    # Determine build directory
    if args.build_dir:
        build_dir = Path(args.build_dir).resolve()
    else:
        # Default to build/ in project root
        build_dir = project_root / "build"
    
    # Find FreeCADCmd
    freecad_cmd = args.freecad_cmd or find_freecad_cmd()
    if not freecad_cmd:
        print("Error: FreeCADCmd not found. Please install FreeCAD or specify --freecad-cmd")
        sys.exit(1)
    
    # Build command: execute an internal runner inside FreeCADCmd
    # Inject repo root into sys.path so 'import bbcadam' works inside FreeCAD's Python
    repo_root = Path(__file__).resolve().parents[2]
    runner_code = (
        f"import sys; sys.path.insert(0, {repr(str(repo_root))}); "
        f"import bbcadam.cli._runner_build as r; r.main()"
    )
    cmd = [freecad_cmd, "-c", runner_code]

    # Provide context via environment variables for runner to read
    env = os.environ.copy()
    # Avoid writing __pycache__/pyc files during builds
    env.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    env["BB_PROJECT_ROOT"] = str(project_root)
    env["BB_BUILD_DIR"] = str(build_dir)
    env["BB_SCRIPTS"] = os.pathsep.join(str(Path(s).resolve()) for s in args.scripts)
    if args.dump_json:
        env["BB_DUMP_JSON"] = str(args.dump_json)
    # Keep PYTHONPATH addition as a backup
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (str(repo_root) if not existing else f"{repo_root}{os.pathsep}{existing}")
    
    print(f"Project root: {project_root}")
    print(f"Build output: {build_dir}")
    print(f"Building with FreeCADCmd: {' '.join(cmd)}")
    
    try:
        proc = subprocess.run(cmd, check=True, env=env, capture_output=True, text=True)
        if proc.stdout:
            print(proc.stdout, end="")
        if proc.stderr:
            print(proc.stderr, end="")
    except subprocess.CalledProcessError as e:
        # Surface child process output so tests can assert on errors
        if e.stdout:
            print(e.stdout, end="")
        if e.stderr:
            print(e.stderr, end="")
        print(f"Error building: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nBuild interrupted")
        sys.exit(1)


if __name__ == "__main__":
    main()
