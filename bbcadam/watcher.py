"""In-GUI watcher for BbCadam using Qt's QFileSystemWatcher (runs inside FreeCAD)."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import FreeCAD as App
import FreeCADGui as Gui

try:
    from PySide6.QtCore import QFileSystemWatcher, QTimer
except Exception:
    from PySide2.QtCore import QFileSystemWatcher, QTimer


# Ensure the project root (BbCadam/) is importable so we can import bbcadam
_PKG_PARENT = Path(__file__).resolve().parents[1]
if str(_PKG_PARENT) not in sys.path:
    sys.path.insert(0, str(_PKG_PARENT))

from bbcadam.builder import build_part_script, build_assembly_script  # noqa: E402


def _resolve_project_root() -> Path:
    env_root = os.environ.get("BB_PROJECT_ROOT")
    if env_root:
        return Path(env_root).resolve()
    # Fallback to current working directory
    cur = Path.cwd().resolve()
    # Prefer nearest ancestor containing specs/
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


def _find_controller_script(changed: Path) -> Path | None:
    base_dir = changed.parent if changed.is_file() else changed
    preferred = base_dir / f"{base_dir.name}.py"
    if preferred.exists():
        return preferred
    for p in base_dir.glob("*.py"):
        return p
    return None


def _classify(py_path: Path) -> str:
    try:
        text = py_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return "part"
    if re.search(r"def\s+build_assembly\s*\(", text):
        return "assembly"
    if re.search(r"def\s+build_part\s*\(", text):
        return "part"
    return "part"


class _GuiWatcher:
    def __init__(self) -> None:
        self.project_root = _resolve_project_root()
        self.watch_dir = _resolve_watch_dir(self.project_root)
        self.verbose = bool(os.environ.get("BB_WATCH_VERBOSE"))

        self.watcher = QFileSystemWatcher()
        self.debounce: dict[str, QTimer] = {}
        self.known_files: set[str] = set()
        self.known_dirs: set[str] = set()
        self.mtimes: dict[str, float] = {}
        self._last_counts: tuple[int, int] = (-1, -1)

        # Optional periodic poll to catch metadata-only changes (e.g., touch)
        # Disabled by default; enable by setting BB_WATCH_POLL_MS
        self.poll_ms = 0
        try:
            self.poll_ms = int(os.environ.get("BB_WATCH_POLL_MS", "0") or "0")
        except Exception:
            self.poll_ms = 0
        if self.poll_ms > 0:
            self.scan_timer = QTimer()
            self.scan_timer.setInterval(self.poll_ms)
            self.scan_timer.timeout.connect(self._poll)
            self.scan_timer.start()
            if self.verbose:
                App.Console.PrintMessage(f"[bbcadam] polling enabled: {self.poll_ms} ms\n")

        self._attach()
        App.Console.PrintMessage(f"[bbcadam] Watch root: {self.watch_dir}\n")

    def _attach(self) -> None:
        # Always watch the root directory itself
        try:
            self.watcher.addPath(str(self.watch_dir))
        except Exception:
            pass
        self._rescan()
        # Initial mtime snapshot
        for p in list(self.known_files):
            try:
                self.mtimes[p] = os.path.getmtime(p)
            except Exception:
                self.mtimes.pop(p, None)
        self.watcher.directoryChanged.connect(self._on_dir)
        self.watcher.fileChanged.connect(self._on_file)
        if self.verbose:
            App.Console.PrintMessage(f"[bbcadam] attached watcher to root: {self.watch_dir}\n")

    def _rescan(self) -> None:
        exts = (".py", ".yaml", ".yml")
        current_files: set[str] = set()
        current_dirs: set[str] = set()
        base = self.watch_dir
        if not base.exists():
            return
        for root, dirs, files in os.walk(str(base)):
            # prune ignored directories in-place
            dirs[:] = [d for d in dirs if d != "__pycache__" and not d.startswith('.')]
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
        if self.verbose:
            counts = (len(self.known_dirs), len(self.known_files))
            if counts != self._last_counts:
                App.Console.PrintMessage(
                    f"[bbcadam] tracking {counts[0]} dirs, {counts[1]} files\n"
                )
                self._last_counts = counts
        # Do not update mtimes here to preserve change detection

    def _poll(self) -> None:
        # Rescan to pick up new files/dirs, but don't overwrite mtimes for existing files
        prev_known = set(self.known_files)
        self._rescan()
        # Initialize mtimes for any newly discovered files
        new_files = self.known_files - prev_known
        for p in new_files:
            try:
                self.mtimes[p] = os.path.getmtime(p)
            except Exception:
                self.mtimes.pop(p, None)
        # Queue rebuilds for newly discovered controller files immediately
        for p in new_files:
            try:
                pp = Path(p)
                target = None
                if pp.suffix.lower() == ".py":
                    target = pp
                elif pp.suffix.lower() in {".yaml", ".yml"}:
                    target = _find_controller_script(pp)
                if target and target.exists():
                    self._queue(target)
            except Exception:
                pass
        # Detect changes on existing files
        for p in list(self.known_files & prev_known):
            try:
                mt = os.path.getmtime(p)
            except Exception:
                continue
            old = self.mtimes.get(p)
            if old is not None and mt != old:
                if self.verbose:
                    App.Console.PrintMessage(f"[bbcadam] poll detected change: {p}\n")
                self.mtimes[p] = mt
                self._queue(Path(p))

    def _on_dir(self, _path: str) -> None:
        prev = dict(self.mtimes)
        prev_known = set(self.known_files)
        self._rescan()
        # Initialize mtimes for new files
        new_files = self.known_files - prev_known
        for p in new_files:
            try:
                self.mtimes[p] = os.path.getmtime(p)
            except Exception:
                self.mtimes.pop(p, None)
        # Queue rebuilds for newly discovered controller files on dir change
        for p in new_files:
            try:
                pp = Path(p)
                target = None
                if pp.suffix.lower() == ".py":
                    target = pp
                elif pp.suffix.lower() in {".yaml", ".yml"}:
                    target = _find_controller_script(pp)
                if target and target.exists():
                    self._queue(target)
            except Exception:
                pass
        # Detect changes for existing files
        for p in self.known_files & prev_known:
            try:
                mt = os.path.getmtime(p)
            except Exception:
                continue
            old = prev.get(p)
            if old is not None and mt != old:
                if self.verbose:
                    App.Console.PrintMessage(f"[bbcadam] dir change detected: {p}\n")
                self.mtimes[p] = mt
                self._queue(Path(p))

    def _on_file(self, path: str) -> None:
        if self.verbose:
            App.Console.PrintMessage(f"[bbcadam] fs event: {path}\n")
        if os.path.exists(path) and path not in self.watcher.files():
            try:
                self.watcher.addPath(path)
            except Exception:
                pass
        self._queue(Path(path))

    def _queue(self, path: Path) -> None:
        key = str(path)
        t = self.debounce.get(key)
        if not t:
            t = QTimer()
            t.setSingleShot(True)
            t.timeout.connect(lambda p=path: self._rebuild(p))
            self.debounce[key] = t
        t.start(250)

    def _rebuild(self, changed: Path) -> None:
        try:
            target_py: Path | None = None
            if changed.suffix.lower() == ".py":
                target_py = changed
            elif changed.suffix.lower() in {".yaml", ".yml"}:
                target_py = _find_controller_script(changed)
            if not target_py or not target_py.exists():
                return

            kind = _classify(target_py)
            if self.verbose:
                App.Console.PrintMessage(f"[bbcadam] Rebuild: {target_py} ({kind})\n")

            if kind == "assembly":
                build_assembly_script(self.project_root, target_py)
            else:
                build_part_script(self.project_root, target_py)
        except Exception as e:
            import traceback
            App.Console.PrintError(f"[bbcadam] Error rebuilding {changed}: {e}\n{traceback.format_exc()}\n")


_STARTED = False
_WATCHER_INSTANCE = None


def main() -> None:
    global _STARTED
    global _WATCHER_INSTANCE
    if _STARTED:
        return
    _STARTED = True
    App.Console.PrintMessage("[bbcadam] GUI watcher module loaded.\n")
    _WATCHER_INSTANCE = _GuiWatcher()


# Start immediately on import as FreeCAD may not set __name__ == '__main__'
main()


