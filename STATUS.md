# Implementation Checklist

## Current Status: Core DSL Implementation
- [x] Part-based Section DSL (formerly sketch): 2D ops (circle, rectangle, polygon, from_/to/go, arc, close); 3D ops (pad, revolve, sweep); holes; XY plane
- [x] Plane support: XZ/YZ for section.pad/revolve; sweep respects path plane and auto-aligns profile normal
- [x] Examples: mount_plate (rounded), piston (revolve), worm (sweep)
- [x] API rename: sketch() → section()
- [x] Section backend abstraction
- [x] Generic Section API with materialization flag

## Migration to Standalone Package

### Phase 1: Package Structure & Setup
- [ ] Create new package structure (bbcadam/ instead of BbCadam/)
- [ ] Create setup.py with entry points for CLI tools
- [ ] Create pyproject.toml for modern Python packaging
- [ ] Add LICENSE file
- [ ] Create bbcadam/__init__.py with proper package initialization
- [ ] Move tools/ scripts to scripts/ directory
- [ ] Create bbcadam/cli/ module for CLI entry points
- [ ] Create bbcadam-py shebang wrapper script

### Phase 2: Code Refactoring
- [ ] Refactor api.py into modules:
  - [ ] bbcadam/core/dsl_core.py (Feature, param, export)
  - [ ] bbcadam/core/profiles.py (geometry classes: lines, arcs, circles; adapters)
  - [ ] bbcadam/core/primitives.py (box, cylinder)
  - [ ] bbcadam/core/assemblies.py (component helpers)
  - [ ] bbcadam/backends/part.py (PartSectionBackend)
  - [ ] bbcadam/backends/sketcher.py (SketcherSectionBackend)
- [ ] Update all imports to use new module structure
- [ ] Create bbcadam/__init__.py to re-export public API
- [ ] Move watcher/ to bbcadam/watcher/
- [ ] Update builder.py to use new module structure

### Phase 3: CLI Integration
- [ ] Implement bbcadam/cli/launch.py (bbcadam-launch command)
- [ ] Implement bbcadam/cli/build.py (bbcadam-build command for abbreviated format)
- [ ] Implement bbcadam/cli/py_runner.py (bbcadam-py command for full Python format)
- [ ] Implement bbcadam/cli/dump.py (bbcadam-dump command)
- [ ] Test CLI entry points work after pip install
- [ ] Test both script formats work correctly

### Phase 4: Examples & Documentation
- [ ] Move kwave examples to bbcadam/examples/
- [ ] Create docs/ directory with:
  - [ ] docs/installation.md
  - [ ] docs/api.md (updated)
  - [ ] docs/examples.md
- [ ] Update README.md for standalone package
- [ ] Add docstrings to all public APIs
- [ ] Create example CAD scripts using shebang wrapper

### Phase 5: Testing & Distribution
- [ ] Create tests/ directory with unit tests
- [ ] Test installation via pip install -e .
- [ ] Test CLI commands work after installation
- [ ] Test shebang wrapper with example scripts
- [ ] Create GitHub Actions for CI/CD
- [ ] Test cross-platform compatibility (macOS, Linux, Windows)

### Phase 6: Publishing Preparation
- [ ] Add version management (__version__ in __init__.py)
- [ ] Create CHANGELOG.md
- [ ] Test PyPI upload (test.pypi.org first)
- [ ] Create GitHub releases
- [ ] Update documentation for published package

## Remaining Core Features (can be done in parallel)
- [ ] Internal geometry representation (backend‑agnostic)
  - [ ] Refactor `_SectionProfile` to store pure geometry (lines/arcs/circles as numbers), not Part edges
  - [ ] Add adapters: PartProfileAdapter, SketcherProfileAdapter
  - [ ] Update PartSectionBackend to use PartProfileAdapter
  - [ ] Implement SketcherSectionBackend using SketcherProfileAdapter (materialized=True)

