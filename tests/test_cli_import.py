"""Sprint 4: CLI `import` command tests."""

from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from tests.cli_support import CLITestMixin

FULL_HEADER = ["date", "type", "category", "amount", "memo", "tags"]


def write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for row in rows:
            writer.writerow(row)


class ImportCLITests(CLITestMixin, unittest.TestCase):
    def setUp(self) -> None:
        self.data_dir = self.make_data_dir()
        self.run_cli(["category", "add"], inputs=["food"], data_dir=self.data_dir)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.csv_dir = Path(self.tmp.name)

    def test_import_success(self) -> None:
        path = self.csv_dir / "a.csv"
        write_csv(path, FULL_HEADER, [["2026-09-01", "expense", "food", "1000", "lunch", ""]])
        code, out, err = self.run_cli(["import", "--from", str(path)], data_dir=self.data_dir)
        self.assertEqual(code, 0)
        self.assertIn("[완료] imported=1, skipped=0", out)

    def test_import_with_skipped_rows_reports_each(self) -> None:
        path = self.csv_dir / "a.csv"
        write_csv(
            path,
            FULL_HEADER,
            [
                ["2026-09-01", "expense", "food", "1000", "", ""],
                ["2026-09-02", "expense", "nonexistent", "1000", "", ""],
                ["2026-09-03", "expense", "food", "-1", "", ""],
            ],
        )
        code, out, err = self.run_cli(["import", "--from", str(path)], data_dir=self.data_dir)
        self.assertEqual(code, 0)
        self.assertIn("[건너뜀] row=2:", out)
        self.assertIn("[건너뜀] row=3:", out)
        self.assertIn("[완료] imported=1, skipped=2", out)

    def test_import_verified_by_subsequent_list(self) -> None:
        path = self.csv_dir / "a.csv"
        write_csv(path, FULL_HEADER, [["2026-09-01", "expense", "food", "4500", "lunch", "work"]])
        self.run_cli(["import", "--from", str(path)], data_dir=self.data_dir)
        code, out, err = self.run_cli(["list"], data_dir=self.data_dir)
        self.assertIn("4500", out)
        self.assertIn("tags: work", out)

    def test_missing_source_file(self) -> None:
        code, out, err = self.run_cli(
            ["import", "--from", str(self.csv_dir / "nope.csv")], data_dir=self.data_dir
        )
        self.assertEqual(code, 1)
        self.assertNotIn("Traceback", err)
        self.assertIn("[오류]", err)
        self.assertIn("[힌트]", err)

    def test_missing_header_column(self) -> None:
        path = self.csv_dir / "a.csv"
        write_csv(path, ["date", "type", "category", "amount"], [["2026-09-01", "expense", "food", "1000"]])
        code, out, err = self.run_cli(["import", "--from", str(path)], data_dir=self.data_dir)
        self.assertEqual(code, 1)
        self.assertNotIn("Traceback", err)
        self.assertIn("[오류]", err)
        self.assertIn("[힌트]", err)


if __name__ == "__main__":
    unittest.main()
