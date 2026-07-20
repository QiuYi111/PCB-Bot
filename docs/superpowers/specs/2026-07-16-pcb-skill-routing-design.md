# PCB Skill Routing Design

## Goal

Create a global PCB-design Skill family with `pcb` as the entry-point router and two domain Skills:

- `circuit-synth`: generate circuit intent and KiCad project artifacts from natural-language requirements.
- `kicad-happy`: analyze, cross-check, validate, and assess KiCad designs for manufacturing readiness.

The router must keep the user-facing workflow unified while delegating implementation details to the narrowest capable Skill.

## Scope

The family covers the full path from circuit requirements to reviewable KiCad artifacts:

1. Requirements and electrical constraints.
2. Topology, power tree, interfaces, and net contract.
3. Circuit-Synth Python generation.
4. JSON/netlist and KiCad project generation.
5. Schematic/PCB/BOM/DRC/ERC/DFM validation.
6. Datasheet-backed verification, SPICE, EMC, thermal, and lifecycle checks when applicable.
7. Manufacturing-readiness report and explicit review gaps.

It does not duplicate existing sourcing, BOM enrichment, SPICE, EMC, or KiCad parsing implementations. Those capabilities are invoked through existing Skills and scripts.

## Routing Rules

| User intent | Route |
|---|---|
| New circuit from a description | `circuit-synth` → `kicad-happy` |
| Generate/repair Circuit-Synth Python | `circuit-synth` |
| Analyze or review `.kicad_sch`, `.kicad_pcb`, Gerbers, or `.kicad_pro` | `kicad-happy` |
| Check readiness for fabrication | `kicad-happy` → `bom`/`jlcpcb`/`pcbway` as applicable |
| Simulate or sweep component values | `kicad-happy` → `spice` |
| Datasheet/pinout verification | `kicad-happy` → `datasheets`/supplier Skill |
| Existing design plus requested topology change | `circuit-synth` for intent/code change → `kicad-happy` for regression review |

The router must not generate KiCad files directly and must not claim fabrication readiness from code execution alone.

## `circuit-synth` Contract

Input may be a natural-language circuit request, an existing Circuit-Synth Python file, or a requested topology/value change.

The Skill must produce, as applicable:

- an assumptions and requirements summary;
- a topology and named-net plan;
- Circuit-Synth Python using `@circuit`, `Component`, `Net`, templates, and hierarchical subcircuits where useful;
- executed JSON/netlist and KiCad project artifacts;
- a list of generated files and unresolved component/datasheet assumptions.

It must use the documented Python → JSON → KiCad flow, preserve the source Python, and validate that generated files are actually created before handing off.

## `kicad-happy` Contract

This Skill wraps the installed KiCad analysis Skill and its scripts. It must:

- scan all available KiCad and fabrication files;
- use `.kicad-happy.json` when present or recommend project-level configuration when absent;
- run every applicable analyzer instead of stopping at one output;
- cross-check analyzer JSON against raw schematic/PCB files;
- distinguish deterministic, heuristic, and datasheet-backed evidence;
- hand off BOM, SPICE, EMC, datasheet, and fabrication actions to existing Skills;
- report blockers, verification basis, skipped analyses, and remaining risks.

## Validation

Each Skill receives a valid `SKILL.md` frontmatter, an `agents/openai.yaml`, and only the references it needs. Each folder is initialized with `init_skill.py`, validated with `quick_validate.py`, and checked for discoverability keywords and broken handoffs.

Because the current workspace is not a Git repository, this design document is created locally but cannot be committed without initializing or supplying a repository.
