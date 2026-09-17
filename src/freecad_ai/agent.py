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
    def run(self, instruction: str) -> Any:
        """Full agent loop: instruction -> tool call -> result.

        Implement the missing backend (OpenAI / Anthropic / local model)
        and return a dict with keys ``tool`` and ``arguments`` as JSON:
            prompt = f"{instruction}\n\nTools:\n{json.dumps(self.describe())}"
            reply = <your LLM call here>
            return json.loads(reply)
        """
        raise NotImplementedError(
            "LLM backend not wired yet — see README roadmap. "
            "Meanwhile use agent.execute() with a hand-written tool call."
        )
