# Implementation Checklist

- [ ] Implement Part-based Sketch DSL: `sketch()`, 2D ops (circle, rectangle, from_/to/go, close), `pad()` with holes on plane='XY'
- [ ] Add plane support for `XZ` and `YZ` to `sketch()` and `pad()`
- [ ] Add `revolve(angle_deg, axis)` to Sketch
- [ ] Add `follow(path_sketch)` (sweep) to Sketch
- [ ] Add optional Sketcher materialization flag to emit `Sketcher::SketchObject` for inspection
- [ ] Add edge selectors and `Feature.chamfer()` base-level op
- [ ] Documentation: extend `api.md` with examples and caveats

Current task: Implement Part-based Sketch DSL (plane='XY'), 2D ops and `pad()` with holes.


