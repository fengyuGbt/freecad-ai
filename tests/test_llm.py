"""Tests for the LLM agent loop — offline, using a scripted fake client."""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from freecad_ai.agent import FreeCADAgent
from freecad_ai.llm import ChatClient, LLMError


class FakeClient:
    """Duck-typed stand-in for ChatClient: replays scripted responses."""

    def __init__(self, responses: list[dict]) -> None:
        self.responses = list(responses)
        self.requests: list[tuple[int, bool]] = []  # (n_messages, has_tools)

    def chat(self, messages: list[dict], tools: list[dict] | None = None) -> dict:
        self.requests.append((len(messages), bool(tools)))
        if not self.responses:
            raise AssertionError("FakeClient ran out of scripted responses")
        return self.responses.pop(0)


def _assistant_text(content: str) -> dict:
    return {"choices": [{"message": {"role": "assistant", "content": content}}]}


def _assistant_toolcall(name: str, arguments: dict, call_id: str = "call_1") -> dict:
    return {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": call_id,
                    "function": {"name": name, "arguments": json.dumps(arguments)},
                }],
            }
        }]
    }


class LLMLoopTest(unittest.TestCase):

    def setUp(self) -> None:
        import FreeCAD as App

        if App.activeDocument() is not None:
            App.closeDocument(App.activeDocument().Name)
        self.agent = FreeCADAgent()

    def test_single_tool_call_then_final_reply(self) -> None:
        fake = FakeClient([
            _assistant_toolcall("make_box", {"length": 1, "width": 2, "height": 3}),
            _assistant_text("Built a 1x2x3 box."),
        ])
        result = self.agent.run("make a box", client=fake)

        self.assertEqual(result["finish_reason"], "stop")
        self.assertEqual(len(result["steps"]), 1)
        self.assertEqual(result["steps"][0]["tool"], "make_box")
        self.assertEqual(result["steps"][0]["result"]["volume_mm3"], 6.0)
        self.assertEqual(result["reply"], "Built a 1x2x3 box.")
        # tool requests must carry the tool schema
        self.assertTrue(fake.requests[0][1])

    def test_two_tool_calls_in_sequence(self) -> None:
        fake = FakeClient([
            _assistant_toolcall("make_box", {"length": 4, "width": 4, "height": 1}, "call_1"),
            _assistant_toolcall("make_cylinder", {"radius": 1, "height": 1}, "call_2"),
            _assistant_text("Plate and hole ready."),
        ])
        result = self.agent.run("plate with hole", client=fake)

        self.assertEqual(len(result["steps"]), 2)
        self.assertEqual([s["tool"] for s in result["steps"]], ["make_box", "make_cylinder"])

    def test_unknown_tool_error_reported_back(self) -> None:
        fake = FakeClient([
            _assistant_toolcall("does_not_exist", {}),
            _assistant_text("Sorry."),
        ])
        result = self.agent.run("do it", client=fake)
        self.assertIn("error", result["steps"][0])
        self.assertIn("unknown tool", result["steps"][0]["error"])

    def test_invalid_json_arguments_reported_back(self) -> None:
        response = {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": "call_1",
                        "function": {"name": "make_box", "arguments": "not json"},
                    }],
                }
            }]
        }
        fake = FakeClient([response, _assistant_text("fixed.")])
        result = self.agent.run("make it", client=fake)
        self.assertIn("error", result["steps"][0])
        self.assertIn("invalid JSON", result["steps"][0]["error"])

    def test_max_steps_stops_loop(self) -> None:
        script = [_assistant_toolcall("make_box", {"length": 1, "width": 1, "height": 1})] * 3
        fake = FakeClient(script)
        result = self.agent.run("keep going", client=fake, max_steps=2)

        self.assertEqual(result["finish_reason"], "max_steps")
        self.assertEqual(len(result["steps"]), 2)

    def test_llm_error_propagates(self) -> None:
        class BrokenClient:
            def chat(self, messages, tools=None):  # noqa: ANN001
                raise LLMError("boom")

        with self.assertRaises(LLMError):
            self.agent.run("hi", client=BrokenClient())

    def test_chat_client_requires_key(self) -> None:
        client = ChatClient(api_key="", base_url="http://127.0.0.1:9/v1", model="x")
        with self.assertRaises(LLMError):
            client.chat([{"role": "user", "content": "hi"}])


if __name__ == "__main__":
    unittest.main()
