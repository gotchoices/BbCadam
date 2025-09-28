# BbCadam — Scripted CAD Framework for FreeCAD

BbCadam is a lightweight framework that lets you author parts and assemblies as Python scripts using a small, consistent DSL. It includes a GUI watcher for live rebuilds and a headless builder for CI/batch.

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
  - Sections/Sketches: `section(...)` for Part-based profiles; `sketch(..., visible=True|False)` to materialize a Sketcher object for inspection
  - Assemblies: `component(path, as_name).at(...).rot_xyz_deg(...)`
  - Exports: `export()` resolves via param/settings or `export(['step','stl'])`
- GUI watcher macro that rebuilds on file save and exports STEP/STL (configurable).
- Headless builder that mirrors the watcher logic.
- Documentation and templates.

## Light guardrails
- The DSL is auto-exposed to part/assembly scripts. Raw FreeCAD access requires explicit imports (e.g., `import FreeCAD as App, Part`).
- Escapes are allowed and logged; CI can optionally warn.

## Project checklist (for BbCadam)
- Define API and `ctx` shape (see `api.md`).
- Implement shared builder core invoked by both watcher and headless tools.
- Implement watcher (Qt `QFileSystemWatcher`), debounce, and document lifecycle.
- Implement exports (STEP/STL) with consistent paths and settings.
- Provide templates and examples for parts and assemblies.
- Provide logging and minimal diagnostics.
- Document units, coordinate frames, and conventions.
- Optional (phase 2): dependency graph (parts→assemblies) for impacted rebuilds.

## Installation (from GitHub)

Clone and install in editable mode (recommended for development):

```bash
git clone https://github.com/gotchoices/BbCadam.git
cd BbCadam
python -m venv .venv && source .venv/bin/activate  # optional but recommended
pip install -U pip
pip install -e .
```

Prerequisites:

- Python 3.10+
- FreeCAD installed. CLI detection prefers `FreeCADCmd` on PATH; otherwise set `FREECAD_PATH` or `BB_FREECAD` to the FreeCAD installation directory.

Verify install:

```bash
bbcadam-build --help | head -n 5
bbcadam-launch --help | head -n 5
bbcadam-py --help | head -n 5
```

## Quick Start: Author parts in your own repo

Typical structure in a separate project (e.g., `myproj/`):

```
myproj/
  specs/
    parts/<name>/<name>.py           # defines build_part(ctx)
    assemblies/<name>/<name>.py      # defines build_assembly(ctx)
  build/{parts,assemblies}/          # generated
  exports/{step,stl}/{parts,assemblies}/
```

Create the structure and your first part:

```bash
mkdir -p myproj/{specs/parts/demo,build/{parts,assemblies},exports/{step,stl}/{parts,assemblies}}
cat > myproj/specs/parts/demo/demo.py <<'PY'
def build_part(ctx):
    from bbcadam import box
    box(10, 20, 5).add()
PY
```

Build headless:

```bash
bbcadam-build myproj/specs/parts/demo/demo.py --export step stl
```

Launch FreeCAD + watcher (rebuilds on save):

```bash
bbcadam-launch --project myproj
```

See `api.md` for the DSL authoring guide.

## Script Formats

### Abbreviated Format
```python
def build_part(ctx):
    # Parameters
    radius = param('radius', 10)
    
    # Create part using DSL
    box = box(radius, radius, radius)
```

**Usage**: `bbcadam-build mypart.py`

### Full Python Format (standalone)
```python
#!/usr/bin/env bbcadam-py
import bbcadam

# Direct DSL usage
box = bbcadam.box(10, 10, 10)
bbcadam.export_stl(box, "output.stl")
```

**Usage**: `bbcadam-py myscript.py` or `./myscript.py`

## Usage (conceptual)
Project structure in a dependent repo (e.g., `myproj/`):
```
myproj/
  specs/
    parts/<name>/<name>.py           # defines build_part(ctx)
    assemblies/<name>/<name>.py      # defines build_assembly(ctx)
  build/{parts,assemblies}/          # generated
  exports/{step,stl}/{parts,assemblies}/
```

Run the GUI watcher via launcher, or build headless with the wrappers:
```bash
# GUI + watcher (auto-detects FreeCAD):
bbcadam-launch --project myproj

# Abbreviated format:
bbcadam-build myproj/specs/parts/lagoon/lagoon.py

# Full Python format:
bbcadam-py myscript.py

# Interactive development:
bbcadam-launch

# Debug dump (JSON bbox/faces/edges/volume):
bbcadam-dump myproj/specs/parts/lagoon/lagoon.py
```

See `api.md` for the DSL and authoring guide, including arc input validation rules and the `sketch(visible=...)` flag.

## AI → Python promotion policy (guardrails)
- Generated scripts should include a header at the top:
  - `# model: <name>`
  - `# generated_from: <file.md>`
  - `# md_hash: <sha256>`
  - `# status: draft|frozen`
- Overwrite rules for installing generated files:
  - If target .py does not exist → install.
  - If header exists and `status: draft` → overwrite allowed.
  - Otherwise → do not overwrite; write `<name>.ai.py` alongside and exit non-zero.
- Use `BbCadam/tools/install_generated_py.sh` (Bash) to install generated scripts safely.

## Scaffolding a project (for humans or AI agents)
From an empty project folder (e.g., `myproj/`):
```bash
mkdir -p myproj/{config,specs/parts/caisson,specs/assemblies,build/{parts,assemblies},exports/{step,stl}/{parts,assemblies}}
cat > myproj/config/settings.yaml <<'YAML'
units: in
exports: { step: true, stl: true }
YAML
cat > myproj/specs/parts/caisson/caisson.md <<'MD'
# model: caisson
# generated_from: caisson.md
# md_hash: <fill>
# status: draft
MD
cat > myproj/specs/parts/caisson/caisson.py <<'PY'
def build_part(ctx):
  # placeholder script; replace via AI or edit manually
  box(size=(10,10,10)).add()
PY
```

To install a newly generated part script without clobbering human-owned files:
```bash
bash BbCadam/tools/install_generated_py.sh /tmp/caisson.generated.py myproj/specs/parts/caisson/caisson.py
```

To launch the watcher from inside the project folder:
```bash
bash ../BbCadam/tools/launch_freecad_with_watcher.sh
```



