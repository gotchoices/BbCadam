#!/usr/bin/env python3
"""
bbcadam-launch: Launch FreeCAD with file watcher for interactive development.
"""

import sys
import os
import platform
import shutil
import subprocess
from pathlib import Path


def find_freecad() -> str | None:
    """Find FreeCAD GUI executable with robust, cross-platform heuristics.

    Mirrors legacy finder behavior while preferring standard install paths.
    """
    # 1) Respect explicit env var if provided
    for env_var in ("FREECAD_PATH", "FREECAD_GUI"):
        candidate = os.environ.get(env_var)
        if candidate and Path(candidate).exists():
            return candidate

    system_name = platform.system()

    candidates: list[str] = []

    if system_name == "Darwin":
        # macOS common locations
        candidates.extend([
            "/Applications/FreeCAD.app/Contents/MacOS/FreeCAD",
            "/Applications/FreeCAD.app/Contents/Resources/bin/FreeCAD",
            "/Applications/FreeCAD.app/Contents/Resources/bin/freecad",
        ])
    else:
        # Generic Unix-like
        candidates.extend([
            "/usr/bin/FreeCAD",
            "/usr/local/bin/FreeCAD",
            "/usr/bin/freecad",
            "/usr/local/bin/freecad",
        ])

    # 2) Known path candidates
    for path in candidates:
        if Path(path).exists():
            return path

    # 3) PATH lookup (both casings)
    for exe in ("FreeCAD", "freecad"):
        resolved = shutil.which(exe)
        if resolved:
            return resolved

    return None


def main():
    """Main entry point for bbcadam-launch."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Launch FreeCAD with file watcher for interactive development"
    )
    parser.add_argument(
        "--project", 
        help="Project root directory to watch (default: current directory)"
    )
    parser.add_argument(
        "--watch-dir",
        help="Directory to watch for changes (default: specs/ in project root)"
    )
    parser.add_argument(
        "--build-dir",
        help="Directory for build outputs (default: build/ in project root)"
    )
    parser.add_argument(
        "--freecad-path",
        help="Path to FreeCAD executable"
    )
    # Watch is the default behavior now; --no-watch disables
    parser.add_argument(
        "--no-watch",
        action="store_true",
        help="Disable watching (default: watch enabled)"
    )
    parser.add_argument(
        "--watch-verbose",
        action="store_true",
        help="Verbose watcher logging (file events and decisions)"
    )
    
    args = parser.parse_args()
    
    # Determine project root
    project_root = Path(args.project) if args.project else Path.cwd()
    project_root = project_root.resolve()
    
    # Determine watch directory
    if args.watch_dir:
        watch_dir = Path(args.watch_dir).resolve()
    else:
        # Default to specs/ in project root, or project root if no specs/
        specs_dir = project_root / "specs"
        watch_dir = specs_dir if specs_dir.exists() else project_root
    
    # Determine build directory
    if args.build_dir:
        build_dir = Path(args.build_dir).resolve()
    else:
        # Default to build/ in project root
        build_dir = project_root / "build"
    
    # Find FreeCAD
    freecad_path = args.freecad_path or find_freecad()
    if not freecad_path:
        print("Error: FreeCAD not found. Please install FreeCAD or specify --freecad-path")
        sys.exit(1)
    
    # Prepare environment for FreeCAD (GUI watcher reads these)
    env = os.environ.copy()
    env["BB_PROJECT_ROOT"] = str(project_root)
    env["BB_WATCH_DIR"] = str(watch_dir)
    env["BB_BUILD_DIR"] = str(build_dir)
    if args.watch_verbose:
        env["BB_WATCH_VERBOSE"] = "1"

    # Build command: do not pass custom flags FreeCAD doesn't understand
    cmd = [freecad_path]

    print(f"Project root: {project_root}")
    print(f"Watching: {watch_dir}")
    print(f"Build output: {build_dir}")
    print(f"Launching FreeCAD: {' '.join(cmd)}")

    try:
        # Start the internal GUI watcher by passing the watcher script file to FreeCAD (foreground)
        if not args.no_watch:
            watcher_path = Path(__file__).resolve().parents[1] / "watcher.py"
            cmd.append(str(watcher_path))
            subprocess.run(cmd, env=env, check=False)
            return

        # No watcher: launch FreeCAD detached and exit
        subprocess.Popen(cmd, env=env)
        return
    except Exception as e:
        print(f"Error launching FreeCAD: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
