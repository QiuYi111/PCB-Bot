#!/usr/bin/env python3
"""Report the local PCB/Circuit-Synth toolchain without modifying the machine."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def _candidate_paths(name: str) -> list[str]:
    override = os.environ.get(name.upper().replace("-", "_"))
    candidates = [override] if override else []
    if name == "kicad-cli":
        candidates += [
            shutil.which("kicad-cli"),
            "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli",
        ]
        program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        candidates += [
            str(Path(program_files) / "KiCad" / "bin" / "kicad-cli.exe"),
            str(Path(local_app_data) / "Programs" / "KiCad" / "bin" / "kicad-cli.exe"),
        ]
    else:
        candidates.append(shutil.which(name))
    return [candidate for candidate in candidates if candidate]


def _find(name: str) -> str | None:
    for candidate in _candidate_paths(name):
        path = shutil.which(candidate) if os.path.basename(candidate) == candidate else candidate
        if path and Path(path).exists():
            return str(Path(path).resolve())
    return None


def _version(executable: str) -> str | None:
    try:
        result = subprocess.run(
            [executable, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    output = (result.stdout or result.stderr).strip().splitlines()
    return output[0] if output else None


def _package_version(package: str) -> str | None:
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return None


def build_report() -> dict[str, Any]:
    python_ok = sys.version_info >= (3, 12)
    tools: dict[str, Any] = {}
    for name in ("kicad-cli", "ngspice", "gh"):
        path = _find(name)
        tools[name] = {
            "available": path is not None,
            "path": path,
            "version": _version(path) if path else None,
        }

    packages = {
        package: _package_version(package)
        for package in ("circuit-synth", "PySpice")
    }
    required = {
        "python": python_ok,
        "circuit-synth": packages["circuit-synth"] is not None,
        "kicad-cli": tools["kicad-cli"]["available"],
    }
    return {
        "platform": platform.platform(),
        "python": {
            "executable": sys.executable,
            "version": platform.python_version(),
            "minimum": "3.12",
            "meets_minimum": python_ok,
        },
        "packages": packages,
        "tools": tools,
        "required": required,
        "optional": {
            "ngspice": tools["ngspice"]["available"],
            "gh": tools["gh"]["available"],
            "PySpice": packages["PySpice"] is not None,
        },
        "status": "pass" if all(required.values()) else "blocked",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument("--strict", action="store_true", help="return non-zero when a required capability is missing")
    args = parser.parse_args()
    report = build_report()
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"status: {report['status']}")
        print(f"python: {report['python']['version']} ({report['python']['executable']})")
        for name, value in report["packages"].items():
            print(f"package {name}: {value or 'missing'}")
        for name, value in report["tools"].items():
            print(f"tool {name}: {value['version'] or 'missing'} [{value['path'] or 'not found'}]")
        print("required:", ", ".join(f"{name}={'ok' if value else 'missing'}" for name, value in report["required"].items()))
    return 1 if args.strict and report["status"] != "pass" else 0


if __name__ == "__main__":
    raise SystemExit(main())
