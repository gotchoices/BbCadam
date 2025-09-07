import importlib.util
import json
import sys
from pathlib import Path

import FreeCAD as App

from . import api as dsl


class Paths:
    def __init__(self, root: Path):
        self.root = root
        self.build_parts = root / 'build' / 'parts'
        self.build_asms = root / 'build' / 'assemblies'
        self.step_parts = root / 'exports' / 'step' / 'parts'
        self.step_asms = root / 'exports' / 'step' / 'assemblies'
        self.stl_parts = root / 'exports' / 'stl' / 'parts'
        self.stl_asms = root / 'exports' / 'stl' / 'assemblies'
        for p in [self.build_parts, self.build_asms, self.step_parts, self.step_asms, self.stl_parts, self.stl_asms]:
            p.mkdir(parents=True, exist_ok=True)


class Ctx:
    def __init__(self, doc, part_name, params, settings, root: Path):
        self.doc = doc
        self.part_name = part_name
        self.params = params or {}
        self.settings = settings or {}
        self.paths = Paths(root)
        self.log = App.Console
        self.units = self.settings.get('units', 'in')


def _read_yaml_or_json(path: Path):
    if path.suffix.lower() == '.json':
        with path.open('r') as f:
            return json.load(f)
    try:
        import yaml
    except Exception as e:
        raise RuntimeError(f'PyYAML is required: {e}')
    with path.open('r') as f:
        return yaml.safe_load(f)


def _merge_params(project_params, part_params):
    out = {}
    if project_params:
        out.update(project_params)
    if part_params:
        out.update(part_params)
    return out


def _load_script(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[path.stem] = mod
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _detect_repo_root_from_script(script_path: Path) -> Path:
    cur = script_path.parent.resolve()
    for _ in range(6):
        if (cur / 'specs').is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return script_path.parent


def build_part_script(repo_root: Path, script_path: Path):
    # Choose effective root (prefer provided, but fall back to script-based detection)
    root = repo_root if (repo_root / 'specs').is_dir() else _detect_repo_root_from_script(script_path)
    # Resolve names and params
    part_name = script_path.stem
    project_params = _safe_read(root / 'config' / 'params.yaml')
    part_params = _safe_read(script_path.parent / 'params.yaml')
    params = _merge_params(project_params, part_params)
    settings = _safe_read(root / 'config' / 'settings.yaml') or {}

    # Document lifecycle
    doc_name = f'part__{part_name}'
    try:
        old = App.getDocument(doc_name)
        if old:
            App.closeDocument(doc_name)
    except Exception:
        pass
    doc = App.newDocument(doc_name)

    # Context and DSL setup
    ctx = Ctx(doc, part_name, params, settings, root)
    dsl._set_ctx(ctx)
    try:
        dsl._reset_state()
    except Exception:
        pass

    mod = _load_script(script_path)
    # Inject DSL symbols so scripts can call them without explicit imports
    for _name in ['box', 'cylinder', 'feature', 'lcs', 'add_lcs', 'param', 'export', 'export_step', 'export_stl']:
        try:
            setattr(mod, _name, getattr(dsl, _name))
        except Exception:
            pass
    fn = getattr(mod, 'build_part', None)
    if not callable(fn):
        raise RuntimeError('build_part(ctx) not found')
    fn(ctx)

    # Finalize and save FCStd
    obj = dsl._finish_build(part_name)
    out_fcstd = ctx.paths.build_parts / f'{part_name}.FCStd'
    if obj:
        doc.saveAs(str(out_fcstd))
        App.Console.PrintMessage(f"[bbcadam] Rebuilt part: {script_path} → {out_fcstd}\n")
        try:
            import FreeCADGui as Gui  # type: ignore
            if Gui.ActiveDocument and Gui.ActiveDocument.ActiveView:
                Gui.ActiveDocument.ActiveView.fitAll()
        except Exception:
            pass
    return out_fcstd


def _safe_read(path: Path):
    try:
        if path.exists():
            return _read_yaml_or_json(path)
    except Exception as e:
        App.Console.PrintError(f'[bbcadam] Failed reading {path}: {e}\n')
    return None


def build_assembly_script(repo_root: Path, script_path: Path):
    # Choose effective root
    root = repo_root if (repo_root / 'specs').is_dir() else _detect_repo_root_from_script(script_path)
    asm_name = script_path.stem
    project_params = _safe_read(root / 'config' / 'params.yaml')
    asm_params = _safe_read(script_path.parent / 'params.yaml')
    params = _merge_params(project_params, asm_params)
    settings = _safe_read(root / 'config' / 'settings.yaml') or {}

    doc_name = f'asm__{asm_name}'
    try:
        old = App.getDocument(doc_name)
        if old:
            App.closeDocument(doc_name)
    except Exception:
        pass
    doc = App.newDocument(doc_name)

    ctx = Ctx(doc, asm_name, params, settings, root)
    dsl._set_ctx(ctx)
    try:
        dsl._reset_state()
    except Exception:
        pass

    # Minimal assembly fluent API
    def component(path: str, as_name: str = None):
        p = Path(path)
        if not p.is_absolute():
            p = (script_path.parent / p).resolve()
        if not p.exists():
            alt = ctx.paths.build_parts / (p.stem + '.FCStd')
            if alt.exists():
                p = alt
        link = doc.addObject('App::Link', as_name or p.stem)
        link.setLink(str(p))

        class Comp:
            def at(self, pos):
                link.Placement.Base = App.Vector(float(pos[0]), float(pos[1]), float(pos[2]))
                return self

            def rotate(self, axis=(0, 0, 1), deg=0):
                # Simple rotation around origin axis
                return self

            def rot_xyz_deg(self, r):
                # Placeholder for explicit Euler rotations
                return self

        return Comp()

    # Inject assembly helpers into module globals by calling script with a globals dict
    mod = _load_script(script_path)
    # Bind helper into module
    setattr(mod, 'component', component)
    setattr(mod, 'lcs', dsl.lcs)
    setattr(mod, 'export', dsl.export)
    setattr(mod, 'param', dsl.param)
    fn = getattr(mod, 'build_assembly', None)
    if not callable(fn):
        raise RuntimeError('build_assembly(ctx) not found')
    fn(ctx)

    out_fcstd = ctx.paths.build_asms / f'{asm_name}.FCStd'
    doc.recompute()
    doc.saveAs(str(out_fcstd))
    App.Console.PrintMessage(f"[bbcadam] Rebuilt assembly: {script_path} → {out_fcstd}\n")
    try:
        import FreeCADGui as Gui  # type: ignore
        if Gui.ActiveDocument and Gui.ActiveDocument.ActiveView:
            Gui.ActiveDocument.ActiveView.fitAll()
    except Exception:
        pass
    return out_fcstd


