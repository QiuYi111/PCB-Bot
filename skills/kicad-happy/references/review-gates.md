# KiCad Happy Review Gates

## Minimum gates by artifact

| Inputs present | Required gate |
|---|---|
| `.kicad_sch` only | Schematic analyzer, raw-file spot checks, datasheet gap disclosure |
| `.kicad_sch` + `.kicad_pcb` | Schematic, PCB `--full`, schematic–PCB cross-analysis, pin/pad cross-check |
| Gerbers/Excellon | Gerber completeness, alignment, drill and board-outline checks |
| Power or hot components | Power-tree and thermal analysis when inputs support it |
| Analog/filter/feedback subcircuits | SPICE when a simulator is installed |
| Schematic + PCB with production intent | EMC and manufacturing/DFM checks |
| MPNs and network/API access | Datasheet and lifecycle checks |

## Evidence labels

- `deterministic`: directly parsed or computed from the design files.
- `topology-based`: inferred from connectivity and component patterns.
- `heuristic`: plausible but not manufacturer-confirmed.
- `datasheet-backed`: tied to a manufacturer datasheet or structured extraction with a source location.
- `consistency-only`: schematic, PCB, and analyzer agree, but physical pinout or electrical correctness is not independently verified.

Use the strongest supported label and downgrade claims when the evidence source is absent.

## Generated-project gate

For Circuit-Synth output, confirm:

- the source Python ran successfully;
- JSON/netlist and requested KiCad files exist;
- references are unique and expected components are present;
- named nets and critical pin mappings match the design contract;
- schematic–PCB synchronization is resolved or explicitly incomplete;
- generated PCB geometry is not mistaken for a routed, DRC-clean board;
- all omitted checks are listed as review gaps.

## Report blockers

Prioritize blockers such as:

- wrong or unverified critical IC/connector/transistor pin mapping;
- missing power source, floating power input, or incorrect rail voltage;
- schematic/PCB net or pad mismatch;
- unrouted critical nets or broken ground return;
- DRC/ERC violations affecting function or safety;
- insufficient thermal path, clearance, or current capacity;
- missing manufacturing files or incomplete Gerber set;
- unresolved high-severity analyzer findings.
