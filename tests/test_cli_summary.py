"""Sprint 3: CLI `summary` command tests."""

from __future__ import annotations

import unittest

from tests.cli_support import CLITestMixin


class SummaryCLITests(CLITestMixin, unittest.TestCase):
    def setUp(self) -> None:
        self.data_dir = self.make_data_dir()
        self.run_cli(["category", "add"], inputs=["food"], data_dir=self.data_dir)

    def test_month_required(self) -> None:
        with self.assertRaises(SystemExit) as cm:
            self.run_cli(["summary"], data_dir=self.data_dir)
        self.assertEqual(cm.exception.code, 2)

    def test_no_data(self) -> None:
        code, out, err = self.run_cli(["summary", "--month", "2026-01"], data_dir=self.data_dir)
        self.assertEqual(code, 0)
        self.assertIn("데이터 없음", out)

    def test_normal_summary(self) -> None:
        self.run_cli(
            ["add"],
            inputs=["2026-09-01", "income", "food", "100000", "", ""],
            data_dir=self.data_dir,
        )
        self.run_cli(
            ["add"],
            inputs=["2026-09-02", "expense", "food", "30000", "", ""],
            data_dir=self.data_dir,
        )
        code, out, err = self.run_cli(["summary", "--month", "2026-09"], data_dir=self.data_dir)
        self.assertEqual(code, 0)
        self.assertIn("총 수입: 100000", out)
        self.assertIn("총 지출: 30000", out)
        self.assertIn("잔액: 70000", out)

    def test_top_n(self) -> None:
        self.run_cli(["category", "add"], inputs=["transport"], data_dir=self.data_dir)
        self.run_cli(
            ["add"], inputs=["2026-09-01", "expense", "food", "1000", "", ""], data_dir=self.data_dir
        )
        self.run_cli(
            ["add"],
            inputs=["2026-09-02", "expense", "transport", "5000", "", ""],
            data_dir=self.data_dir,
        )
        code, out, err = self.run_cli(
            ["summary", "--month", "2026-09", "--top", "1"], data_dir=self.data_dir
        )
        self.assertIn("transport", out)
        self.assertNotIn("food:", out)

    def test_budget_usage(self) -> None:
        self.run_cli(
            ["budget", "set", "--month", "2026-09", "--amount", "10000"], data_dir=self.data_dir
        )
        self.run_cli(
            ["add"], inputs=["2026-09-01", "expense", "food", "5000", "", ""], data_dir=self.data_dir
        )
        code, out, err = self.run_cli(["summary", "--month", "2026-09"], data_dir=self.data_dir)
        self.assertIn("예산: 10000", out)
        self.assertIn("사용률: 50.0%", out)
        self.assertIn("예산 초과: 아니오", out)

    def test_budget_exceeded_warning(self) -> None:
        self.run_cli(
            ["budget", "set", "--month", "2026-09", "--amount", "1000"], data_dir=self.data_dir
        )
        self.run_cli(
            ["add"], inputs=["2026-09-01", "expense", "food", "5000", "", ""], data_dir=self.data_dir
        )
        code, out, err = self.run_cli(["summary", "--month", "2026-09"], data_dir=self.data_dir)
        self.assertIn("[경고]", out)


if __name__ == "__main__":
    unittest.main()
