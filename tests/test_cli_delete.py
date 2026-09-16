"""Sprint 3: CLI `delete` command tests."""

from __future__ import annotations

import unittest

from tests.cli_support import CLITestMixin


class DeleteCLITests(CLITestMixin, unittest.TestCase):
    def setUp(self) -> None:
        self.data_dir = self.make_data_dir()
        self.run_cli(["category", "add"], inputs=["food"], data_dir=self.data_dir)
        self.run_cli(
            ["add"], inputs=["2026-09-01", "expense", "food", "1000", "", ""], data_dir=self.data_dir
        )

    def test_success(self) -> None:
        code, out, err = self.run_cli(["delete", "--id", "1"], data_dir=self.data_dir)
        self.assertEqual(code, 0)
        self.assertIn("[삭제 완료]", out)
        code, out, err = self.run_cli(["list"], data_dir=self.data_dir)
        self.assertNotIn("TX-000001", out)

    def test_missing_id(self) -> None:
        code, out, err = self.run_cli(["delete", "--id", "999"], data_dir=self.data_dir)
        self.assertEqual(code, 1)
        self.assertIn("[오류]", err)
        self.assertIn("[힌트]", err)


if __name__ == "__main__":
    unittest.main()
