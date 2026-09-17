#!/usr/bin/env python3
"""Natural-language part description -> FreeCAD model via an LLM.

Configuration (environment variables):
    OPENAI_API_KEY     required (any OpenAI-compatible key works)
    OPENAI_BASE_URL    optional, default https://api.openai.com/v1
    OPENAI_MODEL       optional, default gpt-4o-mini
    FC_INSTRUCTION     optional custom part description

Run headlessly:
    set OPENAI_API_KEY=sk-...
    "C:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe" examples\llm_modeling.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from freecad_ai.agent import FreeCADAgent
from freecad_ai.llm import ChatClient, LLMError


def main() -> None:
    instruction = os.environ.get(
        "FC_INSTRUCTION",
        "Create a plate 60 by 40 by 8 mm and drill a centered through hole of radius 10 mm.",
    )
    client = ChatClient()

    if not client.api_key:
        print("[skip] OPENAI_API_KEY is not set - the real LLM loop needs it.")
        print("Expected tool calls for this instruction: make_box, make_cylinder, cut.")
        print("Set OPENAI_API_KEY (and optionally OPENAI_BASE_URL / OPENAI_MODEL) and rerun.")
        return

    agent = FreeCADAgent()
    print("Instruction:", instruction)
    try:
        result = agent.run(instruction, client=client)
    except LLMError as exc:
        print(f"[error] LLM call failed: {exc}")
        return

    print("\nSteps executed by the agent:")
    for i, step in enumerate(result["steps"], 1):
        detail = step.get("result", step.get("error"))
        print(f"  {i}. {step['tool']}({step['arguments']}) -> {detail}")
    print("\nAgent reply:", result["reply"])


main()
