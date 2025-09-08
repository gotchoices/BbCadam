# BbCadam API and Authoring Guide

This document describes the proposed DSL, authoring contract, and light guardrails. The API preserves all capabilities from `try1` (box, cut with box/cylinder, basic assemblies with `App::Link`) and extends them for ergonomics and stability.

## Authoring contract
- Parts define:
  - `def build_part(ctx): ...`
- Assemblies define:
  - `def build_assembly(ctx): ...`

`ctx` (build context) provides:
- `doc`: active FreeCAD document for the build
- `params`: dict-like parameters (from adjacent `params.yaml` or inline; optional)
- `units`: default unit system (`"in"` or `"mm"`) and helpers
- `paths`: named paths to `build/` and `exports/` targets
- `log`: structured logger (`info`, `warn`, `error`)
- `settings`: project settings loaded from `config/settings.yaml`

BbCadam auto-exposes the DSL in the script’s global namespace. You can also import it explicitly as `from bbcadam.api import *` or `import bbcadam.api as dsl`.

## Light guardrails
- Raw FreeCAD is not pre-imported. If you need primitives or advanced features, explicitly import them:
  - `import FreeCAD as App, Part`
- BbCadam logs when FreeCAD modules appear during a build (warning only). CI can surface warnings.

## Units and numeric helpers
- Default units are configured per project. Provide values as floats; unit converters are available:
```python
inch(12)  # → 12.0
mm(25.4)  # → 1.0 in if default units are inches
```

## Geometry DSL (parts)
Small, fluent vocabulary. Primitives return a Feature you can transform and then apply with `.add()` (fuse) or `.cut()` (subtract). The first committed feature becomes the base. If you omit `.add()`/`.cut()`, add is implicit.

Primitives → Feature:
```python
box(size=(x, y, z), at=None, name=None)        # returns Feature
cylinder(d=None, r=None, h=None, at=None, name=None)  # returns Feature
```

Feature methods:
```python
Feature.at((x,y,z))
Feature.translate((x,y,z))
Feature.rotate(axis=(1,0,0), deg=0)
Feature.add()      # fuse into current solid (implicit if omitted)
Feature.cut()      # subtract from current solid
```

Sketch profiles → Feature (extrusions/revolves/sweeps):
```python
sketch(name=None, plane='XY', at=(0,0,0)) -> Sketch

# 2D drawing on Sketch (fluent)
Sketch.circle(d=None, r=None, at=(x,y))
Sketch.rectangle(w, h=None, at=(x,y))
Sketch.polygon(n=6, side=None, d=None, at=(x,y))
Sketch.from_(x=None, y=None)
Sketch.to(x=None, y=None)
Sketch.go(dx=None, dy=None, r=None, a_deg=None)
Sketch.arc(radius, dir='ccw', quad=None, end=(dx,dy)|endAt=(x,y), center=(dx,dy)|centerAt=(x,y))
Sketch.close()

# 3D ops (return Feature)
Sketch.pad(dist, dir='+Z')
Sketch.revolve(angle_deg=360, axis='Z')
Sketch.sweep(path_sketch)  # sweep along a path Sketch (lines/arcs)
```

Holes: include inner profiles (e.g., `circle` inside a `rectangle`), then `pad` to produce solids with voids.

Composite feature (build a tool, then apply):
```python
with feature() as f:
    f.box(size=(...)).at((...))
    f.cylinder(d=..., h=...).translate((...))
# Apply the composite to the current solid:
f.cut()
```

Datum / LCS:
```python
lcs(name, at=(x,y,z), rot_xyz_deg=(0,0,0))    # alias: add_lcs(...)
```

Exports (project-controlled defaults apply):
```python
export_step(part_name: str)
export_stl(part_name: str)
```

