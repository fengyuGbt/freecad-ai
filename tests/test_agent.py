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

    def test_execute_invalid_json_raises(self) -> None:
        with self.assertRaises(ToolCallError):
            self.agent.execute({"tool": "make_box", "arguments": "not json"})

    def test_run_without_key_raises_clear_error(self) -> None:
        from freecad_ai.llm import LLMError

        with self.assertRaises(LLMError):
            self.agent.run("make a box 10 by 20 by 30")


if __name__ == "__main__":
    unittest.main()
