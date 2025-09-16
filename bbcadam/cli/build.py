#!/usr/bin/env python3
"""
bbcadam-build: Build CAD models using abbreviated format (kwave-style).
"""

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
    
    # Build command
    cmd = [freecad_cmd]
    
    # Add project arguments
    cmd.extend(["--project", str(project_root)])
    cmd.extend(["--build-dir", str(build_dir)])
    
    # Add dump-json argument if provided
    if args.dump_json:
        cmd.extend(["--dump-json", args.dump_json])
    
    # Add script files
    cmd.extend(args.scripts)
    
    print(f"Project root: {project_root}")
    print(f"Build output: {build_dir}")
    print(f"Building with FreeCADCmd: {' '.join(cmd)}")
    
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error building: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nBuild interrupted")
        sys.exit(1)


if __name__ == "__main__":
    main()
