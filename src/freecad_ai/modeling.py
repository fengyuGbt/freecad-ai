"""Headless modeling API built on FreeCAD's Part module.

These helpers never open a GUI, so they are safe to call from
AI agents, scripts, and CI. Use them through ``freecadcmd.exe``.
"""
from __future__ import annotations

import os
from typing import Iterable

import FreeCAD as App  # noqa: F401  (must load before Part)
import Part


class ModelingError(Exception):
    """Raised when a modeling operation cannot be completed."""


def new_document(name: str = "freecad_ai") -> App.Document:
    """Create a new document (or return existing one with that name)."""
    if App.activeDocument() is None:
        App.newDocument(name)
    return App.activeDocument()


def make_box(
    length: float,
    width: float,
    height: float,
    x: float = 0.0,
    y: float = 0.0,
    z: float = 0.0,
    name: str = "Box",
    doc: App.Document | None = None,
) -> Part.Feature:
    """Create a parametric box feature (mm units) with its base corner at (x, y, z)."""
    if doc is None:
        doc = new_document()
    box = doc.addObject("Part::Box", name)
    box.Length = float(length)
    box.Width = float(width)
    box.Height = float(height)
    box.Placement = App.Placement(App.Vector(x, y, z), App.Rotation())
    doc.recompute()
    return box


def make_cylinder(
    radius: float,
    height: float,
    angle: float = 360.0,
    x: float = 0.0,
    y: float = 0.0,
    z: float = 0.0,
    name: str = "Cylinder",
    doc: App.Document | None = None,
) -> Part.Feature:
    """Create a parametric cylinder feature; (x, y, z) is its base-center position."""
    if doc is None:
        doc = new_document()
    cyl = doc.addObject("Part::Cylinder", name)
    cyl.Radius = float(radius)
    cyl.Height = float(height)
    cyl.Angle = float(angle)
    cyl.Placement = App.Placement(App.Vector(x, y, z), App.Rotation())
    doc.recompute()
    return cyl


def make_sphere(
    radius: float,
    x: float = 0.0,
    y: float = 0.0,
    z: float = 0.0,
    name: str = "Sphere",
    doc: App.Document | None = None,
) -> Part.Feature:
    """Create a parametric sphere feature centered at (x, y, z)."""
    if doc is None:
        doc = new_document()
    sphere = doc.addObject("Part::Sphere", name)
    sphere.Radius = float(radius)
    sphere.Placement = App.Placement(App.Vector(x, y, z), App.Rotation())
    doc.recompute()
    return sphere


def make_cone(
    radius1: float,
    radius2: float,
    height: float,
    x: float = 0.0,
    y: float = 0.0,
    z: float = 0.0,
    name: str = "Cone",
    doc: App.Document | None = None,
) -> Part.Feature:
    """Create a parametric cone/truncated-cone feature with base-center at (x, y, z)."""
    if doc is None:
        doc = new_document()
    cone = doc.addObject("Part::Cone", name)
    cone.Radius1 = float(radius1)
    cone.Radius2 = float(radius2)
    cone.Height = float(height)
    cone.Placement = App.Placement(App.Vector(x, y, z), App.Rotation())
    doc.recompute()
    return cone


def fuse(body: Part.Feature, tool: Part.Feature, name: str = "Fusion") -> Part.Feature:
    """Boolean-union `body` with `tool`."""
    doc = body.Document
    fusion = doc.addObject("Part::Fuse", name)
    fusion.Base = body
    fusion.Tool = tool
    doc.recompute()
    return fusion


def common(body: Part.Feature, tool: Part.Feature, name: str = "Common") -> Part.Feature:
    """Boolean-intersection of `body` and `tool`."""
    doc = body.Document
    inter = doc.addObject("Part::Common", name)
    inter.Base = body
    inter.Tool = tool
    doc.recompute()
    return inter


def fillet(
    base: Part.Feature,
    radius: float,
    edges: list[Part.Edge] | None = None,
    name: str = "Fillet",
) -> Part.Feature:
    """Round all (or the given) edges of ``base``'s shape.

    Implemented with ``TopoShape.makeFillet`` (the ``Part::Fillet`` feature's
    ``Edges`` property is unreliable to assign in headless mode). Returns a
    non-parametric ``Part::Feature``; to change parameters, re-run the call
    and rebuild the downstream features.
    """
    shape = base.Shape
    new_shape = shape.makeFillet(float(radius), edges or list(shape.Edges))
    doc = base.Document
    feat = doc.addObject("Part::Feature", name)
    feat.Shape = new_shape
    doc.recompute()
    return feat


def chamfer(
    base: Part.Feature,
    size: float,
    edges: list[Part.Edge] | None = None,
    name: str = "Chamfer",
) -> Part.Feature:
    """Bevel all (or the given) edges of ``base``'s shape.

    Implemented with ``TopoShape.makeChamfer`` (see ``fillet`` for why).
    Returns a non-parametric ``Part::Feature``.
    """
    shape = base.Shape
    new_shape = shape.makeChamfer(float(size), edges or list(shape.Edges))
    doc = base.Document
    feat = doc.addObject("Part::Feature", name)
    feat.Shape = new_shape
    doc.recompute()
    return feat


def cut(body: Part.Feature, tool: Part.Feature, name: str = "Cut") -> Part.Feature:
    """Boolean-subtract `tool` from `body` (classic hole/plate workflow)."""
    doc = body.Document
    cut = doc.addObject("Part::Cut", name)
    cut.Base = body
    cut.Tool = tool
    doc.recompute()
    return cut


def move(
    feature: Part.Feature,
    dx: float = 0.0,
    dy: float = 0.0,
    dz: float = 0.0,
) -> Part.Feature:
    """Translate `feature` by (dx, dy, dz) relative to its current position."""
    base = feature.Placement.Base
    feature.Placement = App.Placement(
        App.Vector(base.x + dx, base.y + dy, base.z + dz),
        feature.Placement.Rotation,
    )
    feature.Document.recompute()
    return feature


def set_position(
    feature: Part.Feature,
    x: float = 0.0,
    y: float = 0.0,
    z: float = 0.0,
) -> Part.Feature:
    """Set the absolute position (placement base point) of `feature`."""
    feature.Placement = App.Placement(
        App.Vector(x, y, z),
        feature.Placement.Rotation,
    )
    feature.Document.recompute()
    return feature


def shape_volume(feature: Part.Feature) -> float:
    """Return the volume of a feature's shape in mm^3."""
    return float(feature.Shape.Volume)


def bounding_box(feature: Part.Feature) -> dict[str, float]:
    """Return the axis-aligned bounding box of a feature."""
    bb = feature.Shape.BoundBox
    return {
        "xmin": bb.XMin, "ymin": bb.YMin, "zmin": bb.ZMin,
        "xmax": bb.XMax, "ymax": bb.YMax, "zmax": bb.ZMax,
    }


def export_shapes(shapes: Iterable[Part.Feature], path: str) -> str:
    """Export shapes to a file; format chosen by extension (.stl/.step/.obj).

    Parent directories are created automatically. Returns the absolute path.
    """
    path = os.path.abspath(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Part.export(list(shapes), path)
    return path


def save_document(doc: App.Document, path: str) -> str:
    """Save the whole document to a .FCStd file."""
    path = os.path.abspath(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    doc.saveAs(path)
    return path
