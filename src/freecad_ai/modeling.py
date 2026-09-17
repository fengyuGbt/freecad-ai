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
    name: str = "Box",
    doc: App.Document | None = None,
) -> Part.Feature:
    """Create a parametric box feature (mm units)."""
    if doc is None:
        doc = new_document()
    box = doc.addObject("Part::Box", name)
    box.Length = float(length)
    box.Width = float(width)
    box.Height = float(height)
    doc.recompute()
    return box


def make_cylinder(
    radius: float,
    height: float,
    angle: float = 360.0,
    name: str = "Cylinder",
    doc: App.Document | None = None,
) -> Part.Feature:
    """Create a parametric cylinder feature."""
    if doc is None:
        doc = new_document()
    cyl = doc.addObject("Part::Cylinder", name)
    cyl.Radius = float(radius)
    cyl.Height = float(height)
    cyl.Angle = float(angle)
    doc.recompute()
    return cyl


def cut(body: Part.Feature, tool: Part.Feature, name: str = "Cut") -> Part.Feature:
    """Boolean-subtract `tool` from `body` (classic hole/plate workflow)."""
    doc = body.Document
    cut = doc.addObject("Part::Cut", name)
    cut.Base = body
    cut.Tool = tool
    doc.recompute()
    return cut


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
