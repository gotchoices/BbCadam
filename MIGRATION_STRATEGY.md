# BbCadam Migration to Standalone Package

## Current State
BbCadam is currently tightly coupled with the kwave project for development and testing. It's a FreeCAD-based scripting framework that provides a DSL for parametric CAD design.

## Target State
A standalone, pip-installable Python package that provides:
- CLI tools for FreeCAD integration
- Python library for CAD scripting
- Clean separation from any specific project

## Migration Strategy

### 1. Package Structure
```
bbcadam/                          # Main package (renamed from BbCadam)
├── setup.py                      # Package definition with entry points
├── pyproject.toml                # Modern Python packaging
├── README.md                     # Package documentation
├── LICENSE                       # License file
├── bbcadam/                      # Python package
│   ├── __init__.py              # Package initialization
│   ├── api.py                   # Core DSL API
│   ├── builder.py               # Build system
│   ├── core/                    # Core modules
│   │   ├── __init__.py
│   │   ├── dsl_core.py          # Feature, param, export
│   │   ├── profiles.py          # Geometry classes and adapters
│   │   ├── primitives.py        # box, cylinder, etc.
│   │   └── assemblies.py        # component helpers
│   ├── backends/                # Section backends
│   │   ├── __init__.py
│   │   ├── part.py              # PartSectionBackend
│   │   └── sketcher.py          # SketcherSectionBackend
│   ├── cli/                     # CLI tools
│   │   ├── __init__.py
│   │   ├── launch.py            # Launch FreeCAD with watcher
│   │   ├── build.py             # Headless build
│   │   ├── dump.py              # Debug dump
│   │   └── runner.py            # Shebang wrapper
│   └── watcher/                 # File watching system
│       ├── __init__.py
│       └── watch_specs.py
├── scripts/                     # Executable scripts
│   ├── bbcadam-launch           # CLI entry point
│   ├── bbcadam-build            # CLI entry point
│   ├── bbcadam-dump             # CLI entry point
│   └── bbcadam-runner           # Shebang wrapper
├── examples/                    # Example projects
│   ├── mount_plate/
│   ├── piston/
│   └── worm/
└── docs/                        # Documentation
    ├── api.md
    ├── examples.md
    └── installation.md
```

### 2. CLI Integration Strategy

**Entry Points (setup.py):**
```python
entry_points={
    'console_scripts': [
        'bbcadam-launch=bbcadam.cli.launch:main',
        'bbcadam-build=bbcadam.cli.build:main',
        'bbcadam-py=bbcadam.cli.py_runner:main',
        'bbcadam-dump=bbcadam.cli.dump:main',
    ],
}
```

**Two Script Formats:**

**1. Abbreviated Format (`bbcadam-build`):**
- Supports current kwave-style scripts with `build_part(ctx)` function
- Build system injects DSL functions and calls `build_part(ctx)`
- Backward compatible with existing part scripts

**2. Full Python Format (`bbcadam-py`):**
- Direct Python execution with shebang support
- Scripts can use `#!/usr/bin/env bbcadam-py`
- Direct DSL usage: `import bbcadam; box = bbcadam.box(10, 10, 10)`

### 3. Installation Methods

**Primary: pip install**
```bash
pip install bbcadam
bbcadam-launch                    # Launch FreeCAD with watcher
bbcadam-build mypart.py          # Headless build
```

**Secondary: Development install**
```bash
git clone https://github.com/user/bbcadam
cd bbcadam
pip install -e .
```

**Alternative: pipx (npx equivalent)**
```bash
pipx install bbcadam
pipx run bbcadam mypart.py
```

### 4. Usage Patterns

**CLI Usage:**
```bash
# Interactive development
bbcadam-launch

# Abbreviated format (kwave-style)
bbcadam-build mypart.py

# Full Python format
bbcadam-py mypart.py

# Debug dump
bbcadam-dump mypart.py
```

**Script Usage:**

**Abbreviated Format:**
```python
def build_part(ctx):
    # Parameters
    radius = param('radius', 10)
    
    # Create part using DSL
    box = box(radius, radius, radius)
```

**Full Python Format:**
```python
#!/usr/bin/env bbcadam-py
import bbcadam

# Your CAD code here
part = bbcadam.box(10, 10, 10)
bbcadam.export_stl(part, "output.stl")
```

**Library Usage:**
```python
import bbcadam
# Use in other Python scripts
```

### 5. Dependencies

**Required:**
- FreeCAD (user-provided, not packaged)
- Python 3.7+

**Optional:**
- watchdog (for file watching)
- pyyaml (for YAML parameter files)

### 6. Documentation Strategy

**Package Documentation:**
- README.md: Quick start, installation, basic usage
- docs/installation.md: Detailed installation instructions
- docs/api.md: Complete API reference
- docs/examples.md: Tutorial examples

**Code Documentation:**
- Docstrings for all public APIs
- Type hints where appropriate
- Inline comments for complex logic

### 7. Testing Strategy

**Unit Tests:**
- Test individual DSL functions
- Mock FreeCAD dependencies where possible
- Test CLI entry points

**Integration Tests:**
- Test with real FreeCAD installation
- Test example projects
- Test cross-platform compatibility

**CI/CD:**
- GitHub Actions for testing
- Automated PyPI publishing
- Documentation generation

### 8. Versioning & Distribution

**Versioning:**
- Semantic versioning (semver)
- Version in setup.py and __init__.py

**Distribution:**
- PyPI package
- GitHub releases
- Source distribution (sdist)
- Wheel distribution (bdist_wheel)

### 9. Migration Benefits

**For Users:**
- Easy installation via pip
- Standard Python package management
- CLI tools in PATH
- Shebang support for CAD scripts

**For Development:**
- Clean separation from kwave
- Standard Python project structure
- Better testing and CI/CD
- Easier contribution and maintenance

**For Distribution:**
- Professional package presentation
- Standard installation methods
- Version management
- Dependency handling
