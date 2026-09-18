"""AI drives the third-party Curves workbench (Gordon surface) through freecad-ai.

Prerequisite (remote FreeCAD 1.0.2, headless):
  - Curves workbench installed under  <user>/AppData/Roaming/FreeCAD/Mod/Curves
  - import name is CASE-SENSITIVE: `freecad.Curves` (not freecad.curves)

Pattern: "LLM gives intent, framework gives geometry". The model passes
semantic numbers (length/width/arch_height); the framework builds the 2x2
curve network and calls the Gordon solver. Verified with GLM-4-Flash
(2026-09-18): one tool call -> 60x40x15.2 mm B-spline arch surface, STL out.

Run (Windows, headless):
  "C:\\Program Files\\FreeCAD 1.0\\bin\\freecadcmd.exe" examples\\ai_curves_surface.py
"""
import json
import os
import sys

try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import FreeCAD as App  # noqa: E402
import Part  # noqa: E402
import Mesh  # noqa: E402

from freecad_ai.agent import FreeCADAgent  # noqa: E402
from freecad_ai.llm import ChatClient  # noqa: E402


def make_panel_surface(name="CurvedPanel", length=60.0, width=40.0, arch_height=10.0):
    """Create a smooth arching panel surface with the Curves workbench.

    length: size along X in mm (positive).
    width: size along Y in mm (positive).
    arch_height: peak rise in Z at the panel center in mm (positive).
    Builds 2 profiles along X (arching arch_height in the middle) and
    2 guides along Y (arching arch_height/2), then generates an interpolated
    B-spline (Gordon) surface through the network. Returns the surface feature.
    """
    from freecad.Curves import gordon

    L, W, H = float(length), float(width), float(arch_height)
    if L <= 0 or W <= 0 or H < 0:
        raise ValueError("length and width must be > 0, arch_height >= 0")

    doc = App.activeDocument() or App.newDocument("ai_curves")

    def make_bspline(points):
        b = Part.BSplineCurve()
        b.interpolate([App.Vector(*p) for p in points])
        return b

    profiles = [
        make_bspline([(0, 0, 0), (L / 2, 0, H), (L, 0, 0)]),
        make_bspline([(0, W, 0), (L / 2, W, H), (L, W, 0)]),
    ]
    guides = [
        make_bspline([(0, 0, 0), (0, W / 2, H / 2), (0, W, 0)]),
        make_bspline([(L, 0, 0), (L, W / 2, H / 2), (L, W, 0)]),
    ]
    net = gordon.InterpolateCurveNetwork(profiles, guides)
    shape = net.surface().toShape()
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = shape
    doc.recompute()
    return obj


def main():
    agent = FreeCADAgent()
    agent.register(make_panel_surface)

    result = agent.run(
        "Create a curved panel surface: 60 mm long along X, 40 mm wide along "
        "Y, arching up 10 mm in the middle (Z peak). Use make_panel_surface.",
        client=ChatClient(),
    )
    print("finish:", result.get("finish_reason"))
    print("reply:", result.get("reply"))
    for i, step in enumerate(result.get("steps", []), 1):
        print(f"[{i}] {step.get('tool')} {json.dumps(step.get('arguments'), ensure_ascii=False)}")
        if step.get("error"):
            print("    ERROR:", step["error"])

    doc = App.activeDocument()
    obj = doc.getObject("CurvedPanel") or doc.Objects[0]
    shape = obj.Shape
    print("area mm2:", round(shape.Area, 3))
    bb = shape.BoundBox
    print("bounds:", bb.XMin, bb.YMin, bb.ZMin, bb.XMax, bb.YMax, bb.ZMax)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ai_gordon_surface.stl")
    mesh = Mesh.Mesh()
    mesh.addFacets(shape.tessellate(0.5))
    mesh.write(out)
    print("STL:", out)


main()
