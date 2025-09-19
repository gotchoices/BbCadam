"""Primitives implemented on top of core Feature/state."""

from .dsl_core import Feature, _STATE  # type: ignore


def _apply_pending(feat_shape):
    # Flush any previous pending feature as an implicit add before starting a new one
    if _STATE.get('pending_feature') is not None:
        import bbcadam.core.dsl_core as core  # local import to avoid cycles
        core._apply_add(_STATE['pending_feature'])
        _STATE['pending_feature'] = None
    _STATE['pending_feature'] = feat_shape


def box(size, at=None, name=None):
    import Part
    w, d, h = [float(x) for x in size]
    shape = Part.makeBox(w, d, h)
    feat = Feature(shape)
    if at is not None:
        feat.at(at)
    _apply_pending(feat.shape)
    return feat


def cylinder(d=None, r=None, h=None, at=None, name=None):
    import Part
    if r is None:
        if d is None:
            raise ValueError('cylinder requires r or d')
        r = float(d) / 2.0
    shape = Part.makeCylinder(float(r), float(h))
    feat = Feature(shape)
    if at is not None:
        feat.at(at)
    _apply_pending(feat.shape)
    return feat


__all__ = ["box", "cylinder"]


