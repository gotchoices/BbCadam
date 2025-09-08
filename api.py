import ast
import json
from pathlib import Path

import FreeCAD as App


# --- Context wiring is provided by builder; these globals are set at runtime ---
_CTX = None
_STATE = {
    'base_shape': None,
    'pending_feature': None,
}


def _set_ctx(ctx):
    global _CTX
    _CTX = ctx


def _ensure_part_module():
    try:
        import Part  # noqa: F401
    except Exception as e:
        raise RuntimeError(f"Part module not available: {e}")


def _vec3(p):
    x, y, z = p
    return App.Vector(float(x), float(y), float(z))


class Feature:
    def __init__(self, shape):
        self.shape = shape

    # fluent transforms
    def at(self, pos):
        self.shape.translate(_vec3(pos))
        return self

    def translate(self, by):
        self.shape.translate(_vec3(by))
        return self

    def rotate(self, axis=(0, 0, 1), deg=0):
        # Simple rotation around origin; more advanced placement can be added later
        ax = App.Vector(*axis)
        self.shape.rotate(App.Vector(0, 0, 0), ax, float(deg))
        return self

    # apply
    def add(self):
        _commit_pending_if_any(skip_shape=self.shape)
        _apply_add(self.shape)
        return self

    def cut(self):
        _commit_pending_if_any(skip_shape=self.shape)
        _apply_cut(self.shape)
        return self


def _commit_pending_if_any(skip_shape=None):
    pf = _STATE.get('pending_feature')
    if pf is not None:
        # Avoid implicitly adding the same shape that is about to be applied explicitly
        if skip_shape is not pf:
            _apply_add(pf)
        _STATE['pending_feature'] = None


def _apply_add(shape):
    import Part
    if _STATE['base_shape'] is None:
        _STATE['base_shape'] = shape
    else:
        _STATE['base_shape'] = _STATE['base_shape'].fuse(shape)


def _apply_cut(shape):
    if _STATE['base_shape'] is None:
        raise RuntimeError("No base solid yet; start with an additive feature before cut().")
    try:
        _STATE['base_shape'] = _STATE['base_shape'].cut(shape)
    except Exception:
        # retry once (geometric tolerance)
        _STATE['base_shape'] = _STATE['base_shape'].cut(shape)


def _emit_result(name='Part'):
    # Create/replace a single Part::Feature with the final shape
    if _STATE['base_shape'] is None:
        return None
    doc = _CTX.doc
    obj = doc.addObject('Part::Feature', name)
    obj.Shape = _STATE['base_shape']
    return obj


def _reset_state():
    _STATE['base_shape'] = None
    _STATE['pending_feature'] = None


def _finish_build(part_name='Part'):
    # Flush pending feature as add
    _commit_pending_if_any()
    obj = _emit_result(part_name)
    if obj:
        doc = _CTX.doc
        doc.recompute()
    return obj


# --- Primitives ---
def box(size, at=None, name=None):
    _ensure_part_module()
    import Part
    w, d, h = [float(x) for x in size]
    shape = Part.makeBox(w, d, h)
    feat = Feature(shape)
    if at is not None:
        feat.at(at)
    # Defer application to allow implicit add
    # Flush any previous pending feature as an implicit add before starting a new one
    if _STATE.get('pending_feature') is not None:
        _apply_add(_STATE['pending_feature'])
        _STATE['pending_feature'] = None
    _STATE['pending_feature'] = feat.shape
    return feat


def cylinder(d=None, r=None, h=None, at=None, name=None):
    _ensure_part_module()
    import Part
    if r is None:
        if d is None:
            raise ValueError('cylinder requires r or d')
        r = float(d) / 2.0
    shape = Part.makeCylinder(float(r), float(h))
    feat = Feature(shape)
    if at is not None:
        feat.at(at)
    if _STATE.get('pending_feature') is not None:
        _apply_add(_STATE['pending_feature'])
        _STATE['pending_feature'] = None
    _STATE['pending_feature'] = feat.shape
    return feat


# --- Composite feature builder ---
class _FeatureComposer:
    def __init__(self):
        self.shape = None

    def box(self, size, at=None):
        sh = box(size, at).shape
        self._add(sh)
        return self

    def cylinder(self, d=None, r=None, h=None, at=None):
        sh = cylinder(d=d, r=r, h=h, at=at).shape
        self._add(sh)
        return self

    def _add(self, new_shape):
        if self.shape is None:
            self.shape = new_shape
        else:
            self.shape = self.shape.fuse(new_shape)

    # Apply to global base
    def add(self):
        _commit_pending_if_any()
        _apply_add(self.shape)

    def cut(self):
        _commit_pending_if_any()
        _apply_cut(self.shape)


