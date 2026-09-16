"""Sprint 4: CLI `export` command tests."""

from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from tests.cli_support import CLITestMixin


class ExportCLITests(CLITestMixin, unittest.TestCase):
    def setUp(self) -> None:
        self.data_dir = self.make_data_dir()
        self.run_cli(["category", "add"], inputs=["food"], data_dir=self.data_dir)
        self.run_cli(
            ["add"],
            inputs=["2026-09-01", "expense", "food", "1000", "lunch", "work"],
            data_dir=self.data_dir,
        )
        self.run_cli(
            ["add"],
            inputs=["2026-08-01", "expense", "food", "500", "old", ""],
            data_dir=self.data_dir,
        )
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out_dir = Path(self.tmp.name)

    def test_month_export_success(self) -> None:
        out_path = self.out_dir / "out.csv"
        code, out, err = self.run_cli(
            ["export", "--out", str(out_path), "--month", "2026-09"], data_dir=self.data_dir
        )
        self.assertEqual(code, 0)
        self.assertIn(f"[완료] {out_path} (1 records)", out)
        with out_path.open("r", encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["memo"], "lunch")

    def test_date_range_export_success(self) -> None:
        out_path = self.out_dir / "out.csv"
        code, out, err = self.run_cli(
            ["export", "--out", str(out_path), "--from", "2026-08-01", "--to", "2026-09-30"],
            data_dir=self.data_dir,
        )
        self.assertEqual(code, 0)
        self.assertIn("(2 records)", out)

    def test_export_without_filter_rejected(self) -> None:
        out_path = self.out_dir / "out.csv"
        code, out, err = self.run_cli(["export", "--out", str(out_path)], data_dir=self.data_dir)
        self.assertEqual(code, 1)
        self.assertNotIn("Traceback", err)
        self.assertIn("[오류]", err)
        self.assertIn("[힌트]", err)

    def test_export_from_only_rejected(self) -> None:
        out_path = self.out_dir / "out.csv"
        code, out, err = self.run_cli(
            ["export", "--out", str(out_path), "--from", "2026-09-01"], data_dir=self.data_dir
        )
        self.assertEqual(code, 1)
        self.assertNotIn("Traceback", err)


if __name__ == "__main__":
    unittest.main()
