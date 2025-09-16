"""
Test BbCadam package imports and basic functionality
"""
import pytest


def test_bbcadam_import():
    """Test that bbcadam package can be imported"""
    import bbcadam
    assert hasattr(bbcadam, '__version__')
    # Should not crash even without FreeCAD
    # When FreeCAD is not available, __all__ should be empty
    assert isinstance(bbcadam.__all__, list)


def test_cli_module_import():
    """Test that CLI modules can be imported"""
    from bbcadam.cli import launch, build, py_runner, dump
    assert hasattr(launch, 'main')
    assert hasattr(build, 'main')
    assert hasattr(py_runner, 'main')
    assert hasattr(dump, 'main')


def test_cli_functions_callable():
    """Test that CLI main functions are callable"""
    from bbcadam.cli import launch, build, py_runner, dump
    
    # These should be callable functions
    assert callable(launch.main)
    assert callable(build.main)
    assert callable(py_runner.main)
    assert callable(dump.main)


def test_package_metadata():
    """Test that package has required metadata"""
    import bbcadam
    
    # Check for version
    assert hasattr(bbcadam, '__version__')
    assert bbcadam.__version__ is not None
    
    # Check for package info
    assert hasattr(bbcadam, '__name__')
    assert bbcadam.__name__ == 'bbcadam'
