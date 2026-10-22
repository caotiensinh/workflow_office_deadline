"""W39 real model-authored *source code* candidate, sandbox test, bounded repair.

Unlike fixed-template test compilers, Ollama returns the entire Python function
body and its bytes become the candidate artifact. Never execute generated code
in a host Python interpreter. Only a network-disabled, read-only, non-root,
resource-limited Docker sandbox may import it. Publication is a distinct
privileged reviewed-PR job, never a model process or an approval/merge.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.error

from .autopilot_ollama_heartbeat_w36 import stream_generate
from .autopilot_probe_w28a import GIB, available_memory_bytes
from .autopilot_worker_w27 import local_ollama, no_duplicates

TASK_ID = "W39-DEADLINE"
TARGET_PATH = "python/edu_workflow/deadline_priority_w39.py"
SOURCE_NAME = "deadline_priority_w39.py"
DOCKER_IMAGE = "python:3.12-alpine"
MAX_SOURCE = 5000
MAX_MODEL_BYTES = 4 * GIB
MAX_CALLS = 2
VALID_STATES = frozenset({"BLOCKED", "OVERDUE", "DUE_SOON", "TODAY", "SCHEDULED"})
SAFE_AST = (
    ast.Module, ast.FunctionDef, ast.arguments, ast.arg, ast.Return,
    ast.If, ast.Compare, ast.Name, ast.Constant, ast.BoolOp, ast.And,
    ast.Or, ast.UnaryOp, ast.Not, ast.USub, ast.Load,
    ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Eq, ast.NotEq, ast.IfExp,
    ast.Pass,
)
PROMPT = (
    "You are authoring REAL Python source for a PUBLIC fictional-data-only "
    "office deadline system. Output only JSON with keys "
    "task_id, path, code, requires_human_review. "
    "task_id=W39-DEADLINE, path=python/edu_workflow/deadline_priority_w39.py, "
    "requires_human_review=true. The code MUST be exactly one pure function "
    "def deadline_priority(minutes_remaining: int, has_blocker: bool) -> str: "
    "with no imports, calls, attributes, assignments, decorators, loops, "
    "global references or external effects. "
    "Return BLOCKED when has_blocker is true; otherwise OVERDUE if minutes_remaining<0, "
    "DUE_SOON if 0<=minutes_remaining<=60, TODAY if 61..1440, "
    "SCHEDULED if >1440. Input types are int and bool. "
    "Use simple conditions, direct return statements, and string literals. "
    "No company/institution/customer data. Never claim tests were run."
)
TRUSTED_TESTS = '''"""Independent expected behavior for a model-authored implementation."""
import unittest
from deadline_priority_w39 import deadline_priority

class DeadlinePolicyAcceptance(unittest.TestCase):
    def test_blocked_wins_over_late(self):
        self.assertEqual(deadline_priority(-100, True), "BLOCKED")
    def test_blocked_wins_over_distant(self):
        self.assertEqual(deadline_priority(5000, True), "BLOCKED")
    def test_overdue_negative_one(self):
        self.assertEqual(deadline_priority(-1, False), "OVERDUE")
    def test_overdue_negative_large(self):
        self.assertEqual(deadline_priority(-100000, False), "OVERDUE")
    def test_zero_due_soon(self):
        self.assertEqual(deadline_priority(0, False), "DUE_SOON")
    def test_sixty_due_soon(self):
        self.assertEqual(deadline_priority(60, False), "DUE_SOON")
    def test_sixty_one_today(self):
        self.assertEqual(deadline_priority(61, False), "TODAY")
    def test_one_day_today(self):
        self.assertEqual(deadline_priority(1440, False), "TODAY")
    def test_day_plus_one_scheduled(self):
        self.assertEqual(deadline_priority(1441, False), "SCHEDULED")
    def test_distant_scheduled(self):
        self.assertEqual(deadline_priority(999999, False), "SCHEDULED")
    def test_same_inputs_deterministic(self):
        self.assertEqual(deadline_priority(59, False), deadline_priority(59, False))

if __name__ == "__main__":
    unittest.main()
'''
FIXTURE_LABEL = "SYNTHETIC_FIXTURE_NOT_AI"
LIVE_LABEL = "LIVE_OLLAMA_INFERENCE"
ALLOWED_TESTS = re.findall(r"    def (test_[a-z0-9_]+)\(", TRUSTED_TESTS)


def _sha(raw):
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def validate_code(code):
    """Constrain model authored source; never run/eval/exec it on host."""
    if (not isinstance(code, str) or len(code.encode("utf-8")) > MAX_SOURCE
            or not 60 <= len(code) or "\x00" in code):
        raise ValueError("Invalid generated source bounds")
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        raise ValueError("Model source is not valid Python") from None
    if (len(tree.body) != 1 or not isinstance(tree.body[0], ast.FunctionDef)
            or tree.body[0].name != "deadline_priority"):
        raise ValueError("Model must author exactly one policy function")
    fn = tree.body[0]
    args = fn.args
    if (fn.decorator_list or args.posonlyargs or args.kwonlyargs or args.vararg
            or args.kwarg or args.defaults or args.kw_defaults
            or len(args.args) != 2
            or [(a.arg, getattr(a.annotation, "id", None)) for a in args.args]
               != [("minutes_remaining", "int"), ("has_blocker", "bool")]
            or not isinstance(fn.returns, ast.Name) or fn.returns.id != "str"):
        raise ValueError("Function signature or decorators not authorized")
    if len(list(ast.walk(tree))) > 180:
        raise ValueError("Over-complex policy AST")
    names = {"minutes_remaining", "has_blocker", "int", "bool", "str"}
    for node in ast.walk(tree):
        if not isinstance(node, SAFE_AST):
            raise ValueError("Unsafe code AST node")
        if isinstance(node, ast.Name) and node.id not in names:
            raise ValueError("Unapproved identifier in model source")
        if isinstance(node, ast.Constant):
            if type(node.value) is str and node.value not in VALID_STATES:
                raise ValueError("Unapproved model string in source")
            if type(node.value) not in (str, int, bool, type(None)):
                raise ValueError("Unsafe model constant")
    if not any(isinstance(n, ast.Return) for n in ast.walk(fn)):
        raise ValueError("Missing explicit return")
    return code if code.endswith("\n") else code + "\n"


def parse_candidate(raw):
    if isinstance(raw, str):
        if len(raw.encode("utf-8")) > MAX_SOURCE + 600:
            raise ValueError("Oversized model envelope")
        value = json.loads(raw, object_pairs_hook=no_duplicates)
    else:
        value = raw
    if (not isinstance(value, dict)
            or set(value) != {"task_id", "path", "code", "requires_human_review"}
            or value["task_id"] != TASK_ID
            or value["path"] != TARGET_PATH
            or value["requires_human_review"] is not True):
        raise ValueError("Wrong model task/path/review contract")
    return validate_code(value["code"])


def ensure_output(root):
    path = Path(root)
    runner = os.environ.get("RUNNER_TEMP")
    if (not runner or not Path(runner).is_absolute()
            or not path.is_absolute() or not path.is_dir()
            or path.is_symlink() or
            Path(runner).resolve() not in path.resolve().parents
            or any(path.iterdir())):
        raise ValueError("Only a new empty directory below RUNNER_TEMP is accepted")
    return path


def docker_verify(source, folder, *, runner=subprocess.run):
    """Sandbox source; never call source under host Python.

    The runner must already have explicitly pulled the fixed Docker image.
    No network, host secrets or runtime credentials are passed.
    """
    code = validate_code(source)
    folder = Path(folder)
    if not folder.is_absolute() or not folder.is_dir() or folder.is_symlink():
        raise ValueError("Unsafe staging directory")
    source_file = folder / SOURCE_NAME
    test_file = folder / "test_deadline_w39.py"
    if source_file.exists() or test_file.exists():
        raise ValueError("Refusing to overwrite an existing staging file")
    source_file.write_text(code, encoding="utf-8")
    test_file.write_text(TRUSTED_TESTS, encoding="utf-8")
    source_file.chmod(0o644)
    test_file.chmod(0o644)
    command = [
        "docker", "run", "--rm", "--pull=never",
        "--network=none", "--read-only",
        "--cap-drop=ALL", "--security-opt=no-new-privileges",
        "--pids-limit=32", "--memory=256m", "--memory-swap=256m",
        "--cpus=1", "--user=65534:65534",
        "--tmpfs=/tmp:rw,nosuid,noexec,size=16m",
        "--mount", f"type=bind,src={folder},dst=/work,readonly",
        "--workdir=/work", "--entrypoint=python",
        DOCKER_IMAGE, "-I", "-B", "-c",
        ("import sys,unittest;sys.path.insert(0,'/work');"
         "suite=unittest.defaultTestLoader.loadTestsFromName('test_deadline_w39');"
         "result=unittest.TextTestRunner(verbosity=2).run(suite);"
         "sys.exit(0 if result.wasSuccessful() else 1)")
    ]
    try:
        run = runner(command, capture_output=True, timeout=45, text=True,
                     check=False)
        result = {"success": run.returncode == 0,
                  "sandbox_used": True, "sandbox_network_disabled": True,
                  "sandbox_git_credentials": False}
        text = (run.stdout or "") + "\n" + (run.stderr or "")
        # Feedback uses only trusted unittest function identifiers, never
        # arbitrary model text, shell output, stack traces or URLs.
        failed = [name for name in ALLOWED_TESTS
                  if re.search(r"(?m)^" + name +
                               r" \(.*\) \.\.\. (?:FAIL|ERROR)\s*$", text)]
        result["failed_cases"] = failed or (
            ["unknown_test_or_sandbox_failure"] if run.returncode else [])
        return result
    finally:
        for filepath in (source_file, test_file):
            if filepath.exists():
                filepath.unlink()


def run_pipeline(output, *, fixture=None, model=None,
                 transport=None, sandbox=docker_verify):
    """Stage only a verified candidate; never write the source into Git."""
    dest = ensure_output(output)
    if (fixture is None) == (model is None):
        raise ValueError("Choose exactly one fixture OR live model")
    if fixture is not None:
        if os.environ.get("EDU_W39_FIXTURE_ONLY") != "1":
            raise ValueError("Fixture must be explicitly tagged non-AI")
        origin = FIXTURE_LABEL
        source = parse_candidate(fixture)
        calls = 0
    else:
        if (os.environ.get("EDU_AUTOPILOT_ENABLE") != "1"
                or os.environ.get("EDU_W39_MODEL_CODE_ENABLE") != "1"
                or os.environ.get("EDU_W39_FIXTURE_ONLY") == "1"):
            raise ValueError("Live model coding opt-in required")
        if not isinstance(model, str) or not re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9_.:-]{1,100}", model):
            raise ValueError("Unsafe model")
        tags = local_ollama("/api/tags")
        models = tags.get("models") if isinstance(tags, dict) else None
        if (not isinstance(models, list) or
                not any(isinstance(m, dict) and m.get("name") == model
                        and type(m.get("size")) is int and
                        0 < m["size"] <= MAX_MODEL_BYTES
                        for m in models)):
            raise ValueError("Requested small local model not installed")
        origin = LIVE_LABEL
        transport = transport or stream_generate
        calls = 0
        source = None
    errors = []
    for attempt in range(MAX_CALLS):
        if origin == LIVE_LABEL:
            if calls and not errors:
                raise ValueError("No trusted failure feedback")
            prompt = PROMPT + (
                "\nTests that failed on previous attempt: " + ", ".join(errors)
                if errors else "")
            payload = {
                "model": model, "prompt": prompt, "format": "json",
                "stream": True, "keep_alive": 0,
                "options": {"temperature": 0.1, "num_predict": 1100,
                            "num_ctx": 2048, "num_thread": 2, "num_gpu": 0}
            }
            calls += 1
            response = transport(payload)
            if not isinstance(response, dict):
                raise ValueError("Invalid streaming model envelope")
            source = parse_candidate(response.get("response"))
        source = validate_code(source)
        from tempfile import TemporaryDirectory
        with TemporaryDirectory(prefix="w39-sandbox-stage-") as tmp:
            verdict = sandbox(source, Path(tmp))
        if verdict.get("success") is True and verdict.get("sandbox_used") is True:
            break
        if origin == FIXTURE_LABEL:
            raise ValueError("Fixture candidate failed isolated tests")
        errors = verdict.get("failed_cases") or ["unknown_test_or_sandbox_failure"]
        if attempt == MAX_CALLS-1:
            raise ValueError("Two model candidate attempts did not pass sandbox")
    source_file = dest / SOURCE_NAME
    source_file.write_text(source, encoding="utf-8")
    source_file.chmod(0o644)
    receipt = {
        "phase": "W39", "task_id": TASK_ID,
        "target_path": TARGET_PATH, "origin": origin,
        "model_calls": calls, "sandbox_verified": True,
        "sandbox_network_disabled": True, "sandbox_git_credentials": False,
        "candidate_sha256": _sha(source), "trusted_tests": len(ALLOWED_TESTS),
        "human_review_required": True, "git_writes": False,
        "auto_merged": False, "production_accepted": False
    }
    (dest / "receipt.json").write_text(json.dumps(receipt, sort_keys=True),
                                      encoding="utf-8")
    return receipt


def verify_artifact(folder, *, require_live=False, sandbox=docker_verify):
    """Publisher re-verifies exact bytes and sandbox tests, not producer claims."""
    folder = Path(folder)
    source_file, receipt_file = folder / SOURCE_NAME, folder / "receipt.json"
    if (folder.is_symlink() or source_file.is_symlink()
            or receipt_file.is_symlink()
            or source_file.stat().st_size > MAX_SOURCE
            or receipt_file.stat().st_size > 2048):
        raise ValueError("Unsafe artifact files")
    source = source_file.read_text(encoding="utf-8")
    receipt = json.loads(receipt_file.read_text(encoding="utf-8"),
                         object_pairs_hook=no_duplicates)
    if (not isinstance(receipt, dict)
            or receipt.get("target_path") != TARGET_PATH
            or receipt.get("candidate_sha256") != _sha(source)
            or receipt.get("origin") not in (FIXTURE_LABEL, LIVE_LABEL)
            or (require_live and (receipt["origin"] != LIVE_LABEL or
                                  not 1 <= receipt.get("model_calls", 0) <= 2))
            or receipt.get("human_review_required") is not True
            or receipt.get("git_writes") is not False
            or receipt.get("auto_merged") is not False):
        raise ValueError("Publisher candidate identity or real-model claim invalid")
    validate_code(source)
    from tempfile import TemporaryDirectory
    with TemporaryDirectory(prefix="w39-independent-verify-") as root:
        verdict = sandbox(source, Path(root))
    if not (verdict.get("success") is True and
            verdict.get("sandbox_used") is True):
        raise ValueError("Publisher sandbox tests failed")
    return {"path": TARGET_PATH, "sha256": _sha(source),
            "publisher_sandbox_verified": True,
            "human_review_required": True, "auto_merge": False}


def main(argv=None):
    p = argparse.ArgumentParser(description="W39 bounded Ollama-authored source + Docker tests")
    p.add_argument("--output-dir")
    p.add_argument("--fixture")
    p.add_argument("--model")
    p.add_argument("--verify-artifact")
    p.add_argument("--require-live", action="store_true")
    p.add_argument("--execute", action="store_true")
    args = p.parse_args(argv)
    if not args.execute:
        print(json.dumps({"phase": "W39", "status": "DRY_RUN_NO_MODEL_OR_DOCKER",
                          "model_calls": 0, "git_writes": False}))
        return 0
    try:
        if args.verify_artifact:
            receipt = verify_artifact(args.verify_artifact,
                                      require_live=args.require_live)
        elif args.fixture:
            data = Path(args.fixture).read_text(encoding="utf-8")
            receipt = run_pipeline(args.output_dir, fixture=data)
        else:
            receipt = run_pipeline(args.output_dir, model=args.model)
        print(json.dumps(receipt, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, KeyError, UnicodeError,
            urllib.error.URLError, subprocess.SubprocessError):
        print("W39_CODE_CANDIDATE_FAIL_CLOSED", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
