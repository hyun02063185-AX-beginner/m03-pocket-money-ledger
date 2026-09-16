"""Sprint 3: CLI `update` command tests."""

from __future__ import annotations

import unittest

from tests.cli_support import CLITestMixin


class UpdateCLITests(CLITestMixin, unittest.TestCase):
    def setUp(self) -> None:
        self.data_dir = self.make_data_dir()
        self.run_cli(["category", "add"], inputs=["food"], data_dir=self.data_dir)
        self.run_cli(["category", "add"], inputs=["transport"], data_dir=self.data_dir)
        self.run_cli(
            ["add"],
            inputs=["2026-09-01", "expense", "food", "1000", "lunch", "work"],
            data_dir=self.data_dir,
        )

    def test_single_field(self) -> None:
        code, out, err = self.run_cli(
            ["update", "--id", "1", "--amount", "9999"], data_dir=self.data_dir
        )
        self.assertEqual(code, 0)
        code, out, err = self.run_cli(["list"], data_dir=self.data_dir)
        self.assertIn("9999", out)

    def test_multiple_fields(self) -> None:
        code, out, err = self.run_cli(
            ["update", "--id", "1", "--amount", "500", "--category", "transport"],
            data_dir=self.data_dir,
        )
        self.assertEqual(code, 0)
        code, out, err = self.run_cli(["list"], data_dir=self.data_dir)
        self.assertIn("transport", out)
        self.assertIn("500", out)

    def test_only_id_rejected(self) -> None:
        code, out, err = self.run_cli(["update", "--id", "1"], data_dir=self.data_dir)
        self.assertEqual(code, 1)
        self.assertIn("[오류]", err)
        self.assertIn("[힌트]", err)

    def test_clear_memo(self) -> None:
        code, out, err = self.run_cli(["update", "--id", "1", "--memo", ""], data_dir=self.data_dir)
        self.assertEqual(code, 0)
        code, out, err = self.run_cli(["list"], data_dir=self.data_dir)
        self.assertNotIn("lunch", out)

    def test_clear_tags(self) -> None:
        code, out, err = self.run_cli(["update", "--id", "1", "--tags", ""], data_dir=self.data_dir)
        self.assertEqual(code, 0)
        code, out, err = self.run_cli(["list"], data_dir=self.data_dir)
        self.assertNotIn("tags:", out)

    def test_invalid_new_category(self) -> None:
        code, out, err = self.run_cli(
            ["update", "--id", "1", "--category", "nonexistent"], data_dir=self.data_dir
        )
        self.assertEqual(code, 1)
        self.assertIn("[오류]", err)

    def test_missing_transaction(self) -> None:
        code, out, err = self.run_cli(
            ["update", "--id", "999", "--amount", "1"], data_dir=self.data_dir
        )
        self.assertEqual(code, 1)
        self.assertIn("[오류]", err)
        self.assertIn("[힌트]", err)


if __name__ == "__main__":
    unittest.main()
