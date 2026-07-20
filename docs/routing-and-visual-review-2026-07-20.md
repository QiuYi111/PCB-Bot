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

## DRC environment blocker

On the current macOS installation, `kicad-cli` is KiCad 10.0.4. Running the
strict native DRC command exits with code 134 before writing a report. The
same behavior was reproduced on the installed KiCad template board and on a
minimal one-pad board, so this run cannot be presented as either a DRC pass or
a board-specific violation list.

Before fabrication, unlock the Mac and run DRC in PCB Editor after refill and
save, or rerun the strict CLI gate with a different supported KiCad build.
Only a written report plus zero exit status may change this gate to pass.
