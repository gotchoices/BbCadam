"""Sketcher backend implementation (adapts materialization, defers ops)."""

try:
    import FreeCAD as App  # type: ignore
except Exception:  # pragma: no cover
    App = None  # type: ignore

from ..core.profiles import SketcherProfileAdapter
from .part import PartSectionBackend


class SketcherSectionBackend:
    def _materialize_sketch(self, section):
        """Ensure a Sketcher::SketchObject exists and reflects current profile paths."""
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
        """Materialize sketch (for GUI) then extrude using Part backend."""
        self._materialize_sketch(section)
        return PartSectionBackend().pad(section, dist, dir)

    def revolve(self, section, angle_deg=360.0, axis='Y'):
        """Materialize sketch then revolve using Part backend."""
        self._materialize_sketch(section)
        return PartSectionBackend().revolve(section, angle_deg, axis)

    def sweep(self, section, path_section):
        """Materialize both profiles as sketches for GUI, then sweep via Part backend."""
        self._materialize_sketch(section)
        try:
            SketcherProfileAdapter(path_section).build_sketch(name=(path_section.name or 'Path'))
        except Exception:
            pass
        return PartSectionBackend().sweep(section, path_section)

__all__ = ["SketcherSectionBackend"]


