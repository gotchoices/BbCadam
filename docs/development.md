# BbCadam Development Guide

This guide covers contributing to BbCadam framework development.

There are two main development scenarios:

1. **Framework Development**: Modifying BbCadam source code and running its test suite
2. **Testing Changes**: Using your modified BbCadam in actual CAD projects

## Framework Development Setup

For editing BbCadam source code and running framework tests:

```bash
git clone https://github.com/gotchoices/BbCadam.git
cd BbCadam
python -m venv .venv && source .venv/bin/activate
pip install -U pip
pip install -e .
```

This creates a virtual environment **inside the BbCadam repository** for framework development. Use this environment to:
- Edit BbCadam source code (`bbcadam/core/`, `bbcadam/backends/`, etc.)
- Run the framework test suite
- Debug framework internals

## Testing Changes in Real CAD Projects

After modifying BbCadam source code, test your changes in actual CAD projects:

```bash
# In your CAD project directory (separate from BbCadam repo)
cd /path/to/myproject
source .venv/bin/activate  # Project's own venv
pip install -e /path/to/BbCadam  # Link to your development version

# Now your project uses your modified BbCadam
bbcadam-build specs/parts/mypart/mypart.py
```

This creates a **separate environment** for your CAD project that links to your modified BbCadam source. Use this to:
- Test framework changes with real parts/assemblies
- Verify new DSL features work as expected
- Debug issues in actual usage scenarios

The `-e` flag creates a live link, so changes to BbCadam source immediately affect your project without reinstalling.

**Typical workflow:**
1. Edit BbCadam source in framework environment
2. Run framework tests: `cd BbCadam && source .venv/bin/activate && pytest`
3. Test with real project: `cd myproject && source .venv/bin/activate && bbcadam-build ...`
4. Iterate between steps 1-3 until satisfied

**Note:** Use `deactivate` to exit any active venv before switching environments.

## Running Tests

```bash
source .venv/bin/activate
pytest tests/
```

## Project Structure

- `bbcadam/` - Main package source
  - `core/` - Core DSL functionality
  - `backends/` - FreeCAD backend implementations
  - `cli/` - Command-line tools
- `tests/` - Test suite
- `docs/` - Documentation
- `scripts/` - Utility scripts

## Development Workflow

1. Create feature branch
2. Make changes with tests
3. Run test suite
4. Update documentation
5. Submit pull request

## Architecture Overview

See `docs/STATUS.md` for current implementation status and `docs/MIGRATION_STRATEGY.md` for the refactoring approach.

## Prerequisites for Development

- Python 3.10+
- FreeCAD installed (for running tests)
- Git

## Contributing

- Follow existing code style
- Add tests for new features
- Update documentation
- Check that all tests pass before submitting
