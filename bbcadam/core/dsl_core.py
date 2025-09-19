"""Core DSL helpers (initial: logging facility).

Non-breaking: provide a central log() used by DSL internals. This avoids
duplicating the logging code across modules.
"""

import os
from pathlib import Path

_LOG_ENABLED = os.environ.get('BB_LOG_ENABLE') == '1'
_LOG_TAGS = set(t.strip() for t in os.environ.get('BB_LOG_TAGS', '').split(',') if t.strip())
_LOG_FILE = os.environ.get('BB_LOG_FILE') or ''


def _log_is_enabled(tag: str) -> bool:
    if not _LOG_ENABLED:
        return False
    if not _LOG_TAGS or '*' in _LOG_TAGS:
        return True
    return tag in _LOG_TAGS


def log(tag: str, message: str) -> None:
    if not _log_is_enabled(tag):
        return
    line = f"[{tag}] {message}"
    if _LOG_FILE:
        try:
            p = Path(_LOG_FILE)
            try:
                p.parent.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass
            with p.open('a', encoding='utf-8') as fh:
                fh.write(line + "\n")
            return
        except Exception:
            pass
    try:
        import FreeCAD as App  # type: ignore
        App.Console.PrintMessage(line + "\n")
    except Exception:
        try:
            print(line)
        except Exception:
            pass


__all__ = ["log", "_log_is_enabled"]

# -------- Context and Feature primitives --------

try:
    import FreeCAD as App  # type: ignore
except Exception:  # pragma: no cover
    App = None  # type: ignore

_CTX = None
_STATE = {
    'base_shape': None,
    'pending_feature': None,
    'view': {},
}


def _set_ctx(ctx):
    global _CTX
    _CTX = ctx


def _reset_state():
    _STATE['base_shape'] = None
    _STATE['pending_feature'] = None


def _vec3(p):
    x, y, z = p
    return App.Vector(float(x), float(y), float(z))


class Feature:
    def __init__(self, shape):
        self.shape = shape

    def at(self, pos):
        self.shape.translate(_vec3(pos))
        return self

    def translate(self, by):
        self.shape.translate(_vec3(by))
        return self

    def rotate(self, axis=(0, 0, 1), deg=0):
        ax = App.Vector(*axis)
        self.shape.rotate(App.Vector(0, 0, 0), ax, float(deg))
        return self

    def add(self):
        _commit_pending_if_any(skip_shape=self.shape)
        _apply_add(self.shape)
        return self

    def cut(self):
        _commit_pending_if_any(skip_shape=self.shape)
        _apply_cut(self.shape)
        return self

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
        _STATE['base_shape'] = _STATE['base_shape'].cut(shape)