- [ ] 3D Section Enhancement (post-testing)
  - [ ] Rename `section` to `profile` (more generic name)
  - [ ] Add 3D path creation directives: `profile.line3d()`, `profile.arc3d()`, `profile.helix3d()`
  - [ ] Extend sweep to work with 3D paths: `profile.sweep3d(path_profile)`
  - [ ] Add 3D coordinate support: `profile.to3d(x, y, z)`, `profile.arc3d(center, radius, start, end)`
  - [ ] Maintain backward compatibility with 2D operations
  - [ ] Document 3D vs 2D usage patterns

- [ ] LCS/Datum plane targeting
  - [x] Accept plane strings `LCS:Name`/`Datum:Name` (and object references)
  - [x] Resolve datum in `ctx.doc` and derive Placement for section plane
  - [x] Apply datum plane Placement in pad/revolve/sweep
  - [ ] TEST: Add example placing a section on a named LCS and verify placement

- [ ] Sweep orientation options
  - [ ] Add parameters: `align={'auto'|'fixed'|'frenet'}`, `up=(0,0,1)`, `use_frenet: bool`
  - [ ] Keep default `align='auto'` (current behavior: align +Z to path start tangent)
  - [ ] Document caveats (kinks, twist) and usage

- [ ] Edge selectors + chamfer
  - [ ] Add base-level `chamfer(radius, where=...)` operating on current solid
  - [ ] Add simple selectors: `outside_all`, `top_edges`, `bottom_edges`, `vertical_edges`
  - [ ] Implement for box/cylinder results (axis-aligned), document limitations

## Known Issues
- [ ] Assembly watcher focus/view: When rebuilding an assembly, FreeCAD can still switch active doc (e.g., to a part) and alter the assembly viewpoint. We mitigated part rebuilds by reusing the part document and delaying view restore, but assembly-level focus flips persist. Proper fix likely requires:
  - Avoiding opening part documents during assembly linking (load shapes directly without activating docs), or
  - Using App::Link with document path without opening the target document, or
  - A small transaction/deferred activation mechanism in the watcher to guarantee the original active doc remains active throughout the rebuild.
- [x] LCS duplication on part rebuilds fixed: `lcs()` now reuses existing objects by name.
- [x] Sketch duplication fixed: Sketcher materialization reuses an existing sketch by name and clears geometry.

## Current Priority
**Phase 1: Package Structure & Setup** - Create the foundation for a standalone package while maintaining current functionality.


## Obsolete Files Cleanup (as replacements are validated)
- [x] Remove `scripts/launch_freecad_with_watcher.sh` (replaced by `bbcadam-launch`)
- [ ] Remove `scripts/build_headless.sh` (superseded by `bbcadam-build`)
- [ ] Remove `scripts/build_headless.py` (logic migrated into `bbcadam/cli/build.py`)
- [ ] Remove `scripts/dump.sh` (superseded by `bbcadam-dump`)
- [ ] Remove `scripts/install_generated_py.sh` (no longer needed with standalone packaging)
- [ ] Decide fate of `scripts/find_freecad.sh` (either integrate into CLI or keep as dev helper)
- [x] Remove `watcher/` package-local directory (watching now handled via user project + CLI)

## Watcher Migration (port from legacy `watcher/watch_specs.py`)
- [ ] Recreate watcher as `bbcadam.watcher` (library) invoked by `bbcadam-launch`
- [ ] Env-config: honor `BB_PROJECT_ROOT`, `BB_WATCH_DIR`, `BB_BUILD_DIR`
- [ ] Directory scope:
  - If `specs/` exists, watch `specs/parts` and `specs/assemblies`
  - Else watch `BB_WATCH_DIR` (or project root)
- [ ] File types: watch `.py`, `.yaml`, `.yml`; recursive
- [ ] Debounce: coalesce rapid changes (≈250ms) before rebuild
- [ ] Rebuild rules:
  - Under `specs/parts/<part>/`: prefer `<part>.py`, else first `.py`
  - Under `specs/assemblies/<asm>/`: prefer `<asm>.py`, else first `.py`
  - Else (cwd mode): infer part vs assembly from parent folder name
- [ ] Execute rebuilds headless via `FreeCADCmd` (CLI fallback if GUI absent)
- [ ] (Later) GUI niceties: active doc + camera restore for assembly rebuilds
- [ ] Tests: simulate file changes; assert calls to build functions; debounce works

