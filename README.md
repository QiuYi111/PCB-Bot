# PCB Skills and Tooling

This repository provides a routed PCB workflow for circuit generation, KiCad review, and project-level evidence collection.

```text
pcb (main router)
├── circuit-synth (natural language → circuit intent and generated artifacts)
└── kicad-happy (KiCad/Circuit-Synth review and manufacturing gates)
    └── installed domain Skills: kicad, datasheets, bom, spice, emc, fabrication
```

## Repository layout

- `skills/pcb/` — the main router, toolchain setup chapter, and capability checker.
- `skills/circuit-synth/` — Circuit-Synth generation workflow and handoff contract.
- `skills/kicad-happy/` — KiCad review workflow and evidence gates.
- `tools/pcbflow/` — reusable project orchestrator for preflight, review, and release packaging.
- `docs/` — design and implementation records.

## Install and verify

Read the dedicated [toolchain installation and configuration chapter](skills/pcb/references/toolchain-installation.md) first. The shortest macOS/Linux setup is:

```bash
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e tools/pcbflow
python skills/pcb/scripts/check_toolchain.py
```

On Windows PowerShell, activate with `\.venv\Scripts\Activate.ps1` and run the same checker. KiCad, Circuit-Synth, and `kicad-cli` are required for generation/review; `ngspice` and `gh` are optional capability-dependent tools.

The checker is read-only and supports machine-readable output:

```bash
python skills/pcb/scripts/check_toolchain.py --json
python skills/pcb/scripts/check_toolchain.py --strict
```

Generated KiCad files, analysis runs, release archives, environments, caches, and the concrete example boards are intentionally ignored. Keep credentials such as supplier API keys and GitHub tokens outside the repository.
