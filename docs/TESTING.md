# Testing Guide for BbCadam

This document explains how to set up, run, and contribute to the BbCadam test suite.

## Overview

BbCadam uses **pytest** as its testing framework, similar to how Node.js projects use Mocha. The test suite verifies that our DSL creates expected geometric results and that CLI tools work correctly.

## Quick Start

### 1. Set Up Testing Environment

```bash
# Create virtual environment (recommended)
python3 -m venv test_env
source test_env/bin/activate

# Install BbCadam in development mode
pip install -e .

# Install testing dependencies
pip install pytest pytest-cov pytest-mock
```

### 2. Run Tests

```bash
# Run all tests (equivalent to 'npm test')
pytest

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=bbcadam

# Run specific test file
pytest tests/test_cli.py
```

## Test Structure

```
tests/
├── conftest.py              # pytest configuration and fixtures
├── test_imports.py          # Package import tests
├── test_cli.py              # CLI command tests
├── test_dsl.py              # DSL function tests
├── integration/
│   └── test_headless_build.py  # Full pipeline tests
└── fixtures/
    ├── sample_parts/        # Sample scripts for testing
    └── expected_outputs/    # Expected results
```

## Test Categories

### 1. Unit Tests
- **`test_imports.py`** - Verify package can be imported and basic functionality
- **`test_cli.py`** - Test CLI commands work correctly
- **`test_dsl.py`** - Test individual DSL functions (requires FreeCAD)

### 2. Integration Tests
- **`test_headless_build.py`** - Test full build pipeline
- **`test_watcher.py`** - Test file watching functionality

### 3. Fixtures
- **`sample_parts/`** - Sample part scripts for testing
- **`expected_outputs/`** - Expected output files for verification

## Testing Strategy

### 1. JSON Export for Verification
We export shapes to JSON format containing:
- Bounding box (min/max coordinates)
- Volume, area, face/edge/vertex counts
- Center of mass
- Solid/closed properties
- Surface sampling points

### 2. Property-Based Testing
Tests verify geometric properties rather than exact shape matching:
- Volume calculations
- Face/edge/vertex counts
- Bounding box dimensions
- Solid/closed properties

### 3. CLI Testing
Tests verify command-line tools work correctly:
- Exit codes
- Output format
- File generation
- Error handling

## Test Fixtures

### `freecad_available`
Checks if FreeCAD is available for testing. Tests are skipped if FreeCAD is not installed.

```python
def test_box_creation(freecad_available):
    if not freecad_available:
        pytest.skip("FreeCAD not available")
    # Test implementation
```

### `temp_dir`
Creates a temporary directory for test files. Automatically cleaned up after tests.

```python
def test_script_execution(temp_dir):
    script = temp_dir / "test.py"
    script.write_text("def build_part(ctx): pass")
    # Test implementation
```

## Running Tests

### Basic Commands

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_cli.py

# Run specific test function
pytest tests/test_cli.py::test_cli_commands_available

# Run tests matching a pattern
pytest -k "cli"

# Run with coverage
pytest --cov=bbcadam

# Run integration tests only
pytest -m integration
```

### Test Markers

Tests can be marked for different categories:

```python
@pytest.mark.integration
def test_full_build_pipeline():
    """Test complete build process"""
    pass

@pytest.mark.slow
def test_large_assembly():
    """Test with large assembly"""
    pass

@pytest.mark.freecad
def test_dsl_function():
    """Test DSL function requiring FreeCAD"""
    pass
```

Run marked tests:
```bash
pytest -m integration    # Run integration tests
pytest -m "not slow"     # Skip slow tests
pytest -m freecad        # Run FreeCAD-dependent tests
```

## Example Test Patterns

### CLI Test Example

```python
def test_bbcadam_build_help():
    """Test bbcadam-build help output"""
    result = subprocess.run(['bbcadam-build', '--help'], 
                          capture_output=True, text=True)
    assert result.returncode == 0
    assert 'Build CAD models using abbreviated format' in result.stdout
    assert '--project' in result.stdout
```

### DSL Test Example

```python
def test_box_creation(freecad_available, temp_dir):
    """Test box creation with JSON export"""
    if not freecad_available:
        pytest.skip("FreeCAD not available")
    
    # Create test script
    script = temp_dir / "test_box.py"
    script.write_text("""
import bbcadam
box = bbcadam.box(10, 20, 30)
data = bbcadam.export_json(box)
print(data)
""")
    
    # Run script
    result = subprocess.run(['bbcadam-py', str(script)], 
                          capture_output=True, text=True)
    assert result.returncode == 0
    
    # Verify JSON output
    import json
    data = json.loads(result.stdout)
    assert data['volume'] == 6000  # 10 * 20 * 30
    assert data['faces'] == 6
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.9
    - name: Install dependencies
      run: |
        pip install -e .[dev]
    - name: Run tests
      run: pytest --cov=bbcadam
```

## Troubleshooting

### Common Issues

**1. FreeCAD Not Available**
```
SKIPPED (FreeCAD not available)
```
- This is expected when FreeCAD is not installed
- Tests marked with `@pytest.mark.freecad` will be skipped
- Install FreeCAD to run full test suite

**2. Import Errors**
```
ModuleNotFoundError: No module named 'bbcadam'
```
- Make sure you're in the virtual environment: `source test_env/bin/activate`
- Install in development mode: `pip install -e .`

**3. CLI Commands Not Found**
```
command not found: bbcadam-launch
```
- Ensure virtual environment is activated
- Verify package installation: `pip list | grep bbcadam`

### Debug Mode

```bash
# Run tests with debug output
pytest -v -s

# Run single test with debug
pytest tests/test_cli.py::test_cli_commands_available -v -s

# Drop into debugger on failure
pytest --pdb
```

## Contributing

### Adding New Tests

1. **Follow naming conventions**: `test_*.py` files, `test_*` functions
2. **Use appropriate fixtures**: `freecad_available`, `temp_dir`
3. **Add docstrings**: Explain what the test verifies
4. **Include both positive and negative cases**
5. **Update this guide** if adding new test categories

### Test Quality Guidelines

- **Fast**: Unit tests should run quickly
- **Isolated**: Tests shouldn't depend on each other
- **Deterministic**: Tests should produce consistent results
- **Clear**: Test names and assertions should be self-documenting

## Performance Testing

For performance-critical code:

```python
@pytest.mark.slow
def test_large_assembly_performance():
    """Test performance with large assembly"""
    import time
    start = time.time()
    # Create large assembly
    end = time.time()
    assert (end - start) < 10.0  # Should complete in under 10 seconds
```

## Future Enhancements

1. **Cross-platform testing** - Test on macOS, Linux, Windows
2. **Performance benchmarking** - Track build times and memory usage
3. **Visual regression testing** - Screenshot comparison for GUI elements
4. **Stress testing** - Large assemblies and complex geometries
5. **Property-based testing** - Use hypothesis for random input testing

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [Python Testing Best Practices](https://docs.python.org/3/library/unittest.html)
- [FreeCAD Python API](https://wiki.freecad.org/Python_scripting_tutorial)
