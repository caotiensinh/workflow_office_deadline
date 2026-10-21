"""W31D offline safety regressions; they do not claim CI dispatch happened."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGETS = ["ci.yml", "windows-e2e.yml", "w4-desktop.yml", "w5-desktop.yml"]
WF = (ROOT / ".github/workflows/w31d-trusted-ci-dispatch.yml").read_text(encoding="utf-8")


class W31DTrustedDispatchTests(unittest.TestCase):
    def test_four_workflows_are_dispatchable(self):
        for name in TARGETS:
            with self.subTest(workflow=name):
                y = (ROOT / ".github/workflows" / name).read_text(encoding="utf-8")
                self.assertIn("  workflow_dispatch:", y)
                self.assertIn("  pull_request:", y)
                self.assertIn("    branches: [main]", y)

    def test_four_workflows_have_read_only_token(self):
        for name in TARGETS:
            with self.subTest(workflow=name):
                y = (ROOT / ".github/workflows" / name).read_text(encoding="utf-8")
                self.assertIn("permissions:\n  contents: read", y)
                self.assertNotIn("secrets.", y)

    def test_publisher_exact_repo_main_and_optin(self):
        for token in ("github.ref == 'refs/heads/main'", "github.repository == 'caotiensinh/workflow_office_deadline'",
                      "vars.EDU_AUTOPILOT_DOC_PR_LIVE == 'true'"):
            self.assertIn(token, WF)

    def test_branch_preview_does_not_publish(self):
        self.assertIn("feat/w31d-trusted-exact-sha-ci-dispatch", WF)
        self.assertIn("if: ${{ github.event_name == 'push' && github.ref == 'refs/heads/main'", WF)

    def test_single_fictional_document_path(self):
        self.assertIn("docs/autopilot-proposals/W31D_TRUSTED_CI_DISPATCH.md", WF)
        self.assertIn('test "$(git diff --cached --name-only | wc -l)" -eq 1', WF)
        self.assertIn('test "$staged" = "$path"', WF)

    def test_four_ci_dispatch_requests(self):
        self.assertIn("for workflow in ci.yml windows-e2e.yml w4-desktop.yml w5-desktop.yml;", WF)
        self.assertIn('gh workflow run "$workflow" --repo "$GITHUB_REPOSITORY" --ref "$branch"', WF)

    def test_never_auto_merge_or_push_main(self):
        self.assertNotIn("gh pr merge", WF)
        self.assertNotIn("git push origin main", WF)
        self.assertIn("review required", WF.lower().replace("-", " "))
        self.assertIn("CI_PASSED_NOT_MERGED", WF)

    def test_dispatch_is_after_successful_pr_creation(self):
        self.assertLess(WF.index("gh pr create"), WF.index("gh workflow run"))
        self.assertIn("W31D_BOT_PR_CREATION_FAILED_CLEANUP_ATTEMPTED", WF)
        self.assertIn('git push origin --delete "$branch"', WF)


if __name__ == "__main__":
    unittest.main()
