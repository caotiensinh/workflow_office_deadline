"""W15 safety gates for sealed portable Python+Rust selfhost CMD-only E2E."""
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from w15_make_bundle_manifest import build_manifest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "w15-portable-selfhost-e2e.yml"
RUNNER_SCRIPT = ROOT / "tests" / "w15_portable_selfhost_e2e.py"
SHA = "a" * 40
spec = importlib.util.spec_from_file_location("w15_e2e", RUNNER_SCRIPT)
e2e = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e2e)


def fixture(folder):
    root = Path(folder)
    content = {
        "python.exe": b"PORTABLE_TEST_ONLY",
        "python312._pth": b"python312.zip\n.\n",
        "edu_rules.exe": b"TEST_RUST_BINARY",
        "cases.json": b"[]",
        "w15_e2e.py": b"test",
        "edu_workflow/cli.py": b"test",
        "edu_workflow/policy.py": b"test",
    }
    for path, data in content.items():
        file = root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(data)
    build_manifest(root, SHA)
    return root


class W15BundleSafety(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.folder = fixture(tmp.name)

    def test_manifest_attests_all_python_and_rust_bundle_members(self):
        with patch.dict(os.environ, {"GITHUB_SHA": SHA}):
            self.assertEqual(e2e.verify_bundle(self.folder), SHA)
        report = json.loads((self.folder / "w15_manifest.json").read_text())
        self.assertIn("edu_rules.exe", report["files"])
        self.assertIn("edu_workflow/policy.py", report["files"])

    def test_tampered_rust_binary_is_rejected(self):
        (self.folder / "edu_rules.exe").write_bytes(b"changed")
        with patch.dict(os.environ, {"GITHUB_SHA": SHA}):
            with self.assertRaisesRegex(RuntimeError, "BUNDLE_SHA256_MISMATCH"):
                e2e.verify_bundle(self.folder)

    def test_mismatched_commit_prevents_execution(self):
        with patch.dict(os.environ, {"GITHUB_SHA": "b" * 40}):
            with self.assertRaisesRegex(RuntimeError, "SHA_NOT_PINNED"):
                e2e.verify_bundle(self.folder)

    def test_unlisted_python_module_is_rejected(self):
        (self.folder / "edu_workflow" / "new.py").write_text("test")
        with patch.dict(os.environ, {"GITHUB_SHA": SHA}):
            with self.assertRaisesRegex(RuntimeError, "SOURCE_NOT_IN_MANIFEST"):
                e2e.verify_bundle(self.folder)

    def test_path_traversal_in_manifest_is_rejected(self):
        manifest = self.folder / "w15_manifest.json"
        data = json.loads(manifest.read_text())
        data["files"]["../private"] = "0" * 64
        manifest.write_text(json.dumps(data))
        with patch.dict(os.environ, {"GITHUB_SHA": SHA}):
            with self.assertRaisesRegex(RuntimeError, "UNSAFE_MANIFEST_PATH"):
                e2e.verify_bundle(self.folder)

    def test_manifest_cannot_silently_overwrite(self):
        with self.assertRaises(FileExistsError):
            build_manifest(self.folder, SHA)

    def test_manifest_generator_rejects_non_sha_commit(self):
        (self.folder / "w15_manifest.json").unlink()
        with self.assertRaises(ValueError):
            build_manifest(self.folder, "refs/heads/main")
        self.assertFalse((self.folder / "w15_manifest.json").exists())

    def test_run_cannot_launch_on_nonwindows_or_write_artifacts(self):
        if os.name == "nt":
            self.skipTest("run requires actual sealed portable interpreter on Windows")
        p = self.folder / "never-evidence"
        with self.assertRaisesRegex(RuntimeError, "WINDOWS_REQUIRED"):
            e2e.run(p)
        self.assertFalse(p.exists())

    def test_selfhost_job_uses_cmd_and_no_setup_or_powershell(self):
        yaml = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("feat/w15-selfhost-portable-cmd-e2e", yaml)
        self.assertIn("build-tested-portable:", yaml)
        self.assertIn("runs-on: windows-latest", yaml)
        self.assertIn("selfhost-cmd-e2e:", yaml)
        self.assertIn("runs-on: [self-hosted, Windows]", yaml)
        host = yaml.split("  selfhost-cmd-e2e:", 1)[1]
        self.assertIn("shell: cmd", host)
        self.assertIn("actions/download-artifact@v4", host)
        self.assertIn("W15_CMD_PYTHON_RUST_SQLITE_FILE_AUDIT_PASS", host)
        for forbidden in ("actions/checkout", "shell: pwsh",
                          "-ExecutionPolicy", "schtasks", "setup-python",
                          "Invoke-WebRequest", "Set-ExecutionPolicy",
                          "edu_workflow.cli --db"):
            self.assertNotIn(forbidden, host)
        self.assertNotIn("workflow_dispatch:", yaml)


if __name__ == "__main__":
    unittest.main()
