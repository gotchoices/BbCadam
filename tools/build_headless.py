import sys
from pathlib import Path

import FreeCAD as App

from ..builder import build_part_script, build_assembly_script


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


def main():
    args = sys.argv[1:]
    if not args:
        print('Usage: FreeCADCmd BbCadam/tools/build_headless.py [--project PATH] <spec.py> [more ...]')
        sys.exit(2)
    # Parse optional --project
    repo_root = None
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
        cleaned.append(a)
    args = cleaned
    if repo_root is None:
        env = os.environ.get('BB_PROJECT_ROOT')
        if env:
            repo_root = Path(env).resolve()
        else:
            # derive from first spec path
            first = Path(args[0]).resolve()
            repo_root = _detect_repo_root(first.parent)
    for arg in args:
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
        except Exception as e:
            import traceback
            App.Console.PrintError(f'[bbcadam] Error: {e}\n{traceback.format_exc()}\n')


if __name__ == '__main__':
    main()


