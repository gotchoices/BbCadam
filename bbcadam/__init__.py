"""
BbCadam - A FreeCAD-based scripting framework for parametric CAD design.

This package provides a DSL for creating 3D CAD models using Python scripts
that run within FreeCAD's Python interpreter.
"""

__version__ = "0.1.0"
__author__ = "BbCadam Contributors"
__email__ = ""
__description__ = "A FreeCAD-based scripting framework for parametric CAD design"

# Import the main DSL functions for easy access (only when FreeCAD is available)
try:
    from .api import (
        # Core DSL functions
        box,
        cylinder,
        feature,
        section,
        sketch,
        
        # Assembly functions
        # component,  # temporarily disabled until assembly API is restored
        
        # Utility functions
        lcs,
        add_lcs,
        param,
        export,
        export_step,
        export_stl,
    )
    
    # Re-export for backward compatibility
    __all__ = [
        "box",
        "cylinder", 
        "feature",
        "section",
        "sketch",
        # "component",
        "lcs",
        "add_lcs",
        "param",
        "export",
        "export_step",
        "export_stl",
    ]
except ImportError:
    # FreeCAD not available - CLI tools can still work
    __all__ = []