def _finish_build(part_name='Part'):
    _commit_pending_if_any()
    if _STATE['base_shape'] is None:
        return None
    doc = _CTX.doc
    obj = doc.addObject('Part::Feature', part_name)
    obj.Shape = _STATE['base_shape']
    try:
        v = _STATE.get('view') or {}
        if hasattr(obj, 'ViewObject') and obj.ViewObject is not None:
            if 'opacity' in v:
                obj.ViewObject.Transparency = int(v['opacity'])
            if 'color' in v:
                c = v['color']
                obj.ViewObject.ShapeColor = (float(c[0]), float(c[1]), float(c[2]))
    except Exception:
        pass
    try:
        _CTX.doc.recompute()
    except Exception:
        pass
    return obj


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
    import ast as _ast

    def _get(n: str):
        if n not in env:
            raise KeyError(n)
        v = env[n]
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str) and v.strip().startswith('='):
            return float(_eval_expr(v.strip()[1:], env))
        if isinstance(v, str):
            return float(v)
        raise ValueError(f'Bad param {n}')

    def _ev(node):
        if isinstance(node, _ast.Expression):
            return _ev(node.body)
        if isinstance(node, _ast.BinOp):
            a = _ev(node.left); b = _ev(node.right)
            import ast as _a
            if isinstance(node.op, _a.Add): return a + b
            if isinstance(node.op, _a.Sub): return a - b
            if isinstance(node.op, _a.Mult): return a * b
            if isinstance(node.op, _a.Div): return a / b
            raise ValueError('Unsupported op')
        if isinstance(node, _ast.UnaryOp):
            v = _ev(node.operand)
            import ast as _a
            if isinstance(node.op, _a.UAdd): return +v
            if isinstance(node.op, _a.USub): return -v
            raise ValueError('Unsupported unary')
        if isinstance(node, _ast.Name):
            return _get(node.id)
        if isinstance(node, _ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        raise ValueError('Unsupported expr element')

    tree = _ast.parse(expr, mode='eval')
    return _ev(tree)


# -------- Helpers: lcs/add_lcs and feature() composer --------

def lcs(name, at=(0, 0, 0), rot_xyz_deg=(0, 0, 0)):
    doc = _CTX.doc
    obj = None
    try:
        obj = doc.getObject(name)
    except Exception:
        obj = None
    if obj is None:
        obj = doc.addObject('Part::Feature', name)
    # Update placement
    obj.Placement.Base = _vec3(at)
    try:
        rx, ry, rz = float(rot_xyz_deg[0]), float(rot_xyz_deg[1]), float(rot_xyz_deg[2])
        if any(abs(a) > 1e-12 for a in (rx, ry, rz)):
            rX = App.Rotation(App.Vector(1, 0, 0), rx)
            rY = App.Rotation(App.Vector(0, 1, 0), ry)
            rZ = App.Rotation(App.Vector(0, 0, 1), rz)
            obj.Placement.Rotation = rZ.multiply(rY).multiply(rX)
    except Exception:
        pass
    return obj


add_lcs = lcs


class _FeatureComposer:
    def __init__(self):
        self.shape = None

    def box(self, size, at=None):
        from . import primitives as prim
        sh = prim.box(size, at).shape
        self._add(sh)
        return self

    def cylinder(self, d=None, r=None, h=None, at=None):
        from . import primitives as prim
        sh = prim.cylinder(d=d, r=r, h=h, at=at).shape
        self._add(sh)
        return self

    def _add(self, new_shape):
        if self.shape is None:
            self.shape = new_shape
        else:
            self.shape = self.shape.fuse(new_shape)

    def add(self):
        _commit_pending_if_any()
        _apply_add(self.shape)

    def cut(self):
        _commit_pending_if_any()
        _apply_cut(self.shape)


class feature:
    def __enter__(self):
        self.comp = _FeatureComposer()
        return self.comp

    def __exit__(self, exc_type, exc, tb):
        return False

# -------- Export helpers (used by api.export) --------

def shape_summary(shape):
    """Create a compact, deterministic JSON-serializable summary for tests."""
    bb = shape.BoundBox
    try:
        com = shape.CenterOfMass
        com_list = [float(com.x), float(com.y), float(com.z)]
    except Exception:
        com_list = [0.0, 0.0, 0.0]
    faces = getattr(shape, 'Faces', []) or []
    edges = getattr(shape, 'Edges', []) or []
    face_count = len(faces)
    edge_count = len(edges)
    try:
        vol = float(shape.Volume)
    except Exception:
        vol = 0.0
    try:
        area = float(shape.Area)
    except Exception:
        area = 0.0
    try:
        shash = int(shape.hashCode(1e-6))
    except Exception:
        shash = 0
    circle_edges = 0
    line_edges = 0
    other_edges = 0
    circle_edge_lengths = []
    try:
        for e in edges:
            try:
                cname = getattr(getattr(e, 'Curve', None), '__class__', type(None)).__name__
            except Exception:
                cname = None
            if cname in ('Circle', 'ArcOfCircle'):
                circle_edges += 1
                try:
                    circle_edge_lengths.append(float(e.Length))
                except Exception:
                    pass
            elif cname in ('Line', 'LineSegment'):
                line_edges += 1
            else:
                other_edges += 1
    except Exception:
        pass
    return {
        'shape_hash': shash,
        'bbox': [float(bb.XMin), float(bb.YMin), float(bb.ZMin), float(bb.XMax), float(bb.YMax), float(bb.ZMax)],
        'volume': vol,
        'area': area,
        'center_of_mass': com_list,
        'counts': {
            'faces': face_count,
            'edges': edge_count,
            'vertices': len(getattr(shape, 'Vertexes', []) or []),
            'edge_kinds': {'circle': circle_edges, 'line': line_edges, 'other': other_edges},
        },
        'edge_metrics': {
            'circle_lengths': circle_edge_lengths,
        },
        'version': 1,
    }


def export_step(obj, out_path):
    try:
        import Import
        out_path.parent.mkdir(parents=True, exist_ok=True)
        Import.export([obj], str(out_path))
    except Exception:
        import Part
        Part.export([obj], str(out_path))


def export_stl(obj, out_path):
    try:
        import Mesh
        out_path.parent.mkdir(parents=True, exist_ok=True)
        Mesh.export([obj], str(out_path))
    except Exception as e:
        try:
            import FreeCAD as App  # type: ignore
            App.Console.PrintError(f"[bbcadam] STL export failed: {e}\n")
        except Exception:
            pass


def export_formats(ctx, obj, kinds=None, name=None, to=None):
    import json as _json
    from pathlib import Path as _Path
    # Resolve kinds
    kinds_list = []
    if kinds is not None:
        kinds_list = [kinds] if isinstance(kinds, str) else list(kinds)
    else:
        try:
            p = ctx.params.get('export')
        except Exception:
            p = None
        if p:
            kinds_list = [p] if isinstance(p, str) else list(p)
        else:
            ex = getattr(ctx, 'settings', {}).get('exports', {}) if hasattr(ctx, 'settings') else {}
            if ex.get('step'):
                kinds_list.append('step')
            if ex.get('stl'):
                kinds_list.append('stl')
            if not kinds_list:
                kinds_list = ['step', 'stl']

    part_name = name or ctx.part_name
    # JSON
    if 'json' in kinds_list:
        data = shape_summary(obj.Shape)
        s = _json.dumps(data, separators=(',', ':'), sort_keys=True)
        if to == '-':
            try:
                import FreeCAD as App  # type: ignore
                App.Console.PrintMessage(s + "\n")
            except Exception:
                print(s)
        elif to:
            out_path = _Path(to)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(s)
        else:
            out_path = ctx.paths.parts / f"{part_name}.json"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(s)

    # BREP
    if 'brep' in kinds_list:
        if to == '-':
            try:
                txt = obj.Shape.exportBrepToString()
                import FreeCAD as App  # type: ignore
                App.Console.PrintMessage(txt + "\n")
            except Exception:
                pass
        elif to:
            out_path = _Path(to)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            obj.Shape.exportBrep(str(out_path))
        else:
            out_path = ctx.paths.parts / f"{part_name}.brep"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            obj.Shape.exportBrep(str(out_path))

    # STEP
    if 'step' in kinds_list:
        export_step(obj, ctx.paths.step_parts / f"{part_name}.step")

    # STL
    if 'stl' in kinds_list:
        export_stl(obj, ctx.paths.stl_parts / f"{part_name}.stl")



