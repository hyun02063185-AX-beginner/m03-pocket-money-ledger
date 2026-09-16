"""Sprint 4: LedgerService.export_csv() tests."""

from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from ledger.errors import ValidationError
from tests.support import ServiceTestMixin


class ExportCsvTests(ServiceTestMixin, unittest.TestCase):
    def setUp(self) -> None:
        self.service = self.make_service()
        self.service.add_category("food")
        self.service.add_category("salary")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out_dir = Path(self.tmp.name)

        self.service.add_transaction("expense", "2026-08-31", "food", 100, "aug", [])
        self.service.add_transaction("expense", "2026-09-01", "food", 1000, "lunch", ["meal", "work"])
        self.service.add_transaction("income", "2026-09-15", "salary", 500000, "점심", [])
        self.service.add_transaction("expense", "2026-09-30", "food", 2000, "", [])
        self.service.add_transaction("expense", "2026-10-01", "food", 300, "oct", [])

    def _read_rows(self, path: Path) -> list[dict]:
        with path.open("r", encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))

    def test_month_export(self) -> None:
        out = self.out_dir / "out.csv"
        count = self.service.export_csv(out, month="2026-09")
        self.assertEqual(count, 3)
        rows = self._read_rows(out)
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(row["date"].startswith("2026-09") for row in rows))

    def test_date_range_export(self) -> None:
        out = self.out_dir / "out.csv"
        count = self.service.export_csv(out, from_date="2026-09-01", to_date="2026-09-15")
        self.assertEqual(count, 2)

    def test_inclusive_boundaries(self) -> None:
        out = self.out_dir / "out.csv"
        # exactly on both boundaries
        count = self.service.export_csv(out, from_date="2026-09-01", to_date="2026-09-30")
        self.assertEqual(count, 3)

    def test_header_exists_and_id_column_absent(self) -> None:
        out = self.out_dir / "out.csv"
        self.service.export_csv(out, month="2026-09")
        with out.open("r", encoding="utf-8", newline="") as f:
            header = next(csv.reader(f))
        self.assertEqual(header, ["date", "type", "category", "amount", "memo", "tags"])

    def test_memo_and_tags_encoded(self) -> None:
        out = self.out_dir / "out.csv"
        self.service.export_csv(out, month="2026-09")
        rows = self._read_rows(out)
        lunch_row = next(r for r in rows if r["memo"] == "lunch")
        self.assertEqual(lunch_row["tags"], "meal,work")

    def test_utf8_content(self) -> None:
        out = self.out_dir / "out.csv"
        self.service.export_csv(out, month="2026-09")
        rows = self._read_rows(out)
        self.assertTrue(any(row["memo"] == "점심" for row in rows))

    def test_only_matching_records_exported(self) -> None:
        out = self.out_dir / "out.csv"
        self.service.export_csv(out, month="2026-09")
        rows = self._read_rows(out)
        self.assertFalse(any(row["memo"] == "aug" for row in rows))
        self.assertFalse(any(row["memo"] == "oct" for row in rows))

    def test_zero_matches_still_produces_header(self) -> None:
        out = self.out_dir / "out.csv"
        count = self.service.export_csv(out, month="2020-01")
        self.assertEqual(count, 0)
        with out.open("r", encoding="utf-8", newline="") as f:
            header = next(csv.reader(f))
        self.assertEqual(header, ["date", "type", "category", "amount", "memo", "tags"])
        rows = self._read_rows(out)
        self.assertEqual(rows, [])

    def test_missing_period_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            self.service.export_csv(self.out_dir / "out.csv")

    def test_from_only_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            self.service.export_csv(self.out_dir / "out.csv", from_date="2026-09-01")

    def test_to_only_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            self.service.export_csv(self.out_dir / "out.csv", to_date="2026-09-30")

    def test_reversed_range_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            self.service.export_csv(
                self.out_dir / "out.csv", from_date="2026-09-30", to_date="2026-09-01"
            )

    def test_month_and_range_combination_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            self.service.export_csv(
                self.out_dir / "out.csv",
                month="2026-09",
                from_date="2026-09-01",
                to_date="2026-09-30",
            )


if __name__ == "__main__":
    unittest.main()
