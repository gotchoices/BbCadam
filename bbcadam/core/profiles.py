"""Section/profile path builder and adapters.

Implements 2D profile construction (lines/arcs) and adapters for Part/Sketcher.
"""

from __future__ import annotations

try:
    import FreeCAD as App  # type: ignore
except Exception:  # pragma: no cover
    App = None  # type: ignore

from .dsl_core import _set_ctx as set_ctx  # re-export if needed


class Section:
    def __init__(self, name=None, plane='XY', at=(0.0, 0.0, 0.0), backend=None, visible: bool = True):
        """Create a new 2D section/profile.

        - name: optional label for debugging/materialization
        - plane: 'XY' | 'XZ' | 'YZ' or 'LCS:Name' to place on datum/LCS
        - at: local offset within the chosen plane/datum
        - backend: Part or Sketcher backend (Part by default)
        - visible: for Sketcher backend, show sketch in GUI
        """
        self.name = name or 'Sketch'
        self.plane = str(plane).upper()
        self.origin = at
        self._profile = _SectionProfile()
        self._sketch_visible = bool(visible)
        self._datum_placement = None
        try:
            if isinstance(plane, str):
                p = plane.strip()
                key = p.split(':', 1)[0]
                if key in ('LCS', 'Datum', 'DATUM') and ':' in p:
                    obj_name = p.split(':', 1)[1]
                    from .dsl_core import _CTX
                    doc = _CTX.doc if _CTX else None
                    if doc:
                        obj = doc.getObject(obj_name)
                        if obj and hasattr(obj, 'Placement'):
                            self._datum_placement = obj.Placement
        except Exception:
            pass
        if backend is None:
            from ..backends.part import PartSectionBackend
            self._backend = PartSectionBackend()
        else:
            self._backend = backend

    def _map_xy(self, x, y):
        if self.plane == 'YZ':
            return (y, x)
        return (x, y)

    def _map_tuple(self, p):
        if p is None:
            return None
        if self.plane == 'YZ':
            return (p[1], p[0])
        return p

    def on(self, plane=None, origin=None, normal=None, x_axis=None, rotate=None, translate=None, inherit=True):
        """Set the current working plane/frame for subsequent ops.

        Minimal implementation supports plane ('XY'|'XZ'|'YZ'|'LCS:Name') and origin.
        Other arguments are accepted for future extensions.
        """
        try:
            if plane is not None:
                if isinstance(plane, str):
                    p = plane.strip()
                    self.plane = p.split(':', 1)[0].upper()
                    self._datum_placement = None
                    key = p.split(':', 1)[0]
                    if key in ('LCS', 'DATUM') and ':' in p:
                        obj_name = p.split(':', 1)[1]
                        from .dsl_core import _CTX
                        doc = _CTX.doc if _CTX else None
                        if doc:
                            obj = doc.getObject(obj_name)
                            if obj and hasattr(obj, 'Placement'):
                                self._datum_placement = obj.Placement
                else:
                    # Future: accept freeform plane tuples/objects
                    pass
            if origin is not None:
                self.origin = origin
        except Exception:
            pass
        return self

    # 2D primitives
    def circle(self, d=None, r=None, at=(0.0, 0.0), hole=False):
        """Add a circle to the profile (outer or hole).
        Provide diameter d or radius r; at is the center in section plane.
        """
        at_m = self._map_tuple(at)
        self._profile.circle(d=d, r=r, at=at_m, hole=hole)
        return self

    def rectangle(self, w, h=None, at=(0.0, 0.0), hole=False):
        """Add an axis-aligned rectangle (outer or hole).
        Width w, height h (defaults to w); centered at 'at'.
        """
        at_m = self._map_tuple(at)
        self._profile.rectangle(w=w, h=h, at=at_m, hole=hole)
        return self

    def polygon(self, n=6, side=None, d=None, at=(0.0, 0.0), hole=False):
        """Add a regular polygon with n sides (outer or hole).
        Provide side length or circumscribed diameter d; centered at 'at'.
        """
        at_m = self._map_tuple(at)
        self._profile.polygon(n=n, side=side, d=d, at=at_m, hole=hole)
        return self

    # Path builder
    def from_(self, x=None, y=None, hole=False):
        """Move the path cursor to (x,y) and start a new path (optionally a hole)."""
        mx, my = self._map_xy(x, y)
        self._profile.from_(x=mx, y=my, hole=hole)
        return self

    def to(self, x=None, y=None):
        """Add a straight line from the current cursor to (x,y)."""
        mx, my = self._map_xy(x, y)
        self._profile.to(x=mx, y=my)
        return self

    def go(self, dx=None, dy=None, r=None, a_deg=None):
        """Relative line: move by (dx,dy) or by polar (r,a_deg)."""
        if self.plane == 'YZ':
            if r is not None and a_deg is not None:
                import math
                dx0 = float(r) * math.cos(math.radians(float(a_deg)))
                dy0 = float(r) * math.sin(math.radians(float(a_deg)))
                mdx, mdy = dy0, dx0
                self._profile.go(dx=mdx, dy=mdy)
            else:
                mdx, mdy = (dy, dx)
                self._profile.go(dx=mdx, dy=mdy)
        else:
            self._profile.go(dx=dx, dy=dy, r=r, a_deg=a_deg)
        return self

    def arc(self, radius=None, dir='ccw', end=None, endAt=None, center=None, centerAt=None, sweep=None, tangent=False):
        """Add a circular arc. Modes:
        - center(+radius)+end
        - center(+radius)+sweep (end inferred)
        - radius+end+dir (center inferred, minor arc)
        - radius+end+sweep (center inferred)
        """
        import math
        # Map inputs
        end_in = endAt if endAt is not None else end
        center_in = centerAt if centerAt is not None else center
        end_m = self._map_tuple(end_in) if end_in is not None else None
        center_m = self._map_tuple(center_in) if center_in is not None else None

        # Current start
        if self._profile._cursor is None:
            raise RuntimeError('arc() called before from_()')
        sx, sy = self._profile._cursor

        # If center not provided, infer from radius + end (+ dir/sweep)
        if center_m is None:
            if radius is None:
                raise ValueError('arc requires radius when center is omitted')
            if end_m is None and sweep is None:
                raise ValueError('arc requires end or sweep to infer center')
            if end_m is None:
                raise ValueError('arc requires end to infer center')
            ex, ey = float(end_m[0]) + 0.0, float(end_m[1]) + 0.0
            vx, vy = ex - sx, ey - sy
            chord_len = math.hypot(vx, vy)
            if chord_len == 0:
                raise ValueError('arc start and end coincide; use circle() or adjust end')
            if float(radius) < chord_len / 2.0 - 1e-8:
                raise ValueError('arc radius too small for given end')
            mx, my = (sx + ex) / 2.0, (sy + ey) / 2.0
            h = math.sqrt(max(float(radius) * float(radius) - (chord_len / 2.0) ** 2, 0.0))
            nx, ny = -vy / chord_len, vx / chord_len
            c1 = (mx + nx * h, my + ny * h)
            c2 = (mx - nx * h, my - ny * h)
            def _sweep_sign(center):
                a0 = math.atan2(sy - center[1], sx - center[0])
                a1 = math.atan2(ey - center[1], ex - center[0])
                a0 = (a0 + 2*math.pi) % (2*math.pi)
                a1 = (a1 + 2*math.pi) % (2*math.pi)
                delta = a1 - a0
                if delta < 0:
                    delta += 2 * math.pi
                return +1 if delta <= math.pi else -1
            if sweep is not None:
                want_ccw = float(sweep) > 0
                center_m = c1 if (_sweep_sign(c1) > 0) == want_ccw else c2
            else:
                pick_ccw = (str(dir).lower() == 'ccw')
                center_m = c1 if (_sweep_sign(c1) > 0) == pick_ccw else c2

        # If center is provided and end missing but sweep provided, infer end from sweep
        exey = end_m
        if center_m is not None and end_m is None and sweep is not None:
            cx, cy = float(center_m[0]), float(center_m[1])
            R = float(radius) if radius is not None else math.hypot(sx - cx, sy - cy)
            a0 = math.atan2(sy - cy, sx - cx)
            a1 = a0 + math.radians(float(sweep))
            exey = (cx + R * math.cos(a1), cy + R * math.sin(a1))

        # Pass absolute coordinates to the profile (centerAt/endAt)
        self._profile.arc(radius=radius if radius is not None else math.hypot(sx - float(center_m[0]), sy - float(center_m[1])),
                          dir=dir,
                          end=None,
                          endAt=exey,
                          center=None,
                          centerAt=center_m,
                          sweep=sweep)
        return self

    def close(self):
        """Close the current path to the starting point and finalize it."""
        self._profile.close()
        return self

    # 3D ops
    def pad(self, dist, dir='+'):
        """Extrude the closed profile by dist along section normal (sign by dir)."""
        return self._backend.pad(self, dist, dir)

    def revolve(self, angle_deg=360.0, axis='Y'):
        """Revolve the closed profile around X/Y/Z by angle_deg degrees."""
        return self._backend.revolve(self, angle_deg, axis)

    def sweep(self, path_section):
        """Sweep the closed profile along an open path defined by another Section."""
        return self._backend.sweep(self, path_section)

    # --- 3D path rough-ins ---
    def to3d(self, x=None, y=None, z=None):
        """Record an absolute 3D point in the profile's 3D path (experimental)."""
        try:
            px = float(x) if x is not None else 0.0
            py = float(y) if y is not None else 0.0
            pz = float(z) if z is not None else 0.0
            self._profile._p3_cursor = (px, py, pz)
            self._profile._geom3d.append(('p3', (px, py, pz)))
        except Exception:
            pass
        return self

    def arc3d(self, center=None, end=None, sweep=None, dir='ccw'):
        """Record a 3D arc via center+end or center+sweep (experimental)."""
        try:
            data = {
                'center': tuple(center) if center is not None else None,
                'end': tuple(end) if end is not None else None,
                'sweep': float(sweep) if sweep is not None else None,
                'dir': str(dir),
                'start': self._profile._p3_cursor,
            }
            self._profile._geom3d.append(('a3', data))
            if end is not None:
                self._profile._p3_cursor = tuple(end)
        except Exception:
            pass
        return self

    def spline3d(self, points, tangents=None):
        """Record a 3D spline through points (experimental)."""
        try:
            pts = [tuple(p) for p in points]
            self._profile._geom3d.append(('s3', {'points': pts, 'tangents': tangents}))
            if pts:
                self._profile._p3_cursor = pts[-1]
        except Exception:
            pass
        return self

    def helix3d(self, radius, pitch, turns=None, height=None, axis='Z'):
        """Record a helical 3D segment (experimental)."""
        try:
            self._profile._geom3d.append(('h3', {'radius': float(radius), 'pitch': float(pitch), 'turns': turns, 'height': height, 'axis': str(axis)}))
        except Exception:
            pass
        return self

    def _place_shape(self, shape):
        placed = shape.copy()
        if getattr(self, '_datum_placement', None) is not None:
            placed.Placement = self._datum_placement
            try:
                off_local = App.Vector(float(self.origin[0]), float(self.origin[1]), float(self.origin[2]))
            except Exception:
                off_local = App.Vector(0, 0, 0)
            off_world = self._datum_placement.Rotation.multVec(off_local)
            placed.translate(off_world)
            return placed
        if self.plane == 'XY':
            pass
        elif self.plane == 'XZ':
            placed.rotate(App.Vector(0, 0, 0), App.Vector(1, 0, 0), 90)
        elif self.plane == 'YZ':
            placed.rotate(App.Vector(0, 0, 0), App.Vector(0, 1, 0), -90)
        placed.translate(App.Vector(float(self.origin[0]), float(self.origin[1]), float(self.origin[2])))
        return placed


