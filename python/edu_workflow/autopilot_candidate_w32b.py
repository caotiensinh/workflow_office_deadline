"""W32B: compile allowlisted *declarative* synthetic QA proposals to trusted tests.

A model may select named scenarios; it may NOT supply executable source code,
commands, file paths or free-form assertions. No network, Git, subprocess or
model invocation happens in this module. Generated source requires review.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from .autopilot_plan_w27 import load_backlog, reject_duplicates

INPUT_PATH = Path("autopilot/w32b_qa_candidate.json")
OUTPUT_PATH = Path("tests/test_autopilot_generated_w32b.py")
MAGIC = "# W32B_TRUSTED_TEMPLATE_GENERATED_DO_NOT_HAND_EDIT"
MAX_SPEC_BYTES = 4096
SCENARIOS = frozenset({
    "valid_qa_proposal", "duplicate_task_ids", "blocked_without_approval",
    "unknown_domain", "unexpected_field", "duplicate_json_keys",
})
BODIES = {
    "valid_qa_proposal": (
        "        self.assertEqual(len(load_backlog(self.save([self.task()]))), 1)"
    ),
    "duplicate_task_ids": (
        "        with self.assertRaises(ValueError):\n"
        "            load_backlog(self.save([self.task(), self.task()]))"
    ),
    "blocked_without_approval": (
        "        task = self.task()\n"
        "        task['kind'] = 'BLOCKED_EXTERNAL'\n"
        "        with self.assertRaises(ValueError):\n"
        "            load_backlog(self.save([task]))"
    ),
    "unknown_domain": (
        "        task = self.task()\n"
        "        task['domain'] = 'untrusted-network-ops'\n"
        "        with self.assertRaises(ValueError):\n"
        "            load_backlog(self.save([task]))"
    ),
    "unexpected_field": (
        "        task = self.task()\n"
        "        task['real_outlook_access'] = True\n"
        "        with self.assertRaises(ValueError):\n"
        "            load_backlog(self.save([task]))"
    ),
    "duplicate_json_keys": (
        "        path = self.root / 'bad.json'\n"
        "        path.write_text('{\"schema\":1,\"schema\":1,\"tasks\":[]}', encoding='utf-8')\n"
        "        with self.assertRaises(ValueError):\n"
        "            load_backlog(path)"
    ),
}
HEADER = '''# W32B_TRUSTED_TEMPLATE_GENERATED_DO_NOT_HAND_EDIT
"""Synthetic backlog policy regressions generated from a strict scenario enum.

All executable lines come from the trusted repository generator, NOT model
text. No employee data, Git writes, network, shell, auto-merge or approval.
"""
import json
import tempfile
import unittest
from pathlib import Path
from edu_workflow.autopilot_plan_w27 import load_backlog


class W32BGeneratedBacklogContract(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def task(self):
        return {
            "id": "W27-QA",
            "title": "Propose synthetic QA cases",
            "domain": "qa-security",
            "kind": "AUTO_PROPOSAL",
            "approval_required": False,
            "description": "Review fictional test cases for safety and audit",
        }

    def save(self, tasks):
        path = self.root / "cases.json"
        path.write_text(json.dumps({"schema": 1, "tasks": tasks}),
                        encoding="utf-8")
        return path

'''


def load_spec(path):
    src = Path(path)
    if src.is_symlink() or not src.is_file() or not 0 < src.stat().st_size <= MAX_SPEC_BYTES:
        raise ValueError("Missing, linked or oversized candidate")
    data = json.loads(src.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicates)
    if not isinstance(data, dict) or set(data) != {"schema", "task_id", "scenarios"}:
        raise ValueError("Untrusted candidate shape")
    if type(data["schema"]) is not int or data["schema"] != 1:
        raise ValueError("Unknown candidate schema")
    if data["task_id"] != "W27-QA":
        raise ValueError("Only approved synthetic QA proposal can select tests")
    cases = data["scenarios"]
    if not isinstance(cases, list) or not 1 <= len(cases) <= len(SCENARIOS):
        raise ValueError("Invalid test case count")
    if any(not isinstance(c, str) or c not in SCENARIOS for c in cases):
        raise ValueError("Unknown test case selection")
    if len(set(cases)) != len(cases):
        raise ValueError("Duplicate test case")
    return tuple(sorted(cases))


def render(cases):
    """No user-controlled text is interpolated into any executable line."""
    if (not isinstance(cases, tuple) or not cases or len(set(cases)) != len(cases)
            or any(type(c) is not str or c not in SCENARIOS for c in cases)):
        raise ValueError("Invalid trusted scenario selection")
    return HEADER + "".join(
        "    def test_" + name + "(self):\n" + BODIES[name] + "\n\n"
        for name in cases
    ) + "\nif __name__ == '__main__':\n    unittest.main()\n"


def safe_root(root):
    path = Path(root)
    if path.is_symlink() or not path.is_dir():
        raise ValueError("Unsafe checkout root")
    root = path.resolve()
    for directory in ("autopilot", "tests"):
        item = root / directory
        if item.is_symlink() or not item.is_dir():
            raise ValueError("Missing or linked repository directory")
    return root


def prepare(repo_root, *, write=False, verify=False):
    if write and verify:
        raise ValueError("write and verify are mutually exclusive")
    root = safe_root(repo_root)
    backlog = root / "autopilot/w27_backlog.json"
    spec = root / INPUT_PATH
    if backlog.is_symlink() or spec.is_symlink():
        raise ValueError("No linked input files")
    tasks = load_backlog(backlog)
    matches = [t for t in tasks if t["id"] == "W27-QA"]
    if (len(matches) != 1 or matches[0]["domain"] != "qa-security"
            or matches[0]["kind"] != "AUTO_PROPOSAL"
            or matches[0]["approval_required"] is not False):
        raise ValueError("QA candidate has no authorized synthetic task")
    cases = load_spec(spec)
    content = render(cases)
    output = root / OUTPUT_PATH
    if output.is_symlink() or (output.exists() and not output.is_file()):
        raise ValueError("Linked or nonregular generated test forbidden")
    prior = output.read_text(encoding="utf-8") if output.exists() else None
    if prior is not None and prior != content:
        # Refuse tampered OR human-edited existing tests. No overwrite.
        raise ValueError("Existing test differs; human reconciliation required")
    if verify:
        if prior != content:
            raise ValueError("Generated candidate not present or changed")
        status = "EXACT_RENDER_VERIFIED_NOT_GITHUB_CI"
    elif write:
        if os.environ.get("EDU_AUTOPILOT_TEST_STAGE") != "1":
            raise ValueError("Explicit staging opt-in required")
        if prior is None:
            with output.open("x", encoding="utf-8") as stream:
                stream.write(content)
        status = "TRUSTED_TEST_STAGED_NOT_PR_OR_CI"
    else:
        status = "DRY_RUN_NO_FILES_CHANGED"
    return {"phase": "W32B", "status": status, "task_id": "W27-QA",
            "scenarios": list(cases), "scenario_count": len(cases),
            "destination": str(OUTPUT_PATH), "untrusted_code_executed": False,
            "model_calls": 0, "git_writes": False, "approved_for_merge": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Strict synthetic QA candidate compiler")
    parser.add_argument("--repo-root", default=".")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--write", action="store_true")
    group.add_argument("--verify", action="store_true")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(prepare(args.repo_root, write=args.write, verify=args.verify),
                         sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, UnicodeError, KeyError):
        print("W32B_FAIL_CLOSED_UNTRUSTED_TEST_CANDIDATE", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