Example (equivalent to `try1` caisson subset):
```python
def build_part(ctx):
    W = param('M')
    V = param('V')
    R = param('R')
    T = param('T')
    H = V + T
    D = R * V
    t_w = param('t_w')

    # Base (implicit add)
    box(size=(W, D, H), at=(-W/2, 0, 0))
    # Hollow and front opening
    box(size=(W - 2*t_w, D - 2*t_w, H - 2*t_w), at=(-W/2 + t_w, t_w, t_w)).cut()
    box(size=(W - 2*t_w, t_w + 0.1, V), at=(-W/2 + t_w, -0.1, 0)).cut()
    # Valve hole
    cylinder(d=param('valve_dia'), h=t_w + 0.1, at=(0, D - param('valve_back_offset'), H - 0.1)).cut()
```

Parameter access and expressions:
```python
param(name: str, default=None)  # returns float; raises if missing and no default
```

Parameter sources (recommended):
- Project defaults: `config/params.yaml` (optional)
- Part-specific: `specs/parts/<part>/params.yaml` (optional)
Values merge (project → part), expressions supported via `"=..."` strings.

## Assembly DSL (fluent)
Primitives for assemblies are linked components; they return a `Comp` that you position.

Create components → `Comp`:
```python
component(path: str, as_name: str=None)  # inserts App::Link and returns Comp
```

`Comp` methods:
```python
Comp.at((x,y,z))
Comp.rotate(axis=(0,0,1), deg=0)
Comp.rot_xyz_deg((rx,ry,rz))
```

Optional future helpers (not required now):
```python
# Comp.mate(lcs='PartLCS', to='AsmLCS', offset=(0,0,0), rot_xyz_deg=(0,0,0))
```

Example:
```python
def build_assembly(ctx):
    component('../parts/caisson/caisson.FCStd', as_name='c1').at((0, 0, 0))
    component('../parts/caisson/caisson.FCStd', as_name='c2').at((144, 0, 0)).rot_xyz_deg((0, 0, 0))
    # lcs('Asm_Origin', at=(0,0,0))  # optional datum for assembly
    export()  # see export behavior below
```

## Export behavior
Preferred API:
```python
export(kinds=None)
```

Behavior and precedence:
- If `kinds` is provided, it can be a string (`'step'`) or list (e.g., `['step','stl']`).
- If omitted, resolve in this order:
  1) `param('export')` if present (string or list)
  2) `ctx.settings.exports` toggles from `config/settings.yaml` (e.g., `step: true`, `stl: true`)
  3) Built-in default (e.g., `['step','stl']`)

Existing helpers `export_step(name)` and `export_stl(name)` may remain for explicit use, but `export()` is recommended.

## Headless and watcher behavior (shared)
- Both use the same builder core.
- On build success, save to `build/{parts,assemblies}/<name>.FCStd` and optionally export STEP/STL.
- On error, write a readable message to the console/log with the script location.

## Extensions (future but compatible)
- Sketch/pad/pocket DSL wrappers
- Fillet/chamfer helpers
- Basic mating helpers using LCS and offsets
- Content-hash caching to skip rebuilds when inputs unchanged

## Implementation notes: Part vs Sketcher
- Part-based approach (initial): build 2D edges/wires/faces directly via `Part` (no constraints). This is robust headless, faster, and easier to serialize. The resulting 3D solid appears as a single `Part::Feature`. We will store the 2D profile data internally for debugging.
- Sketcher-based approach (later optional): create a `Sketcher::SketchObject` in `PartDesign::Body`, draw geometry and constraints, then pad/pocket. This yields a richer feature tree but requires PartDesign context and has more overhead. We can offer a mode to materialize a Sketcher object for inspection while still using Part ops underneath for the final solid.

Default: Part-based for performance and simplicity; offer an option to `materialize_sketch=True` to emit a `Sketcher::SketchObject` as a sibling for visualization (no constraints initially). Plane selection is supported via `plane='XY'|'XZ'|'YZ'` and `at=(x,y,0)` offset.

### Sweep orientation behavior
- By default, the profile is placed at the path start and auto-aligned so its local +Z is along the path tangent at the start. This keeps sweeps intuitive without pre-rotating the profile.
- Future options planned: `use_frenet`, `up` vector, and `align={'auto'|'fixed'|'frenet'}` to control orientation and twist behavior.


