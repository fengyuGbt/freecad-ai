"""Tests for freecad_ai.agent — tool registry + executor for LLM tool calls."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from freecad_ai.agent import FreeCADAgent, ToolCallError


class AgentTest(unittest.TestCase):

    def setUp(self) -> None:
        import FreeCAD as App

        if App.activeDocument() is not None:
            App.closeDocument(App.activeDocument().Name)
        self.agent = FreeCADAgent()

    def test_describe_lists_tools(self) -> None:
        names = {t["name"] for t in self.agent.describe()}
        self.assertIn("make_box", names)
        self.assertIn("make_cylinder", names)
        self.assertIn("cut", names)
        self.assertIn("shape_volume", names)

    def test_execute_make_box(self) -> None:
        result = self.agent.execute({
            "tool": "make_box",
            "arguments": {"length": 1, "width": 2, "height": 3},
        })
        self.assertAlmostEqual(result.Shape.Volume, 6.0, places=6)

    def test_execute_with_json_string_arguments(self) -> None:
        result = self.agent.execute({
            "tool": "make_cylinder",
            "arguments": '{"radius": 2, "height": 5}',
        })
        self.assertAlmostEqual(result.Shape.Volume, 20.0 * 3.1415926535, places=4)

    def test_execute_unknown_tool_raises(self) -> None:
        with self.assertRaises(ToolCallError):
            self.agent.execute({"tool": "does_not_exist", "arguments": {}})

    def test_object_name_resolution(self) -> None:
        import FreeCAD as App

        plate = self.agent.execute({
            "tool": "make_box",
            "arguments": {"length": 40, "width": 40, "height": 5, "name": "plate"},
        })
        hole = self.agent.execute({
            "tool": "make_cylinder",
            "arguments": {"radius": 8, "height": 5, "name": "hole"},
        })
        # Center the hole, referencing objects by NAME (as an LLM would)
        self.agent.execute({"tool": "set_position",
                            "arguments": {"feature": "hole", "x": 20, "y": 20}})
        result = self.agent.execute({
            "tool": "cut",
            "arguments": {"body": "plate", "tool": "hole", "name": "Cut"},
        })
        self.assertAlmostEqual(result.Shape.Volume, 40 * 40 * 5 - 3.1415926535 * 64 * 5,
                               delta=0.001)
        # the unresolved name stays a string
        self.assertIsNone(App.activeDocument().getObject("no_such_object"))
        self.assertEqual(self.agent._resolve_object("no_such_object"), "no_such_object")

    def test_set_position_and_move(self) -> None:
        box = self.agent.execute({
            "tool": "make_box",
            "arguments": {"length": 10, "width": 10, "height": 10},
        })
        self.agent.execute({"tool": "move", "arguments": {"feature": box, "dx": 5}})
        self.assertAlmostEqual(box.Placement.Base.x, 5.0, places=9)
        self.agent.execute({"tool": "set_position", "arguments": {"feature": box, "x": 3, "y": 4, "z": 5}})
        self.assertAlmostEqual(box.Placement.Base.x, 3.0, places=9)
        self.assertAlmostEqual(box.Placement.Base.y, 4.0, places=9)
        self.assertAlmostEqual(box.Placement.Base.z, 5.0, places=9)

    def test_string_numbers_are_coerced(self) -> None:
        # LLMs often emit numbers as strings; they must be coerced per annotation
        box = self.agent.execute({
            "tool": "make_box",
            "arguments": {"length": "10", "width": "20", "height": "30"},
        })
        self.assertAlmostEqual(box.Shape.Volume, 6000, places=6)
        self.agent.execute({
            "tool": "move",
            "arguments": {"feature": box, "dx": "5", "dy": "2", "dz": "0"},
        })
        self.assertAlmostEqual(box.Placement.Base.x, 5.0, places=9)
        self.assertAlmostEqual(box.Placement.Base.y, 2.0, places=9)

    def test_execute_invalid_json_raises(self) -> None:
        with self.assertRaises(ToolCallError):
            self.agent.execute({"tool": "make_box", "arguments": "not json"})

    def test_run_without_key_raises_clear_error(self) -> None:
        from freecad_ai.llm import ChatClient, LLMError

        client = ChatClient(api_key="", base_url="http://127.0.0.1:9/v1", model="x")
        with self.assertRaises(LLMError):
            self.agent.run("make a box 10 by 20 by 30", client=client)


if __name__ == "__main__":
    unittest.main()
