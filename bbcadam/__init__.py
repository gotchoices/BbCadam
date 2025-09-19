"""
BbCadam - A FreeCAD-based scripting framework for parametric CAD design.

This package provides a DSL for creating 3D CAD models using Python scripts
that run within FreeCAD's Python interpreter.
"""

__version__ = "0.1.0"
__author__ = "BbCadam Contributors"
__email__ = ""
__description__ = "A FreeCAD-based scripting framework for parametric CAD design"

# Prefer new scaffold modules; keep api.py as reference (not imported here)
try:
    # Core DSL elements from new scaffold
    from .core.primitives import box, cylinder
    from .core.dsl_core import (
        log,
        _set_ctx,
        _reset_state,
        param,
        lcs,
        add_lcs,
        feature,
    )
    # Expose internals needed by builder
    from .core.dsl_core import _finish_build
    from .core.profiles import section, sketch
    # Provide export() facade that finishes build and delegates to core
    def export(kinds=None, name=None, to=None):
        from .core.dsl_core import export_formats as _export_formats
        from .core.dsl_core import _finish_build as _finish
        from .core.dsl_core import _CTX
        obj = _finish(name or _CTX.part_name)
        if obj:
            _export_formats(_CTX, obj, kinds=kinds, name=name, to=to)
    # Keep explicit step/stl helpers via export wrapper (name-compatible re-export)
    def export_step(part_name: str):
        from .core.dsl_core import export_step as _estep
        from .core.dsl_core import _finish_build as _finish
        from .core.dsl_core import _CTX
        obj = _finish(part_name)
        if obj:
            _estep(obj, _CTX.paths.step_parts / f"{part_name}.step")

    def export_stl(part_name: str):
        from .core.dsl_core import export_stl as _estl
        from .core.dsl_core import _finish_build as _finish
        from .core.dsl_core import _CTX
        obj = _finish(part_name)
        if obj:
            _estl(obj, _CTX.paths.stl_parts / f"{part_name}.stl")

    __all__ = [
        "box",
        "cylinder",
        "feature",
        "section",
        "sketch",
        "lcs",
        "add_lcs",
        "param",
        "export",
        "export_step",
        "export_stl",
        "log",
        "_set_ctx",
        "_reset_state",
    ]
except Exception:
    __all__ = []
