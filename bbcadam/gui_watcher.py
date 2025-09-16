"""
GUI Watcher for BbCadam (runs inside FreeCAD GUI).

Behavior:
- Watches a user-specified directory (and subdirectories) for .py/.yaml/.yml changes.
- On change, classifies the target as part/assembly based on function defs and triggers
  the corresponding build using the existing builder API (build_part_script/build_assembly_script).

Environment variables honored:
- BB_PROJECT_ROOT: project root directory
- BB_WATCH_DIR: directory to watch (defaults to <project_root>/specs if present, else project root)
- BB_BUILD_DIR: output directory (used by builder logic)
- BB_WATCH_VERBOSE: if set/non-empty, print verbose events
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import FreeCAD as App
import FreeCADGui as Gui

try:  # PySide6 on newer FreeCADs
    from PySide6.QtCore import QFileSystemWatcher, QTimer
except Exception:  # Fallback to PySide2
    from PySide2.QtCore import QFileSystemWatcher, QTimer


# Ensure the directory containing the 'bbcadam' package is importable
# FreeCAD runs this script directly, so we add the project root (BbCadam/) to sys.path
_PACKAGE_PARENT = Path(__file__).resolve().parents[1]  # .../BbCadam
if str(_PACKAGE_PARENT) not in sys.path:
    sys.path.insert(0, str(_PACKAGE_PARENT))

from bbcadam.builder import build_part_script, build_assembly_script  # noqa: E402


def _resolve_project_root() -> Path:
    env_root = os.environ.get("BB_PROJECT_ROOT")
    if env_root:
        return Path(env_root).resolve()
    # Fallback: try to detect a specs folder above CWD
    cur = Path.cwd().resolve()
    for _ in range(10):
        if (cur / "specs").is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return Path.cwd().resolve()


def _resolve_watch_dir(project_root: Path) -> Path:
    env_watch = os.environ.get("BB_WATCH_DIR")
    if env_watch:
        return Path(env_watch).resolve()
    specs = project_root / "specs"
    return specs if specs.exists() else project_root


def _classify_script(py_path: Path) -> str:
    try:
        text = py_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return "part"
    if re.search(r"def\s+build_assembly\s*\(", text):
        return "assembly"
    if re.search(r"def\s+build_part\s*\(", text):
        return "part"
    return "part"


def _find_controller_script(changed: Path) -> Path | None:
    base_dir = changed.parent if changed.is_file() else changed
    preferred = base_dir / f"{base_dir.name}.py"
    if preferred.exists():
        return preferred
    for p in base_dir.glob("*.py"):
        return p
    return None


class GuiSpecWatcher:
    def __init__(self) -> None:
        self.verbose = bool(os.environ.get("BB_WATCH_VERBOSE"))
        self.project_root = _resolve_project_root()
        self.watch_dir = _resolve_watch_dir(self.project_root)
        self.watcher = QFileSystemWatcher()
        self.debounce: dict[str, QTimer] = {}
        self.known_files: set[str] = set()
        self.known_dirs: set[str] = set()
        self.mtimes: dict[str, float] = {}

        # Periodic polling timer to detect metadata-only changes (e.g., touch) reliably
        self.scan_timer = QTimer()
        self.scan_timer.setInterval(750)  # ms
        self.scan_timer.timeout.connect(self._poll)
        self.scan_timer.start()

        # Initial scan and attach
        self._rescan()
        self.watcher.directoryChanged.connect(self._on_dir)
        self.watcher.fileChanged.connect(self._on_file)
        App.Console.PrintMessage(f"[bbcadam] GUI watcher active. Root: {self.project_root}\n")
        App.Console.PrintMessage(f"[bbcadam] Watching (recursive): {self.watch_dir}\n")

    def _rescan(self) -> None:
        exts = (".py", ".yaml", ".yml")
        current_files: set[str] = set()
        current_dirs: set[str] = set()
        base = self.watch_dir
        if not base.exists():
            return
        for root, _dirs, files in os.walk(str(base)):
            current_dirs.add(root)
            for f in files:
                if f.lower().endswith(exts):
                    current_files.add(str(Path(root) / f))
        # add new dirs
        for d in current_dirs - self.known_dirs:
            try:
                self.watcher.addPath(d)
            except Exception:
                pass
        self.known_dirs = current_dirs
        # add files
        for p in current_files - self.known_files:
            try:
                self.watcher.addPath(p)
            except Exception:
                pass
        self.known_files = current_files
        # update mtimes snapshot
        for p in list(self.known_files):
            try:
                self.mtimes[p] = os.path.getmtime(p)
            except Exception:
                self.mtimes.pop(p, None)

    def _poll(self) -> None:
        # Periodic scan for changes by mtime
        self._rescan()
        changed: list[str] = []
        for p in list(self.known_files):
            try:
                mt = os.path.getmtime(p)
            except Exception:
                continue
            old = self.mtimes.get(p)
            if old is not None and mt != old:
                changed.append(p)
                self.mtimes[p] = mt
        for p in changed:
            if self.verbose:
                App.Console.PrintMessage(f"[bbcadam] poll detected change: {p}\n")
            self._queue_rebuild(Path(p))

    def _on_dir(self, _path: str) -> None:
        self._rescan()
        # Detect metadata-only changes (e.g., touch) by mtime diff
        changed: list[str] = []
        for p in list(self.known_files):
            try:
                mt = os.path.getmtime(p)
            except Exception:
                continue
            old = self.mtimes.get(p)
            if old is not None and mt != old:
                changed.append(p)
                self.mtimes[p] = mt
        for p in changed:
            if self.verbose:
                App.Console.PrintMessage(f"[bbcadam] dir scan detected change: {p}\n")
            self._queue_rebuild(Path(p))

    def _on_file(self, path: str) -> None:
        if self.verbose:
            App.Console.PrintMessage(f"[bbcadam] fs event: {path}\n")
        if os.path.exists(path) and path not in self.watcher.files():
            try:
                self.watcher.addPath(path)
            except Exception:
                pass
        self._queue_rebuild(Path(path))

    def _queue_rebuild(self, path: Path) -> None:
        key = str(path)
        t = self.debounce.get(key)
        if not t:
            t = QTimer()
            t.setSingleShot(True)
            t.timeout.connect(lambda p=path: self._rebuild(p))
            self.debounce[key] = t
        t.start(250)

    def _rebuild(self, path: Path) -> None:
        try:
            target_py: Path | None = None
            if path.suffix.lower() == ".py":
                target_py = path
            elif path.suffix.lower() in {".yaml", ".yml"}:
                target_py = _find_controller_script(path)
            if not target_py or not target_py.exists():
                return

            kind = _classify_script(target_py)
            if self.verbose:
                App.Console.PrintMessage(f"[bbcadam] Rebuilding in-GUI: {target_py} ({kind})\n")

            # Call into existing builder API
            if kind == "assembly":
                build_assembly_script(self.project_root, target_py)
            else:
                build_part_script(self.project_root, target_py)

            # Optional: view restore could be added here
        except Exception as e:
            import traceback
            App.Console.PrintError(f"[bbcadam] Error rebuilding {path}: {e}\n{traceback.format_exc()}\n")


def main() -> None:
    # Instantiate once; QFileSystemWatcher lives as long as Python session
    try:
        _ = GuiSpecWatcher()
    except Exception as e:
        import traceback
        App.Console.PrintError(f"[bbcadam] Failed to start GUI watcher: {e}\n{traceback.format_exc()}\n")


if __name__ == "__main__":
    main()


