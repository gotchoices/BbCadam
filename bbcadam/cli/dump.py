#!/usr/bin/env python3
"""
bbcadam-dump: Dump debug information about CAD models.
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
    """Main entry point for bbcadam-dump."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Dump debug information about CAD models"
    )
    parser.add_argument(
        "script",
        help="Python script file to analyze"
    )
    parser.add_argument(
        "--project",
        help="Project root directory (default: current directory)"
    )
    parser.add_argument(
        "--output",
        help="Output file for debug information (default: stdout)"
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
    
    # Find FreeCADCmd
    freecad_cmd = args.freecad_cmd or find_freecad_cmd()
    if not freecad_cmd:
        print("Error: FreeCADCmd not found. Please install FreeCAD or specify --freecad-cmd")
        sys.exit(1)
    
    # Create temporary output file if not specified
    import tempfile
    if args.output:
        output_path = Path(args.output)
    else:
        output_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        output_path = Path(output_file.name)
        output_file.close()
    
    # Build command to execute script with debug dump
    cmd = [freecad_cmd, "--project", str(project_root), "--dump-json", str(output_path), str(script_path)]
    
    print(f"Project root: {project_root}")
    print(f"Dumping debug info for: {script_path}")
    
    try:
        subprocess.run(cmd, check=True)
        
        # If no output file specified, print to stdout
        if not args.output:
            with open(output_path, 'r') as f:
                print(f.read())
            output_path.unlink()  # Clean up temp file
        else:
            print(f"Debug info saved to: {output_path}")
            
    except subprocess.CalledProcessError as e:
        print(f"Error dumping debug info: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nDump interrupted")
        sys.exit(1)


if __name__ == "__main__":
    main()
