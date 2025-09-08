# Implementation Checklist

- [x] Implement Part-based Sketch DSL: `sketch()`, 2D ops (circle, rectangle, from_/to/go, close), `pad()` with holes on plane='XY'
- [ ] Add plane support for `XZ` and `YZ` to `sketch()` and `pad()`
- [ ] Add `revolve(angle_deg, axis)` to Sketch
- [x] Add `revolve(angle_deg, axis)` to Sketch
- [x] Add `sweep(path_sketch)` (sweep) to Sketch
 - [x] Implement `Sketch.arc` with centerAt/endAt (ccw/cw)
- [ ] Add optional Sketcher materialization flag to emit `Sketcher::SketchObject` for inspection
- [ ] Add edge selectors and `Feature.chamfer()` base-level op
- [ ] Documentation: extend `api.md` with examples and caveats

Current task: Plane support for XZ/YZ in sketch/pad; optional Sketcher materialization flag; edge selectors + chamfer().


