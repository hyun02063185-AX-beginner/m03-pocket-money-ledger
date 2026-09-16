"""Sprint 4: LedgerService.import_csv() tests."""

from __future__ import annotations

import csv
import datetime
import tempfile
import unittest
from pathlib import Path

from ledger.errors import CategoryNotFoundError, CSVFormatError, PersistenceError
from tests.support import ServiceTestMixin


def write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for row in rows:
            writer.writerow(row)


FULL_HEADER = ["date", "type", "category", "amount", "memo", "tags"]


class ImportCsvTests(ServiceTestMixin, unittest.TestCase):
    def setUp(self) -> None:
        self.service = self.make_service()
        self.service.add_category("food")
        self.service.add_category("salary")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.csv_dir = Path(self.tmp.name)

    def test_valid_one_row_import(self) -> None:
        path = self.csv_dir / "a.csv"
        write_csv(path, FULL_HEADER, [["2026-09-01", "expense", "food", "1000", "lunch", "work"]])
        result = self.service.import_csv(path)
        self.assertEqual(result.imported, 1)
        self.assertEqual(result.skipped, 0)
        self.assertEqual(result.errors, [])

    def test_multiple_valid_rows_import(self) -> None:
        path = self.csv_dir / "a.csv"
        write_csv(
            path,
            FULL_HEADER,
            [
                ["2026-09-01", "expense", "food", "1000", "", ""],
                ["2026-09-02", "income", "salary", "500000", "", ""],
                ["2026-09-03", "expense", "food", "2000", "", ""],
            ],
        )
        result = self.service.import_csv(path)
        self.assertEqual(result.imported, 3)
        self.assertEqual(result.skipped, 0)

    def test_generated_internal_ids(self) -> None:
        self.service.add_transaction("expense", "2026-09-01", "food", 100)  # id 1 already exists
        path = self.csv_dir / "a.csv"
        write_csv(path, FULL_HEADER, [["2026-09-02", "expense", "food", "200", "", ""]])
        self.service.import_csv(path)
        ids = {t.id for t in self.service.transactions.iter_all()}
        self.assertEqual(ids, {1, 2})

    def test_imported_records_persist_after_reload(self) -> None:
        path = self.csv_dir / "a.csv"
        write_csv(path, FULL_HEADER, [["2026-09-01", "expense", "food", "1000", "lunch", ""]])
        self.service.import_csv(path)
        reloaded = list(self.service.transactions.iter_all())
        self.assertEqual(len(reloaded), 1)
        self.assertEqual(reloaded[0].amount, 1000)

    def test_unknown_category_row_skipped(self) -> None:
        path = self.csv_dir / "a.csv"
        write_csv(path, FULL_HEADER, [["2026-09-01", "expense", "nonexistent", "1000", "", ""]])
        result = self.service.import_csv(path)
        self.assertEqual(result.imported, 0)
        self.assertEqual(result.skipped, 1)
        self.assertEqual(len(result.errors), 1)
        self.assertIsInstance(result.errors[0][1], CategoryNotFoundError)
        self.assertEqual(result.errors[0][0], 1)  # 1-indexed data row

    def test_invalid_date_row_skipped(self) -> None:
        path = self.csv_dir / "a.csv"
        write_csv(path, FULL_HEADER, [["09/01/2026", "expense", "food", "1000", "", ""]])
        result = self.service.import_csv(path)
        self.assertEqual(result.imported, 0)
        self.assertEqual(result.skipped, 1)

    def test_invalid_type_row_skipped(self) -> None:
        path = self.csv_dir / "a.csv"
        write_csv(path, FULL_HEADER, [["2026-09-01", "spending", "food", "1000", "", ""]])
        result = self.service.import_csv(path)
        self.assertEqual(result.imported, 0)
        self.assertEqual(result.skipped, 1)

    def test_invalid_amount_row_skipped(self) -> None:
        path = self.csv_dir / "a.csv"
        write_csv(path, FULL_HEADER, [["2026-09-01", "expense", "food", "-100", "", ""]])
        result = self.service.import_csv(path)
        self.assertEqual(result.imported, 0)
        self.assertEqual(result.skipped, 1)

    def test_valid_rows_before_and_after_invalid_still_import(self) -> None:
        path = self.csv_dir / "a.csv"
        write_csv(
            path,
            FULL_HEADER,
            [
                ["2026-09-01", "expense", "food", "1000", "", ""],
                ["2026-09-02", "expense", "food", "-999", "", ""],  # invalid
                ["2026-09-03", "expense", "food", "2000", "", ""],
            ],
        )
        result = self.service.import_csv(path)
        self.assertEqual(result.imported, 2)
        self.assertEqual(result.skipped, 1)
        amounts = {t.amount for t in self.service.transactions.iter_all()}
        self.assertEqual(amounts, {1000, 2000})

    def test_empty_tags(self) -> None:
        path = self.csv_dir / "a.csv"
        write_csv(path, FULL_HEADER, [["2026-09-01", "expense", "food", "1000", "", ""]])
        self.service.import_csv(path)
        transaction = next(self.service.transactions.iter_all())
        self.assertEqual(transaction.tags, [])

    def test_multiple_tags(self) -> None:
        path = self.csv_dir / "a.csv"
        write_csv(path, FULL_HEADER, [["2026-09-01", "expense", "food", "1000", "", "meal,lunch"]])
        self.service.import_csv(path)
        transaction = next(self.service.transactions.iter_all())
        self.assertEqual(transaction.tags, ["meal", "lunch"])

    def test_quoted_comma_separated_tags(self) -> None:
        # csv.writer will quote the "meal,lunch,work" field automatically
        # because it contains commas.
        path = self.csv_dir / "a.csv"
        write_csv(
            path, FULL_HEADER, [["2026-09-01", "expense", "food", "1000", "", "meal,lunch,work"]]
        )
        content = path.read_text(encoding="utf-8")
        self.assertIn('"meal,lunch,work"', content)
        self.service.import_csv(path)
        transaction = next(self.service.transactions.iter_all())
        self.assertEqual(transaction.tags, ["meal", "lunch", "work"])

    def test_utf8_korean_memo(self) -> None:
        path = self.csv_dir / "a.csv"
        write_csv(path, FULL_HEADER, [["2026-09-01", "expense", "food", "1000", "점심", ""]])
        self.service.import_csv(path)
        transaction = next(self.service.transactions.iter_all())
        self.assertEqual(transaction.memo, "점심")

    def test_header_missing_raises(self) -> None:
        path = self.csv_dir / "a.csv"
        path.write_text("", encoding="utf-8")
        with self.assertRaises(CSVFormatError):
            self.service.import_csv(path)

    def test_required_header_missing_raises(self) -> None:
        path = self.csv_dir / "a.csv"
        write_csv(path, ["date", "type", "category", "amount"], [["2026-09-01", "expense", "food", "1000"]])
        with self.assertRaises(CSVFormatError):
            self.service.import_csv(path)

    def test_header_missing_writes_nothing(self) -> None:
        path = self.csv_dir / "a.csv"
        write_csv(path, ["date", "type"], [["2026-09-01", "expense"]])
        with self.assertRaises(CSVFormatError):
            self.service.import_csv(path)
        self.assertEqual(list(self.service.transactions.iter_all()), [])

    def test_source_file_missing_raises(self) -> None:
        with self.assertRaises(PersistenceError):
            self.service.import_csv(self.csv_dir / "does_not_exist.csv")

    def test_source_file_not_modified(self) -> None:
        path = self.csv_dir / "a.csv"
        write_csv(path, FULL_HEADER, [["2026-09-01", "expense", "food", "1000", "", ""]])
        before = path.read_bytes()
        self.service.import_csv(path)
        after = path.read_bytes()
        self.assertEqual(before, after)

    def test_extra_column_is_ignored(self) -> None:
        path = self.csv_dir / "a.csv"
        write_csv(
            path,
            ["id", *FULL_HEADER],
            [["999", "2026-09-01", "expense", "food", "1000", "", ""]],
        )
        result = self.service.import_csv(path)
        self.assertEqual(result.imported, 1)
        transaction = next(self.service.transactions.iter_all())
        self.assertEqual(transaction.id, 1)  # CSV's "id" column never wins


if __name__ == "__main__":
    unittest.main()
