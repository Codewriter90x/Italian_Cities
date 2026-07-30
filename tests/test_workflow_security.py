from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from check_workflow_pins import find_unpinned_actions  # noqa: E402


class WorkflowSecurityTests(unittest.TestCase):
    def test_repository_actions_are_immutably_pinned(self) -> None:
        self.assertEqual([], find_unpinned_actions())

    def test_tag_and_branch_action_references_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workflows = Path(directory)
            (workflows / "unsafe.yml").write_text(
                "steps:\n"
                "  - uses: actions/checkout@v7\n"
                "  - uses: owner/action@main\n",
                encoding="utf-8",
            )
            errors = find_unpinned_actions(workflows)
        self.assertEqual(2, len(errors))
        self.assertTrue(all("40-character commit SHA" in item for item in errors))

    def test_local_actions_are_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workflows = Path(directory)
            (workflows / "local.yaml").write_text(
                "steps:\n  - uses: ./.github/actions/check\n",
                encoding="utf-8",
            )
            self.assertEqual([], find_unpinned_actions(workflows))


if __name__ == "__main__":
    unittest.main()