def generic_section(materialized: bool = False, name=None, plane='XY', at=(0.0, 0.0, 0.0), visible: bool = True):
    if materialized:
        from ..backends.sketcher import SketcherSectionBackend
        backend = SketcherSectionBackend()
    else:
        from ..backends.part import PartSectionBackend
        backend = PartSectionBackend()
    return Section(name=name, plane=plane, at=at, backend=backend, visible=visible)


def profile(name=None, plane='XY', at=(0.0, 0.0, 0.0)):
    return generic_section(materialized=False, name=name, plane=plane, at=at)


def sketch(name=None, plane='XY', at=(0.0, 0.0, 0.0), visible: bool = True):
    return generic_section(materialized=True, name=name, plane=plane, at=at, visible=visible)


class _SectionProfile:
    def __init__(self):
        self._outer_wire = None
        self._hole_wires = []
        self._cursor = None
        self._first_point = None
        self._building_hole = False
        self._geom_outer = None
        self._geom_holes = []
        self._geom_current = None
        # 3D path capture (rough-in)
        self._p3_cursor = None
        self._geom3d = []

    def circle(self, d=None, r=None, at=(0.0, 0.0), hole=False):
        import Part
        if r is None:
            if d is None:
                raise ValueError('circle requires r or d')
            r = float(d) / 2.0
        cx, cy = float(at[0]), float(at[1])
        edge = Part.Edge(Part.Circle(App.Vector(cx, cy, 0), App.Vector(0, 0, 1), float(r)))
        wire = Part.Wire([edge])
        self._add_wire(wire, hole or self._building_hole)

    def rectangle(self, w, h=None, at=(0.0, 0.0), hole=False):
        import Part
        w = float(w)
        h = float(h) if h is not None else w
        cx, cy = float(at[0]), float(at[1])
        x0, y0 = cx - w / 2.0, cy - h / 2.0
        pts = [
            App.Vector(x0, y0, 0),
            App.Vector(x0 + w, y0, 0),
            App.Vector(x0 + w, y0 + h, 0),
            App.Vector(x0, y0 + h, 0),
            App.Vector(x0, y0, 0),
        ]
        edges = [Part.makeLine(pts[i], pts[i + 1]) for i in range(4)]
        wire = Part.Wire(edges)
        self._add_wire(wire, hole or self._building_hole)
        path = []
        for i in range(4):
            path.append(('line', (float(pts[i].x), float(pts[i].y), float(pts[i+1].x), float(pts[i+1].y))))
        self._add_geom_path(path, hole or self._building_hole)

    def polygon(self, n=6, side=None, d=None, at=(0.0, 0.0), hole=False):
        import math, Part
        n = int(n)
        cx, cy = float(at[0]), float(at[1])
        if d is not None:
            R = float(d) / 2.0
        elif side is not None:
            a = float(side)
            R = a / (2.0 * math.sin(math.pi / n))
        else:
            R = 1.0
        pts = [
            App.Vector(cx + R * math.cos(2 * math.pi * i / n), cx * 0 + cy + R * math.sin(2 * math.pi * i / n), 0)
            for i in range(n)
        ]
        pts.append(pts[0])
        edges = [Part.makeLine(pts[i], pts[i + 1]) for i in range(n)]
        wire = Part.Wire(edges)
        self._add_wire(wire, hole or self._building_hole)
        path = []
        for i in range(n):
            path.append(('line', (float(pts[i].x), float(pts[i].y), float(pts[i+1].x), float(pts[i+1].y))))
        self._add_geom_path(path, hole or self._building_hole)

    def from_(self, x=None, y=None, hole=False):
        x = float(x) if x is not None else (self._cursor[0] if self._cursor else 0.0)
        y = float(y) if y is not None else (self._cursor[1] if self._cursor else 0.0)
        self._cursor = (x, y)
        self._first_point = (x, y)
        self._building_hole = bool(hole)
        self._geom_current = []
        self._geom_current.append(('move', (float(x), float(y))))

    def to(self, x=None, y=None):
        if self._cursor is None:
            raise RuntimeError('to() called before from_()')
        px, py = self._cursor
        nx = float(x) if x is not None else px
        ny = float(y) if y is not None else py
        self._append_segment((px, py), (nx, ny))
        if self._geom_current is not None:
            self._geom_current.append(('line', (float(px), float(py), float(nx), float(ny))))
        self._cursor = (nx, ny)

    def go(self, dx=None, dy=None, r=None, a_deg=None):
        if self._cursor is None:
            raise RuntimeError('go() called before from_()')
        if r is not None and a_deg is not None:
            import math
            dx = float(r) * math.cos(math.radians(float(a_deg)))
            dy = float(r) * math.sin(math.radians(float(a_deg)))
        px, py = self._cursor
        nx = px + (float(dx) if dx is not None else 0.0)
        ny = py + (float(dy) if dy is not None else 0.0)
        self._append_segment((px, py), (nx, ny))
        if self._geom_current is not None:
            self._geom_current.append(('line', (float(px), float(py), float(nx), float(ny))))
        self._cursor = (nx, ny)

    def arc(self, radius, dir='ccw', end=None, endAt=None, center=None, centerAt=None, sweep=None):
        import math
        import Part
        if self._cursor is None:
            raise RuntimeError('arc() called before from_()')
        dir_l = str(dir).lower()
        if dir_l not in ('ccw', 'cw'):
            raise ValueError("arc dir must be 'ccw' or 'cw'")
        cx0, cy0 = self._cursor
        if centerAt is not None:
            cx, cy = float(centerAt[0]), float(centerAt[1])
        elif center is not None:
            cx = cx0 + float(center[0])
            cy = cy0 + float(center[1])
        else:
            raise ValueError('arc requires center or centerAt')
        if endAt is not None:
            ex, ey = float(endAt[0]), float(endAt[1])
        elif end is not None:
            ex = cx0 + float(end[0])
            ey = cy0 + float(end[1])
        else:
            raise ValueError('arc requires end or endAt')
        R = float(radius)
        if not (R > 0.0):
            raise ValueError('arc radius must be > 0')
        ds = math.hypot(cx0 - cx, cy0 - cy)
        de = math.hypot(ex - cx, ey - cy)
        tol_abs = 1e-4
        tol_rel = 1e-4
        ok_s = math.isclose(ds, R, rel_tol=tol_rel, abs_tol=tol_abs)
        ok_e = math.isclose(de, R, rel_tol=tol_rel, abs_tol=tol_abs)
        if not ok_e:
            raise ValueError('arc end not on circle defined by center/radius')
        sx, sy = cx0, cy0
        if math.hypot(ex - sx, ey - sy) <= tol_abs:
            raise ValueError("arc start and end coincide; use circle() for full circle or adjust end")
        a_start = math.atan2(sy - cy, sx - cx)
        a_end = math.atan2(ey - cy, ex - cx)
        def norm(a):
            while a < 0:
                a += 2 * math.pi
            while a >= 2 * math.pi:
                a -= 2 * math.pi
            return a
        a_start = norm(a_start)
        a_end = norm(a_end)
        if sweep is None:
            if dir_l == 'ccw':
                delta = a_end - a_start
                if delta < 0:
                    delta += 2 * math.pi
            else:
                delta = a_end - a_start
                if delta > 0:
                    delta -= 2 * math.pi
            diff = abs(a_end - a_start)
            diff = min(diff, 2 * math.pi - diff)
            if abs(diff - math.pi) < 1e-8:
                delta = math.pi if dir_l == 'ccw' else -math.pi
        else:
            delta = math.radians(float(sweep))
        tol_ang = 1e-6
        if abs(delta) < tol_ang:
            raise ValueError('arc sweep too small (degenerate); adjust end or direction')
        if abs(abs(delta) - 2 * math.pi) < tol_ang:
            raise ValueError("full-circle arc not supported via arc(); use circle() instead")
        a_mid = a_start + delta / 2.0
        smid_x = cx + R * math.cos(a_mid)
        smid_y = cy + R * math.sin(a_mid)
        start_v = App.Vector(sx, sy, 0)
        mid_v = App.Vector(smid_x, smid_y, 0)
        end_v = App.Vector(ex, ey, 0)
        edge = Part.Arc(start_v, mid_v, end_v).toShape()
        if not hasattr(self, '_poly_edges'):
            self._poly_edges = []
        self._poly_edges.append(edge)
        self._cursor = (ex, ey)
        if self._geom_current is not None:
            self._geom_current.append(('arc', dict(radius=float(radius), dir=dir, center=(float(cx), float(cy)), end=(float(ex), float(ey)), sweep_rad=float(delta), start=(float(sx), float(sy)))))

    def close(self):
        import Part
        if self._cursor is None or self._first_point is None:
            return
        tol_close = 1e-6
        need_close = True
        try:
            dx = float(self._cursor[0]) - float(self._first_point[0])
            dy = float(self._cursor[1]) - float(self._first_point[1])
            need_close = (dx*dx + dy*dy) > tol_close*tol_close
        except Exception:
            need_close = self._cursor != self._first_point
        if need_close:
            self._append_segment(self._cursor, self._first_point)
            if self._geom_current is not None:
                px, py = self._cursor
                qx, qy = self._first_point
                self._geom_current.append(('line', (float(px), float(py), float(qx), float(qy))))
        wire = Part.Wire(self._poly_edges) if getattr(self, '_poly_edges', None) else None
        self._poly_edges = []
        if wire is not None:
            self._add_wire(wire, self._building_hole)
        current_hole = self._building_hole
        self._cursor = None
        self._first_point = None
        self._building_hole = False
        if self._geom_current is not None:
            self._add_geom_path(self._geom_current, hole=current_hole)
            self._geom_current = None

    def _append_segment(self, p0, p1):
        import Part
        a = App.Vector(float(p0[0]), float(p0[1]), 0)
        b = App.Vector(float(p1[0]), float(p1[1]), 0)
        edge = Part.makeLine(a, b)
        if not hasattr(self, '_poly_edges'):
            self._poly_edges = []
        self._poly_edges.append(edge)

    def _add_wire(self, wire, hole):
        if hole:
            self._hole_wires.append(wire)
        else:
            if self._outer_wire is not None:
                raise RuntimeError('Only one outer profile is supported in section v1')
            self._outer_wire = wire

    def build_face_with_holes(self):
        import Part
        if self._outer_wire is not None:
            face = Part.Face(self._outer_wire)
            for hw in self._hole_wires:
                try:
                    face = face.cut(Part.Face(hw))
                except Exception:
                    pass
            return face
        return PartProfileAdapter(self).build_face_with_holes()

    def build_open_wire(self):
        import Part
        if hasattr(self, '_poly_edges') and self._poly_edges:
            return Part.Wire(self._poly_edges)
        if self._outer_wire is not None and not self._hole_wires:
            return Part.Wire(self._outer_wire.Edges)
        if self._geom_outer:
            return PartProfileAdapter(self).build_open_wire()
        raise RuntimeError('No open path available in section profile')

    def _add_geom_path(self, path_ops, hole=False):
        if hole:
            self._geom_holes.append(list(path_ops))
        else:
            if self._geom_outer is None:
                self._geom_outer = list(path_ops)
            else:
                self._geom_holes.append(list(path_ops))


