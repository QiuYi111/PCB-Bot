---
name: pcb
description: Use when a user asks to design, generate, inspect, validate, simulate, review, or prepare a PCB or circuit project, especially when the request mentions Circuit-Synth, KiCad, `.kicad_sch`, `.kicad_pcb`, `.kicad_pro`, Gerbers, BOM, DRC/ERC, DFM, SPICE, or manufacturing readiness. Route new circuit generation to `circuit-synth` and existing KiCad/design review work to `kicad-happy`.
---

# PCB Design Router

Use this Skill as the entry point for PCB and circuit-design work. Decide which domain owns the next action, load the narrowest specific Skill, and keep the user-facing workflow continuous.

## Toolchain installation and configuration

Before generation or automated review, prepare the local toolchain. Follow [references/toolchain-installation.md](references/toolchain-installation.md) for platform-specific installation, PATH setup, project configuration, and verification commands. Run `scripts/check_toolchain.py` and pass the resulting capability report to downstream Skills; a missing optional tool is a disclosed review gap, not a silent skip.

## Route by intent

| Request pattern | Route |
|---|---|
| New circuit from natural language; topology, power tree, interfaces, or component architecture | `circuit-synth` → `kicad-happy` |
| Generate, repair, or refactor Circuit-Synth Python/JSON/KiCad output | `circuit-synth` → `kicad-happy` when files exist |
| Inspect or review `.kicad_sch`, `.kicad_pcb`, `.kicad_pro`, `.sch`, `.net`, Gerbers, or a PDF schematic | `kicad-happy` |
| Check schematic–PCB synchronization, DRC/ERC, DFM, thermal, EMC, BOM, or ready-to-fab status | `kicad-happy` with the relevant handoffs |
| Simulate, sweep values, or validate analog subcircuits | `kicad-happy` → `spice` |
| Find parts, verify datasheets, enrich BOM, or order boards | `kicad-happy` → `datasheets`, `bom`, `digikey`, `mouser`, `lcsc`, `jlcpcb`, or `pcbway` |

## Routing rules

1. Scan the workspace before choosing a route. Identify source code, Circuit-Synth JSON, KiCad files, Gerbers, datasheets, BOMs, and prior analysis output.
2. For a new design, capture requirements before generating code: input/output rails, voltage/current limits, interfaces, environment, package/assembly constraints, target manufacturer, and unresolved choices.
3. Do not generate KiCad files directly from this router. Use `circuit-synth` for intent-to-artifact generation.
4. Do not reimplement KiCad parsing or review logic here. Use `kicad-happy`, which wraps the installed `kicad` Skill and its analyzer scripts.
5. If a generated project exists, route it through `kicad-happy` before claiming the task is complete. Code execution alone is not design validation.
6. Preserve evidence boundaries: label results as deterministic, heuristic, consistency-only, or datasheet-backed. Never call a design production-ready when required checks were skipped.
7. For routed boards, require an octilinear/45-degree-aware routing policy where the backend supports it, then run native DRC and a top/bottom visual review. An autorouter is an implementation aid, not a sign-off authority.

For the routing decision tree and FreeRouting DSN/SES handoff, use
[references/autorouting.md](references/autorouting.md).

## Project orchestrator

If the workspace contains `pcbflow.json` and a `pcbflow` package, use the project-local orchestrator as the first review action:

```bash
<project>/.venv/bin/pcbflow preflight --project <project> --target <target>
<project>/.venv/bin/pcbflow review --project <project> --target <target> --full
```

Treat `analysis/pcbflow/<run>/gate_report.json` as the workflow ledger. It does not replace the domain Skills: it invokes their deterministic analyzers, records commands and hashes, and makes missing KiCad CLI, SPICE, datasheets, lifecycle data, or manufacturer mapping explicit. A release package is allowed only when the report says `fab_ready`; `warning`, `not_performed`, `failed`, or `blocked` requires review or a documented decision.

## Handoff contract

Pass these artifacts between Skills whenever available:

- requirements and assumptions;
- named-net/topology contract;
- Circuit-Synth Python source;
- generated JSON/netlist and KiCad project files;
- BOM and MPN/footprint mapping;
- analysis directory and prior-run manifest;
- open findings, verification gaps, and user decisions.

### Complete route

For “design and prepare this PCB” requests, use:

`pcb` → `circuit-synth` → `kicad-happy` → applicable `datasheets`/`bom`/`spice`/`emc`/fabrication Skills

Return one concise status with generated files, checks run, blockers, and the next actionable decision.

## Examples

- “设计一个 5V 转 3.3V、500mA 的电源模块” → `circuit-synth`, then `kicad-happy`.
- “检查这个 `.kicad_sch` 是否能生产” → `kicad-happy`, then BOM/fabrication handoffs.
- “把 R5 改成 4.7k 并检查影响” → `kicad-happy` and `spice` when applicable.
- “找一个可在嘉立创生产的 LDO” → `kicad-happy` with `lcsc`/`jlcpcb`; do not force Circuit-Synth generation.
