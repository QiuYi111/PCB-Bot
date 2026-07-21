# pcbflow

`pcbflow` is the project-local orchestration layer for this KiCad PCB. It keeps the source files read-only, runs the existing deterministic analyzers, records tool availability and source hashes, and emits one gate report per run.

From this directory:

```bash
.venv/bin/pcbflow preflight --project . --target jlcpcb
.venv/bin/pcbflow review --project . --target jlcpcb --full
# if kicad-cli crashes during zone refill, open PCB Editor and save a DRC report:
.venv/bin/pcbflow review --project . --target jlcpcb --open-gui-drc
.venv/bin/pcbflow review --project . --target jlcpcb --gui-drc-report /path/to/native-drc-gui.rpt
# after opening visual/board-top.png and visual/board-bottom.png:
.venv/bin/pcbflow review --project . --target jlcpcb --full --visual-approved
.venv/bin/pcbflow status --run analysis/pcbflow/<run-id>
.venv/bin/pcbflow release --project . --target jlcpcb
```

The release command is intentionally strict: it packages the KiCad sources, Gerbers, and review evidence only when the latest gate report is `fab_ready` and the reviewed source hashes still match. `warning`, `not_performed`, `failed`, and `blocked` states require a design decision or another review run.

Install the editable project command once with:

```bash
uv pip install --python .venv/bin/python -e .
```

The tool does not replace KiCad GUI review, native DRC, SPICE, datasheet verification, BOM matching, or manufacturer DFM checks. Every review renders top and bottom board images and writes `visual/layout-audit.json`; release remains blocked until a human inspects those images and explicitly supplies `--visual-approved`. It makes each handoff explicit and prevents a successful autorouter or analyzer subprocess from being mistaken for a complete fabrication sign-off.
