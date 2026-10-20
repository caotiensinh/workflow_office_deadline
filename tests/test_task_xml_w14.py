"""W14 exact offline audit of Task Scheduler XML: not proof of live execution."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from edu_workflow.task_xml_audit import inspect_xml

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "examples" / "w14_task_synthetic.xml"
WORKFLOW = ROOT / ".github" / "workflows" / "w14-cmd-selfhost-probe.yml"


class TaskXMLAuditW14(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.file = self.root / "evidence.xml"
        self.file.write_bytes(SAMPLE.read_bytes())

    def rewrite(self, original, replacement):
        source = self.file.read_text(encoding="utf-8")
        self.assertIn(original, source)
        self.file.write_text(source.replace(original, replacement),
                             encoding="utf-8")
        return inspect_xml(self.file)

    def statuses(self, r):
        return {x["id"]: x["pass"] for x in r["checks"]}

    def test_matching_source_never_means_live_acceptance(self):
        result = inspect_xml(self.file)
        self.assertEqual(result["status"], "CONFIG_MATCH_UNVERIFIED")
        self.assertEqual(len(result["checks"]), 8)
        self.assertTrue(all(self.statuses(result).values()))
        for key in ("task_existence_verified", "task_executed_verified",
                    "fifteen_minute_runs_observed", "machine_policy_changed",
                    "external_actions_performed", "production_accepted"):
            self.assertFalse(result[key])
        self.assertTrue(result["configured_only"])

    def test_repetition_must_be_exact_15_minutes(self):
        for interval in ("PT5M", "PT10M", "PT30M", "PT1H"):
            self.file.write_bytes(SAMPLE.read_bytes())
            r = self.rewrite("PT15M", interval)
            self.assertEqual(r["status"], "CONFIG_MISMATCH")
            self.assertFalse(self.statuses(r)["EXACT_15_MIN_REPEAT"])

    def test_overprivileged_task_not_accepted(self):
        result = self.rewrite("LeastPrivilege", "HighestAvailable")
        self.assertFalse(self.statuses(result)["LIMITED_RUN_LEVEL"])

    def test_task_disabled_is_not_valid(self):
        # Disables both the trigger and task setting.
        result = self.rewrite("<Enabled>true</Enabled>", "<Enabled>false</Enabled>")
        self.assertFalse(self.statuses(result)["TASK_ENABLED"])
        self.assertFalse(self.statuses(result)["SINGLE_ENABLED_TIME_TRIGGER"])

    def test_additional_action_is_rejected(self):
        result = self.rewrite("</Actions>",
                              "<Exec><Command>cmd.exe</Command></Exec></Actions>")
        self.assertFalse(self.statuses(result)["SINGLE_EXEC_ACTION"])

    def test_external_mail_and_outlook_flags_are_rejected(self):
        for extra in ("-Channel smtp", "-ImportOutlookClassic",
                      "-ExecutionPolicy Bypass", "-Command Write-Host"):
            self.file.write_bytes(SAMPLE.read_bytes())
            r = self.rewrite("-Channel file", "-Channel file " + extra)
            self.assertFalse(self.statuses(r)["FILE_ONLY_NO_ADDITIONAL_FLAGS"])

    def test_unknown_binary_and_alternate_script_rejected(self):
        for original, changed, key in (
            ("<Command>powershell.exe</Command>", "<Command>cmd.exe</Command>",
             "POWERSHELL_COMMAND_FIXED"),
            ("run_once.ps1", "update_system.ps1",
             "FILE_ONLY_NO_ADDITIONAL_FLAGS"),
            ("-NoProfile", "-NoProfile -WindowStyle Hidden",
             "FILE_ONLY_NO_ADDITIONAL_FLAGS"),
        ):
            self.file.write_bytes(SAMPLE.read_bytes())
            self.assertFalse(self.statuses(self.rewrite(original, changed))[key])

    def test_command_metacharacters_and_unquoted_path_fail(self):
        for value in (" & calc", " | curl", "%PATH%", "$env:SECRET", ";Write-Host"):
            self.file.write_bytes(SAMPLE.read_bytes())
            # XML metacharacters such as '&' are rejected by the parser
            # itself; well-formed injected text must fail the action allowlist.
            try:
                r = self.rewrite("-Channel file", "-Channel file" + value)
            except ValueError:
                continue
            self.assertFalse(self.statuses(r)["FILE_ONLY_NO_ADDITIONAL_FLAGS"])

    def test_working_directory_action_metadata_rejected(self):
        r = self.rewrite("</Exec>",
                         "<WorkingDirectory>C:\\Temp</WorkingDirectory></Exec>")
        self.assertFalse(self.statuses(r)["NO_ACTION_WORKDIR"])

    def test_duplicate_principal_rejected(self):
        r = self.rewrite("</Principals>",
                         "<Principal><RunLevel>LeastPrivilege</RunLevel></Principal></Principals>")
        self.assertFalse(self.statuses(r)["LIMITED_RUN_LEVEL"])

    def test_bad_namespace_and_root_rejected(self):
        r = self.file.read_text(encoding="utf-8").replace(
            "http://schemas.microsoft.com/windows/2004/02/mit/task",
            "https://example.invalid/malicious")
        self.file.write_text(r, encoding="utf-8")
        with self.assertRaises(ValueError):
            inspect_xml(self.file)

    def test_dtd_entities_and_malformed_xml_rejected(self):
        for body in ('<!DOCTYPE Task [<!ENTITY ex "bad">]><Task/>',
                     "<Task><Unclosed></Task>",
                     "<!ENTITY ex SYSTEM 'file:///C:/secret'>"):
            self.file.write_text(body, encoding="utf-8")
            with self.assertRaises(ValueError):
                inspect_xml(self.file)

    def test_overlarge_and_missing_xml_fail_closed(self):
        self.file.write_bytes(b"A" * 131073)
        with self.assertRaises(ValueError):
            inspect_xml(self.file)
        self.file.unlink()
        with self.assertRaises(ValueError):
            inspect_xml(self.file)

    def test_symlink_to_export_is_rejected(self):
        link = self.root / "symlink.xml"
        try:
            link.symlink_to(self.file)
        except (OSError, NotImplementedError):
            self.skipTest("Symlink unavailable under non-admin Windows")
        with self.assertRaises(ValueError):
            inspect_xml(link)

    def test_cli_does_not_create_files_or_expose_task_paths(self):
        before = {x.name for x in self.root.iterdir()}
        p = subprocess.run(
            [sys.executable, "-m", "edu_workflow.task_xml_audit",
             "--xml", str(self.file)],
            cwd=ROOT, env=dict(os.environ, PYTHONPATH=str(ROOT / "python"),
                               PYTHONIOENCODING="cp1252"),
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(p.returncode, 0, p.stderr)
        report = json.loads(p.stdout)
        self.assertEqual(report["status"], "CONFIG_MATCH_UNVERIFIED")
        self.assertFalse(report["production_accepted"])
        self.assertNotIn("C:\\Synthetic", p.stdout)
        self.assertEqual(before, {x.name for x in self.root.iterdir()})

    def test_cli_nonmatching_xml_returns_three(self):
        self.rewrite("PT15M", "PT30M")
        p = subprocess.run(
            [sys.executable, "-m", "edu_workflow.task_xml_audit",
             "--xml", str(self.file)],
            cwd=ROOT, env=dict(os.environ, PYTHONPATH=str(ROOT / "python")),
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(p.returncode, 3)
        self.assertEqual(json.loads(p.stdout)["status"], "CONFIG_MISMATCH")

    def test_cmd_transport_workflow_is_restricted_and_no_checkout(self):
        doc = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("feat/w14-safe-cmd-runner-probe", doc)
        self.assertIn("runs-on: [self-hosted, Windows]", doc)
        self.assertIn("shell: cmd", doc)
        self.assertIn("W14_CMD_RUNNER_TRANSPORT_PASS", doc)
        self.assertNotIn("workflow_dispatch:", doc)
        for forbidden in ("uses:", "checkout@", "powershell.exe",
                          "-ExecutionPolicy", "schtasks", "Get-Process",
                          "python -m", "curl ", "Invoke-WebRequest",
                          "windows/run_once.ps1"):
            self.assertNotIn(forbidden, doc)

if __name__ == "__main__":
    unittest.main()
