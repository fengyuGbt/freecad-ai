#!/usr/bin/env python3
"""Parametric example: a plate with a centered through-hole (boolean cut).

Run headlessly:
    freecadcmd.exe examples/parametric_part.py
"""
import os
import sys

import FreeCAD as App

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from freecad_ai import modeling as m


def main() -> None:
    plate_len, plate_wid, plate_h = 60.0, 40.0, 8.0
    hole_r = 10.0

    plate = m.make_box(plate_len, plate_wid, plate_h, name="Plate")
    hole = m.make_cylinder(hole_r, plate_h, name="Hole")
    # Center the hole in the plate
    hole.Placement = App.Placement(
        App.Vector(plate_len / 2, plate_wid / 2, 0), App.Rotation()
    )
    part = m.cut(plate, hole, name="PlateWithHole")

    expected = plate_len * plate_wid * plate_h - 3.1415926535 * hole_r ** 2 * plate_h
    print(f"Plate volume: {m.shape_volume(part):.3f} mm^3 (expected ~{expected:.3f})")
    print(f"Bounding box: {m.bounding_box(part)}")

    out_dir = os.path.join(os.path.dirname(__file__), "output")
    print(f"STEP exported: {m.export_shapes([part], os.path.join(out_dir, 'plate_with_hole.step'))}")
    print(f"FCStd saved:   {m.save_document(part.Document, os.path.join(out_dir, 'plate_with_hole.FCStd'))}")


main()