class PartProfileAdapter:
    def __init__(self, profile: _SectionProfile):
        self.p = profile

    def build_face_with_holes(self):
        import Part
        if self.p._geom_outer:
            outer = self._wire_from_ops(self.p._geom_outer)
            holes = [self._wire_from_ops(h) for h in self.p._geom_holes] if self.p._geom_holes else []
            if getattr(self.p, '_hole_wires', None):
                holes.extend(self.p._hole_wires)
            face = Part.Face(outer)
            for hw in holes:
                try:
                    face = face.cut(Part.Face(hw))
                except Exception:
                    pass
            return face
        if self.p._outer_wire is None:
            raise RuntimeError('section requires an outer profile')
        face = Part.Face(self.p._outer_wire)
        for hw in self.p._hole_wires:
            try:
                face = face.cut(Part.Face(hw))
            except Exception:
                pass
        return face

    def build_open_wire(self):
        import Part
        if self.p._geom_outer:
            return self._wire_from_ops(self.p._geom_outer)
        if getattr(self.p, '_geom_current', None):
            return self._wire_from_ops(self.p._geom_current)
        if hasattr(self.p, '_poly_edges') and self.p._poly_edges:
            return Part.Wire(self.p._poly_edges)
        if self.p._outer_wire is not None and not self.p._hole_wires:
            return Part.Wire(self.p._outer_wire.Edges)
        raise RuntimeError('No open path geometry available')

    def _wire_from_ops(self, ops):
        import Part
        edges = []
        for op in ops:
            if op[0] == 'move':
                continue
            if op[0] == 'line':
                x1, y1, x2, y2 = op[1]
                a = App.Vector(x1, y1, 0)
                b = App.Vector(x2, y2, 0)
                edges.append(Part.makeLine(a, b))
            elif op[0] == 'arc':
                data = op[1]
                cx, cy = data['center']
                ex, ey = data['end']
                sx, sy = data.get('start', (None, None))
                if sx is None:
                    if edges:
                        sx = float(edges[-1].Vertexes[-1].Point.x)
                        sy = float(edges[-1].Vertexes[-1].Point.y)
                    else:
                        continue
                R = float(data['radius'])
                import math
                if 'sweep_rad' in data:
                    a_start = math.atan2(sy - cy, sx - cx)
                    a_mid = a_start + float(data['sweep_rad']) / 2.0
                else:
                    a_start = math.atan2(sy - cy, sx - cx)
                    a_end = math.atan2(ey - cy, ex - cx)
                    def norm(a):
                        while a < 0:
                            a += 2 * math.pi
                        while a >= 2 * math.pi:
                            a -= 2 * math.pi
                        return a
                    a_start = norm(a_start)
                    a_end = norm(a_end)
                    direction = str(data.get('dir', 'ccw')).lower()
                    if direction == 'ccw':
                        delta = a_end - a_start
                        if delta < 0:
                            delta += 2 * math.pi
                    else:
                        delta = a_end - a_start
                        if delta > 0:
                            delta -= 2 * math.pi
                    diff = abs(a_end - a_start)
                    diff = min(diff, 2 * math.pi - diff)
                    if abs(diff - math.pi) < 1e-8:
                        delta = math.pi if direction == 'ccw' else -math.pi
                    a_mid = a_start + delta / 2.0
                mid = App.Vector(cx + R * math.cos(a_mid), cy + R * math.sin(a_mid), 0)
                edges.append(Part.Arc(App.Vector(sx, sy, 0), mid, App.Vector(ex, ey, 0)).toShape())
        import Part
        return Part.Wire(edges)


