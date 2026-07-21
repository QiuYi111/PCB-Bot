import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from pcbflow.core import _power_budget_gate, discover_project, release_package, sha256_file
from pcbflow.visual import layout_audit
from pcbflow.gui_drc import gui_drc_gate, parse_drc_report


class PcbflowTests(unittest.TestCase):
    def test_sha256_is_stable(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.txt"
            path.write_text("pcbflow")
            self.assertEqual(sha256_file(path), sha256_file(path))

    def test_discover_release_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            source = project / "release" / "kicad_import"
            source.mkdir(parents=True)
            (source / "design.kicad_sch").write_text("(kicad_sch)")
            (source / "design.kicad_pcb").write_text("(kicad_pcb)")
            (source / "design.kicad_pro").write_text("{}")
            files = discover_project(project)
            self.assertIsNotNone(files.schematic)
            self.assertIsNotNone(files.pcb)
            self.assertIn("release/kicad_import", files.schematic.as_posix())

    def test_motor_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            context = project / "pcbflow.json"
            context.write_text(json.dumps({"motor": {"voltage_v": 5, "phase_resistance_ohm": 20, "count": 2, "energized_phases_per_motor": 2}}))
            files = discover_project(project)
            gate = _power_budget_gate(files, None)
            self.assertEqual(gate["status"], "pass")
            self.assertIn("1.000A", " ".join(gate["evidence"]))

    def test_release_requires_fab_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            run = project / "analysis" / "pcbflow" / "run"
            run.mkdir(parents=True)
            (run / "gate_report.json").write_text(json.dumps({"readiness": "not_ready"}))
            files = discover_project(project)
            with self.assertRaisesRegex(RuntimeError, "readiness=not_ready"):
                release_package(files, run)

    def test_release_packages_reviewed_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            pcb = project / "design.kicad_pcb"
            pcb.write_text("(kicad_pcb)")
            run = project / "analysis" / "pcbflow" / "run"
            run.mkdir(parents=True)
            files = discover_project(project)
            (run / "gate_report.json").write_text(json.dumps({
                "readiness": "fab_ready",
                "run_id": "run",
                "source_hashes": {str(pcb): sha256_file(pcb)},
            }))
            output = release_package(files, run)
            self.assertTrue(output.exists())
            with zipfile.ZipFile(output) as archive:
                self.assertIn("kicad/design.kicad_pcb", archive.namelist())

    def test_layout_audit_counts_octilinear_segments(self):
        with tempfile.TemporaryDirectory() as tmp:
            pcb = Path(tmp) / "design.kicad_pcb"
            pcb.write_text('''
(kicad_pcb (version 20240108) (generator pcbnew)
  (segment (start 10 10) (end 12 10) (width 0.3) (layer "F.Cu") (net 1))
  (segment (start 12 10) (end 13 11) (width 0.3) (layer "F.Cu") (net 1))
)
''')
            audit = layout_audit(pcb)
            self.assertEqual(audit["segments"], 2)
            self.assertEqual(audit["orientation_counts"]["axis"], 1)
            self.assertEqual(audit["orientation_counts"]["45deg"], 1)
            self.assertEqual(audit["corner_counts"]["other"], 1)

    def test_gui_drc_report_is_passed_only_when_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "drc.rpt"
            report.write_text("** Found 0 DRC violations **\n** Found 0 unconnected pads **\n** Found 0 Footprint errors **\n")
            self.assertEqual(parse_drc_report(report)["status"], "pass")
            self.assertEqual(gui_drc_gate(report)["status"], "pass")


if __name__ == "__main__":
    unittest.main()
