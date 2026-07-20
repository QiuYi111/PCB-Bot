# PCB Toolchain Installation and Configuration

This chapter prepares the tools used by `pcb`, `circuit-synth`, and `kicad-happy`. Keep installation separate from design files and record the verified versions in the project report.

## Required tools

- Python 3.12 or newer for the current Circuit-Synth release.
- Circuit-Synth in the project environment.
- KiCad with the `kicad-cli` executable available on `PATH` or configured explicitly.

Recommended optional tools:

- `uv` for reproducible Python environments;
- `ngspice` for SPICE simulation;
- `gh` for publishing the Skill repository;
- manufacturer datasheets and supplier credentials for evidence-backed component checks.

## macOS

Install KiCad from the official download page. The CLI is commonly inside the application bundle:

```bash
export PATH="/Applications/KiCad/KiCad.app/Contents/MacOS:$PATH"
kicad-cli version
```

If KiCad is installed in a versioned or custom location, set `KICAD_CLI` to the absolute executable path instead of adding a guessed directory:

```bash
export KICAD_CLI="/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
"$KICAD_CLI" version
```

Install the optional simulator with Homebrew:

```bash
brew install ngspice
ngspice --version
```

## Debian/Ubuntu

Install KiCad from the official KiCad package instructions or the distribution package, then verify the CLI:

```bash
sudo apt update
sudo apt install kicad
command -v kicad-cli
kicad-cli version
```

Install ngspice when simulation is required:

```bash
sudo apt install ngspice ngspice-doc
ngspice --version
```

Do not assume the system package version matches the project review baseline; record the version returned by `kicad-cli version`.

## Windows PowerShell

Install KiCad from the official download page. Add its `bin` directory for the current session, adjusting the version/path to the actual installation:

```powershell
$env:Path += ";C:\Program Files\KiCad\<version>\bin"
kicad-cli version
```

If PATH configuration is managed centrally, set `KICAD_CLI` to the full `kicad-cli.exe` path and restart the shell before running the check script. Install ngspice from its official distribution and verify:

```powershell
ngspice --version
```

## Python environment

Use one environment per repository. With `uv`:

```bash
uv venv --python 3.12
source .venv/bin/activate                 # macOS/Linux
uv pip install circuit-synth
python -c "import circuit_synth; print(circuit_synth.__version__)"
```

PowerShell activation:

```powershell
\.venv\Scripts\Activate.ps1
uv pip install circuit-synth
python -c "import circuit_synth; print(circuit_synth.__version__)"
```

For an existing `pyproject.toml`, prefer `uv add circuit-synth` or `uv sync` so the dependency is recorded. `pip install circuit-synth` remains a supported fallback. Do not install into the system Python when the project has a managed environment.

## Project configuration

1. Put Circuit-Synth source under the project source directory and generate into a dedicated `generated/` directory.
2. Keep `analysis/` for analyzer JSON, manifests, logs, and reports; do not commit generated analysis by default.
3. Use `.kicad-happy.json` for project metadata, design intent, power-rail overrides, BOM field priority, suppressions, and analysis retention.
4. Set `KICAD_CLI`, `KICAD_SKILL_ROOT`, and `EMC_SKILL_ROOT` only when the executable or Skill is not discoverable from the standard environment.
5. Never store distributor API keys or GitHub tokens in the repository. Use environment variables or the credential stores managed by the respective CLI.

## Verification gate

Run the bundled capability checker from the repository root:

```bash
python skills/pcb/scripts/check_toolchain.py
python skills/pcb/scripts/check_toolchain.py --json
```

Then probe the commands used by the current workflow:

```bash
kicad-cli pcb drc --help
kicad-cli pcb export gerbers --help
kicad-cli sch export pdf --help
```

Treat Python, Circuit-Synth, and KiCad CLI as required for generation. Treat ngspice, `gh`, datasheets, and supplier credentials as capability-dependent. If a required item is missing, stop generation/review and report the exact installation gap.

## Official references

- Circuit-Synth installation: https://circuit-synth.readthedocs.io/en/latest/installation.html
- Circuit-Synth simulation setup: https://circuit-synth.readthedocs.io/en/latest/SIMULATION_SETUP.html
- KiCad CLI manual: https://docs.kicad.org/10.0/en/cli/cli.html
- KiCad downloads: https://www.kicad.org/download/
- ngspice downloads: http://ngspice.sourceforge.net/download.html
