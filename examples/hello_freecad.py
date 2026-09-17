#!/usr/bin/env python3
"""Minimal headless FreeCAD example: create a box and export it as STL.

Run with FreeCAD's console binary (no GUI needed):
    freecadcmd.exe examples/hello_freecad.py
"""
import os

import FreeCAD as App
import Part

OUT_DIR = os.path.join(os.path.dirname(__file__), "output")
OUT_FILE = os.path.join(OUT_DIR, "hello_freecad.stl")


def main() -> None:
    print("FreeCAD Version:", App.Version())

    doc = App.newDocument("hello")

    # Create a parametric-feature box (10 x 20 x 30 mm)
    box = doc.addObject("Part::Box", "Box")
    box.Length = 10
    box.Width = 20
    box.Height = 30
    doc.recompute()

    # Export to STL (headless-safe, no GUI)
    os.makedirs(OUT_DIR, exist_ok=True)
    Part.export([box], OUT_FILE)
    print(f"STL exported: {OUT_FILE}")


# NOTE: freecadcmd does not set __name__ == "__main__" when running a script,
# so call main() at module level (standard for FreeCAD headless scripts).
main()
