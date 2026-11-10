"""Offline-only tests for the EXAONE OpenCode coding task runner."""
import importlib.util
from pathlib import Path
import tempfile
import unittest


SOURCE = Path(__file__).resolve().parents[1] / "automation/exaone-opencode-poc/runner.py"
SPEC = importlib.util.spec_from_file_location("exaone_agent_runner", SOURCE)
agent = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(agent)


class AgentRunnerTests(unittest.TestCase):
    def test_config_is_official_exaone_provider_without_embedded_secret(self):
        import json
        config = json.loads(agent.CONFIG.read_text(encoding="utf-8"))
        agent.validate_config(config)
        self.assertEqual(config["providers"]["exaone"]["settings"]["apiKey"], "{env:EXAONE_API_KEY}")

    def test_ticker_smoke_prepare_and_structure_only_verify(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "scratch"
            agent.prepare("ticker-smoke", workspace)
            (workspace / "ticker_utils.py").write_text(
                "def normalize_ticker(value):\n    return value.strip().upper()\n",
                encoding="utf-8",
            )
            agent.verify(workspace)
            self.assertEqual(len(list(workspace.iterdir())), 4)

    def test_real_task_prepares_only_allowlisted_references(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "scratch"
            agent.prepare("exaone-regression-tests", workspace)
            inputs = agent.TASKS["exaone-regression-tests"]["inputs"]
            self.assertTrue(all((workspace / name).is_file() for name in inputs))
            new_file = workspace / "tests/test_exaone_sector_pilot_agent.py"
            new_file.write_text(
                "import unittest\nclass GeneratedTests(unittest.TestCase):\n"
                "    def test_first(self): pass\n    def test_second(self): pass\n",
                encoding="utf-8",
            )
            agent.verify(workspace)
            (workspace / inputs[0]).write_text("tampered", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "reference_file_modified"):
                agent.verify(workspace)

    def test_extra_scratch_file_is_ignored_but_only_expected_output_is_verified(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "scratch"
            agent.prepare("ticker-smoke", workspace)
            (workspace / "ticker_utils.py").write_text("def normalize_ticker(x): return x", encoding="utf-8")
            (workspace / "unexpected.py").write_text("x=1", encoding="utf-8")
            agent.verify(workspace)
            self.assertTrue((workspace / "unexpected.py").exists())
            self.assertEqual(agent.TASKS["ticker-smoke"]["output"], "ticker_utils.py")

    def test_missing_expected_output_still_fails_with_extra_files(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "scratch"
            agent.prepare("exaone-regression-tests", workspace)
            (workspace / "notes.py").write_text("x=1", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "missing_expected_files"):
                agent.verify(workspace)

    def test_extra_files_cannot_bypass_reference_integrity_check(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "scratch"
            agent.prepare("exaone-regression-tests", workspace)
            generated = workspace / "tests/test_exaone_sector_pilot_agent.py"
            generated.write_text(
                "import unittest\nclass Tests(unittest.TestCase):\n"
                "    def test_first(self): pass\n    def test_second(self): pass\n",
                encoding="utf-8",
            )
            (workspace / "extra.txt").write_text("additional scratch", encoding="utf-8")
            (workspace / "exaone_sector_pilot.py").write_text("corrupt", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "reference_file_modified"):
                agent.verify(workspace)

    def test_extra_symlinks_are_not_allowed(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "scratch"
            agent.prepare("ticker-smoke", workspace)
            (workspace / "ticker_utils.py").write_text("def normalize_ticker(x): return x", encoding="utf-8")
            (workspace / "external-link").symlink_to(Path(temp) / "external")
            with self.assertRaisesRegex(ValueError, "symbolic_link_forbidden"):
                agent.verify(workspace)

    def test_generated_code_never_runs_during_validation(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "scratch"
            agent.prepare("ticker-smoke", workspace)
            sentinel = Path(temp) / "sentinel"
            (workspace / "ticker_utils.py").write_text(
                f"open({str(sentinel)!r}, 'w').write('executed')\n"
                "def normalize_ticker(x): return x\n",
                encoding="utf-8",
            )
            agent.verify(workspace)
            self.assertFalse(sentinel.exists())

    def test_task_and_manifest_tampering_are_rejected(self):
        import json
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "scratch"
            agent.prepare("exaone-regression-tests", workspace)
            output = workspace / "tests/test_exaone_sector_pilot_agent.py"
            output.write_text(
                "import unittest\nclass Extra(unittest.TestCase):\n"
                "    def test_one(self): pass\n    def test_two(self): pass\n",
                encoding="utf-8",
            )
            manifest_file = workspace / "manifest.json"
            original = manifest_file.read_text(encoding="utf-8")
            data = json.loads(original)
            data["inputs"] = {}
            manifest_file.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "manifest_modified"):
                agent.verify(workspace)
            manifest_file.write_text(original, encoding="utf-8")
            (workspace / "task.txt").write_text("change the production system", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "task_instruction_modified"):
                agent.verify(workspace)

    def test_network_import_and_unknown_task_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "scratch"
            with self.assertRaisesRegex(ValueError, "unknown_task"):
                agent.prepare("arbitrary", workspace)
            agent.prepare("ticker-smoke", workspace)
            (workspace / "ticker_utils.py").write_text(
                "import urllib.request\ndef normalize_ticker(x): return x\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "unexpected_generated_import"):
                agent.verify(workspace)


if __name__ == "__main__":
    unittest.main()
