# BbCadam — Scripted CAD Framework for FreeCAD

BbCadam is a lightweight framework that lets you author parts and assemblies as Python scripts using a small, consistent DSL. It includes a GUI watcher for live rebuilds and a headless builder for CI/batch. Projects (like `kwave`) depend on BbCadam but keep their own specs, parameters, and outputs.

## Goals
- Provide an ergonomic DSL for common modeling tasks while allowing explicit escape to FreeCAD primitives when needed (light guardrails, not enforcement).
- Centralize build logic so GUI watcher and headless CLI behave identically.
- Encourage stable modeling practices (datum/LCS, named references) to reduce topological breakage.

## What BbCadam provides
- Part/assembly authoring contract and context (`ctx`) with document, params, units, paths, and logging.
- A small fluent Python DSL:
  - `box(...)` / `cylinder(...)` → `Feature`
  - `Feature.translate(...).rotate(...).add()/cut()`
  - `lcs(name, at, rot_xyz_deg)` (alias `add_lcs`)
  - Implicit add and end-of-build flush of pending features
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

## Usage (conceptual)
Project structure in a dependent repo (e.g., `kwave/`):
```
kwave/
  specs/
    parts/<name>/<name>.py           # defines build_part(ctx)
    assemblies/<name>/<name>.py      # defines build_assembly(ctx)
  build/{parts,assemblies}/          # generated
  exports/{step,stl}/{parts,assemblies}/
```

Run the GUI watcher via launcher, or build headless with `FreeCADCmd` calling the shared builder.

See `api.md` for the DSL and authoring guide.

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
From an empty project folder (e.g., `kwave/`):
```bash
mkdir -p kwave/{config,specs/parts/caisson,specs/assemblies,build/{parts,assemblies},exports/{step,stl}/{parts,assemblies}}
cat > kwave/config/settings.yaml <<'YAML'
units: in
exports: { step: true, stl: true }
YAML
cat > kwave/specs/parts/caisson/caisson.md <<'MD'
# model: caisson
# generated_from: caisson.md
# md_hash: <fill>
# status: draft
MD
cat > kwave/specs/parts/caisson/caisson.py <<'PY'
def build_part(ctx):
  # placeholder script; replace via AI or edit manually
  box(size=(10,10,10)).add()
PY
```

To install a newly generated part script without clobbering human-owned files:
```bash
bash BbCadam/tools/install_generated_py.sh /tmp/caisson.generated.py kwave/specs/parts/caisson/caisson.py
```

To launch the watcher from inside the project folder:
```bash
bash ../BbCadam/tools/launch_freecad_with_watcher.sh
```



