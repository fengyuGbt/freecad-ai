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

import FreeCAD as App

from .llm import ChatClient

SYSTEM_PROMPT = (
    "You are an AI CAD engineer driving FreeCAD through tool calls. "
    "All dimensions are in millimeters. Use the provided tools to create and "
    "modify parametric models step by step. You can set a feature's position "
    "directly when creating it via the x/y/z parameters, e.g. "
    "make_cylinder(radius=10, height=8, x=30, y=20, name='hole') centers the "
    "hole's base at (30, 20, 0). Objects you created in previous steps can be "
    "referenced by their name, e.g. cut(body='plate', tool='hole'). Use "
    "set_position or move to adjust placement later. "
    "CRITICAL: if a previous tool result contains a warning, you MUST fix it "
    "yourself by issuing new tool calls (recreate or reposition the feature "
    "and redo the boolean operation). Never reply with plain text while a "
    "warning is still open. When the part is finished and correct, reply with "
    "a short summary of what you built. Never invent tool arguments; ask the "
    "user if a required value is missing."
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
    def _annotation_type(annotation: Any) -> type | None:
        """Resolve an annotation that may be a postponed (PEP 563) string."""
        if annotation is inspect.Parameter.empty:
            return None
        if isinstance(annotation, str):
            return {"float": float, "int": int, "bool": bool, "str": str}.get(annotation)
        if annotation in (float, int, bool, str):
            return annotation
        return None

    @staticmethod
    def _parameters_schema(func: Callable[..., Any]) -> dict[str, Any]:
        """Build a minimal JSON schema from function annotations."""
        sig = inspect.signature(func)
        properties: dict[str, Any] = {}
        required: list[str] = []
        for pname, param in sig.parameters.items():
            if pname == "doc":
                continue  # FreeCAD internals are not LLM-callable
            ptype = Tool._annotation_type(param.annotation)
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

        # Coerce string values to their annotated type (LLMs often emit "30")
        sig = inspect.signature(self.func)
        for key, value in list(arguments.items()):
            param = sig.parameters.get(key)
            if param is None or not isinstance(value, str):
                continue
            ptype = Tool._annotation_type(param.annotation)
            if ptype is float:
                try:
                    arguments[key] = float(value)
                except ValueError:
                    pass
            elif ptype is int:
                try:
                    arguments[key] = int(float(value))
                except ValueError:
                    pass
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

        for func in (m.make_box, m.make_cylinder, m.make_sphere, m.make_cone,
                     m.fuse, m.common, m.cut, m.move, m.set_position,
                     m.fillet, m.chamfer, m.shape_volume,
                     m.bounding_box, m.export_shapes):
            self.register(func)

    def register(self, func: Callable[..., Any], name: str | None = None) -> None:
        tool = Tool(func, name=name)
        self.tools[tool.name] = tool

    @staticmethod
    def _resolve_object(value: Any) -> Any:
        """Resolve a string argument that names an object in the active document.

        LLMs naturally pass object names (e.g. ``body='plate'``) as strings;
        convert them to the real FreeCAD objects so downstream tools work.
        """
        if isinstance(value, str):
            doc = App.activeDocument()
            if doc is not None:
                obj = doc.getObject(value)
                if obj is not None:
                    return obj
        return value

    def describe(self) -> list[dict[str, Any]]:
        """Return the tool list in LLM-function-calling format."""
        return [
            {"name": t.name, "description": t.description, "parameters": t.parameters}
            for t in self.tools.values()
        ]

    def execute(self, call: dict[str, Any]) -> Any:
        """Execute one tool call: {"tool": str, "arguments": dict|str}.

        String arguments that name an existing object in the active document
        are resolved to the real FreeCAD objects before the tool runs.
        """
        name = call.get("tool") or call.get("name")
        if name not in self.tools:
            raise ToolCallError(f"unknown tool: {name!r}; available: {sorted(self.tools)}")
        arguments = call.get("arguments", {})
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError as exc:
                raise ToolCallError(f"arguments are not valid JSON: {exc}") from exc
        resolved = {k: self._resolve_object(v) for k, v in arguments.items()}
        return self.tools[name].call(resolved)

    # ------------------------------------------------------------------
    # LLM backend hook
    # ------------------------------------------------------------------
    def run(
        self,
        instruction: str,
        client: ChatClient | None = None,
        max_steps: int = 8,
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
                    if name == "cut":
                        warning = self._boolean_quality_warning(result, arguments)
                        if warning:
                            summary["warning"] = warning
                    step: dict[str, Any] = {"tool": name, "arguments": arguments, "result": summary}
                except Exception as exc:
                    summary = {"error": str(exc)}
                    step = {"tool": name, "arguments": arguments, "error": str(exc)}
                steps.append(step)
                messages.append({"role": "tool", "tool_call_id": call_id,
                                 "content": json.dumps(summary, ensure_ascii=False)})

        return {"finish_reason": "max_steps", "steps": steps, "reply": None}

    @staticmethod
    def _boolean_quality_warning(result: Any, arguments: dict[str, Any]) -> str | None:
        """Detect a cut where the tool was not fully inside the body.

        Returns a warning string to feed back to the LLM so it can correct
        the tool's position, or None when the cut looks complete.
        """
        try:
            body_ref = arguments.get("body")
            tool_ref = arguments.get("tool")
            doc = App.activeDocument()
            if doc is None:
                return None
            body = doc.getObject(body_ref) if isinstance(body_ref, str) else body_ref
            tool = doc.getObject(tool_ref) if isinstance(tool_ref, str) else tool_ref
            if body is None or tool is None or not hasattr(body, "Shape") or not hasattr(tool, "Shape"):
                return None
            tool_vol = tool.Shape.Volume
            if tool_vol <= 0:
                return None
            removed = body.Shape.Volume - result.Shape.Volume
            ratio = removed / tool_vol
            if ratio < 0.9:
                body_c = body.Shape.BoundBox.Center
                tool_c = tool.Shape.BoundBox.Center
                return (
                    f"the cut removed only {ratio:.0%} of the tool volume, so the tool "
                    "was NOT fully inside the body (e.g. the hole is not centered). "
                    f"The body center is at ({body_c.x:.1f}, {body_c.y:.1f}, {body_c.z:.1f}) "
                    f"and the tool center is at ({tool_c.x:.1f}, {tool_c.y:.1f}, {tool_c.z:.1f}). "
                    "Fix it now: align the tool with the body center, e.g. call "
                    f"move(feature='{tool.Name}', dx={body_c.x - tool_c.x:.1f}, "
                    f"dy={body_c.y - tool_c.y:.1f}, dz={body_c.z - tool_c.z:.1f}) "
                    "and then cut again."
                )
        except Exception:
            return None
        return None

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
