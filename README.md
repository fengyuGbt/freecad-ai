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

## Project layout

```
freecad-ai/
├── src/freecad_ai/        # reusable package (importable once added to PYTHONPATH)
├── examples/              # runnable scripts
├── requirements.txt       # python deps outside FreeCAD itself
└── README.md
```

## Roadmap (draft)

- [ ] AI agent that turns natural-language part descriptions into parametric models
- [ ] Sketch/constraint solver integration for repair and re-parameterization
- [ ] STEP → STL → mesh pipeline for 3D printing / simulation
- [ ] Evaluation harness for generated models (geometry validity, dimension accuracy)

## License

TBD — see LICENSE once decided.
