# Circuit-Synth API and Patterns

Use this reference when writing or repairing Circuit-Synth code. Prefer the installed package's introspection and the current documentation when an API differs from these patterns.

## Core objects

| Object | Use |
|---|---|
| `@circuit(name="...")` | Declare a circuit-generation function and stable output name |
| `Component(...)` | Instantiate a KiCad symbol with symbol, reference prefix, value, and footprint |
| `Net("...")` | Create a named electrical net |
| `component[1]` / `component["PIN_NAME"]` | Access an integer or named pin |
| `pin += net` / `net += pin` | Connect pins to nets |
| `Circuit` methods | Export JSON/netlists, KiCad projects, BOMs, PDFs, or Gerbers when supported by the installed version |

## Component template

Use a callable template for repeated parts. Keep the template's symbol and footprint paired; change the value or MPN only when the footprint and pin mapping remain valid.

```python
C_100N_0603 = Component(
    symbol="Device:C",
    ref="C",
    value="100nF",
    footprint="Capacitor_SMD:C_0603_1608Metric",
)

decoupler = C_100N_0603()
```

Verify the installed version's template behavior before relying on custom properties or callable templates in a large design.

## Pin access

Prefer names for ICs and connectors:

```python
regulator["VIN"] += vin
regulator["VOUT"] += vout
```

Use integer access for simple library symbols only after checking the pin definition:

```python
resistor[1] += signal
resistor[2] += gnd
```

Mixed access is valid when each pin mapping is explicit. Never infer a transistor, regulator, connector, or multi-unit symbol pinout from package shape alone.

## Hierarchical circuits

Split a non-trivial design into functional blocks such as `power`, `usb`, `mcu`, `sensor`, and `debug`. Give each block a clear input/output net contract. Use the current `Circuit.add_subcircuit` API when composing blocks; if the installed version exposes a different signature, inspect it rather than copying an old example.

## Export strategy

1. Execute the Python source.
2. Inspect the resulting circuit object or JSON representation.
3. Export the JSON/netlist used by the generator.
4. Generate the KiCad project with the installed generator API.
5. Re-open or analyze the generated files.

Keep a stable project name and output directory. Use explicit overwrite/debug options only when requested. Debug options such as bounding boxes are useful for diagnosing placement, but they do not replace KiCad DRC/ERC or a design review.

## Version guard

The public documentation currently identifies Circuit-Synth 0.12.1. Verify the installed package before using methods such as project, BOM, Gerber, PDF, simulation, or flattened/full netlist generation. If the installed API and docs disagree, treat the installed package as executable truth and record the discrepancy.
