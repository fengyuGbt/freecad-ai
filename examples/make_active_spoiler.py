"""Active rear spoiler (like XPeng G6 electric wing) — AI-driven parametric model.

The model has three sub-assemblies:
  1. Wing surface  : NACA-style airfoil lofted along the span (Curves/Part)
  2. Lift mechanism: two parallel four-bar linkages + guide rails
  3. Base          : simplified trunk-mounted base plate with recess

LLM gives intent (span/chord/aoa/rise), framework gives geometry.
Run headless:
  "C:\\Program Files\\FreeCAD 1.0\\bin\\freecadcmd.exe" make_active_spoiler.py
"""
import json
import math
import os
import sys

try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

import FreeCAD as App  # noqa: E402
import Part  # noqa: E402
import Mesh  # noqa: E402

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
os.makedirs(OUT_DIR, exist_ok=True)


def naca_airfoil_points(chord, thickness, n=24):
    """Return (upper, lower) point lists of a NACA 00xx-ish airfoil."""
    upper, lower = [], []
    for i in range(n + 1):
        x = chord * (i / n)
        xt = x / chord
        yt = (thickness / 0.2) * (
            0.2969 * math.sqrt(xt) - 0.1260 * xt - 0.3516 * xt ** 2
            + 0.2843 * xt ** 3 - 0.1015 * xt ** 4
        )
        upper.append(App.Vector(x, 0, yt))
        lower.append(App.Vector(x, 0, -yt))
    return upper, lower


def make_wing(doc, span, chord, thickness, aoa_deg, offset_z):
    """Solid lofted wing (closed airfoil section) with angle of attack."""
    upper, lower = naca_airfoil_points(chord, thickness)
    aoa = math.radians(aoa_deg)
    rot = App.Rotation(App.Vector(0, 1, 0), -math.degrees(aoa))
    off = App.Vector(0, 0, offset_z)

    def closed_wire(scale, dy):
        pts = [rot.multVec(p) * scale + App.Vector(0, dy, 0) + off for p in upper]
        pts += [rot.multVec(p) * scale + App.Vector(0, dy, 0) + off for p in lower[::-1]]
        return Part.Wire(Part.makePolygon(pts + [pts[0]]))

    w_root = closed_wire(1.0, 0)
    w_tip = closed_wire(0.92, span)
    shape = Part.makeLoft([w_root, w_tip])
    obj = doc.addObject("Part::Feature", "WingSurface")
    obj.Shape = shape
    doc.recompute()
    return obj


def make_linkage(doc, side, span, rise, base_z, chord, arm_len=70, arm_thick=10):
    """One four-bar linkage arm (box rod) from base to wing; side=+1/-1."""
    arm = doc.addObject("Part::Box", f"Arm{'L' if side > 0 else 'R'}")
    arm.Length = arm_len
    arm.Width = 14
    arm.Height = arm_thick
    doc.recompute()
    # position: pivot at base inner side, top connects near wing underside
    y = side * (span * 0.42)
    x = chord * 0.45
    z_base = base_z + 12
    dz = rise * 0.55 + 18
    ang = math.degrees(math.atan2(dz, arm_len * 0.9))
    arm.Placement = App.Placement(
        App.Vector(x - arm_len * 0.45, y - 7, z_base),
        App.Rotation(App.Vector(0, 0, 1), -side * 12).multiply(
            App.Rotation(App.Vector(1, 0, 0), -ang)),
    )
    doc.recompute()
    return arm


def make_base(doc, span, chord, rise):
    """Simplified trunk base plate with recess for the stowed wing."""
    base = doc.addObject("Part::Box", "BasePlate")
    base.Length = chord + 60
    base.Width = span + 60
    base.Height = 14
    doc.recompute()
    base.Placement = App.Placement(
        App.Vector(-30, -30, 0), App.Rotation())
    doc.recompute()

    # recess walls (two rails along span)
    for i, y0 in enumerate([-span * 0.5 - 4, span * 0.5 - 6]):
        rail = doc.addObject("Part::Box", f"Rail{i}")
        rail.Length = chord + 20
        rail.Width = 8
        rail.Height = 30 + rise * 0.15
        doc.recompute()
        rail.Placement = App.Placement(
            App.Vector(-10, y0, 12), App.Rotation())
        doc.recompute()
    return base


def build(span=1200.0, chord=180.0, thickness=16.0, aoa_deg=8.0, rise=0.0):
    """Build the active spoiler model. rise=0 stowed, >0 deployed (mm lift)."""
    doc = App.newDocument("ActiveSpoiler")
    base = make_base(doc, span, chord, rise)
    wing = make_wing(doc, span, chord, thickness, aoa_deg, offset_z=14.0 + rise)
    make_linkage(doc, +1, span, rise, base_z=14.0, chord=chord)
    make_linkage(doc, -1, span, rise, base_z=14.0, chord=chord)
    doc.recompute()
    return doc


def export(doc, name):
    shape = Part.makeCompound([o.Shape for o in doc.Objects if o.isDerivedFrom("Part::Feature")])
    step = os.path.join(OUT_DIR, name + ".step")
    shape.exportStep(step)
    mesh = Mesh.Mesh()
    mesh.addFacets(shape.tessellate(2.0))
    stl = os.path.join(OUT_DIR, name + ".stl")
    mesh.write(stl)
    return step, stl


RESULT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "spoiler_result.json")
try:
    params = {"span": 1200.0, "chord": 180.0, "thickness": 16.0, "aoa_deg": 8.0, "rise": 45.0}
    if len(sys.argv) > 1:
        try:
            params.update(json.loads(sys.argv[1]))
        except Exception as e:
            print("bad params:", e)

    doc = build(**params)
    doc.recompute()
    doc2 = App.newDocument("Stowed")
    base = make_base(doc2, params["span"], params["chord"], 0.0)
    wing = make_wing(doc2, params["span"], params["chord"], params["thickness"],
                     params["aoa_deg"], offset_z=14.0)
    make_linkage(doc2, +1, params["span"], 0.0, 14.0, params["chord"])
    make_linkage(doc2, -1, params["span"], 0.0, 14.0, params["chord"])
    doc2.recompute()

    s1 = export(doc, "spoiler_deployed")
    s2 = export(doc2, "spoiler_stowed")

    facts = {"params": params, "deployed_stl": s1, "stowed_stl": s2, "states": {}}
    for label, d in [("deployed", doc), ("stowed", doc2)]:
        comp = Part.makeCompound([o.Shape for o in d.Objects if o.isDerivedFrom("Part::Feature")])
        bb = comp.BoundBox
        facts["states"][label] = {
            "bounds": [bb.XMin, bb.YMin, bb.ZMin, bb.XMax, bb.YMax, bb.ZMax],
            "volume_mm3": comp.Volume,
        }
    with open(RESULT_FILE, "w") as f:
        json.dump(facts, f, indent=2, default=str)
    print("OK ->", RESULT_FILE)
except Exception:
    import traceback
    with open(RESULT_FILE, "w") as f:
        f.write(traceback.format_exc())
    raise