class SketcherProfileAdapter:
    def __init__(self, section: Section):
        self.section = section
        self.profile = section._profile

    def build_sketch(self, name=None):
        doc = __import__('bbcadam.core.dsl_core', fromlist=['_CTX'])._CTX.doc  # lazy import
        sk_name = name or (self.section.name or 'Sketch')
        sk = None
        try:
            sk = doc.getObject(sk_name)
        except Exception:
            sk = None
        if sk is None:
            try:
                sk = doc.addObject('Sketcher::SketchObject', sk_name)
            except Exception as e:
                raise RuntimeError(f'Cannot create Sketcher object: {e}')
        else:
            try:
                for i in range(getattr(sk, 'ConstraintCount', 0) - 1, -1, -1):
                    try:
                        sk.removeConstraint(i)
                    except Exception:
                        pass
                for i in range(getattr(sk, 'GeometryCount', 0) - 1, -1, -1):
                    try:
                        sk.removeGeometry(i)
                    except Exception:
                        pass
            except Exception:
                pass
        pl = App.Placement()
        if getattr(self.section, '_datum_placement', None) is not None:
            pl = self.section._datum_placement
        else:
            if self.section.plane == 'XY':
                pass
            elif self.section.plane == 'XZ':
                pl.Rotation = App.Rotation(App.Vector(1, 0, 0), 90)
            elif self.section.plane == 'YZ':
                pl.Rotation = App.Rotation(App.Vector(0, 1, 0), -90)
            pl.Base = App.Vector(float(self.section.origin[0]), float(self.section.origin[1]), float(self.section.origin[2]))
        sk.Placement = pl

        def add_path(ops):
            import Part, math
            last = None
            for op in ops:
                if op[0] == 'move':
                    last = (float(op[1][0]), float(op[1][1]))
                    continue
                if op[0] == 'line':
                    x1, y1, x2, y2 = op[1]
                    seg = Part.LineSegment(App.Vector(x1, y1, 0), App.Vector(x2, y2, 0))
                    sk.addGeometry(seg, False)
                    last = (x2, y2)
                elif op[0] == 'arc':
                    data = op[1]
                    cx, cy = data['center']
                    ex, ey = data['end']
                    sx, sy = data.get('start', (None, None))
                    if sx is None:
                        if last is None:
                            continue
                        sx, sy = last
                    a_start = math.atan2(sy - cy, sx - cx)
                    a_mid = a_start + float(data.get('sweep_rad', 0.0)) / 2.0
                    mid = App.Vector(cx + float(data['radius']) * math.cos(a_mid),
                                     cy + float(data['radius']) * math.sin(a_mid), 0)
                    arc3 = Part.Arc(App.Vector(sx, sy, 0), mid, App.Vector(ex, ey, 0))
                    sk.addGeometry(arc3, False)
                    last = (ex, ey)

        ops = self.profile._geom_outer if self.profile._geom_outer else getattr(self.profile, '_geom_current', None)
        if ops:
            add_path(ops)
        elif getattr(self.profile, '_outer_wire', None) is not None:
            try:
                for e in self.profile._outer_wire.Edges:
                    if hasattr(e, 'Curve') and e.Curve.__class__.__name__ == 'Circle':
                        sk.addGeometry(e.Curve, False)
                    else:
                        sk.addGeometry(e, False)
            except Exception:
                pass
        for hole_ops in (self.profile._geom_holes or []):
            add_path(hole_ops)
        if getattr(self.profile, '_hole_wires', None):
            for hw in self.profile._hole_wires:
                try:
                    for e in hw.Edges if hasattr(hw, 'Edges') else []:
                        if hasattr(e, 'Curve') and e.Curve.__class__.__name__ == 'Circle':
                            sk.addGeometry(e.Curve, False)
                        else:
                            sk.addGeometry(e, False)
                except Exception:
                    pass
        try:
            doc.recompute()
            if hasattr(sk, 'ViewObject'):
                sk.ViewObject.Visibility = bool(getattr(self.section, '_sketch_visible', True))
        except Exception:
            pass
        return sk


__all__ = [
    "Section",
    "section",
    "sketch",
    "PartProfileAdapter",
    "SketcherProfileAdapter",
]


