"""
Test BbCadam CLI commands
"""
import pytest
import subprocess
import tempfile
import os


def test_cli_commands_available():
    """Test that all CLI commands are installed and accessible"""
    commands = ['bbcadam-launch', 'bbcadam-build', 'bbcadam-py', 'bbcadam-dump']
    for cmd in commands:
        result = subprocess.run([cmd, '--help'], capture_output=True, text=True)
        assert result.returncode == 0, f"Command {cmd} failed with return code {result.returncode}"
        assert 'usage:' in result.stdout, f"Command {cmd} help output missing usage"


def test_bbcadam_launch_help():
    """Test bbcadam-launch help output"""
    result = subprocess.run(['bbcadam-launch', '--help'], capture_output=True, text=True)
    assert result.returncode == 0
    assert 'Launch FreeCAD with file watcher' in result.stdout
    assert '--project' in result.stdout
    assert '--watch-dir' in result.stdout
    assert '--build-dir' in result.stdout
    assert '--freecad-path' in result.stdout


def test_bbcadam_build_help():
    """Test bbcadam-build help output"""
    result = subprocess.run(['bbcadam-build', '--help'], capture_output=True, text=True)
    assert result.returncode == 0
    assert 'Build CAD models using abbreviated format' in result.stdout
    assert '--project' in result.stdout
    assert '--build-dir' in result.stdout
    assert '--dump-json' in result.stdout


def test_bbcadam_py_help():
    """Test bbcadam-py help output"""
    result = subprocess.run(['bbcadam-py', '--help'], capture_output=True, text=True)
    assert result.returncode == 0
    assert 'Execute full Python format CAD scripts' in result.stdout
    assert '--project' in result.stdout
    assert '--output-dir' in result.stdout


def test_bbcadam_dump_help():
    """Test bbcadam-dump help output"""
    result = subprocess.run(['bbcadam-dump', '--help'], capture_output=True, text=True)
    assert result.returncode == 0
    assert 'Dump debug information' in result.stdout
    assert '--project' in result.stdout
    assert '--output' in result.stdout


def test_bbcadam_dump_without_freecad():
    """Test bbcadam-dump command without FreeCAD (should fail gracefully)"""
    # Create a simple test script
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("""
def build_part(ctx):
    # Simple test script
    pass
""")
        script_path = f.name
    
    try:
        result = subprocess.run([
            'bbcadam-dump', script_path
        ], capture_output=True, text=True)
        
        # Should fail because FreeCAD is not available, but command should exist
        assert result.returncode != 0  # Should fail without FreeCAD
        # But the command itself should be found and executed
        assert 'bbcadam-dump' not in result.stderr  # Command not found error
    finally:
        os.unlink(script_path)
