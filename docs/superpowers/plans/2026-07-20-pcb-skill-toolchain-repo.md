# PCB Skill Toolchain and Repository Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:verification-before-completion` before claiming completion.

**Goal:** Package the global PCB Skills and the reusable `pcbflow` scripts into a portable repository, with a dedicated KiCad CLI/toolchain installation chapter and a GitHub publication path.

**Architecture:** `pcb` is the main router. It delegates circuit generation to `circuit-synth` and KiCad/design review to `kicad-happy`; the latter delegates parsing to the installed `kicad` Skill. `tools/pcbflow` records preflight, analyzer commands, hashes, gates, and release packaging without replacing domain Skills.

**Tech Stack:** Markdown Skills, Python 3.12+, Circuit-Synth, KiCad CLI, optional ngspice, `uv`, `unittest`, Git, and GitHub CLI.

## Work items

1. Add the toolchain chapter and read-only capability checker to `skills/pcb`, and add the matching preflight guidance to `skills/kicad-happy`.
2. Mirror the three authored Skills and the reusable `pcbflow` package/tests into repository-owned paths.
3. Remove machine-specific paths from the published router/tool and make `pcbflow` tests use portable temporary fixtures.
4. Add repository documentation and ignore rules that keep generated boards, reports, environments, caches, and release artifacts out of the public source tree.
5. Validate Skill structure, Python tests, checker output, CLI help probes, and repository hygiene.
6. Initialize Git, commit only the authored Skills/tooling/docs, verify GitHub CLI authentication and remote target, then push the repository.
