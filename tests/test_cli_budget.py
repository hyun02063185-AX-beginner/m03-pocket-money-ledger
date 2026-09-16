"""Sprint 3: CLI `budget set` command tests."""

from __future__ import annotations

import unittest

from tests.cli_support import CLITestMixin


class BudgetCLITests(CLITestMixin, unittest.TestCase):
    def setUp(self) -> None:
        self.data_dir = self.make_data_dir()

    def test_set_success(self) -> None:
        code, out, err = self.run_cli(
            ["budget", "set", "--month", "2026-09", "--amount", "500000"], data_dir=self.data_dir
        )
        self.assertEqual(code, 0)
        self.assertIn("[저장 완료]", out)
        self.assertIn("2026-09", out)
        self.assertIn("500000", out)

    def test_invalid_month(self) -> None:
        code, out, err = self.run_cli(
            ["budget", "set", "--month", "2026-9", "--amount", "500000"], data_dir=self.data_dir
        )
        self.assertEqual(code, 1)
        self.assertIn("[오류]", err)
        self.assertIn("[힌트]", err)

    def test_invalid_amount(self) -> None:
        code, out, err = self.run_cli(
            ["budget", "set", "--month", "2026-09", "--amount", "0"], data_dir=self.data_dir
        )
        self.assertEqual(code, 1)
        self.assertIn("[오류]", err)


if __name__ == "__main__":
    unittest.main()
