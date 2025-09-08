# Implementation Checklist

- [x] Part-based Section DSL (formerly sketch): 2D ops (circle, rectangle, polygon, from_/to/go, arc, close); 3D ops (pad, revolve, sweep); holes; XY plane
- [x] Plane support: XZ/YZ for section.pad/revolve; sweep respects path plane and auto-aligns profile normal
- [x] Examples: mount_plate (rounded), piston (revolve), worm (sweep)

- [ ] API rename: sketch() → section()
  - [ ] Rename public API in code (BbCadam/api.py) and remove `sketch` symbol
  - [ ] Update builder injection (inject `section` instead of `sketch`)
  - [ ] Update examples (mount_plate.py, piston.py, worm.py) to call `section`
  - [ ] Update docs (`api.md` and README) to use `section`

- [ ] Section backend abstraction
  - [ ] Define SectionBackend interface (2D ops + pad/revolve/sweep)
  - [ ] Implement PartSectionBackend (current behavior)
  - [ ] Wire `section()` to delegate to backend (default Part backend)
  - [ ] SketcherSectionBackend: design only (no impl yet)

- [ ] LCS/Datum plane targeting
  - [ ] Accept plane strings `LCS:Name`/`Datum:Name` (and object references)
  - [ ] Resolve datum in `ctx.doc` and derive Placement for section plane
  - [ ] Apply datum plane Placement in pad/revolve/sweep
  - [ ] Add example/test placing a section on a named LCS

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
  - [ ] `section_part.py` (2D ops, holes, pad)
  - [ ] `sweep_revolve.py` (revolve/sweep + orientation)
  - [ ] `primitives.py` (box, cylinder)
  - [ ] `assemblies.py` (component helpers)
  - [ ] `exports.py`
  - [ ] Re-export in `BbCadam/__init__.py`

- [ ] Documentation
  - [ ] Update `api.md` for rename: section
  - [ ] Add examples for section.pad (holes), section.revolve (piston), section.sweep (worm)
  - [ ] Document LCS planes and sweep orientation options

Current task: Plan approved → Implement API rename (sketch → section) and builder/docs/example updates; then add backend abstraction skeleton (Part backend default).


