# Routing and visual review handoff

This note records the routing and release-gate changes made for the local
24 V stepper power-board example. The concrete `pcb_power_board/` example is
intentionally ignored by this repository; the reusable workflow and Skills
are the public artifact.

## Routing policy

The local board finalizer now uses an octilinear grid router: A* may move in
the four cardinal directions and the four 45-degree diagonal directions. A
diagonal move is rejected when it would cut a blocked corner, and every
emitted segment is checked against pads, tracks, and vias. Driver-local nets
and controller fan-out are routed early so that high-density areas reserve
space before the remaining nets are attempted.

FreeRouting remains an optional backend for difficult boards. It is not a
release verdict and it is not silently substituted for KiCad review. The
KiCad/FreeRouting handoff is Specctra DSN/SES through PCB Editor; the current
KiCad CLI workflow does not provide a headless DSN/SES export/import command,
so this repository keeps that step explicit and human-operated.

## Release gates

`pcbflow review` now performs all of the following when KiCad CLI and a PCB
are present:

1. native KiCad DRC with all severities enabled, zone refill, a written report,
   and a zero process exit status;
2. top and bottom board renders;
3. an octilinear layout audit containing segment orientations, corner counts,
   and a human inspection checklist;
4. an explicit `--visual-approved` acknowledgement before a release can be
   considered ready.

An autorouter result, independent analyzer result, or render command success
never replaces the native DRC or human visual review. A crash, missing DRC
report, visual-render failure, or missing visual approval blocks release.

## Current local candidate evidence

The regenerated local candidate was reviewed with the independent PCB
analyzer and KiCad renderer:

| Item | Result |
|---|---:|
| Board size | 80 x 65 mm |
| Footprints | 44 |
| Routed nets | 39 |
| Track segments | 337 |
| Vias | 83 |
| Zones | 3 |
| Unrouted nets | 0 |
| Independent analyzer errors | 0 |
| Independent analyzer warnings | 3 |
| 45-degree segments | 106 |
| 90-degree corners | 13 |

The remaining independent warnings are zero test-point coverage and untented
via-in-pad findings at `C15:2` and `R4:2`; they require an engineering or
fabrication decision rather than automatic suppression.

## DRC retry result

On the current macOS installation, `kicad-cli` is KiCad 10.0.4. Running the
strict native DRC command still exits with code 134 before writing a report;
the same behavior was reproduced on the installed KiCad template board.

PCB Editor DRC was then run with refill enabled and completed successfully.
It reports **229 DRC violations**, **18 unconnected pads**, and **0 footprint
errors**. The findings include different-net shorts, clearance violations,
tracks crossing, dangling tracks/vias, drill/hole issues, solder-mask
bridges, and silkscreen collisions. This candidate therefore fails native DRC
and must not be released.

The GUI report is saved locally as
`pcb_power_board/generated/24v_stepper_power_board/native-drc-gui-20260721.rpt`.
Fix the reported shorts, clearances, unconnected items, and fabrication
findings, then rerun PCB Editor DRC and the strict CLI gate with a supported
KiCad build. Only a written report with zero violations may change this gate
to pass.
