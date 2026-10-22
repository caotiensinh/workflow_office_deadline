"""W39 acceptance: bound actual source, sandbox isolation, repair, PR-proof artifacts."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from edu_workflow.autopilot_code_candidate_w39 import (
    ALLOWED_TESTS, DOCKER_IMAGE, FIXTURE_LABEL, LIVE_LABEL,
    SOURCE_NAME, TARGET_PATH, TASK_ID, docker_verify, ensure_output,
    parse_candidate, run_pipeline, validate_code, verify_artifact, main,
)

OK = '''def deadline_priority(minutes_remaining: int, has_blocker: bool) -> str:
    if has_blocker:
        return "BLOCKED"
    if minutes_remaining < 0:
        return "OVERDUE"
    if minutes_remaining <= 60:
        return "DUE_SOON"
    if minutes_remaining <= 1440:
        return "TODAY"
    return "SCHEDULED"
'''
BAD_RESULT = '''def deadline_priority(minutes_remaining: int, has_blocker: bool) -> str:
    return "TODAY"
'''


def candidate(code=OK):
    return {"task_id": TASK_ID, "path": TARGET_PATH,
            "code": code, "requires_human_review": True}


def sandbox_ok(src, folder):
    return {"success": True, "sandbox_used": True,
            "sandbox_network_disabled": True}


class W39CodeCandidates(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)
        self.output = self.root / "out"
        self.output.mkdir()
        self.env = patch.dict(os.environ, {"RUNNER_TEMP": str(self.root),
                                          "EDU_W39_FIXTURE_ONLY": "1"})
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_true_model_code_requires_exact_function(self):
        self.assertEqual(validate_code(OK), OK)

    def test_do_not_allow_source_with_import(self):
        with self.assertRaises(ValueError):
            validate_code("import os\n" + OK)

    def test_do_not_allow_shell_code_or_function_calls(self):
        with self.assertRaises(ValueError):
            validate_code(OK.replace('return "OVERDUE"', 'return __import__("os").system("id")'))

    def test_do_not_allow_raw_attribute_or_subscript(self):
        for attack in ["has_blocker.__class__", "minutes_remaining.__dict__",
                       "minutes_remaining[0]"]:
            with self.subTest(attack=attack):
                with self.assertRaises(ValueError):
                    validate_code(OK.replace("if has_blocker:", f"if {attack}:"))

    def test_do_not_allow_python_exec_or_dunder(self):
        code = OK.replace('return "TODAY"', 'return eval("1")')
        with self.assertRaises(ValueError):
            validate_code(code)

    def test_do_not_allow_loops_or_code_import_path(self):
        with self.assertRaises(ValueError):
            validate_code(OK + "while True: pass\n")

    def test_do_not_allow_nested_or_second_functions(self):
        with self.assertRaises(ValueError):
            validate_code(OK + "\ndef second(x):\n    return x\n")

    def test_wrong_signature_rejected(self):
        for source in [OK.replace("has_blocker: bool", "has_blocker"),
                       OK.replace("minutes_remaining: int", "minutes_remaining: str"),
                       OK.replace("-> str", "-> int")]:
            with self.subTest():
                with self.assertRaises(ValueError):
                    validate_code(source)

    def test_strings_must_be_known_fixed_deadline_categories(self):
        with self.assertRaises(ValueError):
            validate_code(OK.replace('"SCHEDULED"', '"APPROVED_PRODUCTION"'))

    def test_wrong_envelope_path_or_task_rejected(self):
        for broken in [dict(candidate(), path="../secret.py"),
                       dict(candidate(), task_id="W27-OUTLOOK"),
                       dict(candidate(), requires_human_review=False)]:
            with self.assertRaises(ValueError):
                parse_candidate(broken)

    def test_extra_field_or_duplicate_json_keys_rejected(self):
        with self.assertRaises(ValueError):
            parse_candidate(dict(candidate(), extra="yes"))
        with self.assertRaises(ValueError):
            parse_candidate('{"task_id":"W39-DEADLINE","task_id":"another"}')

    def test_valid_json_has_true_model_authored_source(self):
        self.assertEqual(parse_candidate(json.dumps(candidate())), OK)

    def test_fixture_is_never_reported_as_live_model(self):
        receipt = run_pipeline(self.output, fixture=candidate(), sandbox=sandbox_ok)
        self.assertEqual(receipt["origin"], FIXTURE_LABEL)
        self.assertEqual(receipt["model_calls"], 0)
        self.assertTrue(receipt["sandbox_verified"])
        self.assertFalse(receipt["git_writes"])
        self.assertFalse(receipt["auto_merged"])
        self.assertEqual((self.output / SOURCE_NAME).read_text(), OK)
        report = verify_artifact(self.output, sandbox=sandbox_ok)
        self.assertEqual(report["path"], TARGET_PATH)
        self.assertTrue(report["human_review_required"])
        with self.assertRaises(ValueError):
            verify_artifact(self.output, require_live=True, sandbox=sandbox_ok)

    def test_no_fixture_optin_no_code_written(self):
        with patch.dict(os.environ, {"EDU_W39_FIXTURE_ONLY": "0"}):
            with self.assertRaises(ValueError):
                run_pipeline(self.output, fixture=candidate(), sandbox=sandbox_ok)
        self.assertEqual(list(self.output.iterdir()), [])

    def test_empty_runner_temp_required(self):
        (self.output / "owner.txt").write_text("human-owned")
        with self.assertRaises(ValueError):
            run_pipeline(self.output, fixture=candidate(), sandbox=sandbox_ok)
        self.assertEqual((self.output / "owner.txt").read_text(), "human-owned")

    def test_no_repo_or_other_outside_temp_output(self):
        with self.assertRaises(ValueError):
            ensure_output(str(Path.cwd()))

    def test_symlink_to_external_output_rejected(self):
        link = self.root / "link"
        try:
            link.symlink_to(self.output, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("No symlink capability")
        with self.assertRaises(ValueError):
            ensure_output(link)

    def test_failed_policy_tests_fail_closed_without_artifact(self):
        with self.assertRaises(ValueError):
            run_pipeline(self.output, fixture=candidate(BAD_RESULT),
                         sandbox=lambda _src, _dir: {
                             "success": False, "sandbox_used": True,
                             "failed_cases": ["test_zero_due_soon"]})
        self.assertEqual(list(self.output.iterdir()), [])

    def test_publisher_rejects_modified_source(self):
        run_pipeline(self.output, fixture=candidate(), sandbox=sandbox_ok)
        (self.output / SOURCE_NAME).write_text(BAD_RESULT)
        with self.assertRaises(ValueError):
            verify_artifact(self.output, sandbox=sandbox_ok)

    def test_publisher_fails_if_own_independent_sandbox_fails(self):
        run_pipeline(self.output, fixture=candidate(), sandbox=sandbox_ok)
        with self.assertRaises(ValueError):
            verify_artifact(self.output, sandbox=lambda a,b: {
                "success":False, "sandbox_used":True})

    def test_docker_has_no_network_and_is_non_root_readonly_resource_limited(self):
        commands = []
        def fake_run(command, **kwargs):
            commands.append((command, kwargs))
            return SimpleNamespace(returncode=0, stdout="", stderr="OK")
        with tempfile.TemporaryDirectory() as base:
            result = docker_verify(OK, Path(base), runner=fake_run)
            self.assertTrue(result["success"])
            self.assertFalse(list(Path(base).iterdir()))
        argv, args = commands[0]
        for argument in ("--network=none", "--read-only", "--cap-drop=ALL",
                         "--security-opt=no-new-privileges", "--pids-limit=32",
                         "--memory=256m", "--memory-swap=256m", "--cpus=1",
                         "--user=65534:65534", "--pull=never"):
            self.assertIn(argument, argv)
        self.assertIn(DOCKER_IMAGE, argv)
        self.assertEqual(args["timeout"], 45)
        self.assertNotIn("GITHUB_TOKEN", " ".join(argv))
        self.assertNotIn("GH_TOKEN", " ".join(argv))

    def test_docker_failure_feedback_uses_only_known_trusted_test_names(self):
        def fake_run(command, **kwargs):
            return SimpleNamespace(returncode=1, stdout="",
                stderr="test_sixty_due_soon (test_deadline_w39.DeadlinePolicyAcceptance)"
                       " ... FAIL\nattacker text: private-token\n")
        with tempfile.TemporaryDirectory() as base:
            result = docker_verify(BAD_RESULT, Path(base), runner=fake_run)
        self.assertEqual(result["failed_cases"], ["test_sixty_due_soon"])
        self.assertNotIn("private", json.dumps(result))

    def test_no_live_ollama_without_double_optin(self):
        with patch.dict(os.environ, {"EDU_AUTOPILOT_ENABLE": "0",
                                     "EDU_W39_MODEL_CODE_ENABLE": "1",
                                     "EDU_W39_FIXTURE_ONLY":"0"}):
            with self.assertRaises(ValueError):
                run_pipeline(self.output, model="fake:1", sandbox=sandbox_ok)

    def test_model_revision_allowed_once_with_sanitized_failure_names(self):
        from edu_workflow import autopilot_code_candidate_w39 as m
        with patch.dict(os.environ, {
            "EDU_AUTOPILOT_ENABLE":"1", "EDU_W39_MODEL_CODE_ENABLE":"1",
            "EDU_W39_FIXTURE_ONLY":"0"}):
            with patch.object(m, "local_ollama", return_value={
                "models":[{"name":"small:1","size":1*1024**3}]}):
                with patch.object(m, "available_memory_bytes",
                                  return_value=16*1024**3):
                    with patch.object(m.os, "cpu_count", return_value=8):
                        with patch.object(m.os, "getloadavg", return_value=(0,0,0)):
                            with patch("builtins.open", wraps=open) as original_open:
                                # /proc/meminfo is read on Linux in CI; this
                                # mocked transport NEVER reaches Ollama.
                                payloads = []
                                def fake_transport(payload):
                                    payloads.append(payload)
                                    source = BAD_RESULT if len(payloads)==1 else OK
                                    return {"response":json.dumps(candidate(source))}
                                runs = []
                                def sandbox(source, folder):
                                    runs.append(source)
                                    return {"success": source == OK,
                                            "sandbox_used":True,
                                            "failed_cases":["test_zero_due_soon"]}
                                receipt = run_pipeline(
                                    self.output, model="small:1",
                                    transport=fake_transport, sandbox=sandbox)
        self.assertEqual(receipt["origin"], LIVE_LABEL)
        self.assertEqual(receipt["model_calls"], 2)
        self.assertEqual(len(payloads), 2)
        self.assertEqual(len(runs), 2)
        self.assertIn("test_zero_due_soon", payloads[1]["prompt"])
        self.assertEqual(payloads[0]["options"]["num_gpu"], 0)
        self.assertFalse(receipt["git_writes"])

    def test_no_third_model_attempt_after_two_failures(self):
        from edu_workflow import autopilot_code_candidate_w39 as m
        with patch.dict(os.environ, {
            "EDU_AUTOPILOT_ENABLE":"1", "EDU_W39_MODEL_CODE_ENABLE":"1",
            "EDU_W39_FIXTURE_ONLY":"0"}):
            with patch.object(m, "local_ollama", return_value={
                "models":[{"name":"small:1","size":1*1024**3}]}):
                with patch.object(m, "available_memory_bytes",
                                  return_value=16*1024**3):
                    with patch.object(m.os, "cpu_count", return_value=8):
                        with patch.object(m.os, "getloadavg", return_value=(0,0,0)):
                            calls = []
                            def fake_transport(payload):
                                calls.append(payload)
                                return {"response": json.dumps(candidate(BAD_RESULT))}
                            with self.assertRaises(ValueError):
                                run_pipeline(self.output, model="small:1",
                                             transport=fake_transport,
                                             sandbox=lambda a,b:{
                                                 "success": False,
                                                 "sandbox_used": True,
                                                 "failed_cases": ["test_zero_due_soon"]})
        self.assertEqual(len(calls), 2)
        self.assertEqual(list(self.output.iterdir()), [])

    def test_no_execute_is_true_dry_run(self):
        from io import StringIO
        with patch("sys.stdout", new_callable=StringIO) as output:
            self.assertEqual(main([]), 0)
            receipt = json.loads(output.getvalue())
        self.assertEqual(receipt["model_calls"], 0)
        self.assertFalse(receipt["git_writes"])


if __name__ == "__main__":
    unittest.main()
