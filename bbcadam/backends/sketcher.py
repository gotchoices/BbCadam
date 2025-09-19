"""Sketcher backend implementation (adapts materialization, defers ops)."""

try:
    import FreeCAD as App  # type: ignore
except Exception:  # pragma: no cover
    App = None  # type: ignore

from ..core.profiles import SketcherProfileAdapter
from .part import PartSectionBackend


class SketcherSectionBackend:
    def _materialize_sketch(self, section):
        try:
            adapter = SketcherProfileAdapter(section)
            sk = adapter.build_sketch()
            return sk
        except Exception as e:
            try:
                App.Console.PrintWarning(f"[bbcadam] Sketcher materialization failed: {e}\n")
            except Exception:
                pass
            return None

    def pad(self, section, dist, dir='+'):
        self._materialize_sketch(section)
        return PartSectionBackend().pad(section, dist, dir)

    def revolve(self, section, angle_deg=360.0, axis='Y'):
        self._materialize_sketch(section)
        return PartSectionBackend().revolve(section, angle_deg, axis)

    def sweep(self, section, path_section):
        self._materialize_sketch(section)
        try:
            SketcherProfileAdapter(path_section).build_sketch(name=(path_section.name or 'Path'))
        except Exception:
            pass
        return PartSectionBackend().sweep(section, path_section)

__all__ = ["SketcherSectionBackend"]


