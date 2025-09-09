import ast
import json
from pathlib import Path

import FreeCAD as App


# --- Context wiring is provided by builder; these globals are set at runtime ---
_CTX = None
_STATE = {
    'base_shape': None,
    'pending_feature': None,
    'view': {},
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

    # view/appearance helpers (applied to final Part object at emit time)
    def appearance(self, color=None, opacity=None):
        v = _STATE.get('view') or {}
        if color is not None:
            try:
                r, g, b = color
                v['color'] = (float(r), float(g), float(b))
            except Exception:
                pass
        if opacity is not None:
            try:
                v['opacity'] = int(opacity)
            except Exception:
                pass
        _STATE['view'] = v
        return self

    def color(self, color):
        return self.appearance(color=color)

    def opacity(self, opacity):
        return self.appearance(opacity=opacity)


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
    # Apply view settings if GUI present
    try:
        v = _STATE.get('view') or {}
        if hasattr(obj, 'ViewObject') and obj.ViewObject is not None:
            if 'opacity' in v:
                obj.ViewObject.Transparency = int(v['opacity'])
            if 'color' in v:
                c = v['color']
                # FreeCAD expects RGB floats 0..1
                obj.ViewObject.ShapeColor = (float(c[0]), float(c[1]), float(c[2]))
    except Exception:
        pass
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


# --- Section backends (abstraction for Part/Sketcher implementations) ---

class SectionBackend:
    def pad(self, section, dist, dir='+'):
        raise NotImplementedError

    def revolve(self, section, angle_deg=360.0, axis='Y'):
        raise NotImplementedError

    def sweep(self, section, path_section):
        raise NotImplementedError


class PartSectionBackend(SectionBackend):
    def _build_face_with_holes(self, section):
        return PartProfileAdapter(section._profile).build_face_with_holes()

    def pad(self, section, dist, dir='+'):
        face = self._build_face_with_holes(section)
        dist = float(dist)
        if section.plane == 'XY':
            vec = App.Vector(0, 0, dist if dir.startswith('+') else -dist)
        elif section.plane == 'XZ':
            vec = App.Vector(0, dist if dir.startswith('+') else -dist, 0)
        elif section.plane == 'YZ':
            vec = App.Vector(dist if dir.startswith('+') else -dist, 0, 0)
        else:
            raise ValueError('Unknown plane')
        solid = face.extrude(vec)
        try:
            solid = solid.makeSolid()
        except Exception:
            pass
        solid = section._place_shape(solid)
        return Feature(solid)

    def revolve(self, section, angle_deg=360.0, axis='Y'):
        face = self._build_face_with_holes(section)
        ax = axis.upper()
        if ax == 'X':
            axis_dir = App.Vector(1, 0, 0)
        elif ax == 'Y':
            axis_dir = App.Vector(0, 1, 0)
        elif ax == 'Z':
            axis_dir = App.Vector(0, 0, 1)
        else:
            raise ValueError('axis must be X, Y, or Z')
        solid = face.revolve(App.Vector(0, 0, 0), axis_dir, float(angle_deg))
        try:
            solid = solid.makeSolid()
        except Exception:
            pass
        solid = section._place_shape(solid)
        return Feature(solid)

    def sweep(self, section, path_section):
        import Part
        face = self._build_face_with_holes(section)
        # Build path wire from path_section profile via adapter
        path_wire = PartProfileAdapter(path_section._profile).build_open_wire()
        path = path_section._place_shape(path_wire)
        first_edge = path.Edges[0]
        try:
            t0 = first_edge.tangentAt(first_edge.FirstParameter)
        except Exception:
            v0 = first_edge.Vertexes[0].Point
            v1 = first_edge.Vertexes[-1].Point
            t0 = App.Vector(v1.x - v0.x, v1.y - v0.y, v1.z - v0.z)
        if t0.Length == 0:
            t0 = App.Vector(0, 0, 1)
        t0.normalize()
        start_pt = first_edge.Vertexes[0].Point
        prof = face.copy()
        rot = App.Rotation(App.Vector(0, 0, 1), t0)
        pl = App.Placement()
        pl.Rotation = rot
        pl.Base = start_pt
        prof.Placement = pl
        shape = path.makePipeShell([prof.OuterWire], True, True)
        try:
            solids = getattr(shape, 'Solids', [])
            if solids:
                shape = solids[0]
        except Exception:
            pass
        return Feature(shape)


class SketcherSectionBackend(SectionBackend):
    def _materialize_sketch(self, section):
        try:
            adapter = SketcherProfileAdapter(section)
            sk = adapter.build_sketch()
            return sk
        except Exception as e:
            App.Console.PrintWarning(f"[bbcadam] Sketcher materialization failed: {e}\n")
            return None

    def pad(self, section, dist, dir='+'):
        # Materialize for inspection, but build solid via Part backend for now
        self._materialize_sketch(section)
        return PartSectionBackend().pad(section, dist, dir)

    def revolve(self, section, angle_deg=360.0, axis='Y'):
        self._materialize_sketch(section)
        return PartSectionBackend().revolve(section, angle_deg, axis)

    def sweep(self, section, path_section):
        self._materialize_sketch(section)
        # Also materialize path section
        try:
            SketcherProfileAdapter(path_section).build_sketch(name=(path_section.name or 'Path'))
        except Exception:
            pass
        return PartSectionBackend().sweep(section, path_section)


# --- Section (profiles with holes) ---
class Section:
    def __init__(self, name=None, plane='XY', at=(0.0, 0.0, 0.0), backend: SectionBackend | None = None, visible: bool = True):
        self.name = name or 'Sketch'
        self.plane = plane.upper()
        self.origin = at
        self._profile = _SectionProfile()
        # Sketcher-only: whether to show materialized sketch in tree
        self._sketch_visible = bool(visible)
        # Optional datum/LCS placement, resolved if plane like 'LCS:Name' or 'Datum:Name'
        self._datum_placement = None
        try:
            if isinstance(plane, str):
                p = plane.strip()
                key = p.split(':', 1)[0]
                if key in ('LCS', 'Datum', 'DATUM') and ':' in p:
                    obj_name = p.split(':', 1)[1]
                    doc = _CTX.doc if _CTX else None
                    if doc:
                        obj = doc.getObject(obj_name)
                        if obj and hasattr(obj, 'Placement'):
                            self._datum_placement = obj.Placement
        except Exception:
            pass
        # Select backend
        if backend is None:
            self._backend = PartSectionBackend()
        else:
            self._backend = backend

    # ----- 2D primitives -----
    def circle(self, d=None, r=None, at=(0.0, 0.0), hole=False):
        self._profile.circle(d=d, r=r, at=at, hole=hole)
        return self

    def rectangle(self, w, h=None, at=(0.0, 0.0), hole=False):
        self._profile.rectangle(w=w, h=h, at=at, hole=hole)
        return self

    def polygon(self, n=6, side=None, d=None, at=(0.0, 0.0), hole=False):
        self._profile.polygon(n=n, side=side, d=d, at=at, hole=hole)
        return self

    # ----- Line builder -----
    def from_(self, x=None, y=None, hole=False):
        self._profile.from_(x=x, y=y, hole=hole)
        return self

    def to(self, x=None, y=None):
        self._profile.to(x=x, y=y)
        return self

    def go(self, dx=None, dy=None, r=None, a_deg=None):
        self._profile.go(dx=dx, dy=dy, r=r, a_deg=a_deg)
        return self

    def arc(self, radius, dir='ccw', end=None, endAt=None, center=None, centerAt=None):
        self._profile.arc(radius=radius, dir=dir, end=end, endAt=endAt, center=center, centerAt=centerAt)
        return self

    def close(self):
        self._profile.close()
        return self

    # ----- 3D ops -----
    def pad(self, dist, dir='+'):
        return self._backend.pad(self, dist, dir)

    def revolve(self, angle_deg=360.0, axis='Y'):
        return self._backend.revolve(self, angle_deg, axis)

    def sweep(self, path_section):
        return self._backend.sweep(self, path_section)

    # ----- helpers -----
    def _place_shape(self, shape):
        # Rotate shape from local XY into requested plane or datum, then translate by origin
        placed = shape.copy()
        # Datum/LCS placement takes precedence
        if getattr(self, '_datum_placement', None) is not None:
            placed.Placement = self._datum_placement
            try:
                off_local = App.Vector(float(self.origin[0]), float(self.origin[1]), float(self.origin[2]))
            except Exception:
                off_local = App.Vector(0, 0, 0)
            off_world = self._datum_placement.Rotation.multVec(off_local)
            placed.translate(off_world)
            return placed
        # Principal planes
        if self.plane == 'XY':
            pass
        elif self.plane == 'XZ':
            placed.rotate(App.Vector(0, 0, 0), App.Vector(1, 0, 0), 90)
        elif self.plane == 'YZ':
            placed.rotate(App.Vector(0, 0, 0), App.Vector(0, 1, 0), -90)
        placed.translate(_vec3(self.origin))
        return placed
class _SectionProfile:
    def __init__(self):
        self._outer_wire = None
        self._hole_wires = []
        self._cursor = None
        self._first_point = None
        self._building_hole = False
        # Backend-agnostic geometry capture (paths of line/arc ops)
        self._geom_outer = None  # list of ops for outer path
        self._geom_holes = []    # list of path-op lists
        self._geom_current = None

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
        # Geometry capture (circle as polygonal arc set not yet implemented)

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
        # Geometry capture: store as a path of lines
        path = []
        for i in range(4):
            path.append(('line', (float(pts[i].x), float(pts[i].y), float(pts[i+1].x), float(pts[i+1].y))))
        self._add_geom_path(path, hole or self._building_hole)

    def polygon(self, n=6, side=None, d=None, at=(0.0, 0.0), hole=False):
        import math, Part
        n = int(n)
        cx, cy = float(at[0]), float(at[1])
        if d is not None:
            R = float(d) / 2.0
        elif side is not None:
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
        # Geometry capture: polygon lines
        path = []
        for i in range(n):
            path.append(('line', (float(pts[i].x), float(pts[i].y), float(pts[i+1].x), float(pts[i+1].y))))
        self._add_geom_path(path, hole or self._building_hole)

    def from_(self, x=None, y=None, hole=False):
        x = float(x) if x is not None else (self._cursor[0] if self._cursor else 0.0)
        y = float(y) if y is not None else (self._cursor[1] if self._cursor else 0.0)
        self._cursor = (x, y)
        self._first_point = (x, y)
        self._building_hole = bool(hole)
        # start new geom path
        self._geom_current = []

    def to(self, x=None, y=None):
        if self._cursor is None:
            raise RuntimeError('to() called before from_()')
        px, py = self._cursor
        nx = float(x) if x is not None else px
        ny = float(y) if y is not None else py
        self._append_segment((px, py), (nx, ny))
        if self._geom_current is not None:
            self._geom_current.append(('line', (float(px), float(py), float(nx), float(ny))))
        self._cursor = (nx, ny)

    def go(self, dx=None, dy=None, r=None, a_deg=None):
        if self._cursor is None:
            raise RuntimeError('go() called before from_()')
        if r is not None and a_deg is not None:
            import math
            dx = float(r) * math.cos(math.radians(float(a_deg)))
            dy = float(r) * math.sin(math.radians(float(a_deg)))
        px, py = self._cursor
        nx = px + (float(dx) if dx is not None else 0.0)
        ny = py + (float(dy) if dy is not None else 0.0)
        self._append_segment((px, py), (nx, ny))
        if self._geom_current is not None:
            self._geom_current.append(('line', (float(px), float(py), float(nx), float(ny))))
        self._cursor = (nx, ny)

    def arc(self, radius, dir='ccw', end=None, endAt=None, center=None, centerAt=None):
        import math
        import Part
        if self._cursor is None:
            raise RuntimeError('arc() called before from_()')
        dir_l = str(dir).lower()
        if dir_l not in ('ccw', 'cw'):
            raise ValueError("arc dir must be 'ccw' or 'cw'")
        cx0, cy0 = self._cursor
        if centerAt is not None:
            cx, cy = float(centerAt[0]), float(centerAt[1])
        elif center is not None:
            cx = cx0 + float(center[0])
            cy = cy0 + float(center[1])
        else:
            raise ValueError('arc requires center or centerAt')
        if endAt is not None:
            ex, ey = float(endAt[0]), float(endAt[1])
        elif end is not None:
            ex = cx0 + float(end[0])
            ey = cy0 + float(end[1])
        else:
            raise ValueError('arc requires end or endAt')
        # Validate radius
        R = float(radius)
        if not (R > 0.0):
            raise ValueError('arc radius must be > 0')
        # Validate that start and end lie on the circle defined by center/radius
        ds = math.hypot(cx0 - cx, cy0 - cy)
        de = math.hypot(ex - cx, ey - cy)
        # Use combined absolute and relative tolerance to allow rounded inputs
        tol_abs = 1e-4
        tol_rel = 1e-4
        ok_s = math.isclose(ds, R, rel_tol=tol_rel, abs_tol=tol_abs)
        ok_e = math.isclose(de, R, rel_tol=tol_rel, abs_tol=tol_abs)
        if not (ok_s and ok_e):
            raise ValueError(
                f"arc spec inconsistent: start/end not on circle; "
                f"center=({cx},{cy}), radius={R}, start=({cx0},{cy0}) dist={ds}, end=({ex},{ey}) dist={de}"
            )
        sx, sy = cx0, cy0
        # Start/end distinct
        if math.hypot(ex - sx, ey - sy) <= tol_abs:
            raise ValueError("arc start and end coincide; use circle() for full circle or adjust end")
        a_start = math.atan2(sy - cy, sx - cx)
        a_end = math.atan2(ey - cy, ex - cx)
        def norm(a):
            while a < 0:
                a += 2 * math.pi
            while a >= 2 * math.pi:
                a -= 2 * math.pi
            return a
        a_start = norm(a_start)
        a_end = norm(a_end)
        if dir_l == 'ccw':
            delta = a_end - a_start
            if delta < 0:
                delta += 2 * math.pi
        else:
            delta = a_end - a_start
            if delta > 0:
                delta -= 2 * math.pi
        # Reject degenerate sweeps
        tol_ang = 1e-6
        sweep_abs = abs(delta)
        if sweep_abs < tol_ang:
            raise ValueError('arc sweep too small (degenerate); adjust end or direction')
        if abs(sweep_abs - 2 * math.pi) < tol_ang:
            raise ValueError("full-circle arc not supported via arc(); use circle() instead")
        a_mid = a_start + delta / 2.0
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
        if self._geom_current is not None:
            self._geom_current.append(('arc', dict(radius=float(radius), dir=dir, center=(float(cx), float(cy)), end=(float(ex), float(ey)))))

    def close(self):
        import Part
        if self._cursor is None or self._first_point is None:
            return
        if self._cursor != self._first_point:
            self._append_segment(self._cursor, self._first_point)
        wire = Part.Wire(self._poly_edges) if getattr(self, '_poly_edges', None) else None
        self._poly_edges = []
        if wire is not None:
            self._add_wire(wire, self._building_hole)
        self._cursor = None
        self._first_point = None
        self._building_hole = False
        # finalize geometry path
        if self._geom_current is not None:
            self._add_geom_path(self._geom_current, hole=self._building_hole)
            self._geom_current = None

    def _append_segment(self, p0, p1):
        import Part
        a = App.Vector(float(p0[0]), float(p0[1]), 0)
        b = App.Vector(float(p1[0]), float(p1[1]), 0)
        edge = Part.makeLine(a, b)
        if not hasattr(self, '_poly_edges'):
            self._poly_edges = []
        self._poly_edges.append(edge)

    def _add_wire(self, wire, hole):
        if hole:
            self._hole_wires.append(wire)
        else:
            if self._outer_wire is not None:
                raise RuntimeError('Only one outer profile is supported in section v1')
            self._outer_wire = wire

    def build_face_with_holes(self):
        import Part
        # Prefer wires; fallback to geometry via adapter
        if self._outer_wire is not None:
            face = Part.Face(self._outer_wire)
            for hw in self._hole_wires:
                try:
                    face = face.cut(Part.Face(hw))
                except Exception:
                    pass
            return face
        return PartProfileAdapter(self).build_face_with_holes()

    def build_open_wire(self):
        import Part
        if hasattr(self, '_poly_edges') and self._poly_edges:
            return Part.Wire(self._poly_edges)
        if self._outer_wire is not None and not self._hole_wires:
            return Part.Wire(self._outer_wire.Edges)
        # try geometry path (first available path)
        if self._geom_outer:
            return PartProfileAdapter(self).build_open_wire()
        raise RuntimeError('No open path available in section profile')

    def _add_geom_path(self, path_ops, hole=False):
        if hole:
            self._geom_holes.append(list(path_ops))
        else:
            if self._geom_outer is None:
                self._geom_outer = list(path_ops)
            else:
                # treat as additional hole if outer already exists
                self._geom_holes.append(list(path_ops))


class PartProfileAdapter:
    def __init__(self, profile: _SectionProfile):
        self.p = profile

    def build_face_with_holes(self):
        import Part
        # Build from geometry if present
        if self.p._geom_outer:
            outer = self._wire_from_ops(self.p._geom_outer)
            holes = [self._wire_from_ops(h) for h in self.p._geom_holes] if self.p._geom_holes else []
            # Also include any existing wire-based holes captured earlier (e.g., circles)
            if getattr(self.p, '_hole_wires', None):
                holes.extend(self.p._hole_wires)
            face = Part.Face(outer)
            for hw in holes:
                try:
                    face = face.cut(Part.Face(hw))
                except Exception:
                    pass
            return face
        # Fallback: use existing wires
        if self.p._outer_wire is None:
            raise RuntimeError('section requires an outer profile')
        face = Part.Face(self.p._outer_wire)
        for hw in self.p._hole_wires:
            try:
                face = face.cut(Part.Face(hw))
            except Exception:
                pass
        return face

    def build_open_wire(self):
        import Part
        # Prefer finalized outer path
        if self.p._geom_outer:
            return self._wire_from_ops(self.p._geom_outer)
        # Fallback to current in-progress path (open path use-case)
        if getattr(self.p, '_geom_current', None):
            return self._wire_from_ops(self.p._geom_current)
        # Last resort: use existing wires/edges if present
        if hasattr(self.p, '_poly_edges') and self.p._poly_edges:
            return Part.Wire(self.p._poly_edges)
        if self.p._outer_wire is not None and not self.p._hole_wires:
            return Part.Wire(self.p._outer_wire.Edges)
        raise RuntimeError('No open path geometry available')

    def _wire_from_ops(self, ops):
        import Part
        edges = []
        for op in ops:
            if op[0] == 'line':
                x1, y1, x2, y2 = op[1]
                a = App.Vector(x1, y1, 0)
                b = App.Vector(x2, y2, 0)
                edges.append(Part.makeLine(a, b))
            elif op[0] == 'arc':
                data = op[1]
                cx, cy = data['center']
                ex, ey = data['end']
                if edges:
                    sx = float(edges[-1].Vertexes[-1].Point.x)
                    sy = float(edges[-1].Vertexes[-1].Point.y)
                else:
                    continue
                R = float(data['radius'])
                import math
                # angles from center to start/end (note atan2(y,x))
                a_start = math.atan2(sy - cy, sx - cx)
                a_end = math.atan2(ey - cy, ex - cx)
                # normalize to [0, 2pi)
                def norm(a):
                    while a < 0:
                        a += 2 * math.pi
                    while a >= 2 * math.pi:
                        a -= 2 * math.pi
                    return a
                a_start = norm(a_start)
                a_end = norm(a_end)
                # choose mid angle based on desired sweep direction
                direction = str(data.get('dir', 'ccw')).lower()
                if direction == 'ccw':
                    delta = a_end - a_start
                    if delta < 0:
                        delta += 2 * math.pi
                else:  # cw
                    delta = a_end - a_start
                    if delta > 0:
                        delta -= 2 * math.pi
                a_mid = a_start + delta / 2.0
                mid = App.Vector(cx + R * math.cos(a_mid), cy + R * math.sin(a_mid), 0)
                edges.append(Part.Arc(App.Vector(sx, sy, 0), mid, App.Vector(ex, ey, 0)).toShape())
        return Part.Wire(edges)


class SketcherProfileAdapter:
    def __init__(self, section: 'Section'):
        self.section = section
        self.profile = section._profile

    def build_sketch(self, name=None):
        doc = _CTX.doc
        sk_name = name or (self.section.name or 'Sketch')
        try:
            sk = doc.addObject('Sketcher::SketchObject', sk_name)
        except Exception as e:
            raise RuntimeError(f'Cannot create Sketcher object: {e}')
        # Placement per section plane/datum
        pl = App.Placement()
        if getattr(self.section, '_datum_placement', None) is not None:
            pl = self.section._datum_placement
        else:
            if self.section.plane == 'XY':
                pass
            elif self.section.plane == 'XZ':
                pl.Rotation = App.Rotation(App.Vector(1, 0, 0), 90)
            elif self.section.plane == 'YZ':
                pl.Rotation = App.Rotation(App.Vector(0, 1, 0), -90)
            pl.Base = _vec3(self.section.origin)
        sk.Placement = pl
        # Populate geometry from profile paths (outer first, then holes)
        def add_path(ops):
            import Part, math
            last = None
            for op in ops:
                if op[0] == 'line':
                    x1, y1, x2, y2 = op[1]
                    seg = Part.LineSegment(App.Vector(x1, y1, 0), App.Vector(x2, y2, 0))
                    sk.addGeometry(seg, False)
                    last = (x2, y2)
                elif op[0] == 'arc':
                    data = op[1]
                    cx, cy = data['center']
                    ex, ey = data['end']
                    if last is None:
                        continue
                    sx, sy = last
                    # compute mid-point based on direction
                    a_start = math.atan2(sy - cy, sx - cx)
                    a_end = math.atan2(ey - cy, ex - cx)
                    def norm(a):
                        while a < 0:
                            a += 2 * math.pi
                        while a >= 2 * math.pi:
                            a -= 2 * math.pi
                        return a
                    a_start = norm(a_start)
                    a_end = norm(a_end)
                    direction = str(data.get('dir', 'ccw')).lower()
                    if direction == 'ccw':
                        delta = a_end - a_start
                        if delta < 0:
                            delta += 2 * math.pi
                    else:
                        delta = a_end - a_start
                        if delta > 0:
                            delta -= 2 * math.pi
                    a_mid = a_start + delta / 2.0
                    mid = App.Vector(cx + float(data['radius']) * math.cos(a_mid),
                                     cy + float(data['radius']) * math.sin(a_mid), 0)
                    arc3 = Part.Arc(App.Vector(sx, sy, 0), mid, App.Vector(ex, ey, 0))
                    sk.addGeometry(arc3, False)
                    last = (ex, ey)

        # Use finalized outer path if present, else in-progress open path; fallback to wire-based outer
        ops = self.profile._geom_outer if self.profile._geom_outer else getattr(self.profile, '_geom_current', None)
        if ops:
            add_path(ops)
        elif getattr(self.profile, '_outer_wire', None) is not None:
            try:
                for e in self.profile._outer_wire.Edges:
                    if hasattr(e, 'Curve') and e.Curve.__class__.__name__ == 'Circle':
                        sk.addGeometry(e.Curve, False)
                    else:
                        sk.addGeometry(e, False)
            except Exception:
                pass
        for hole_ops in (self.profile._geom_holes or []):
            add_path(hole_ops)
        # also include any pre-existing wire-based holes (e.g., full circle)
        if getattr(self.profile, '_hole_wires', None):
            for hw in self.profile._hole_wires:
                try:
                    for e in hw.Edges if hasattr(hw, 'Edges') else []:
                        # If it's a circle edge, add the circle geometry; otherwise approximate as a line segment
                        if hasattr(e, 'Curve') and e.Curve.__class__.__name__ == 'Circle':
                            sk.addGeometry(e.Curve, False)
                        else:
                            sk.addGeometry(e, False)
                except Exception:
                    pass
        try:
            doc.recompute()
            if hasattr(sk, 'ViewObject'):
                sk.ViewObject.Visibility = bool(getattr(self.section, '_sketch_visible', True))
        except Exception:
            pass
        return sk


def generic_section(materialized: bool = False, name=None, plane='XY', at=(0.0, 0.0, 0.0), visible: bool = True):
    backend = SketcherSectionBackend() if materialized else PartSectionBackend()
    return Section(name=name, plane=plane, at=at, backend=backend, visible=visible)


def section(name=None, plane='XY', at=(0.0, 0.0, 0.0)):
    return generic_section(materialized=False, name=name, plane=plane, at=at)


def sketch(name=None, plane='XY', at=(0.0, 0.0, 0.0), visible: bool = True):
    return generic_section(materialized=True, name=name, plane=plane, at=at, visible=visible)

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



