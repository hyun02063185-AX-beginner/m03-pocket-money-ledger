"""Sprint 3: CLI `category` command tests (interactive add/remove)."""

from __future__ import annotations

import unittest

from tests.cli_support import CLITestMixin


class CategoryCLITests(CLITestMixin, unittest.TestCase):
    def setUp(self) -> None:
        self.data_dir = self.make_data_dir()

    def test_add(self) -> None:
        code, out, err = self.run_cli(["category", "add"], inputs=["food"], data_dir=self.data_dir)
        self.assertEqual(code, 0)
        self.assertIn("[저장 완료]", out)

    def test_list_empty(self) -> None:
        code, out, err = self.run_cli(["category", "list"], data_dir=self.data_dir)
        self.assertEqual(code, 0)
        self.assertIn("[안내]", out)

    def test_list_populated(self) -> None:
        self.run_cli(["category", "add"], inputs=["food"], data_dir=self.data_dir)
        self.run_cli(["category", "add"], inputs=["transport"], data_dir=self.data_dir)
        code, out, err = self.run_cli(["category", "list"], data_dir=self.data_dir)
        self.assertIn("food", out)
        self.assertIn("transport", out)

    def test_remove_unused(self) -> None:
        self.run_cli(["category", "add"], inputs=["food"], data_dir=self.data_dir)
        code, out, err = self.run_cli(
            ["category", "remove"], inputs=["food"], data_dir=self.data_dir
        )
        self.assertEqual(code, 0)
        self.assertIn("[삭제 완료]", out)

    def test_remove_used_category_blocked(self) -> None:
        self.run_cli(["category", "add"], inputs=["food"], data_dir=self.data_dir)
        self.run_cli(
            ["add"], inputs=["2026-09-01", "expense", "food", "1000", "", ""], data_dir=self.data_dir
        )
        code, out, err = self.run_cli(
            ["category", "remove"], inputs=["food"], data_dir=self.data_dir
        )
        self.assertEqual(code, 1)
        self.assertIn("[오류]", err)
        self.assertIn("[힌트]", err)


if __name__ == "__main__":
    unittest.main()
