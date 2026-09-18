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
│   ├── llm_modeling.py    # natural language -> model via LLM agent
│   └── ai_curves_surface.py  # LLM drives the Curves workbench (Gordon surface)
├── docs/
│   └── freecad-modules-ai-research.md  # third-party modules + AI survey
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
Groq, Zhipu (GLM), and local servers (vLLM / Ollama OpenAI-mode) all work by
setting `OPENAI_BASE_URL` / `OPENAI_MODEL`.

### Zhipu GLM-4-Flash (free) — verified end-to-end

```bat
set OPENAI_API_KEY=<your zhipu key>        &  :: id.secret format
set OPENAI_BASE_URL=https://open.bigmodel.cn/api/paas/v4
set OPENAI_MODEL=glm-4-flash
"C:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe" examples\llm_modeling.py
```

Verified live on a remote desktop (FreeCAD 1.0.2): the agent created a
60x40x8 plate, drilled a centered r=10 hole, and the final volume matched the
theoretical value (16686.726 mm^3) after the self-correction loop.

### Reliability features for LLM-driven CAD

- **Object reference by name**: the model can pass `body='plate'`; names are
  resolved to real FreeCAD objects automatically.
- **Type coercion**: string numbers (`'30'`) are converted per parameter
  annotation — LLMs emit strings all the time.
- **Geometry quality feedback**: after each `cut`, the agent checks how much
  of the tool volume was actually removed; if the tool was not fully inside
  the body (e.g. uncentered hole), it feeds the model the exact body/tool
  centers and the required `move` call so it can self-correct.
- **Postponed-annotation support**: works with `from __future__ import
  annotations` (PEP 563) modules.

### Third-party module integration — Curves workbench (verified)

FreeCAD's built-in surfacing is basic; the [Curves workbench](https://github.com/tomate44/CurvesWB)
(Gordon surfaces, sweep-2-rails, zebra analysis) closes part of the gap to
commercial Class-A tooling and is fully scriptable headlessly.

```bat
rem install: unzip CurvesWB into <user>\AppData\Roaming\FreeCAD\Mod\Curves
rem NOTE: the import name is CASE-SENSITIVE in headless FreeCAD 1.0.2:
"C:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe" examples\ai_curves_surface.py
```

Verified live (GLM-4-Flash, 2026-09-18): the model issued one
`make_panel_surface(60, 40, 10)` call and the agent built a
60x40x15.2 mm B-spline arch surface through the Gordon solver, exported STL.

**Pattern — "LLM gives intent, framework gives geometry"**: giving the LLM a
deeply nested point-network JSON argument failed (GLM-4-Flash repeated the
same malformed call 7x); a semantic tool with plain numbers works. Keep
complex geometric data construction inside the framework, not the prompt.

See `docs/freecad-modules-ai-research.md` for the full survey (Curves/Silk/
CurvedShapes, A2plus/Assembly3/Assembly4, FreeCAD MCP ecosystem, CATIA gap
analysis).

A live demo:

```bat
set OPENAI_API_KEY=sk-...
"C:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe" examples\llm_modeling.py
```

## Roadmap (draft)

- [x] AI agent that turns natural-language part descriptions into parametric models
- [x] Third-party module integration (Curves workbench: Gordon surfaces)
- [ ] Sketch/constraint solver integration for repair and re-parameterization
- [ ] STEP → STL → mesh pipeline for 3D printing / simulation
- [ ] Evaluation harness for generated models (geometry validity, dimension accuracy)
- [ ] Assembly integration experiment (Assembly4 / native Assembly WB)

## License

TBD — see LICENSE once decided.
