# Implementation Checklist (current approach and next steps)

- [x] Part-based Section DSL (formerly sketch): 2D ops (circle, rectangle, polygon, from_/to/go, arc, close); 3D ops (pad, revolve, sweep); holes; XY plane
- [x] Plane support: XZ/YZ for section.pad/revolve; sweep respects path plane and auto-aligns profile normal
- [x] Examples: mount_plate (rounded), piston (revolve), worm (sweep)

- [x] API rename: sketch() → section()
  - [x] Rename public API in code (BbCadam/api.py) and remove `sketch` symbol (kept as warning fallback)
  - [x] Update builder injection (inject `section` instead of `sketch`)
  - [x] Update examples (mount_plate.py, piston.py, worm.py) to call `section`
  - [x] Update docs (`api.md` and README) to use `section`

- [x] Section backend abstraction
  - [x] Define SectionBackend interface (pad/revolve/sweep)
  - [x] Implement PartSectionBackend (current behavior)
  - [x] Wire Section to delegate pad/revolve/sweep to backend
  - [ ] SketcherSectionBackend: scaffold (no impl yet)

- [x] Generic Section API with materialization flag
  - [x] Introduce `generic_section(materialized: bool, ...)` as the single entry point
  - [x] Add wrappers: `section(...)` ⇒ materialized=False; `sketch(...)` ⇒ materialized=True (warns/falls back)
  - [x] Route to the same internal geometry pipeline; select backend based on flag

- [ ] Internal geometry representation (backend‑agnostic)
  - [x] Created `_SectionProfile` and moved 2D ops behind a profile layer
  - [ ] Refactor `_SectionProfile` to store pure geometry (lines/arcs/circles as numbers), not Part edges
  - [ ] Add adapters:
    - [ ] PartProfileAdapter → builds Part wires/faces from geometry
    - [ ] SketcherProfileAdapter → creates Sketcher::SketchObject geometry
  - [ ] Update PartSectionBackend to use PartProfileAdapter
  - [ ] Implement SketcherSectionBackend using SketcherProfileAdapter (materialized=True)

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

- [ ] Refactor api.py into modules (no behavior change)
  - [ ] `dsl_core.py` (Feature, param, export)
  - [ ] `profiles.py` (geometry classes: lines, arcs, circles; adapters)
  - [ ] `section_backends/part.py` and `section_backends/sketcher.py`
  - [ ] `primitives.py` (box, cylinder)
  - [ ] `assemblies.py` (component helpers)
  - [ ] `exports.py`
  - [ ] Re-export in `BbCadam/__init__.py`

- [ ] Documentation
  - [x] Update `api.md` for rename: section and add `sketch(visible=...)`
  - [ ] Add examples for section.pad (holes), section.revolve (piston), section.sweep (worm)
  - [ ] Document LCS planes and sweep orientation options
  - [x] Document arc validation (dir/radius, circle membership, degenerate/full-circle)

Assessment of current design vs planned generic API
- We have the backend layer (PartSectionBackend) and a profile layer, but `_SectionProfile` still emits Part geometry; this couples us to Part and is not fully backend‑agnostic.
- Plan: convert `_SectionProfile` to pure numeric geometry and introduce adapters for Part/Sketcher. Add `generic_section(materialized)` with `section()/sketch()` wrappers.

Current task: None blocking for section tests. Next focus: complete backend‑agnostic geometry (circles/arc fidelity) and add SketcherProfileAdapter.


