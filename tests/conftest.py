"""
pytest configuration and fixtures for BbCadam tests
"""
import pytest
import tempfile
import shutil
from pathlib import Path


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
