from __future__ import annotations

import argparse
import json
from pathlib import Path

from .core import discover_project, latest_run, preflight, release_package, review


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pcbflow", description="Run a reproducible KiCad/PCB review flow.")
    sub = parser.add_subparsers(dest="command", required=True)

    for name in ["preflight", "review"]:
        command = sub.add_parser(name)
        command.add_argument("--project", required=True, type=Path)
        command.add_argument("--target", default="generic")
        if name == "review":
            command.add_argument("--full", action="store_true")
            command.add_argument(
                "--visual-approved",
                action="store_true",
                help="Confirm that the generated top/bottom renders were manually inspected.",
            )

    release = sub.add_parser("release")
    release.add_argument("--project", required=True, type=Path)
    release.add_argument("--target", default="generic")
    release.add_argument("--run", type=Path, help="Specific pcbflow run directory; defaults to latest run")
    release.add_argument("--output", type=Path, help="Output zip path")
    status = sub.add_parser("status")
    status.add_argument("--run", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "status":
        path = args.run / "gate_report.json"
        if not path.exists():
            print(json.dumps({"status": "blocked", "reason": f"missing {path}"}, ensure_ascii=False, indent=2))
            return 2
        print(path.read_text())
        return 0

    files = discover_project(args.project)
    if args.command == "preflight":
        result = preflight(files, args.target)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if not any(g["status"] == "blocked" for g in result["gates"] if g["severity"] == "blocker") else 2

    if args.command == "review":
        run_dir = review(files, args.target, args.full, args.visual_approved)
        print(run_dir)
        return 0

    if args.command == "release":
        try:
            output = release_package(files, args.run, args.output)
        except RuntimeError as exc:
            print(json.dumps({"status": "blocked", "reason": str(exc)}, ensure_ascii=False, indent=2))
            return 2
        print(json.dumps({"status": "pass", "target": args.target, "output": str(output)}, ensure_ascii=False, indent=2))
        return 0

    return 2
