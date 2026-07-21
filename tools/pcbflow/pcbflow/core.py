from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import csv
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .visual import layout_audit, visual_commands
from .gui_drc import gui_drc_gate, open_pcb_editor


def _skill_root(env_name: str, relative_path: str, installed_name: str) -> Path:
    """Resolve a bundled Skill first, then the user's installed Skill."""
    override = os.environ.get(env_name)
    if override:
        return Path(override).expanduser()

    source = Path(__file__).resolve()
    for parent in source.parents:
        bundled = parent / relative_path
        if bundled.exists():
            return bundled

    return Path.home() / ".codex" / "skills" / installed_name


KICAD_SKILL = _skill_root("KICAD_SKILL_ROOT", "skills/kicad", "kicad")
EMC_SKILL = _skill_root("EMC_SKILL_ROOT", "skills/emc", "emc")


@dataclass(frozen=True)
class ProjectFiles:
    project: Path
    source_dir: Path | None
    schematic: Path | None
    pcb: Path | None
    pro: Path | None
    config: Path | None
    gerbers: Path | None
    context: Path | None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_dump(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n")


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _preferred_file(paths: list[Path], suffix: str) -> Path | None:
    if not paths:
        return None
    preferred = [p for p in paths if "release/kicad_import" in p.as_posix()]
    if preferred:
        return sorted(preferred)[0]
    root_level = [p for p in paths if p.parent == paths[0].parents[-1]]
    return sorted(root_level or paths)[0]


def discover_project(project: Path) -> ProjectFiles:
    project = project.expanduser().resolve()
    if project.is_file():
        project = project.parent

    schs = sorted(project.rglob("*.kicad_sch"))
    pcbs = sorted(project.rglob("*.kicad_pcb"))
    pros = sorted(project.rglob("*.kicad_pro"))

    source_dirs = [p.parent for p in schs if "release/kicad_import" in p.as_posix()]
    source_dir = source_dirs[0] if source_dirs else None
    schematic = _preferred_file(schs, ".kicad_sch")
    pcb = _preferred_file(pcbs, ".kicad_pcb")
    pro = _preferred_file(pros, ".kicad_pro")

    config_candidates = [project / ".kicad-happy.json", *project.rglob(".kicad-happy.json")]
    config = next((p for p in config_candidates if p.exists()), None)
    context_candidates = [project / "pcbflow.json", *project.rglob("pcbflow.json")]
    context = next((p for p in context_candidates if p.exists()), None)

    gerber_candidates: list[Path] = []
    for directory in sorted({p.parent for p in project.rglob("*.gbrjob")}):
        if any(directory.glob("*F_Cu*")) or any(directory.glob("*F_Cu*.*")):
            gerber_candidates.append(directory)
    if not gerber_candidates:
        for directory in sorted({p.parent for p in project.rglob("*.gtl")}):
            if any(directory.glob("*Edge_Cuts*")):
                gerber_candidates.append(directory)
    gerbers = gerber_candidates[0] if gerber_candidates else None

    return ProjectFiles(project, source_dir, schematic, pcb, pro, config, gerbers, context)


def _tool_candidates(name: str) -> list[str]:
    if name == "kicad-cli":
        return [
            "kicad-cli",
            "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli",
        ]
    return [name]


def find_tool(name: str) -> str | None:
    for candidate in _tool_candidates(name):
        path = shutil.which(candidate) if "/" not in candidate else candidate
        if path and Path(path).exists():
            return path
    return None


def preflight(files: ProjectFiles, target: str) -> dict[str, Any]:
    tools: dict[str, Any] = {}
    for name in ["kicad-cli", "ngspice", "ltspice", "xyce"]:
        found = find_tool(name)
        tools[name] = {"available": bool(found), "path": found}

    source_hashes: dict[str, str] = {}
    for path in [files.schematic, files.pcb, files.pro, files.config, files.context]:
        if path and path.exists():
            source_hashes[str(path)] = sha256_file(path)

    gates = [
        {
            "id": "input_files",
            "status": "pass" if files.schematic or files.pcb else "blocked",
            "severity": "blocker" if not (files.schematic or files.pcb) else "info",
            "evidence": [str(p) for p in [files.schematic, files.pcb] if p],
            "recommendation": "Add a KiCad schematic or PCB to the project." if not (files.schematic or files.pcb) else "",
        },
        {
            "id": "toolchain",
            "status": "pass",
            "severity": "info",
            "evidence": [f"python={sys.executable}", f"python_version={sys.version.split()[0]}"],
            "recommendation": "",
        },
        {
            "id": "gerbers_present",
            "status": "pass" if files.gerbers else "not_performed",
            "severity": "warning" if not files.gerbers else "info",
            "evidence": [str(files.gerbers)] if files.gerbers else [],
            "recommendation": "Generate Gerbers before fabrication review." if not files.gerbers else "",
        },
        {
            "id": "native_drc_available",
            "status": "pass" if tools["kicad-cli"]["available"] else "blocked",
            "severity": "blocker" if not tools["kicad-cli"]["available"] else "info",
            "evidence": [tools["kicad-cli"]["path"]] if tools["kicad-cli"]["available"] else [],
            "recommendation": "Install KiCad CLI or run native DRC/ERC in KiCad GUI." if not tools["kicad-cli"]["available"] else "",
        },
    ]

    return {
        "tool": "pcbflow",
        "version": "0.1.0",
        "target": target,
        "project": str(files.project),
        "files": {k: str(v) if v else None for k, v in files.__dict__.items()},
        "source_hashes": source_hashes,
        "tools": tools,
        "gates": gates,
    }


def _run(args: list[str], log_dir: Path, name: str, timeout_s: int = 900) -> dict[str, Any]:
    log_dir.mkdir(parents=True, exist_ok=True)
    started = time.time()
    try:
        completed = subprocess.run(args, text=True, capture_output=True, timeout=timeout_s, check=False)
        if completed.returncode == 0:
            status = "pass"
            error = None
        elif completed.returncode < 0:
            status = "crashed"
            error = f"terminated by signal {-completed.returncode}"
        else:
            status = "failed"
            error = f"exit code {completed.returncode}"
    except (OSError, subprocess.TimeoutExpired) as exc:
        completed = None
        status = "blocked"
        error = str(exc)

    stdout = completed.stdout if completed else ""
    stderr = completed.stderr if completed else ""
    (log_dir / f"{name}.stdout.log").write_text(stdout)
    (log_dir / f"{name}.stderr.log").write_text(stderr)
    return {
        "name": name,
        "command": args,
        "status": status,
        "returncode": completed.returncode if completed else None,
        "elapsed_s": round(time.time() - started, 3),
        "error": error,
    }


def _analyzer(script: Path, args: list[str], output: Path, config: Path | None) -> list[str]:
    command = [sys.executable, str(script), *args, "--output", str(output)]
    if config:
        command.extend(["--config", str(config)])
    return command


def _context(files: ProjectFiles) -> dict[str, Any]:
    return read_json(files.context) if files.context else {}


def _power_budget_gate(files: ProjectFiles, pcb_json: dict[str, Any] | None) -> dict[str, Any]:
    context = _context(files)
    motor = context.get("motor", {}) if isinstance(context, dict) else {}
    try:
        voltage = float(motor["voltage_v"])
        resistance = float(motor["phase_resistance_ohm"])
        count = int(motor["count"])
        phases = int(motor.get("energized_phases_per_motor", 2))
        current_per_phase = voltage / resistance
        total_current = current_per_phase * count * phases
    except (KeyError, TypeError, ValueError):
        return {
            "id": "power_budget",
            "status": "blocked",
            "severity": "blocker",
            "evidence": [],
            "recommendation": "Add motor voltage, phase resistance, count and energized phases to pcbflow.json.",
        }

    min_width = motor.get("recommended_main_rail_width_mm")
    route_evidence: list[str] = [
        f"phase_current={current_per_phase:.3f}A",
        f"estimated_motor_rail_current={total_current:.3f}A",
    ]
    status = "pass"
    recommendation = ""
    if pcb_json and min_width is not None:
        widths = [
            entry.get("max_width_mm")
            for entry in pcb_json.get("power_net_routing", [])
            if entry.get("net") == motor.get("rail_net", "VOUT_5V_MOTOR")
        ]
        if widths and max(widths) < float(min_width):
            status = "warning"
            route_evidence.append(f"max_rail_width={max(widths):.3f}mm")
            recommendation = f"Increase {motor.get('rail_net', 'VOUT_5V_MOTOR')} copper width/pour for the estimated load."
    return {
        "id": "power_budget",
        "status": status,
        "severity": "warning" if status == "warning" else "info",
        "evidence": route_evidence,
        "recommendation": recommendation,
    }


def _layer_gate(pcb_json: dict[str, Any] | None, gerber_json: dict[str, Any] | None) -> dict[str, Any]:
    if not pcb_json:
        return {"id": "layer_stack", "status": "not_performed", "severity": "warning", "evidence": [], "recommendation": "Analyze the PCB before checking layer consistency."}
    pcb_layers = pcb_json.get("statistics", {}).get("copper_layers_used")
    gerber_layers = gerber_json.get("layer_count") if gerber_json else None
    evidence = [f"pcb_copper_layers={pcb_layers}"]
    if gerber_layers is not None:
        evidence.append(f"gerber_copper_layers={gerber_layers}")
    if gerber_layers is None:
        return {"id": "layer_stack", "status": "warning", "severity": "warning", "evidence": evidence, "recommendation": "Run Gerber analysis before manufacturing."}
    ok = pcb_layers == gerber_layers
    return {"id": "layer_stack", "status": "pass" if ok else "blocked", "severity": "info" if ok else "blocker", "evidence": evidence, "recommendation": "Make KiCad and Gerber layer counts identical." if not ok else ""}


def _find_bom_tracking(files: ProjectFiles) -> Path | None:
    candidates = sorted(files.project.rglob("bom_tracking.csv"))
    return candidates[0] if candidates else None


def _manufacturer_mapping_gate(files: ProjectFiles) -> dict[str, Any]:
    path = _find_bom_tracking(files)
    if not path:
        return {
            "id": "manufacturer_mapping",
            "status": "not_performed",
            "severity": "warning",
            "evidence": [],
            "recommendation": "Add a bom_tracking.csv with LCSC/MPN mapping before JLCPCB handoff.",
        }
    try:
        with path.open(newline="") as handle:
            rows = list(csv.DictReader(handle))
    except (OSError, csv.Error) as exc:
        return {
            "id": "manufacturer_mapping",
            "status": "blocked",
            "severity": "blocker",
            "evidence": [str(path), str(exc)],
            "recommendation": "Repair the BOM tracking CSV and rerun the review.",
        }
    unmapped = [row.get("Reference", "?") for row in rows if not (row.get("LCSC") or row.get("MPN"))]
    evidence = [str(path), f"rows={len(rows)}", f"unmapped={len(unmapped)}"]
    if unmapped:
        evidence.append("unmapped_refs=" + ",".join(unmapped[:20]))
    return {
        "id": "manufacturer_mapping",
        "status": "warning" if unmapped else "pass",
        "severity": "warning" if unmapped else "info",
        "evidence": evidence,
        "recommendation": "Resolve unmapped references and confirm package/assembly method." if unmapped else "",
    }


def _capability_gates(files: ProjectFiles, preflight_result: dict[str, Any]) -> list[dict[str, Any]]:
    tools = preflight_result["tools"]
    spice_tools = [name for name in ("ngspice", "ltspice", "xyce") if tools[name]["available"]]
    datasheet_dirs = [files.project / "datasheets", files.project / "datasheets" / "extracted"]
    datasheet_dir = next((path for path in datasheet_dirs if path.exists()), None)
    return [
        {
            "id": "spice_available",
            "status": "pass" if spice_tools else "not_performed",
            "severity": "info" if spice_tools else "warning",
            "evidence": [f"engines={','.join(spice_tools)}"] if spice_tools else ["no ngspice/LTspice/Xyce found"],
            "recommendation": "Install an SPICE engine and add a validated transient/PDN testbench for power integrity." if not spice_tools else "",
        },
        {
            "id": "datasheet_evidence",
            "status": "pass" if datasheet_dir else "not_performed",
            "severity": "info" if datasheet_dir else "warning",
            "evidence": [str(datasheet_dir)] if datasheet_dir else [],
            "recommendation": "Add datasheets/extracted evidence for regulator, driver, protection and connector decisions." if not datasheet_dir else "",
        },
        {
            "id": "lifecycle_data",
            "status": "not_performed",
            "severity": "warning",
            "evidence": ["lifecycle audit requires explicit network/API-enabled invocation"],
            "recommendation": "Run the lifecycle/obsolescence audit when procurement readiness matters.",
        },
    ]


def _analyzer_gate(path: Path, gate_id: str) -> dict[str, Any]:
    data = read_json(path)
    if data is None:
        return {"id": gate_id, "status": "blocked", "severity": "blocker", "evidence": [str(path)], "recommendation": "Inspect the analyzer log and rerun."}
    summary = data.get("summary", {})
    errors = summary.get("by_severity", {}).get("error", 0)
    warnings = summary.get("by_severity", {}).get("warning", 0)
    status = "warning" if warnings else "pass"
    if errors:
        status = "warning"
    return {
        "id": gate_id,
        "status": status,
        "severity": "warning" if status == "warning" else "info",
        "evidence": [str(path), f"errors={errors}", f"warnings={warnings}"],
        "recommendation": "Triage findings; analyzer results are not native KiCad DRC." if errors or warnings else "",
    }


def _write_report(run_dir: Path, manifest: dict[str, Any], gates: list[dict[str, Any]], commands: list[dict[str, Any]]) -> None:
    blockers = [g for g in gates if g.get("severity") == "blocker" or g.get("status") == "blocked"]
    warnings = [g for g in gates if g.get("status") == "warning"]
    readiness = "not_ready" if blockers else ("needs_review" if warnings else "fab_ready")
    manifest["gates"] = gates
    manifest["readiness"] = readiness
    manifest["commands"] = commands
    json_dump(run_dir / "manifest.json", manifest)
    json_dump(run_dir / "gate_report.json", manifest)

    lines = [
        "# pcbflow Review",
        "",
        f"- Project: `{manifest['project']}`",
        f"- Target: `{manifest['target']}`",
        f"- Readiness: **{readiness}**",
        "",
        "## Gates",
        "",
        "| Gate | Status | Severity | Evidence |",
        "|---|---|---|---|",
    ]
    for gate in gates:
        lines.append(f"| {gate['id']} | {gate['status']} | {gate['severity']} | {'; '.join(gate.get('evidence', []))} |")
    lines += ["", "## Commands", ""]
    for command in commands:
        detail = f"; {command['error']}" if command.get("error") else ""
        lines.append(f"- `{command['name']}`: {command['status']} ({command['elapsed_s']}s){detail}")
    lines += ["", "## Gaps", "", "- Native KiCad DRC/ERC, SPICE, lifecycle and datasheet sync are reported from environment availability and are not silently treated as passed."]
    (run_dir / "report.md").write_text("\n".join(lines) + "\n")


def review(
    files: ProjectFiles,
    target: str,
    full: bool = False,
    visual_approved: bool = False,
    gui_drc_report: Path | None = None,
    open_gui_drc: bool = False,
) -> Path:
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_dir = files.project / "analysis" / "pcbflow" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    pre = preflight(files, target)
    json_dump(run_dir / "preflight.json", pre)

    commands: list[dict[str, Any]] = []
    outputs: dict[str, Path] = {}
    config = files.config

    independent: list[tuple[str, list[str], Path]] = []
    if files.schematic:
        output = run_dir / "schematic.json"
        args = [str(files.schematic)]
        if files.pro:
            args.extend(["--project-root", str(files.schematic)])
        independent.append(("schematic", _analyzer(KICAD_SKILL / "scripts/analyze_schematic.py", args, output, config), output))
    if files.gerbers:
        output = run_dir / "gerbers.json"
        args = [str(files.gerbers)] + (["--full"] if full else [])
        independent.append(("gerbers", _analyzer(KICAD_SKILL / "scripts/analyze_gerbers.py", args, output, None), output))

    with ThreadPoolExecutor(max_workers=max(1, len(independent))) as executor:
        futures = {executor.submit(_run, args, run_dir / "logs", name): (name, output) for name, args, output in independent}
        for future in as_completed(futures):
            name, output = futures[future]
            commands.append(future.result())
            if output.exists():
                outputs[name] = output

    if files.pcb and outputs.get("schematic"):
        output = run_dir / "pcb.json"
        args = [str(files.pcb)] + (["--full", "--proximity"] if full else []) + ["--schematic", str(outputs["schematic"])]
        result = _run(_analyzer(KICAD_SKILL / "scripts/analyze_pcb.py", args, output, config), run_dir / "logs", "pcb")
        commands.append(result)
        if output.exists():
            outputs["pcb"] = output
    elif files.pcb:
        output = run_dir / "pcb.json"
        args = [str(files.pcb)] + (["--full", "--proximity"] if full else [])
        result = _run(_analyzer(KICAD_SKILL / "scripts/analyze_pcb.py", args, output, config), run_dir / "logs", "pcb")
        commands.append(result)
        if output.exists():
            outputs["pcb"] = output

    if outputs.get("schematic") and outputs.get("pcb"):
        for name, script, args, output in [
            ("cross", KICAD_SKILL / "scripts/cross_analysis.py", ["--schematic", str(outputs["schematic"]), "--pcb", str(outputs["pcb"])], run_dir / "cross.json"),
            ("emc", EMC_SKILL / "scripts/analyze_emc.py", ["--schematic", str(outputs["schematic"]), "--pcb", str(outputs["pcb"])], run_dir / "emc.json"),
            ("thermal", KICAD_SKILL / "scripts/analyze_thermal.py", ["--schematic", str(outputs["schematic"]), "--pcb", str(outputs["pcb"]), "--ambient", "25"], run_dir / "thermal.json"),
        ]:
            result = _run(_analyzer(script, args, output, config if name != "cross" else None), run_dir / "logs", name)
            commands.append(result)
            if output.exists():
                outputs[name] = output

    json_outputs = {name: read_json(path) for name, path in outputs.items()}
    gates: list[dict[str, Any]] = list(pre["gates"])
    for name, gate_id in [("schematic", "schematic_analysis"), ("pcb", "pcb_analysis"), ("cross", "cross_analysis"), ("gerbers", "gerber_analysis"), ("emc", "emc_analysis"), ("thermal", "thermal_analysis")]:
        if name in outputs:
            gates.append(_analyzer_gate(outputs[name], gate_id))
    gates.append(_power_budget_gate(files, json_outputs.get("pcb")))
    gates.append(_layer_gate(json_outputs.get("pcb"), json_outputs.get("gerbers")))
    gates.append(_manufacturer_mapping_gate(files))
    gates.extend(_capability_gates(files, pre))

    if pre["tools"]["kicad-cli"]["available"] and files.pcb:
        drc_output = run_dir / "native-drc.txt"
        # Use the strict native gate: include every severity, refill zones
        # before checking copper, and make violations observable to the
        # caller through the process exit code.
        command = [
            pre["tools"]["kicad-cli"]["path"],
            "pcb", "drc",
            "--severity-all",
            "--exit-code-violations",
            "--refill-zones",
            "--output", str(drc_output),
            str(files.pcb),
        ]
        commands.append(_run(command, run_dir / "logs", "native_drc"))
        drc_command = commands[-1]
        drc_status = "pass" if drc_output.exists() and drc_command["status"] == "pass" else "failed"
        evidence = [str(drc_output), f"command_status={drc_command['status']}"]
        if drc_command.get("error"):
            evidence.append(drc_command["error"])
        native_gate = {"id": "native_drc", "status": drc_status, "severity": "info" if drc_status == "pass" else "blocker", "evidence": evidence, "recommendation": "Resolve native DRC/tool crash before fabrication." if drc_status != "pass" else ""}
        gates.append(native_gate)
        if drc_status != "pass":
            if open_gui_drc:
                try:
                    gui_command = open_pcb_editor(files.pcb)
                    commands.append({"name": "open_pcb_editor", "command": gui_command, "status": "pass", "returncode": 0, "elapsed_s": 0, "error": None})
                except OSError as exc:
                    commands.append({"name": "open_pcb_editor", "command": [], "status": "blocked", "returncode": None, "elapsed_s": 0, "error": str(exc)})
            if gui_drc_report:
                fallback_gate = gui_drc_gate(gui_drc_report)
                gates.append(fallback_gate)
                if fallback_gate["status"] == "pass":
                    native_gate["status"] = "pass_via_gui_fallback"
                    native_gate["severity"] = "info"
                    native_gate["recommendation"] = ""
                    native_gate["evidence"].append("CLI failed; clean PCB Editor DRC report accepted as fallback")
            else:
                gates.append({"id": "native_drc_gui_fallback", "status": "blocked", "severity": "blocker", "evidence": ["kicad-cli failed or crashed"], "recommendation": "Run `pcbflow review --open-gui-drc`, execute PCB Editor DRC with refill enabled, save the report, then rerun with --gui-drc-report PATH."})

        visual_dir = run_dir / "visual"
        audit = layout_audit(files.pcb)
        json_dump(visual_dir / "layout-audit.json", audit)
        visual_results = []
        for index, command in enumerate(visual_commands(files.pcb, visual_dir, pre["tools"]["kicad-cli"]["path"])):
            visual_results.append(_run(command, run_dir / "logs", f"visual_render_{index}"))
        commands.extend(visual_results)
        rendered = [visual_dir / "board-top.png", visual_dir / "board-bottom.png"]
        render_ok = all(result["status"] == "pass" and path.exists() for result, path in zip(visual_results, rendered))
        if not render_ok:
            visual_status = "blocked"
            visual_severity = "blocker"
            recommendation = "Fix KiCad render failure before human visual inspection."
        elif visual_approved:
            visual_status = "pass"
            visual_severity = "info"
            recommendation = ""
        else:
            visual_status = "review_required"
            visual_severity = "blocker"
            recommendation = "Inspect visual/board-top.png and board-bottom.png, then rerun with --visual-approved."
        gates.append({
            "id": "visual_layout_review",
            "status": visual_status,
            "severity": visual_severity,
            "evidence": [str(path) for path in rendered] + [str(visual_dir / "layout-audit.json")],
            "recommendation": recommendation,
        })
    else:
        gates.append({"id": "native_drc", "status": "blocked", "severity": "blocker", "evidence": ["kicad-cli unavailable"], "recommendation": "Install KiCad CLI or run DRC/ERC in KiCad GUI."})
        if gui_drc_report:
            gates.append(gui_drc_gate(gui_drc_report))
        else:
            gates.append({"id": "native_drc_gui_fallback", "status": "blocked", "severity": "blocker", "evidence": ["kicad-cli unavailable"], "recommendation": "Run PCB Editor DRC and pass --gui-drc-report PATH."})
        gates.append({"id": "visual_layout_review", "status": "blocked", "severity": "blocker", "evidence": ["kicad-cli unavailable"], "recommendation": "Install KiCad CLI to render the PCB, then visually inspect it in PCBNew."})

    manifest = {
        "tool": "pcbflow",
        "version": "0.1.0",
        "run_id": run_id,
        "project": str(files.project),
        "target": target,
        "source_hashes": pre["source_hashes"],
        "outputs": {name: str(path) for name, path in outputs.items()},
        "preflight": str(run_dir / "preflight.json"),
    }
    _write_report(run_dir, manifest, gates, commands)
    return run_dir


def latest_run(project: Path) -> Path | None:
    root = project.expanduser().resolve() / "analysis" / "pcbflow"
    runs = sorted(path for path in root.iterdir() if path.is_dir() and (path / "gate_report.json").exists()) if root.exists() else []
    return runs[-1] if runs else None


def release_package(files: ProjectFiles, run: Path | None = None, output: Path | None = None) -> Path:
    run = run or latest_run(files.project)
    if not run or not (run / "gate_report.json").exists():
        raise RuntimeError("no pcbflow review run found; run `pcbflow review --full` first")
    report = read_json(run / "gate_report.json")
    if not report:
        raise RuntimeError(f"invalid gate report: {run / 'gate_report.json'}")
    if report.get("readiness") != "fab_ready":
        raise RuntimeError(f"release blocked by readiness={report.get('readiness')}")
    for path, expected in report.get("source_hashes", {}).items():
        source = Path(path)
        if not source.exists() or sha256_file(source) != expected:
            raise RuntimeError(f"source changed after review: {source}")

    output = output or (files.project / "release" / f"pcbflow_release_{report.get('run_id', 'latest')}.zip")
    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    include: list[tuple[Path, str]] = []
    for source in [files.schematic, files.pcb, files.pro, files.config, files.context, files.gerbers]:
        if not source or not source.exists():
            continue
        if source.is_dir():
            include.extend((child, str(Path("gerbers") / child.relative_to(source))) for child in sorted(source.rglob("*")) if child.is_file())
        else:
            include.append((source, str(Path("kicad") / source.name)))
    include.extend((path, str(Path("review") / path.name)) for path in sorted(run.iterdir()) if path.is_file())
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for source, name in include:
            archive.write(source, name)
    return output
