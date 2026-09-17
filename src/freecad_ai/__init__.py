"""freecad_ai — reusable helpers for AI-driven FreeCAD development."""

from .modeling import (  # noqa: F401
    ModelingError,
    bounding_box,
    cut,
    export_shapes,
    make_box,
    make_cylinder,
    new_document,
    save_document,
    shape_volume,
)

__version__ = "0.2.0"
