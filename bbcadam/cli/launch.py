#!/usr/bin/env python3
"""
bbcadam-launch: Launch FreeCAD with file watcher for interactive development.
"""

import sys
import subprocess
from pathlib import Path


def find_freecad():
    """Find FreeCAD executable."""
    # Check common FreeCAD locations
    freecad_paths = [
        "/Applications/FreeCAD.app/Contents/Resources/bin/FreeCAD",
        "/usr/bin/freecad",
        "/usr/local/bin/freecad",
    ]
    
    for path in freecad_paths:
        if Path(path).exists():
            return path
    
    # Check PATH
    import shutil
    freecad_cmd = shutil.which("FreeCAD")
    if freecad_cmd:
        return freecad_cmd
    
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
    
    # Build command
    cmd = [freecad_path]
    
    # Add project arguments
    cmd.extend(["--project", str(project_root)])
    cmd.extend(["--watch-dir", str(watch_dir)])
    cmd.extend(["--build-dir", str(build_dir)])
    
    print(f"Project root: {project_root}")
    print(f"Watching: {watch_dir}")
    print(f"Build output: {build_dir}")
    print(f"Launching FreeCAD: {' '.join(cmd)}")
    
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error launching FreeCAD: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        sys.exit(0)


if __name__ == "__main__":
    main()
