# freecad-ai

AI-driven development on top of [FreeCAD](https://www.freecad.org/) — parametric modeling, geometry generation, and design automation powered by LLM/AI agents.

## Goals

- Headless FreeCAD scripting for AI-agent-driven CAD workflows
- Generate/repair parametric models programmatically (Part, PartDesign, Sketcher)
- Batch conversion between formats (STEP / STL / OBJ / FCStd)
- A clean Python package boundary (`src/freecad_ai`) for reusable modeling logic
- Example scripts that always run without opening the GUI

## Environment

- FreeCAD 1.0.2 installed at `C:\Program Files\FreeCAD 1.0` (Windows), console binary: `freecadcmd.exe`
- Headless mode: `freecadcmd.exe script.py` — no GUI required
- Python 3.11 bundled with FreeCAD; external deps listed in `requirements.txt`

## Quick start

Run the hello-world example headlessly:

```bat
"C:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe" examples\hello_freecad.py
```

Expected output:

```
FreeCAD Version: ['1', '0', '2', ...]
STL exported: examples/output/hello_freecad.stl
```

## Tests

The test suite runs inside FreeCAD's bundled Python (no separate env needed):

```bat
"C:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe" tests\run_tests.py
```

Covers: volume math (box / cylinder / sphere / cone / boolean ops), bounding
boxes, fillet/chamfer, STL/STEP export, FCStd save, the AI tool executor, and
the full agent loop (offline, scripted LLM client).

## Project layout

```
freecad-ai/
├── src/freecad_ai/        # reusable package
│   ├── modeling.py        # headless Part-based API: box/cylinder/sphere/cone/cut/fuse/...
│   ├── agent.py           # LLM tool registry + full agent loop
│   └── llm.py             # zero-dependency OpenAI-compatible chat client
├── examples/              # runnable scripts
│   ├── hello_freecad.py   # minimal box -> STL
│   ├── parametric_part.py # plate with centered hole (boolean cut, STEP/FCStd)
│   └── llm_modeling.py    # natural language -> model via LLM agent
├── tests/                 # unittest suite, run via tests/run_tests.py
├── requirements.txt       # python deps outside FreeCAD itself
└── README.md
```

## AI usage

```python
from freecad_ai.agent import FreeCADAgent
from freecad_ai.llm import ChatClient

agent = FreeCADAgent()
print(agent.describe())  # tool list in LLM function-calling format

# 1) Execute a tool call directly (no LLM):
agent.execute({"tool": "make_box", "arguments": {"length": 10, "width": 20, "height": 30}})

# 2) Full agent loop: instruction -> LLM tool call(s) -> FreeCAD model
#    Configure via env: OPENAI_API_KEY (required), OPENAI_BASE_URL, OPENAI_MODEL
result = agent.run("Create a plate 60 by 40 by 8 mm with a centered hole of radius 10 mm",
                   client=ChatClient())
print(result)  # {"finish_reason", "steps": [...], "reply": "..."}
```

The `ChatClient` speaks the OpenAI Chat Completions protocol with **no
third-party dependencies** (stdlib only) — OpenAI, DeepSeek, Moonshot, Qwen,
Groq, and local servers (vLLM / Ollama OpenAI-mode) all work by setting
`OPENAI_BASE_URL` / `OPENAI_MODEL`. A live demo:

```bat
set OPENAI_API_KEY=sk-...
"C:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe" examples\llm_modeling.py
```

## Roadmap (draft)

- [ ] AI agent that turns natural-language part descriptions into parametric models
- [ ] Sketch/constraint solver integration for repair and re-parameterization
- [ ] STEP → STL → mesh pipeline for 3D printing / simulation
- [ ] Evaluation harness for generated models (geometry validity, dimension accuracy)

## License

TBD — see LICENSE once decided.
