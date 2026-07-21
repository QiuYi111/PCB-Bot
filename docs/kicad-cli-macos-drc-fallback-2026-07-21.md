# KiCad CLI DRC fallback

On this macOS host, KiCad 10.0.4 `kicad-cli pcb drc --refill-zones` exits with code 134. The crash report shows:

`NSEvent mouseLocation -> wxGetMousePosition -> TOOL_MANAGER::doRunAction -> BOARD_COMMIT::Push -> ZONE_FILLER_TOOL::FillAllZones -> PCBNEW_JOBS_HANDLER::JobExportDrc`

This is a GUI-dependent zone-fill abort in the CLI process, not a normal DRC violation result. The workflow therefore remains strict:

1. Run CLI DRC first.
2. If it crashes, open PCB Editor with `pcbflow review --open-gui-drc`.
3. In PCB Editor enable “refill all zones before DRC”, run DRC, and save the report.
4. Rerun with `--gui-drc-report path/to/report.rpt`.
5. The GUI fallback passes only when violations, unconnected pads, and footprint errors are all zero. Visual review remains a separate required gate.

The GUI report is evidence, not a silent bypass of DRC or visual inspection.
