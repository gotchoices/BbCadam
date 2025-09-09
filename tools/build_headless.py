import sys
import os
from pathlib import Path

import FreeCAD as App

# Ensure BbCadam package importable when run directly by FreeCADCmd
HERE = Path(__file__).resolve()
PKG_PARENT = HERE.parents[2]  # repo root (parent of BbCadam)
if str(PKG_PARENT) not in sys.path:
    sys.path.insert(0, str(PKG_PARENT))

from BbCadam.builder import build_part_script, build_assembly_script


def _detect_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(5):
        if (cur / 'specs').is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    # fallback to current working directory
    return Path.cwd()


def _dump_json(obj, out_path: Path):
    import json
    if obj is None:
        data = {'error': 'no object'}
    else:
        try:
            sh = obj.Shape
            b = sh.BoundBox
            # Sample vertices near Y endpoints to analyze floor/side-wall alignment
            def near(a, b, tol=1e-6):
                return abs(a - b) <= tol
            y0 = b.YMin
            yL = b.YMax
            minZ_y0 = None
            maxZ_y0 = None
            minZ_yL = None
            maxZ_yL = None
            for v in getattr(sh, 'Vertexes', []):
                y = float(v.Point.y)
                z = float(v.Point.z)
                if near(y, y0):
                    minZ_y0 = z if minZ_y0 is None else min(minZ_y0, z)
                    maxZ_y0 = z if maxZ_y0 is None else max(maxZ_y0, z)
                if near(y, yL):
                    minZ_yL = z if minZ_yL is None else min(minZ_yL, z)
                    maxZ_yL = z if maxZ_yL is None else max(maxZ_yL, z)
            data = {
                'name': getattr(obj, 'Name', ''),
                'label': getattr(obj, 'Label', ''),
                'bbox': {'xMin': b.XMin, 'xMax': b.XMax, 'yMin': b.YMin, 'yMax': b.YMax, 'zMin': b.ZMin, 'zMax': b.ZMax},
                'numSolids': len(getattr(sh, 'Solids', [])),
                'numFaces': len(getattr(sh, 'Faces', [])),
                'numEdges': len(getattr(sh, 'Edges', [])),
                'volume': getattr(sh, 'Volume', None),
                'area': getattr(sh, 'Area', None),
                'samples': {
                    'y0': {'minZ': minZ_y0, 'maxZ': maxZ_y0},
                    'yL': {'minZ': minZ_yL, 'maxZ': maxZ_yL},
                },
            }
        except Exception as e:
            data = {'error': str(e)}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"[bbcadam] Dumped JSON: {out_path}")


def main():
    args = sys.argv[1:]
    # Parse optional flags
    repo_root = None
    dump_path = None
    cleaned = []
    it = iter(args)
    for a in it:
        if a == '--project':
            try:
                repo_root = Path(next(it)).resolve()
            except StopIteration:
                print('[bbcadam] --project requires a path')
                sys.exit(2)
            continue
        if a == '--dump-json':
            try:
                dump_path = Path(next(it)).resolve()
            except StopIteration:
                print('[bbcadam] --dump-json requires a path')
                sys.exit(2)
            continue
        cleaned.append(a)
    args = cleaned
    # Support env fallbacks
    if not cleaned:
        env_specs = os.environ.get('BBCADAM_SPECS')
        if env_specs:
            cleaned = env_specs.split(':')
    if dump_path is None:
        env_dump = os.environ.get('BBCADAM_DUMP_JSON')
        if env_dump:
            dump_path = Path(env_dump).resolve()
    if repo_root is None:
        env = os.environ.get('BB_PROJECT_ROOT')
        if env:
            repo_root = Path(env).resolve()
        else:
            # derive from first spec path
            if not cleaned:
                print('Usage: FreeCADCmd BbCadam/tools/build_headless.py [--project PATH] [--dump-json PATH] <spec.py> [more ...]')
                sys.exit(2)
            first = Path(cleaned[0]).resolve()
            repo_root = _detect_repo_root(first.parent)
    last_obj = None
    for arg in cleaned:
        path = Path(arg).resolve()
        if not path.exists():
            print(f'[bbcadam] Spec not found: {path}')
            continue
        try:
            # Heuristic: assemblies folder name contains 'assembl'
            if 'assembl' in str(path.parent).lower():
                out = build_assembly_script(repo_root, path)
            else:
                out = build_part_script(repo_root, path)
            print(f'[bbcadam] Built: {out}')
            try:
                # capture last object by name from doc
                doc = App.ActiveDocument
                last_obj = doc.ActiveObject if hasattr(doc, 'ActiveObject') else out
            except Exception:
                last_obj = out
        except Exception as e:
            import traceback
            App.Console.PrintError(f'[bbcadam] Error: {e}\n{traceback.format_exc()}\n')
    if dump_path is not None:
        _dump_json(last_obj, dump_path)


if __name__ == '__main__':
    main()


