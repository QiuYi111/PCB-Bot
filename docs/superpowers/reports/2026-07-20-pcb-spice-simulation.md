# PCB SPICE Simulation Run

Date: 2026-07-20

## Scope

The released 24 V stepper power-board schematic was analyzed first, then passed to the repository `spice` Skill with ngspice and a reproducible 100-sample Gaussian Monte Carlo run (`seed=42`). Generated JSON, netlists, logs, and the local verification entry are kept under the workspace project's ignored `analysis/spice_20260720/` directory; generated simulation artifacts are not committed to this Skill repository.

## Result

- Simulator: ngspice 46.1
- Subcircuits: 12
- Pass: 12
- Warn/fail/skip: 0/0/0
- Elapsed: 11.8 seconds
- Monte Carlo: 11 result groups, all 100 samples converged

The two detected RC filters matched their calculated cutoff frequencies within 0.24%. The voltage-divider and regulator-feedback checks matched their nominal values. Four decoupling networks, two inrush cases, and the protection-device presence check passed.

## Interpretation limits

These are isolated, idealized subcircuit checks. They do not establish full DRV8833 switching-loop stability, motor dynamics, PCB thermal behavior, downstream loading, or manufacturer-specific protection clamp voltage. The D1 result confirms presence only and needs a validated device model for clamp behavior.
