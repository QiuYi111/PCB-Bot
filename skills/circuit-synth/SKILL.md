---
name: circuit-synth
description: Use when a PCB or circuit must be designed from requirements, generated with Circuit-Synth Python, converted to JSON/netlists or KiCad projects, or repaired after Circuit-Synth execution errors. Trigger on Circuit-Synth, `@circuit`, `Component`, `Net`, natural-language circuit generation, power-tree design, hierarchical circuit generation, or requests to create `.kicad_sch`/`.kicad_pro` artifacts from code.
---

# Circuit-Synth Generator

Turn electrical intent into reproducible Circuit-Synth source and generated KiCad artifacts. Keep the Python source as the source of truth, make assumptions explicit, and hand generated projects to `kicad-happy` for review.

## Workflow

### 1. Build the requirements contract

Extract or ask for the smallest set of constraints that changes the design:

- input and output rails, tolerances, current, power and operating temperature;
- interfaces and signal direction, including connector pinout;
- protection, filtering, reset, clock, decoupling and test-point requirements;
- target package/footprint, assembly process, preferred supplier or MPN constraints;
- KiCad version, output directory, and whether PCB generation is required.

If a critical value, pinout, load, or safety constraint is missing, mark it as an assumption and do not silently invent a production constraint.

### 2. Define topology before code

Write a compact design contract before implementing:

1. power tree and source/load direction;
2. named nets and their electrical meaning;
3. component table: reference class, symbol, value, footprint, MPN status;
4. pin-level connection table for every IC, connector, diode, transistor, and polarized part;
5. expected outputs and validation gates.

Use datasheets or a supplier/datasheet Skill for non-obvious pinouts and required external components. A KiCad library symbol is not proof of the real part's pin mapping.

### 3. Generate Circuit-Synth Python

Use the documented primitives and keep the code readable:

```python
from circuit_synth import Component, Net, circuit

@circuit(name="power_supply_3v3")
def power_supply_3v3():
    vin = Net("VIN_5V")
    vout = Net("VOUT_3V3")
    gnd = Net("GND")

    regulator = Component(
        symbol="Regulator_Linear:AMS1117-3.3",
        ref="U",
        value="AMS1117-3.3",
        footprint="Package_TO_SOT_SMD:SOT-223-3_TabPin2",
    )
    regulator["VIN"] += vin
    regulator["VOUT"] += vout
    regulator["GND"] += gnd
    return regulator
```

Prefer named pins when the symbol provides them; use integer pins only when the symbol and datasheet mapping are known. Use component templates for repeated values and subcircuits for independent functional blocks. See [references/circuit-synth-api.md](references/circuit-synth-api.md).

### 4. Execute and export

Run the generated source in the target environment. Confirm:

- the module imports and the circuit function executes;
- references are finalized and unique;
- all named nets have the intended pins;
- JSON/netlist output is produced;
- KiCad project generation completes without overwriting unrelated files.

Use the version-appropriate generator API from the installed package. Do not assume a generated `.kicad_pcb` means the layout is routed or fabrication-ready.

Keep these artifacts together when they exist: source `.py`, JSON/netlist, `.kicad_pro`, `.kicad_sch`, `.kicad_pcb`, and a short generation log. See [references/generation-checklist.md](references/generation-checklist.md).

### 5. Handoff

After generation, invoke `kicad-happy` whenever KiCad artifacts exist. Pass the requirements contract, topology contract, source path, generated files, component/MPN assumptions, and any execution warnings.

If the project includes `pcbflow.json`, install/use the project-local `pcbflow` command after generation and before reporting completion. Run `preflight`, then `review --full`; preserve its run directory and gate report with the generated artifacts. Generation success is not layout, native DRC, SPICE, or manufacturing success.

Hand off to other Skills rather than duplicating them:

- `datasheets` for manufacturer pin tables and recommended circuits;
- `bom` for BOM enrichment and export;
- `spice` for simulation and value sweeps;
- `emc` for EMC pre-compliance when schematic and PCB are available;
- `jlcpcb` or `pcbway` for fabrication-specific checks.

## Failure handling

- `ModuleNotFoundError` or package mismatch: inspect the installed environment and documentation version before changing the design.
- `SymbolNotFoundError`/library errors: report the exact symbol, check KiCad library configuration, and do not substitute a different pinout silently.
- Pin connection errors: print or inspect pin names, compare with the datasheet, then fix the source.
- Missing output: stop before handoff; a successful Python exit without the expected file is a failed generation.
- Existing output conflict: ask before overwriting; use an explicit force/overwrite option only when the user authorized regeneration.

## Completion criteria

Call generation complete only when the source runs, expected artifacts exist, named-net and reference checks pass, and the handoff status is recorded. Call the overall PCB task complete only after `kicad-happy` reports its applicable checks and gaps.
