"""Part backend implementation."""

try:
    import FreeCAD as App  # type: ignore
except Exception:  # pragma: no cover
    App = None  # type: ignore

from ..core.profiles import PartProfileAdapter
from ..core.dsl_core import Feature


class PartSectionBackend:
    def _build_face_with_holes(self, section):
        return PartProfileAdapter(section._profile).build_face_with_holes()

    def pad(self, section, dist, dir='+'):
        face = self._build_face_with_holes(section)
        dist = float(dist)
        placed_face = section._place_shape(face)
        if section.plane == 'XY':
            vec = App.Vector(0, 0, dist if dir.startswith('+') else -dist)
        elif section.plane == 'XZ':
            vec = App.Vector(0, dist if dir.startswith('+') else -dist, 0)
        elif section.plane == 'YZ':
            vec = App.Vector(dist if dir.startswith('+') else -dist, 0, 0)
        else:
            raise ValueError('Unknown plane')
        solid = placed_face.extrude(vec)
        try:
            solid = solid.makeSolid()
        except Exception:
            pass
        return Feature(solid)

    def revolve(self, section, angle_deg=360.0, axis='Y'):
        face = self._build_face_with_holes(section)
        ax = axis.upper()
        if ax == 'X':
            axis_dir = App.Vector(1, 0, 0)
        elif ax == 'Y':
            axis_dir = App.Vector(0, 1, 0)
        elif ax == 'Z':
            axis_dir = App.Vector(0, 0, 1)
        else:
            raise ValueError('axis must be X, Y, or Z')
        solid = face.revolve(App.Vector(0, 0, 0), axis_dir, float(angle_deg))
        try:
            solid = solid.makeSolid()
        except Exception:
            pass
        solid = section._place_shape(solid)
        return Feature(solid)

    def sweep(self, section, path_section):
        import Part
        face = self._build_face_with_holes(section)
        path_wire = PartProfileAdapter(path_section._profile).build_open_wire()
        path = path_section._place_shape(path_wire)
        first_edge = path.Edges[0]
        try:
            t0 = first_edge.tangentAt(first_edge.FirstParameter)
        except Exception:
            v0 = first_edge.Vertexes[0].Point
            v1 = first_edge.Vertexes[-1].Point
            t0 = App.Vector(v1.x - v0.x, v1.y - v0.y, v1.z - v0.z)
        if t0.Length == 0:
            t0 = App.Vector(0, 0, 1)
        t0.normalize()
        start_pt = first_edge.Vertexes[0].Point
        prof = face.copy()
        rot = App.Rotation(App.Vector(0, 0, 1), t0)
        pl = App.Placement()
        pl.Rotation = rot
        pl.Base = start_pt
        prof.Placement = pl
        shape = path.makePipeShell([prof.OuterWire], True, True)
        try:
            solids = getattr(shape, 'Solids', [])
            if solids:
                shape = solids[0]
        except Exception:
            pass
        return Feature(shape)

__all__ = ["PartSectionBackend"]


