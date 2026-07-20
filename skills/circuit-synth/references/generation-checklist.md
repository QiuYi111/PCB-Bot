# Generation Checklist

## Before running

- [ ] Requirements include rail voltages, load current, interfaces, and critical constraints.
- [ ] Every non-trivial IC/connector/transistor has an intended symbol and pin mapping.
- [ ] MPN/datasheet gaps are explicitly listed.
- [ ] Output directory and overwrite behavior are explicit.

## After running Python

- [ ] Import succeeds.
- [ ] Circuit function executes.
- [ ] No unresolved symbol or pin errors remain.
- [ ] References are unique and finalized.
- [ ] Named nets contain the intended pins.

## After generation

- [ ] Expected JSON/netlist exists.
- [ ] `.kicad_pro`/`.kicad_sch` exist when requested.
- [ ] `.kicad_pcb` is treated as generated structure, not proof of routed layout.
- [ ] Source Python and generated artifacts share a stable project name.
- [ ] `kicad-happy` receives the requirements, assumptions, and source path.

## Handoff payload

```text
Requirements: <path or summary>
Source: <path>
Generated artifacts: <paths>
Expected rails/nets: <summary>
MPN/datasheet gaps: <list>
Execution warnings: <list>
Requested next gate: schematic review / PCB review / simulation / fab readiness
```
