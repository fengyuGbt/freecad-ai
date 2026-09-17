"""Tests for freecad_ai.modeling — run inside FreeCAD's Python (see run_tests.py)."""
import math
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from freecad_ai import modeling as m


class ModelingTest(unittest.TestCase):

    def setUp(self) -> None:
        import FreeCAD as App

        if App.activeDocument() is not None:
            App.closeDocument(App.activeDocument().Name)
        self.doc = m.new_document("test")

    def test_box_volume(self) -> None:
        box = m.make_box(10, 20, 30, doc=self.doc)
        self.assertAlmostEqual(m.shape_volume(box), 10 * 20 * 30, places=6)

    def test_cylinder_volume(self) -> None:
        cyl = m.make_cylinder(5, 10, doc=self.doc)
        self.assertAlmostEqual(m.shape_volume(cyl), math.pi * 25 * 10, places=4)

    def test_sphere_volume(self) -> None:
        sphere = m.make_sphere(3, doc=self.doc)
        self.assertAlmostEqual(m.shape_volume(sphere), 4 / 3 * math.pi * 27, places=4)

    def test_cone_volume(self) -> None:
        cone = m.make_cone(5, 0, 10, doc=self.doc)
        self.assertAlmostEqual(m.shape_volume(cone), math.pi * 25 * 10 / 3, places=4)

    def test_fuse_volume(self) -> None:
        import FreeCAD as App

        a = m.make_box(10, 10, 10, name="A", doc=self.doc)
        b = m.make_box(10, 10, 10, name="B", doc=self.doc)
        b.Placement = App.Placement(App.Vector(10, 0, 0), App.Rotation())
        fused = m.fuse(a, b)
        self.assertAlmostEqual(m.shape_volume(fused), 2000, places=6)

    def test_common_volume(self) -> None:
        import FreeCAD as App

        a = m.make_box(10, 10, 10, name="A", doc=self.doc)
        b = m.make_box(10, 10, 10, name="B", doc=self.doc)
        b.Placement = App.Placement(App.Vector(5, 0, 0), App.Rotation())
        inter = m.common(a, b)
        self.assertAlmostEqual(m.shape_volume(inter), 500, places=6)

    def test_fillet_reduces_volume(self) -> None:
        box = m.make_box(40, 40, 40, doc=self.doc)
        before = m.shape_volume(box)
        rounded = m.fillet(box, 5)
        after = m.shape_volume(rounded)
        self.assertGreater(before, after)
        self.assertGreater(after, 0)

    def test_chamfer_reduces_volume(self) -> None:
        box = m.make_box(40, 40, 40, doc=self.doc)
        before = m.shape_volume(box)
        beveled = m.chamfer(box, 5)
        after = m.shape_volume(beveled)
        self.assertGreater(before, after)
        self.assertGreater(after, 0)

    def test_cut_creates_hole(self) -> None:
        import FreeCAD as App

        plate = m.make_box(40, 40, 5, name="Plate", doc=self.doc)
        hole = m.make_cylinder(8, 5, name="Hole", doc=self.doc)
        # Move the cylinder to the plate center before cutting
        hole.Placement = App.Placement(App.Vector(20, 20, 0), App.Rotation())
        result = m.cut(plate, hole, name="Cut")
        expected = 40 * 40 * 5 - math.pi * 64 * 5
        self.assertAlmostEqual(m.shape_volume(result), expected, delta=0.001)

    def test_bounding_box(self) -> None:
        box = m.make_box(10, 20, 30, doc=self.doc)
        bb = m.bounding_box(box)
        self.assertAlmostEqual(bb["xmax"] - bb["xmin"], 10, places=9)
        self.assertAlmostEqual(bb["ymax"] - bb["ymin"], 20, places=9)
        self.assertAlmostEqual(bb["zmax"] - bb["zmin"], 30, places=9)

    def test_export_stl(self) -> None:
        box = m.make_box(1, 1, 1, doc=self.doc)
        tmp = tempfile.mkdtemp()
        path = m.export_shapes([box], os.path.join(tmp, "out.stl"))
        self.assertTrue(os.path.exists(path))
        self.assertGreater(os.path.getsize(path), 0)

    def test_export_creates_parent_dir(self) -> None:
        box = m.make_box(1, 1, 1, doc=self.doc)
        tmp = tempfile.mkdtemp()
        path = m.export_shapes([box], os.path.join(tmp, "deep", "nested", "out.step"))
        self.assertTrue(os.path.exists(path))

    def test_save_document(self) -> None:
        m.make_box(1, 1, 1, doc=self.doc)
        tmp = tempfile.mkdtemp()
        path = m.save_document(self.doc, os.path.join(tmp, "doc.FCStd"))
        self.assertTrue(os.path.exists(path))
        self.assertGreater(os.path.getsize(path), 0)


if __name__ == "__main__":
    unittest.main()
