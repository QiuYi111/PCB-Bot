"""Machine-assisted visual review artifacts for routed KiCad PCBs.

Rendering is deliberately separate from DRC.  A router can be electrically
legal and still produce an impractical placement, an ugly fan-out, an
unserviceable connector orientation, or a copper path that deserves human
attention.  This module creates the images and a small geometry audit; a human
must explicitly approve the images before the release gate can become ready.
"""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any


_START_RE = re.compile(r"\(start\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\)")
_END_RE = re.compile(r"\(end\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\)")
_LAYER_RE = re.compile(r"\(layer\s+\"?([^\"\s)]+)\"?\)")
_NET_RE = re.compile(r"\(net\s+(?:\"([^\"]+)\"|([-+0-9]+))\)")


def _segments(pcb_path: Path) -> list[dict[str, Any]]:
    text = pcb_path.read_text(errors="replace")
    result: list[dict[str, Any]] = []
    lines = text.splitlines()
    blocks: list[str] = []
    index = 0
    while index < len(lines):
        if not lines[index].lstrip().startswith("(segment"):
            index += 1
            continue
        depth = 0
        block_lines: list[str] = []
        while index < len(lines):
            line = lines[index]
            block_lines.append(line)
            depth += line.count("(") - line.count(")")
            index += 1
            if depth == 0:
                break
        blocks.append("\n".join(block_lines))

    for block in blocks:
        start = _START_RE.search(block)
        end = _END_RE.search(block)
        layer = _LAYER_RE.search(block)
        net = _NET_RE.search(block)
        if not (start and end and layer):
            continue
        x1, y1 = (float(value) for value in start.groups())
        x2, y2 = (float(value) for value in end.groups())
        result.append({
            "start": (x1, y1),
            "end": (x2, y2),
            "layer": layer.group(1),
            "net": net.group(1) if net and net.group(1) is not None else (net.group(2) if net else ""),
        })
    return result


def _orientation(x1: float, y1: float, x2: float, y2: float) -> str:
    dx, dy = abs(x2 - x1), abs(y2 - y1)
    if dx < 1e-6 or dy < 1e-6:
        return "axis"
    if abs(dx - dy) < 1e-4:
        return "45deg"
    return "other"


def _corner_angle(first: dict[str, Any], second: dict[str, Any]) -> float | None:
    shared = None
    for point in (first["start"], first["end"]):
        for candidate in (second["start"], second["end"]):
            if math.hypot(point[0] - candidate[0], point[1] - candidate[1]) < 1e-5:
                shared = point
                break
        if shared is not None:
            break
    if shared is None:
        return None
    def vector(segment: dict[str, Any]) -> tuple[float, float]:
        other = segment["end"] if segment["start"] == shared else segment["start"]
        return other[0] - shared[0], other[1] - shared[1]
    ax, ay = vector(first)
    bx, by = vector(second)
    norm = math.hypot(ax, ay) * math.hypot(bx, by)
    if norm < 1e-9:
        return None
    cosine = max(-1.0, min(1.0, (ax * bx + ay * by) / norm))
    return math.degrees(math.acos(cosine))


def layout_audit(pcb_path: Path) -> dict[str, Any]:
    segments = _segments(pcb_path)
    orientations = {"axis": 0, "45deg": 0, "other": 0}
    for segment in segments:
        orientations[_orientation(*segment["start"], *segment["end"])] += 1

    corners = {"90deg": 0, "other": 0}
    by_net_layer: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for segment in segments:
        by_net_layer.setdefault((segment["net"], segment["layer"]), []).append(segment)
    for group in by_net_layer.values():
        for index, first in enumerate(group):
            for second in group[index + 1:]:
                angle = _corner_angle(first, second)
                if angle is None:
                    continue
                if abs(angle - 90.0) < 1.0:
                    corners["90deg"] += 1
                else:
                    corners["other"] += 1

    total = len(segments) or 1
    return {
        "pcb": str(pcb_path),
        "segments": len(segments),
        "orientation_counts": orientations,
        "axis_segment_ratio": round(orientations["axis"] / total, 4),
        "45deg_segment_ratio": round(orientations["45deg"] / total, 4),
        "other_segment_ratio": round(orientations["other"] / total, 4),
        "corner_counts": corners,
        "human_review_required": True,
        "checklist": [
            "component placement and connector orientation",
            "power-flow and high-current copper paths",
            "fan-out, via locations, and thermal relief",
            "silkscreen/reference readability and edge clearance",
            "fabrication/assembly hazards not expressible in DRC",
        ],
    }


def visual_commands(pcb_path: Path, output_dir: Path, kicad_cli: str) -> list[list[str]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    commands = []
    for side in ("top", "bottom"):
        commands.append([
            kicad_cli, "pcb", "render",
            "--side", side,
            "--width", "2400",
            "--height", "1800",
            "--quality", "high",
            "--output", str(output_dir / f"board-{side}.png"),
            str(pcb_path),
        ])
    return commands
