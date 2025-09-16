#!/usr/bin/env python3
"""
bbcadam-py: Execute full Python format CAD scripts.
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
    """Main entry point for bbcadam-py."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Execute full Python format CAD scripts"
    )
    parser.add_argument(
        "script",
        help="Python script file to execute"
    )
    parser.add_argument(
        "--project",
        help="Project root directory (default: current directory)"
    )
    parser.add_argument(
        "--output-dir",
        help="Directory for output files (default: current directory)"
    )
    parser.add_argument(
        "--freecad-cmd",
        help="Path to FreeCADCmd executable"
    )
    
    args = parser.parse_args()
    
    # Check if script exists
    script_path = Path(args.script)
    if not script_path.exists():
        print(f"Error: Script not found: {script_path}")
        sys.exit(1)
    
    # Determine project root
    project_root = Path(args.project) if args.project else Path.cwd()
    project_root = project_root.resolve()
    
    # Determine output directory
    if args.output_dir:
        output_dir = Path(args.output_dir).resolve()
    else:
        # Default to current directory
        output_dir = Path.cwd()
    
    # Find FreeCADCmd
    freecad_cmd = args.freecad_cmd or find_freecad_cmd()
    if not freecad_cmd:
        print("Error: FreeCADCmd not found. Please install FreeCAD or specify --freecad-cmd")
        sys.exit(1)
    
    # Read script content
    try:
        with open(script_path, 'r') as f:
            script_content = f.read()
    except Exception as e:
        print(f"Error reading script: {e}")
        sys.exit(1)
    
    # Build command to execute script with FreeCADCmd
    cmd = [freecad_cmd, "--project", str(project_root), "--output-dir", str(output_dir), "-c", script_content]
    
    print(f"Project root: {project_root}")
    print(f"Output directory: {output_dir}")
    print(f"Executing script with FreeCADCmd: {script_path}")
    
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error executing script: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nExecution interrupted")
        sys.exit(1)


if __name__ == "__main__":
    main()
