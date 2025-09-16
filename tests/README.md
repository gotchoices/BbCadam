# BbCadam Test Suite

This directory contains the test suite for BbCadam, a FreeCAD-based scripting framework for parametric CAD design.

## Testing Strategy

### Overview
We use **pytest** as our primary testing framework, similar to Mocha for Node.js applications. The test suite verifies that our DSL creates the expected geometric results and that CLI tools work correctly.

### Test Categories

#### 1. Unit Tests (`test_*.py`)
- **`test_dsl.py`** - Test individual DSL functions (box, cylinder, section operations)
- **`test_cli.py`** - Test CLI commands (bbcadam-launch, bbcadam-build, bbcadam-py, bbcadam-dump)

#### 2. Integration Tests (`integration/`)
- **`test_headless_build.py`** - Test full headless build pipeline (both abbreviated and full Python formats)
- **`test_watcher.py`** - Test file watching and auto-rebuild functionality

#### 3. Fixtures (`fixtures/`)
- **`sample_parts/`** - Sample part scripts (both abbreviated and full Python formats)
- **`expected_outputs/`** - Expected output files for verification

### Testing Approach

#### 1. JSON Export for Verification
We export shapes to JSON format containing:
- Bounding box (min/max coordinates)
- Volume, area, face/edge/vertex counts
- Center of mass
- Solid/closed properties
- Surface sampling points

#### 2. Property-Based Testing
Tests verify geometric properties rather than exact shape matching:
- Volume calculations
- Face/edge/vertex counts
- Bounding box dimensions
- Solid/closed properties

#### 3. CLI Testing
Tests verify command-line tools work correctly:
- Exit codes
- Output format
- File generation
- Error handling

### Running Tests

#### Prerequisites
```bash
pip install pytest pytest-cov pytest-mock
```

#### Basic Usage
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=bbcadam

# Run specific test file
pytest tests/test_dsl.py

# Run specific test
pytest tests/test_dsl.py::test_box_creation

# Run integration tests
pytest -m integration
```

#### Test Configuration
- **`conftest.py`** - pytest configuration and fixtures
- **`pytest.ini`** - pytest settings and markers

### Test Fixtures

#### `freecad_available`
Checks if FreeCAD is available for testing. Tests are skipped if FreeCAD is not installed.

#### `temp_dir`
Creates a temporary directory for test files. Automatically cleaned up after tests.

#### `sample_box`
Creates a sample box shape for testing (when implemented).

### Example Test Structure

**Abbreviated Format Test:**
```python
def test_abbreviated_box_creation(freecad_available, temp_dir):
    """Test abbreviated format box creation"""
    if not freecad_available:
        pytest.skip("FreeCAD not available")
    
    # Create abbreviated format script
    script = temp_dir / "test_part.py"
    script.write_text("""
def build_part(ctx):
    box = box(10, 20, 30)
""")
    
    # Run bbcadam-build
    result = subprocess.run(['bbcadam-build', str(script)], 
                          capture_output=True, text=True)
    assert result.returncode == 0
```

**Full Python Format Test:**
```python
def test_full_python_box_creation(freecad_available, temp_dir):
    """Test full Python format box creation"""
    if not freecad_available:
        pytest.skip("FreeCAD not available")
    
    # Create full Python format script
    script = temp_dir / "test_script.py"
    script.write_text("""
import bbcadam
box = bbcadam.box(10, 20, 30)
data = bbcadam.export_json(box)
""")
    
    # Run bbcadam-py
    result = subprocess.run(['bbcadam-py', str(script)], 
                          capture_output=True, text=True)
    assert result.returncode == 0
```

### Future Enhancements

1. **Cross-platform testing** - Test on macOS, Linux, Windows
2. **Performance testing** - Benchmark build times and memory usage
3. **Regression testing** - Compare outputs across versions
4. **Visual testing** - Screenshot comparison for GUI elements
5. **Stress testing** - Large assemblies and complex geometries

### Contributing

When adding new tests:
1. Follow the existing naming conventions
2. Use appropriate fixtures
3. Add docstrings explaining what the test verifies
4. Include both positive and negative test cases
5. Update this README if adding new test categories
