"""freecad_ai — reusable helpers for AI-driven FreeCAD development."""

from .modeling import (  # noqa: F401
    ModelingError,
    bounding_box,
    chamfer,
    common,
    cut,
    export_shapes,
    fillet,
    fuse,
    make_box,
    make_cone,
    make_cylinder,
    make_sphere,
    move,
    new_document,
    save_document,
    set_position,
    shape_volume,
)

__version__ = "0.4.0"
