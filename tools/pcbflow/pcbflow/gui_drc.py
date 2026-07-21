"""KiCad PCB Editor fallback for macOS CLI DRC crashes."""

from __future__ import annotations

import re
import subprocess
import glob
from pathlib import Path
from typing import Any


def parse_drc_report(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    def count(pattern: str) -> int:
        match = re.search(pattern, text)
        return int(match.group(1)) if match else -1

    violations = count(r"\*\* Found (\d+) DRC violations \*\*")
    unconnected = count(r"\*\* Found (\d+) unconnected pads \*\*")
    footprint_errors = count(r"\*\* Found (\d+) Footprint errors \*\*")
    return {
        "report": str(path),
        "violations": violations,
        "unconnected_pads": unconnected,
        "footprint_errors": footprint_errors,
        "status": "pass" if (violations, unconnected, footprint_errors) == (0, 0, 0) else "failed",
    }


def open_pcb_editor(pcb: Path) -> list[str]:
    """Open the board in the native PCB Editor; DRC still needs user action."""
    if Path("/Applications/KiCad/KiCad.app").exists():
        command = ["open", "-a", "/Applications/KiCad/KiCad.app/Contents/Applications/pcbnew.app", str(pcb)]
    else:
        command = ["pcbnew", str(pcb)]
    subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return command


def gui_drc_gate(report: Path) -> dict[str, Any]:
    if not report.exists():
        return {
            "id": "native_drc_gui_fallback",
            "status": "blocked",
            "severity": "blocker",
            "evidence": [str(report)],
            "recommendation": "Run PCB Editor DRC with refill enabled and save the report.",
        }
    result = parse_drc_report(report)
    return {
        "id": "native_drc_gui_fallback",
        "status": result["status"],
        "severity": "info" if result["status"] == "pass" else "blocker",
        "evidence": [str(report), f"violations={result['violations']}", f"unconnected_pads={result['unconnected_pads']}", f"footprint_errors={result['footprint_errors']}"],
        "recommendation": "Resolve GUI DRC findings before fabrication." if result["status"] != "pass" else "",
    }


def diagnose_kicad_cli_crash(result: dict[str, Any]) -> list[str]:
    """Return evidence for the known macOS wx zone-fill abort."""
    if result.get("returncode") != 134:
        return []
    evidence = ["exit_code=134 (SIGABRT)"]
    reports = sorted(glob.glob(str(Path.home() / "Library/Logs/DiagnosticReports/kicad-cli-*.ips")))
    if reports:
        latest = Path(reports[-1])
        evidence.append(str(latest))
        text = latest.read_text(encoding="utf-8", errors="replace")
        if "wxGetMousePosition" in text or "mouseLocation" in text:
            evidence.append("crash_stack=wxGetMousePosition/mouseLocation during zone fill")
    return evidence