class _FeatureContext:
    def __enter__(self):
        self.comp = _FeatureComposer()
        return self.comp

    def __exit__(self, exc_type, exc, tb):
        # Do nothing; caller must call .add() or .cut()
        return False


def feature():
    return _FeatureContext()


# --- LCS / Datum ---
def lcs(name, at=(0, 0, 0), rot_xyz_deg=(0, 0, 0)):
    # Placeholder: attach a named datum by creating an empty Part::Feature with placement
    doc = _CTX.doc
    datum = doc.addObject('Part::Feature', name)
    datum.Placement.Base = _vec3(at)
    # Rotation placeholder; can be extended to full Placement rotation
    return datum


add_lcs = lcs


# --- Parameters and expressions ---
def param(name: str, default=None):
    if _CTX is None:
        raise RuntimeError('param() called without active context')
    raw = _CTX.params
    if name in raw:
        value = raw[name]
    else:
        if default is not None:
            return float(default)
        raise KeyError(name)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        s = value.strip()
        if s.startswith('='):
            return float(_eval_expr(s[1:], raw))
        try:
            return float(s)
        except Exception:
            raise ValueError(f'Parameter {name} not numeric: {value}')
    raise ValueError(f'Unsupported parameter type for {name}: {type(value)}')


def _eval_expr(expr: str, env: dict):
    def _get(name: str):
        if name not in env:
            raise KeyError(name)
        v = env[name]
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str) and v.strip().startswith('='):
            return float(_eval_expr(v.strip()[1:], env))
        if isinstance(v, str):
            return float(v)
        raise ValueError(f'Bad param {name}')

    def _eval(node):
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        if isinstance(node, ast.BinOp):
            a = _eval(node.left)
            b = _eval(node.right)
            if isinstance(node.op, ast.Add):
                return a + b
            if isinstance(node.op, ast.Sub):
                return a - b
            if isinstance(node.op, ast.Mult):
                return a * b
            if isinstance(node.op, ast.Div):
                return a / b
            raise ValueError('Unsupported op')
        if isinstance(node, ast.UnaryOp):
            v = _eval(node.operand)
            if isinstance(node.op, ast.UAdd):
                return +v
            if isinstance(node.op, ast.USub):
                return -v
            raise ValueError('Unsupported unary')
        if isinstance(node, ast.Name):
            return _get(node.id)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        raise ValueError('Unsupported expr element')

    tree = ast.parse(expr, mode='eval')
    return _eval(tree)


# --- Export ---
def _resolve_export_kinds(kinds):
    if kinds is not None:
        if isinstance(kinds, str):
            return [kinds]
        return list(kinds)
    # param('export') may be string or list
    try:
        p = _CTX.params.get('export')
    except Exception:
        p = None
    if p:
        return [p] if isinstance(p, str) else list(p)
    # settings.yaml exports toggles
    kinds = []
    ex = getattr(_CTX, 'settings', {}).get('exports', {}) if hasattr(_CTX, 'settings') else {}
    if ex.get('step'):
        kinds.append('step')
    if ex.get('stl'):
        kinds.append('stl')
    return kinds or ['step', 'stl']


def export(kinds=None, name=None):
    kinds_list = _resolve_export_kinds(kinds)
    obj = _finish_build(name or _CTX.part_name)
    if not obj:
        return
    # Export using Import/Mesh
    if 'step' in kinds_list:
        _export_step(obj, _CTX.paths.step_parts / f"{_CTX.part_name}.step")
    if 'stl' in kinds_list:
        _export_stl(obj, _CTX.paths.stl_parts / f"{_CTX.part_name}.stl")


def export_step(part_name: str):
    obj = _finish_build(part_name)
    _export_step(obj, _CTX.paths.step_parts / f"{part_name}.step")


def export_stl(part_name: str):
    obj = _finish_build(part_name)
    _export_stl(obj, _CTX.paths.stl_parts / f"{part_name}.stl")


def _export_step(obj, out_path: Path):
    try:
        import Import
        out_path.parent.mkdir(parents=True, exist_ok=True)
        Import.export([obj], str(out_path))
    except Exception:
        import Part
        Part.export([obj], str(out_path))


def _export_stl(obj, out_path: Path):
    try:
        import Mesh
        out_path.parent.mkdir(parents=True, exist_ok=True)
        Mesh.export([obj], str(out_path))
    except Exception:
        App.Console.PrintError(f"[bbcadam] STL export failed: {out_path}\n")


