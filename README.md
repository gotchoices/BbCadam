# BbCadam — Scripted CAD Framework for FreeCAD

BbCadam (Big-boy Computer Aided Design and Manufacturing) is a lightweight framework that lets you author parts and assemblies as Python scripts using a small, consistent DSL (Domain-Specific Language). It includes a GUI watcher for live rebuilds and a headless builder for CI/batch.

This concept was originally designed using Sketchup/Ruby (before Google stopped not being evil).  FreeCad was not feasible back then.  Today, functional FreeCad and AI make a rebirth of BbCad possible!

## Goals
- Provide an ergonomic DSL for common modeling tasks while allowing explicit escape to FreeCAD primitives when needed (light guardrails, not enforcement).
- Centralize build logic so GUI watcher and headless CLI behave identically.
- Encourage stable modeling practices (datum/LCS, named references) to reduce topological breakage.

## What BbCadam provides
- **Two script formats**: Abbreviated format and full Python format
- **CLI tools**: `bbcadam-build`, `bbcadam-py`, `bbcadam-launch`, `bbcadam-dump`
- **Part/assembly authoring** with context (`ctx`) including document, params, units, paths, and logging
- **A small fluent Python DSL**:
  - `box(...)` / `cylinder(...)` → `Feature`
  - `Feature.translate(...).rotate(...).add()/cut()`
  - `lcs(name, at, rot_xyz_deg)` (alias `add_lcs`)
  - Implicit add and end-of-build flush of pending features
  - Profiles/Sketches: `profile(...)` for Part-based 2D/3D profiles; `sketch(..., visible=True|False)` to materialize a Sketcher object for inspection
  - Assemblies: `component(path, as_name).at(...).rot_xyz_deg(...)`
  - Exports: `export()` resolves via param/settings or `export(['step','stl'])`
- GUI watcher macro that rebuilds on file save and exports STEP/STL (configurable).
- Headless builder that mirrors the watcher logic.
- Documentation and templates.

## Light guardrails
- The DSL is auto-exposed to part/assembly scripts. Raw FreeCAD access requires explicit imports (e.g., `import FreeCAD as App, Part`).
- Escapes are allowed and logged; CI can optionally warn.

## Installation

**From GitHub (recommended):**
```bash
pip install git+https://github.com/gotchoices/BbCadam.git
```

**From PyPI (may be available in future):**
```bash
pip install bbcadam  # Not yet published
```

**Prerequisites:**
- Python 3.10+
- FreeCAD installed and available as `FreeCADCmd` on PATH, or set `FREECAD_PATH`/`BB_FREECAD` environment variable

**Verify installation:**
```bash
bbcadam-build --help
bbcadam-launch --help
```

## Quick Start

Create a new CAD project:

```bash
mkdir myproject && cd myproject
python -m venv .venv && source .venv/bin/activate
pip install git+https://github.com/gotchoices/BbCadam.git

# Create project structure
mkdir -p specs/parts/demo build exports/{step,stl}/{parts,assemblies}

# Create your first part
cat > specs/parts/demo/demo.py <<'EOF'
def build_part(ctx):
    box(10, 20, 5).add()
EOF

# Build it
bbcadam-build specs/parts/demo/demo.py --export step stl

# Launch FreeCAD with watcher (rebuilds on save)
bbcadam-launch --project .
```

## Project Structure

BbCadam expects this directory layout in your CAD projects:

```
myproject/
├── specs/
│   ├── parts/<name>/<name>.py           # Part scripts
│   └── assemblies/<name>/<name>.py      # Assembly scripts
├── build/{parts,assemblies}/            # Generated FreeCAD files
└── exports/{step,stl}/{parts,assemblies}/  # Exported files
```

## Script Formats

### Abbreviated Format (Recommended)

Define a `build_part(ctx)` or `build_assembly(ctx)` function:

```python
def build_part(ctx):
    # Parameters from params.yaml or defaults
    width = param('width', 10)
    height = param('height', 20)
    
    # Create geometry using DSL
    box(width, height, 5).add()
    
    # Export (optional - can be done via CLI)
    export(['step', 'stl'])
```

**Usage:** `bbcadam-build mypart.py`

### Full Python Format (Standalone)

For standalone scripts with shebang:

```python
#!/usr/bin/env bbcadam-py
import bbcadam

# Direct DSL usage
box = bbcadam.box(10, 10, 10)
bbcadam.export_stl(box, "output.stl")
```

**Usage:** `bbcadam-py myscript.py` or `./myscript.py`

## DSL Overview

BbCadam provides a fluent Python DSL for common CAD operations:

- **Primitives:** `box(w,h,d)`, `cylinder(r,h)` or `cylinder(d=10,h=20)`
- **Transforms:** `.at(x,y,z)`, `.rotate(x,y,z)`, `.translate(x,y,z)`
- **Boolean ops:** `.add()`, `.cut()`, feature chaining with `feature().box().cylinder().add()`
- **2D Profiles:** `profile()` for sketching and padding/revolving/sweeping
- **Arrays:** `Feature.array(nx,sx,ny,sy)`, `Feature.radial(n,radius)`
- **Assemblies:** `component(path).at(...).rotate(...)`
- **Exports:** `export(['step','stl'])` or individual `export_step()`, `export_stl()`

## CLI Tools

- **`bbcadam-build`** - Build single part/assembly (abbreviated format)
- **`bbcadam-py`** - Run standalone Python scripts (full format)  
- **`bbcadam-launch`** - Launch FreeCAD with file watcher for live rebuilds
- **`bbcadam-dump`** - Export part geometry as JSON for debugging

## Examples

**Simple box:**
```python
def build_part(ctx):
    box(10, 20, 30).add()
```

**Parametric cylinder:**
```python
def build_part(ctx):
    diameter = param('diameter', 25.4)  # Default 1 inch
    height = param('height', 50)
    
    cylinder(d=diameter, h=height).add()
```

**2D profile with padding:**
```python
def build_part(ctx):
    profile().rectangle(50, 30).pad(10)
```

**Boolean operations:**
```python
def build_part(ctx):
    # Create base box
    box(20, 20, 10).add()
    
    # Cut hole
    cylinder(d=5, h=15).at(10, 10, -2).cut()
```

## Documentation

- **[API Reference](docs/api.md)** - Complete DSL documentation
- **[Profile Guide](docs/profile.md)** - 2D sketching and 3D operations  
- **[Development Guide](docs/development.md)** - Contributing to BbCadam

## License

MIT License - see LICENSE file for details.