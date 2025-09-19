"""
pytest configuration and fixtures for BbCadam tests
"""
import pytest
import tempfile
import shutil
from pathlib import Path
import inspect
import textwrap
import subprocess
import os
import uuid
_REPO_ROOT = Path(__file__).resolve().parents[1]


def _resolve_work_dir(work_dir: Path | None) -> Path:
    """Choose a safe temp work dir under tests/build/tmp when work_dir is root/unspecified.

    We keep artifacts under tests/build/ so preview_clean can remove them.
    """
    if work_dir is None or work_dir == _REPO_ROOT:
        base = _REPO_ROOT / "tests" / "build" / "tmp"
        base.mkdir(parents=True, exist_ok=True)
        # Create a unique subfolder for this invocation
        wd = base / f"run_{uuid.uuid4().hex[:8]}"
        wd.mkdir(parents=True, exist_ok=True)
        return wd
    work_dir.mkdir(parents=True, exist_ok=True)
    return work_dir


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def freecad_available():
    """Check if FreeCAD is available for testing"""
    try:
        import FreeCAD
        return True
    except ImportError:
        pytest.skip("FreeCAD not available")


@pytest.fixture
def sample_box():
    """Create a sample box for testing"""
    # This will be implemented when we have the DSL working
    # For now, just return None
    return None


def run_abbrev_script_and_load_json(source_py: str, work_dir: Path) -> dict:
    """Helper to run an abbreviated DSL script via bbcadam-build and return JSON.

    - Writes the provided source to a temp .py under work_dir
    - Invokes bbcadam-build on it
    - Reads the sibling .json file and returns parsed JSON
    """
    work_dir = _resolve_work_dir(work_dir)
    script = work_dir / "script.py"
    script.write_text(source_py)
    result = subprocess.run(["bbcadam-build", str(script)], capture_output=True, text=True, cwd=str(work_dir))
    if result.returncode != 0:
        raise AssertionError(f"bbcadam-build failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
    out_path = script.with_suffix('.json')
    if not out_path.exists():
        raise AssertionError(f"Expected JSON not found: {out_path}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
    import json
    return json.loads(out_path.read_text())


def run_build_part_callable(build_part_fn, work_dir: Path) -> dict:
    """Write a temporary abbreviated script from a build_part(ctx) function and return JSON.

    The original function remains assertion-free. We wrap it to emit export('json').
    """
    src = textwrap.dedent(inspect.getsource(build_part_fn))
    # Rename original to avoid clobbering, then define wrapper build_part
    if src.lstrip().startswith("def build_part("):
        src = src.replace("def build_part(", "def _orig_build_part(", 1)
    wrapper = textwrap.dedent(
        f"""
        from pathlib import Path
        def build_part(ctx):
            _orig_build_part(ctx)
            import bbcadam
            out = Path(__file__).with_suffix('.json')
            bbcadam.export('json', to=str(out))
        """
    )
    full = src + "\n" + wrapper
    work_dir = _resolve_work_dir(work_dir)
    script = work_dir / "script.py"
    script.write_text(full)
    result = subprocess.run(["bbcadam-build", str(script)], capture_output=True, text=True, cwd=str(work_dir))
    if result.returncode != 0:
        raise AssertionError(f"bbcadam-build failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
    out_path = script.with_suffix('.json')
    if not out_path.exists():
        raise AssertionError(f"Expected JSON not found: {out_path}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
    import json
    return json.loads(out_path.read_text())


def run_abbrev_script_expect_failure(source_py: str, work_dir: Path, expect_substr: str) -> None:
    """Run an abbreviated DSL script expecting failure; assert message appears.

    - Writes the provided source to a temp .py under a safe tmp dir
    - Invokes bbcadam-build on it
    - Asserts non-zero return code and error text contains expect_substr
    """
    work_dir = _resolve_work_dir(work_dir)
    script = work_dir / "script.py"
    script.write_text(source_py)
    result = subprocess.run(["bbcadam-build", str(script)], capture_output=True, text=True, cwd=str(work_dir))
    assert result.returncode != 0, "Expected bbcadam-build to fail"
    combined = (result.stdout or "") + "\n" + (result.stderr or "")
    assert expect_substr in combined, f"Expected '{expect_substr}' in output; got:\n{combined}"