# --- Sketch (Part-based profiles with holes) ---
class Section:
    def __init__(self, name=None, plane='XY', at=(0.0, 0.0, 0.0)):
        self.name = name or 'Sketch'
        self.plane = plane.upper()
        self.origin = at
        self._outer_wire = None
        self._hole_wires = []
        self._cursor = None  # last point in 2D (x,y)
        self._first_point = None
        self._building_hole = False

    # ----- 2D primitives -----
    def circle(self, d=None, r=None, at=(0.0, 0.0), hole=False):
        import Part
        if r is None:
            if d is None:
                raise ValueError('circle requires r or d')
            r = float(d) / 2.0
        cx, cy = float(at[0]), float(at[1])
        edge = Part.Edge(Part.Circle(App.Vector(cx, cy, 0), App.Vector(0, 0, 1), float(r)))
        wire = Part.Wire([edge])
        self._add_wire(wire, hole or self._building_hole)
        return self

    def rectangle(self, w, h=None, at=(0.0, 0.0), hole=False):
        import Part
        w = float(w)
        h = float(h) if h is not None else w
        cx, cy = float(at[0]), float(at[1])
        x0, y0 = cx - w / 2.0, cy - h / 2.0
        pts = [
            App.Vector(x0, y0, 0),
            App.Vector(x0 + w, y0, 0),
            App.Vector(x0 + w, y0 + h, 0),
            App.Vector(x0, y0 + h, 0),
            App.Vector(x0, y0, 0),
        ]
        edges = [Part.makeLine(pts[i], pts[i + 1]) for i in range(4)]
        wire = Part.Wire(edges)
        self._add_wire(wire, hole or self._building_hole)
        return self

    def polygon(self, n=6, side=None, d=None, at=(0.0, 0.0), hole=False):
        import math, Part
        n = int(n)
        cx, cy = float(at[0]), float(at[1])
        if d is not None:
            R = float(d) / 2.0
        elif side is not None:
            # regular polygon circumradius from side length
            a = float(side)
            R = a / (2.0 * math.sin(math.pi / n))
        else:
            R = 1.0
        pts = [
            App.Vector(cx + R * math.cos(2 * math.pi * i / n), cx * 0 + cy + R * math.sin(2 * math.pi * i / n), 0)
            for i in range(n)
        ]
        pts.append(pts[0])
        edges = [Part.makeLine(pts[i], pts[i + 1]) for i in range(n)]
        wire = Part.Wire(edges)
        self._add_wire(wire, hole or self._building_hole)
        return self

    # ----- Line builder -----
    def from_(self, x=None, y=None, hole=False):
        x = float(x) if x is not None else (self._cursor[0] if self._cursor else 0.0)
        y = float(y) if y is not None else (self._cursor[1] if self._cursor else 0.0)
        self._cursor = (x, y)
        self._first_point = (x, y)
        self._building_hole = bool(hole)
        return self

    def to(self, x=None, y=None):
        if self._cursor is None:
            raise RuntimeError('to() called before from_()')
        nx = float(x) if x is not None else self._cursor[0]
        ny = float(y) if y is not None else self._cursor[1]
        self._append_segment(self._cursor, (nx, ny))
        self._cursor = (nx, ny)
        return self

    def go(self, dx=None, dy=None, r=None, a_deg=None):
        if self._cursor is None:
            raise RuntimeError('go() called before from_()')
        if r is not None and a_deg is not None:
            import math
            dx = float(r) * math.cos(math.radians(float(a_deg)))
            dy = float(r) * math.sin(math.radians(float(a_deg)))
        nx = self._cursor[0] + (float(dx) if dx is not None else 0.0)
        ny = self._cursor[1] + (float(dy) if dy is not None else 0.0)
        self._append_segment(self._cursor, (nx, ny))
        self._cursor = (nx, ny)
        return self

    def arc(self, radius, dir='ccw', end=None, endAt=None, center=None, centerAt=None):
        """
        Add a circular arc from current cursor to the given end point, around a given center.
        - radius: arc radius (float)
        - dir: 'ccw' (default) or 'cw' to choose sweep direction (shortest path)
        - end/endAt: endpoint relative (dx,dy) or absolute (x,y)
        - center/centerAt: center relative (dx,dy) or absolute (x,y)
        """
        import math
        import Part
        if self._cursor is None:
            raise RuntimeError('arc() called before from_()')
        cx0, cy0 = self._cursor
        # Determine center
        if centerAt is not None:
            cx, cy = float(centerAt[0]), float(centerAt[1])
        elif center is not None:
            cx = cx0 + float(center[0])
            cy = cy0 + float(center[1])
        else:
            raise ValueError('arc requires center or centerAt')
        # Determine end point
        if endAt is not None:
            ex, ey = float(endAt[0]), float(endAt[1])
        elif end is not None:
            ex = cx0 + float(end[0])
            ey = cy0 + float(end[1])
        else:
            raise ValueError('arc requires end or endAt')
        # Start, end, and mid points
        sx, sy = cx0, cy0
        a_start = math.atan2(sy - cy, sx - cx)
        a_end = math.atan2(ey - cy, ex - cx)
        # Normalize angles to [0, 2pi)
        def norm(a):
            while a < 0:
                a += 2 * math.pi
            while a >= 2 * math.pi:
                a -= 2 * math.pi
            return a
        a_start = norm(a_start)
        a_end = norm(a_end)
        if dir.lower() == 'ccw':
            delta = a_end - a_start
            if delta < 0:
                delta += 2 * math.pi
        else:  # cw
            delta = a_end - a_start
            if delta > 0:
                delta -= 2 * math.pi
        a_mid = a_start + delta / 2.0
        # Build arc via three points on circle of given radius
        R = float(radius)
        # Trust provided radius; adjust mid point to lie on that circle
        smid_x = cx + R * math.cos(a_mid)
        smid_y = cy + R * math.sin(a_mid)
        start_v = App.Vector(sx, sy, 0)
        mid_v = App.Vector(smid_x, smid_y, 0)
        end_v = App.Vector(ex, ey, 0)
        edge = Part.Arc(start_v, mid_v, end_v).toShape()
        if not hasattr(self, '_poly_edges'):
            self._poly_edges = []
        self._poly_edges.append(edge)
        self._cursor = (ex, ey)
        return self

    def close(self):
        if self._cursor is None or self._first_point is None:
            return self
        if self._cursor != self._first_point:
            self._append_segment(self._cursor, self._first_point)
        # finalize current polyline into a wire
        self._finalize_polyline()
        self._cursor = None
        self._first_point = None
        self._building_hole = False
        return self

    # ----- 3D ops -----
    def pad(self, dist, dir='+'):  # returns Feature
        import Part
        if self._cursor is not None:
            # auto-close if user forgot
            self.close()
        if self._outer_wire is None:
            raise RuntimeError('pad() requires an outer profile (use rectangle/circle/polygon or from_/to/close)')
        # Build face with holes robustly by boolean subtract
        face = Part.Face(self._outer_wire)
        for hw in self._hole_wires:
            try:
                hole_face = Part.Face(hw)
                face = face.cut(hole_face)
            except Exception:
                # if hole face fails, skip that hole
                pass
        # plane normal
        dist = float(dist)
        if self.plane == 'XY':
            vec = App.Vector(0, 0, dist if dir.startswith('+') else -dist)
        elif self.plane == 'XZ':
            vec = App.Vector(0, dist if dir.startswith('+') else -dist, 0)
        elif self.plane == 'YZ':
            vec = App.Vector(dist if dir.startswith('+') else -dist, 0, 0)
        else:
            raise ValueError('Unknown plane')
        solid = face.extrude(vec)
        try:
            # Ensure solidness if extrusion produced a shell
            solid = solid.makeSolid()
        except Exception:
            pass
        # place at origin offset and rotate for plane if needed
        solid = self._place_shape(solid)
        return Feature(solid)

    def revolve(self, angle_deg=360.0, axis='Y'):
        import Part
        if self._cursor is not None:
            self.close()
        if self._outer_wire is None:
            raise RuntimeError('revolve() requires an outer profile (use rectangle/circle/polygon or from_/to/close)')
        # Build face with holes by boolean subtract
        face = Part.Face(self._outer_wire)
        for hw in self._hole_wires:
            try:
                hole_face = Part.Face(hw)
                face = face.cut(hole_face)
            except Exception:
                pass
        axis = axis.upper()
        if axis == 'X':
            axis_dir = App.Vector(1, 0, 0)
        elif axis == 'Y':
            axis_dir = App.Vector(0, 1, 0)
        elif axis == 'Z':
            axis_dir = App.Vector(0, 0, 1)
        else:
            raise ValueError('axis must be X, Y, or Z')
        solid = face.revolve(App.Vector(0, 0, 0), axis_dir, float(angle_deg))
        try:
            solid = solid.makeSolid()
        except Exception:
            pass
        solid = self._place_shape(solid)
        return Feature(solid)

    def sweep(self, path_sketch):
        """Sweep the current closed profile along a path defined by another Sketch.
        path_sketch may contain lines and arcs (open path wire)."""
        import Part
        if self._cursor is not None:
            self.close()
        if self._outer_wire is None:
            raise RuntimeError('sweep() requires an outer profile (use rectangle/circle/polygon or from_/to/close)')
        # Build profile face (with holes) in local coords
        face = Part.Face(self._outer_wire)
        for hw in self._hole_wires:
            try:
                face = face.cut(Part.Face(hw))
            except Exception:
                pass
        # Build path wire from path_sketch poly edges (auto-close if needed later)
        if not hasattr(path_sketch, '_poly_edges') and path_sketch._cursor is not None:
            path_sketch.close()
        path_edges = []
        if hasattr(path_sketch, '_poly_edges') and path_sketch._poly_edges:
            path_edges.extend(path_sketch._poly_edges)
        # Also include any explicit wires if user finalized
        if path_sketch._outer_wire is not None and not path_sketch._hole_wires:
            # treat as a single wire path if no holes (open path)
            path_edges = list(path_sketch._outer_wire.Edges)
        if not path_edges:
            raise RuntimeError('sweep() requires a path sketch with lines/arcs')
        path_wire = Part.Wire(path_edges)
        # Place path into external coords
        path = path_sketch._place_shape(path_wire)
        # Compute start point and tangent
        first_edge = path.Edges[0]
        try:
            t0 = first_edge.tangentAt(first_edge.FirstParameter)
        except Exception:
            # fallback approximate tangent
            v0 = first_edge.Vertexes[0].Point
            v1 = first_edge.Vertexes[-1].Point
            t0 = App.Vector(v1.x - v0.x, v1.y - v0.y, v1.z - v0.z)
        if t0.Length == 0:
            t0 = App.Vector(0, 0, 1)
        t0.normalize()
        start_pt = first_edge.Vertexes[0].Point
        # Orient profile so its local Z aligns to tangent and move to start point
        prof = face.copy()
        rot = App.Rotation(App.Vector(0, 0, 1), t0)
        pl = App.Placement()
        pl.Rotation = rot
        pl.Base = start_pt
        prof.Placement = pl
        shape = path.makePipeShell([prof.OuterWire], True, True)
        # If the result already contains a solid, use it; otherwise return the shape as-is
        try:
            solids = getattr(shape, 'Solids', [])
            if solids:
                shape = solids[0]
        except Exception:
            pass
        return Feature(shape)

    # ----- helpers -----
    def _append_segment(self, p0, p1):
        import Part
        a = App.Vector(float(p0[0]), float(p0[1]), 0)
        b = App.Vector(float(p1[0]), float(p1[1]), 0)
        edge = Part.makeLine(a, b)
        if not hasattr(self, '_poly_edges'):
            self._poly_edges = []
        self._poly_edges.append(edge)

    def _finalize_polyline(self):
        import Part
        if not getattr(self, '_poly_edges', None):
            return
        wire = Part.Wire(self._poly_edges)
        self._poly_edges = []
        self._add_wire(wire, self._building_hole)

    def _add_wire(self, wire, hole):
        # Ensure orientation: let outer be CCW, holes CW (Part.Face can tolerate)
        if hole:
            self._hole_wires.append(wire)
        else:
            if self._outer_wire is not None:
                # For v1, only one outer wire is supported
                raise RuntimeError('Only one outer profile is supported in pad() v1')
            self._outer_wire = wire

    def _place_shape(self, shape):
        # Rotate shape from local XY into requested plane, then translate by origin
        import Part
        placed = shape.copy()
        if self.plane == 'XY':
            pass
        elif self.plane == 'XZ':
            # rotate around X axis +90 to map local Z→Y
            placed.rotate(App.Vector(0, 0, 0), App.Vector(1, 0, 0), 90)
        elif self.plane == 'YZ':
            # rotate around Y axis -90 to map local Z→X
            placed.rotate(App.Vector(0, 0, 0), App.Vector(0, 1, 0), -90)
        placed.translate(_vec3(self.origin))
        return placed


def section(name=None, plane='XY', at=(0.0, 0.0, 0.0)):
    return Section(name=name, plane=plane, at=at)

    def _place_geom(self, geom):
        placed = geom.copy()
        if self.plane == 'XY':
            pass
        elif self.plane == 'XZ':
            placed.rotate(App.Vector(0, 0, 0), App.Vector(1, 0, 0), 90)
        elif self.plane == 'YZ':
            placed.rotate(App.Vector(0, 0, 0), App.Vector(0, 1, 0), -90)
        placed.translate(_vec3(self.origin))
        return placed



