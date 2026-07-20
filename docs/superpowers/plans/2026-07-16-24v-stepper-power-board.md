# 24V Stepper Power Board Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a reviewable first-pass KiCad design for a 24V DC input board that supplies two 5V, 20:1, two-phase four-wire stepper motors and a controller interface.

**Architecture:** Use a protected 24V input feeding one 5V/3A buck rail. Feed each GM12-10BY motor from its own dual-H-bridge stepper driver, expose a filtered 5V logic rail for an Arduino UNO R3, and provide an optional 3.3V auxiliary rail. Keep the Circuit-Synth Python source as the intent source, then generate and review KiCad artifacts.

**Tech Stack:** Python, Circuit-Synth 0.12.x when available, KiCad symbol/footprint libraries, and the repository's KiCad Happy analyzers.

---

### Task 1: Capture the electrical contract

**Files:**
- Create: `pcb_power_board/requirements.md`
- Create: `pcb_power_board/.kicad-happy.json`

- [ ] **Step 1: Record confirmed requirements and explicit assumptions**

  Write the confirmed input/output rails, motor parameters, estimated winding current, named nets, connector pinouts, and open decisions. Explicitly state that 24V is nominal because the maximum input voltage and transient environment were not supplied; select a buck family rated at least 40V, preferably 60V, until that value is confirmed. State that the first pass targets a 5V/3A motor rail, UNO 5V logic, optional 3.3V/300mA auxiliary output, and a 2-layer prototype PCB.

- [ ] **Step 2: Configure analysis output**

  Set the project analyzer configuration to retain schematic/PCB/cross-analysis output under `pcb_power_board/analysis/`, use the project basename `24v_stepper_power_board`, and treat the design as a prototype rather than fabrication-ready.

### Task 2: Author the reproducible circuit source

**Files:**
- Create: `pcb_power_board/24v_stepper_power_board.py`

- [ ] **Step 1: Define the named-net topology**

  Implement named nets for `VIN_24V`, `VIN_PROTECTED`, `GND`, `VOUT_5V_MOTOR`, `VOUT_5V_LOGIC`, `VOUT_3V3`, `M1_A`, `M1_B`, `M2_A`, `M2_B`, and the controller signals. Use one 4-pin connector per motor, one 2-pin 24V input connector, one logic power/control connector, two DRV8833 blocks, input protection, buck support components, logic filtering, and the optional 3.3V regulator.

- [ ] **Step 2: Make unresolved MPN choices visible**

  Use symbols and footprints only when the pin mapping is known. For the buck controller, use a datasheet-backed 60V-rated candidate or a clearly named placeholder whose MPN is marked unselected in `requirements.md`; do not silently substitute a regulator with a different pinout. Use the DRV8833 symbol with two sense resistors per driver and expose `nSLEEP`/`nFAULT`.

- [ ] **Step 3: Add component metadata**

  Attach descriptions, estimated values, and footprints for connectors, protection parts, capacitors, sense resistors, drivers, and regulators so the generated BOM can be reviewed. Keep values conservative: 10µF ceramic at each driver VM pin, 2.2µF at VINT, 10nF from VCP to VM, and a shared motor bulk capacitor.

### Task 3: Generate and inspect KiCad artifacts

**Files:**
- Create: `pcb_power_board/generated/24v_stepper_power_board.json`
- Create: `pcb_power_board/generated/24v_stepper_power_board.kicad_sch`
- Create: `pcb_power_board/generated/24v_stepper_power_board.kicad_pro`
- Create: `pcb_power_board/generated/generation.log`

- [ ] **Step 1: Verify the generator runtime**

  Run `python3 -c "import circuit_synth; print(circuit_synth.__version__)"`. If the package is absent, install the documented Circuit-Synth release only after requesting permission for the networked dependency installation; record the installed version in `generation.log`.

- [ ] **Step 2: Execute the source**

  Run the source with an explicit output directory, then verify that JSON, schematic, and project files exist. Inspect component references and named-net membership from the generated JSON before continuing.

- [ ] **Step 3: Record generation limits**

  Mark the generated PCB as absent or unrouted if Circuit-Synth does not produce a routed board. Do not treat a generated schematic or project file as evidence that the power loop, thermal copper, or DRC is complete.

### Task 4: Run the KiCad Happy review gate

**Files:**
- Create: `pcb_power_board/analysis/`
- Create: `pcb_power_board/analysis/review.md`

- [ ] **Step 1: Run applicable schematic and PCB analyzers**

  Run the existing `analyze_schematic.py`, `analyze_pcb.py` when a PCB file exists, and `cross_analysis.py` when both domains exist. Keep raw analyzer outputs in the configured analysis directory.

- [ ] **Step 2: Cross-check critical mappings**

  Confirm that each motor connector has four nets, each DRV8833 has two winding bridges, every regulator has local bypassing, the motor rail is distinct from the logic rail, and all references are unique. Flag missing datasheets, missing maximum-input-voltage confirmation, missing board dimensions, and missing routed-layout checks.

- [ ] **Step 3: Write the review result**

  Report generated files, checks run, deterministic findings, datasheet-backed findings, skipped checks, unresolved risks, and the exact next action required before fabrication.
