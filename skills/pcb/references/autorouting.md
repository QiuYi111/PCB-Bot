# Autorouting and routing quality

Autorouting is a candidate-generation step. It must be followed by native
KiCad DRC, top/bottom rendering, and human layout approval.

## Preferred routing order

1. Place connectors, power entry, switching components, drivers, decoupling,
   and thermal copper deliberately.
2. Lock critical placement and high-current paths.
3. Route sensitive clocks, feedback, current sense, and motor-control nets
   with explicit constraints.
4. Use an octilinear/45-degree-aware router for ordinary signals. Reject
   diagonal corner cutting and validate every segment against pads, vias, and
   other nets.
5. If the board remains difficult, use FreeRouting as an optional second
   candidate. Compare the result against the design-intent constraints; do not
   blindly accept its output.
6. Refill zones, run strict native DRC, render both sides, and perform the
   visual checklist. Unrouted nets, DRC failure, render failure, or missing
   human approval blocks release.

## FreeRouting handoff

FreeRouting uses the Specctra DSN/SES exchange. In KiCad, export the DSN from
PCB Editor, run FreeRouting, then import the resulting SES back into PCB
Editor. Keep the original board and the autorouted candidate as separate
artifacts until the candidate has passed the full review.

The official project documents GUI, CLI, and API modes. A typical CLI run is:

```bash
java -jar freerouting.jar \
  -de board.dsn \
  -do board.ses
```

Check the installed release with `java -jar freerouting.jar -help`; options
can change between releases. KiCad CLI alone should not be assumed to provide
the DSN/SES exchange, so this handoff is intentionally explicit.

## Human visual checklist

Open the top and bottom renders, then inspect PCB Editor in 2D and 3D as
available:

- no accidental right-angle-heavy detours or visually sharp acute jogs;
- connector pin 1, polarity, and cable access are unambiguous;
- power and motor-current paths are short, wide, and thermally plausible;
- fan-out, vias, thermal vias, and copper pours do not obstruct assembly;
- silkscreen is readable and clear of pads, holes, and board edges;
- traces, vias, mounting holes, and copper respect edge and mechanical
  clearances;
- no hidden copper island, unexpected neck-down, or unreviewed layer change;
- fabrication and assembly risks not expressed by DRC are recorded.

## References

- [FreeRouting](https://github.com/freerouting/freerouting)
- [Using FreeRouting with KiCad](https://freerouting.org/freerouting/using-with-kicad)
