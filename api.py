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
        _commit_pending_if_any()
        _apply_add(self.shape)
        return self

    def cut(self):
        _commit_pending_if_any()
        _apply_cut(self.shape)
        return self


def _commit_pending_if_any():
    pf = _STATE.get('pending_feature')
    if pf is not None:
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


