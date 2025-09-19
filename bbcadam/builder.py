import importlib.util
import json
import sys
from pathlib import Path

import FreeCAD as App

# Use package-level DSL facade (prefers new scaffold; api remains as reference)
import bbcadam as dsl


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

    # Capture original active doc and camera to restore after rebuild
    orig_doc_name = None
    orig_cam = None
    try:
        import FreeCADGui as Gui  # type: ignore
        if Gui.ActiveDocument:
            orig_doc_name = Gui.ActiveDocument.Name
            if Gui.ActiveDocument.ActiveView:
                orig_cam = Gui.ActiveDocument.ActiveView.getCamera()
    except Exception:
        pass

    # Document lifecycle: reuse existing doc to preserve view; remove prior result object if present
    doc_name = f'part__{part_name}'
    doc = None
    try:
        doc = App.getDocument(doc_name)
    except Exception:
        doc = None
    if doc is None:
        doc = App.newDocument(doc_name)
    else:
        try:
            prior = doc.getObject(part_name)
            if prior:
                doc.removeObject(prior.Name)
        except Exception:
            pass

    # Context and DSL setup
    ctx = Ctx(doc, part_name, params, settings, root)
    dsl._set_ctx(ctx)
    try:
        dsl._reset_state()
    except Exception:
        pass

    mod = _load_script(script_path)
    # Inject DSL symbols so scripts can call them without explicit imports
    for _name in ['box', 'cylinder', 'feature', 'profile', 'sketch', 'generic_section', 'lcs', 'add_lcs', 'param', 'export', 'export_step', 'export_stl']:
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
        # Restore original active doc and camera on next GUI tick only; do not touch other docs
        try:
            import FreeCADGui as Gui  # type: ignore
            try:
                from PySide6.QtCore import QTimer
            except Exception:
                from PySide2.QtCore import QTimer  # type: ignore
            def _restore_part_view():
                try:
                    if orig_doc_name:
                        try:
                            App.setActiveDocument(orig_doc_name)
                        except Exception:
                            pass
                        try:
                            Gui.activateDocument(orig_doc_name)
                        except Exception:
                            pass
                    if orig_cam and Gui.ActiveDocument and Gui.ActiveDocument.ActiveView:
                        Gui.ActiveDocument.ActiveView.setCamera(orig_cam)
                except Exception:
                    pass
            QTimer.singleShot(0, _restore_part_view)
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

    # Capture original active doc and camera to restore after rebuild
    orig_doc_name = None
    orig_cam = None
    try:
        import FreeCADGui as Gui  # type: ignore
        if Gui.ActiveDocument:
            orig_doc_name = Gui.ActiveDocument.Name
            if Gui.ActiveDocument.ActiveView:
                orig_cam = Gui.ActiveDocument.ActiveView.getCamera()
    except Exception:
        pass

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
        # If given a part script, prefer linking to the saved FCStd to avoid transient link breaks
        target_obj = None
        target_doc = None
        if p.suffix.lower() == '.py':
            part_name = p.stem
            fc = ctx.paths.build_parts / f"{part_name}.FCStd"
            if not fc.exists():
                try:
                    build_part_script(root, p)
                except Exception:
                    pass
            if fc.exists():
                try:
                    target_doc = App.openDocument(str(fc))
                except Exception:
                    try:
                        target_doc = App.getDocument(fc.stem)
                    except Exception:
                        target_doc = None
                # Re-activate the assembly doc to keep focus
                try:
                    import FreeCADGui as Gui  # type: ignore
                    Gui.activateDocument(doc_name)
                except Exception:
                    pass
                if target_doc:
                    target_obj = target_doc.getObject(part_name)
                    if target_obj is None:
                        try:
                            feats = [o for o in target_doc.Objects if hasattr(o, 'Shape')]
                            target_obj = feats[0] if feats else None
                        except Exception:
                            target_obj = None
            # fallback: if FCStd still missing, try live doc
            if target_obj is None:
                try:
                    target_doc = App.getDocument(f'part__{part_name}')
                    if target_doc:
                        target_obj = target_doc.getObject(part_name)
                except Exception:
                    target_obj = None
        else:
            # FCStd path: open if needed and pick primary feature
            if not p.exists():
                alt = ctx.paths.build_parts / (p.stem + '.FCStd')
                if alt.exists():
                    p = alt
            try:
                target_doc = App.openDocument(str(p))
            except Exception:
                try:
                    target_doc = App.getDocument(p.stem)
                except Exception:
                    target_doc = None
            # Re-activate the assembly doc to keep focus
            try:
                import FreeCADGui as Gui  # type: ignore
                Gui.activateDocument(doc_name)
            except Exception:
                pass
            if target_doc:
                # prefer object named like the file stem
                target_obj = target_doc.getObject(p.stem)
                if target_obj is None:
                    try:
                        feats = [o for o in target_doc.Objects if hasattr(o, 'Shape')]
                        target_obj = feats[0] if feats else None
                    except Exception:
                        target_obj = None

        link_name = as_name or (p.stem if p.stem else 'Component')
        link = doc.addObject('App::Link', link_name)
        linked_ok = False
        if target_obj is not None:
            try:
                link.setLink(target_obj)
                linked_ok = True
            except Exception:
                try:
                    link.LinkedObject = target_obj
                    linked_ok = True
                except Exception:
                    linked_ok = False
        if not linked_ok:
            # Fallback: copy shape into a Part::Feature so the assembly isn't empty
            try:
                doc.removeObject(link.Name)
            except Exception:
                pass
            try:
                if target_obj is not None and hasattr(target_obj, 'Shape'):
                    pf = doc.addObject('Part::Feature', link_name)
                    pf.Shape = target_obj.Shape.copy()
                    link = pf  # use pf for placement API below
                else:
                    App.Console.PrintWarning(f"[bbcadam] component: could not resolve target for {p}\n")
            except Exception as e:
                App.Console.PrintWarning(f"[bbcadam] component fallback failed: {e}\n")

        class Comp:
            def at(self, pos):
                link.Placement.Base = App.Vector(float(pos[0]), float(pos[1]), float(pos[2]))
                return self

            def rotate(self, axis=(0, 0, 1), deg=0):
                try:
                    ax = App.Vector(float(axis[0]), float(axis[1]), float(axis[2]))
                    rot = App.Rotation(ax, float(deg))
                    pl = link.Placement
                    pl.Rotation = rot.multiply(pl.Rotation)
                    link.Placement = pl
                except Exception:
                    pass
                return self

            def rot_xyz_deg(self, r):
                try:
                    rx, ry, rz = float(r[0]), float(r[1]), float(r[2])
                    rX = App.Rotation(App.Vector(1, 0, 0), rx)
                    rY = App.Rotation(App.Vector(0, 1, 0), ry)
                    rZ = App.Rotation(App.Vector(0, 0, 1), rz)
                    rot = rZ.multiply(rY).multiply(rX)
                    pl = link.Placement
                    pl.Rotation = rot.multiply(pl.Rotation)
                    link.Placement = pl
                except Exception:
                    pass
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
    # Restore original active doc and camera on next GUI tick
    try:
        import FreeCADGui as Gui  # type: ignore
        try:
            from PySide6.QtCore import QTimer
        except Exception:
            from PySide2.QtCore import QTimer  # type: ignore
        def _restore_asm_view():
            try:
                if orig_doc_name:
                    try:
                        App.setActiveDocument(orig_doc_name)
                    except Exception:
                        pass
                    try:
                        Gui.activateDocument(orig_doc_name)
                    except Exception:
                        pass
                if orig_cam and Gui.ActiveDocument and Gui.ActiveDocument.ActiveView:
                    Gui.ActiveDocument.ActiveView.setCamera(orig_cam)
            except Exception:
                pass
        QTimer.singleShot(0, _restore_asm_view)
    except Exception:
        pass
    return out_fcstd


