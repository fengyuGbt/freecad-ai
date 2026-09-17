"""AI agent scaffolding: expose FreeCAD modeling helpers as LLM tools.

The idea: an LLM emits a structured *tool call* (function name + JSON
arguments); this module executes it against the real FreeCAD kernel.
Wire any backend by implementing ``FreeCADAgent.complete()`` — see the
``run()`` docstring.

Example tool call (as produced by OpenAI/Anthropic-style function calling):
    {"tool": "make_box", "arguments": {"length": 10, "width": 20, "height": 30}}
"""
from __future__ import annotations

import inspect
import json
from typing import Any, Callable

from .llm import ChatClient

SYSTEM_PROMPT = (
    "You are an AI CAD engineer driving FreeCAD through tool calls. "
    "All dimensions are in millimeters. Use the provided tools to create and "
    "modify parametric models step by step. When the part is finished, reply "
    "with a short summary of what you built. Never invent tool arguments; "
    "ask the user if a required value is missing."
)


class ToolCallError(Exception):
    """Raised when a tool call cannot be executed."""


class Tool:
    """A callable exposed to the LLM, with a JSON schema for its arguments."""

    def __init__(self, func: Callable[..., Any], name: str | None = None) -> None:
        self.func = func
        self.name = name or func.__name__
        self.description = inspect.getdoc(func) or ""
        self.parameters = self._parameters_schema(func)

    @staticmethod
    def _parameters_schema(func: Callable[..., Any]) -> dict[str, Any]:
        """Build a minimal JSON schema from function annotations."""
        sig = inspect.signature(func)
        properties: dict[str, Any] = {}
        required: list[str] = []
        for pname, param in sig.parameters.items():
            if pname == "doc":
                continue  # FreeCAD internals are not LLM-callable
            ptype = param.annotation if param.annotation is not inspect.Parameter.empty else "string"
            schema_type = {
                float: "number", int: "integer", str: "string", bool: "boolean",
            }.get(ptype, "string")
            properties[pname] = {"type": schema_type}
            if param.default is inspect.Parameter.empty:
                required.append(pname)
        return {"type": "object", "properties": properties, "required": required}

    def call(self, arguments: dict[str, Any] | str) -> Any:
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError as exc:
                raise ToolCallError(f"arguments are not valid JSON: {exc}") from exc
        if not isinstance(arguments, dict):
            raise ToolCallError("arguments must be a JSON object")
        return self.func(**arguments)


class FreeCADAgent:
    """Tool registry + executor for LLM-driven FreeCAD modeling.

    Usage:
        agent = FreeCADAgent()          # registers the default modeling tools
        result = agent.execute({"tool": "make_box", "arguments": {...}})
    """

    def __init__(self) -> None:
        self.tools: dict[str, Tool] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        import freecad_ai.modeling as m

        for func in (m.make_box, m.make_cylinder, m.cut, m.shape_volume,
                     m.bounding_box, m.export_shapes):
            self.register(func)

    def register(self, func: Callable[..., Any], name: str | None = None) -> None:
        tool = Tool(func, name=name)
        self.tools[tool.name] = tool

    def describe(self) -> list[dict[str, Any]]:
        """Return the tool list in LLM-function-calling format."""
        return [
            {"name": t.name, "description": t.description, "parameters": t.parameters}
            for t in self.tools.values()
        ]

    def execute(self, call: dict[str, Any]) -> Any:
        """Execute one tool call: {"tool": str, "arguments": dict|str}."""
        name = call.get("tool") or call.get("name")
        if name not in self.tools:
            raise ToolCallError(f"unknown tool: {name!r}; available: {sorted(self.tools)}")
        return self.tools[name].call(call.get("arguments", {}))

    # ------------------------------------------------------------------
    # LLM backend hook
    # ------------------------------------------------------------------
    def run(
        self,
        instruction: str,
        client: ChatClient | None = None,
        max_steps: int = 5,
    ) -> dict[str, Any]:
        """Full agent loop: instruction -> LLM tool call(s) -> FreeCAD execution.

        ``client`` is any object exposing ``chat(messages, tools=...) -> dict``
        (``ChatClient`` by default, which reads OPENAI_API_KEY / OPENAI_BASE_URL /
        OPENAI_MODEL from the environment). The loop repeats until the model
        answers with plain text or ``max_steps`` tool rounds are exhausted.

        Returns {"finish_reason", "steps", "reply"} where each step is
        {"tool", "arguments", "result"} and ``result`` is a JSON-safe summary.
        """
        if client is None:
            client = ChatClient()

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": instruction},
        ]
        steps: list[dict[str, Any]] = []

        for _ in range(max_steps):
            data = client.chat(messages, tools=self.describe())
            msg = data["choices"][0]["message"]
            messages.append({k: v for k, v in msg.items() if k in ("role", "content", "tool_calls")})

            if not msg.get("tool_calls"):
                return {
                    "finish_reason": "stop",
                    "steps": steps,
                    "reply": msg.get("content"),
                }

            for call in msg["tool_calls"]:
                name = call["function"]["name"]
                call_id = call.get("id", f"call_{len(steps) + 1}")

                try:
                    arguments = json.loads(call["function"].get("arguments") or "{}")
                except json.JSONDecodeError as exc:
                    summary = {"error": f"invalid JSON arguments: {exc}"}
                    steps.append({"tool": name, "arguments": {}, **summary})
                    messages.append({"role": "tool", "tool_call_id": call_id,
                                     "content": json.dumps(summary, ensure_ascii=False)})
                    continue

                try:
                    result = self.execute({"tool": name, "arguments": arguments})
                    summary = self._summarize(result)
                    step: dict[str, Any] = {"tool": name, "arguments": arguments, "result": summary}
                except Exception as exc:
                    summary = {"error": str(exc)}
                    step = {"tool": name, "arguments": arguments, "error": str(exc)}
                steps.append(step)
                messages.append({"role": "tool", "tool_call_id": call_id,
                                 "content": json.dumps(summary, ensure_ascii=False)})

        return {"finish_reason": "max_steps", "steps": steps, "reply": None}

    @staticmethod
    def _summarize(value: Any) -> Any:
        """Turn a FreeCAD object (or anything) into a JSON-safe summary."""
        if value is None or isinstance(value, (bool, int, float, str)):
            return value
        if isinstance(value, dict):
            return {k: FreeCADAgent._summarize(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [FreeCADAgent._summarize(v) for v in value]

        # FreeCAD document objects
        if hasattr(value, "Name") and hasattr(value, "TypeId"):
            summary: dict[str, Any] = {"object": value.Name, "type": value.TypeId}
            try:
                volume = value.Shape.Volume
                bb = value.Shape.BoundBox
                summary["volume_mm3"] = round(float(volume), 3)
                summary["bounds"] = [
                    round(bb.XMin, 3), round(bb.YMin, 3), round(bb.ZMin, 3),
                    round(bb.XMax, 3), round(bb.YMax, 3), round(bb.ZMax, 3),
                ]
            except Exception:
                pass
            return summary
        return repr(value)[:200]
