import os
import sys
from pathlib import Path

import FreeCAD as App
import FreeCADGui as Gui

try:
    from PySide6.QtCore import QFileSystemWatcher, QTimer
except Exception:
    from PySide2.QtCore import QFileSystemWatcher, QTimer

# Ensure we can import the package regardless of how this macro is executed
_PKG_ROOT = Path(__file__).resolve().parents[1]
_SYS_ROOT = _PKG_ROOT.parent
if str(_SYS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SYS_ROOT))

from BbCadam.builder import build_part_script, build_assembly_script
App.Console.PrintMessage('[bbcadam] Watcher module loaded.\n')


def _detect_repo_root(start: Path) -> Path:
    # If a specs folder exists in or above, use its parent as repo root; else use CWD
    cur = start.resolve()
    for _ in range(10):
        specs = cur / 'specs'
        if specs.exists() and specs.is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return start


class SpecWatcher:
    def __init__(self, start_dir: Path):
        env_root = os.environ.get('BB_PROJECT_ROOT')
        if env_root:
            self.repo_root = Path(env_root).resolve()
        else:
            self.repo_root = _detect_repo_root(start_dir)
        self.specs_dir = self.repo_root / 'specs'
        self.watcher = QFileSystemWatcher()
        self.debounce = {}
        self.known_files = set()
        self.known_dirs = set()

        # Choose what to watch
        if self.specs_dir.exists():
            base_dirs = [self.specs_dir / 'parts', self.specs_dir / 'assemblies']
        else:
            base_dirs = [self.repo_root]

        for d in base_dirs:
            if d.exists():
                self.watcher.addPath(str(d))
        self.watcher.directoryChanged.connect(self._on_dir)
        self.watcher.fileChanged.connect(self._on_file)
        self._rescan()
        App.Console.PrintMessage(f"[bbcadam] Watching under: {', '.join(map(str, base_dirs))}\n")

    def _rescan(self):
        exts = ('.py', '.yaml', '.yml')
        current_files = set()
        current_dirs = set()
        search_roots = []
        if self.specs_dir.exists():
            search_roots = [self.specs_dir / 'parts', self.specs_dir / 'assemblies']
        else:
            search_roots = [self.repo_root]
        for base in search_roots:
            if not base.exists():
                continue
            for root, dirs, files in os.walk(base):
                current_dirs.add(str(root))
                for f in files:
                    if f.lower().endswith(exts):
                        current_files.add(str(Path(root) / f))
        # Add new dirs
        for d in current_dirs - self.known_dirs:
            try:
                self.watcher.addPath(d)
            except Exception:
                pass
        self.known_dirs = current_dirs
        # Add files
        for p in current_files - self.known_files:
            try:
                self.watcher.addPath(p)
            except Exception:
                pass
        self.known_files = current_files

    def _on_dir(self, _):
        self._rescan()

    def _on_file(self, path):
        if os.path.exists(path) and path not in self.watcher.files():
            try:
                self.watcher.addPath(path)
            except Exception:
                pass
        t = self.debounce.get(path)
        if not t:
            t = QTimer()
            t.setSingleShot(True)
            t.timeout.connect(lambda p=path: self._rebuild(Path(p)))
            self.debounce[path] = t
        t.start(250)

    def _rebuild(self, path: Path):
        try:
            if self.specs_dir.exists() and (self.specs_dir / 'parts') in path.parents:
                if path.suffix.lower() == '.py':
                    build_part_script(self.repo_root, path)
                else:
                    self._rebuild_part_for_params(path)
            elif self.specs_dir.exists() and (self.specs_dir / 'assemblies') in path.parents:
                if path.suffix.lower() == '.py':
                    build_assembly_script(self.repo_root, path)
                else:
                    self._rebuild_assembly_for_params(path)
            else:
                # cwd mode: decide by folder name
                if path.suffix.lower() == '.py':
                    if '/assembl' in str(path.parent).lower():
                        build_assembly_script(self.repo_root, path)
                    else:
                        build_part_script(self.repo_root, path)
                else:
                    # params change in cwd mode: attempt local rebuild
                    self._rebuild_part_for_params(path)
        except Exception as e:
            import traceback
            App.Console.PrintError(f"[bbcadam] Error rebuilding {path}: {e}\n{traceback.format_exc()}\n")

    def _rebuild_part_for_params(self, changed: Path):
        # Given a params change under specs/parts/<part>/, rebuild the sibling .py
        part_dir = changed.parent if changed.is_file() else changed
        # Prefer <dir_name>.py, else any .py in the folder
        preferred = part_dir / f"{part_dir.name}.py"
        if preferred.exists():
            build_part_script(self.repo_root, preferred)
            return
        # fallback: first .py in dir
        for p in part_dir.glob('*.py'):
            build_part_script(self.repo_root, p)
            return

    def _rebuild_assembly_for_params(self, changed: Path):
        asm_dir = changed.parent if changed.is_file() else changed
        preferred = asm_dir / f"{asm_dir.name}.py"
        if preferred.exists():
            build_assembly_script(self.repo_root, preferred)
            return
        for p in asm_dir.glob('*.py'):
            build_assembly_script(self.repo_root, p)
            return


WATCHER = None


def run():
    global WATCHER
    if WATCHER is None:
        # Prefer explicit BB_PROJECT_ROOT if set; else cwd; else active doc location
        env = os.environ.get('BB_PROJECT_ROOT')
        if env:
            start = Path(env)
        else:
            start = Path.cwd()
            try:
                if App.ActiveDocument and App.ActiveDocument.FileName:
                    start = Path(App.ActiveDocument.FileName).parent
            except Exception:
                pass
        WATCHER = SpecWatcher(start)
    else:
        App.Console.PrintMessage('[bbcadam] Watcher already running.\n')

# Call run() on import to ensure it starts when executed as a macro or via CLI
run()


