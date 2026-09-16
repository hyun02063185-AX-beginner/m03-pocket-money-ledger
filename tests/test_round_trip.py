"""Sprint 4 section 30: export -> import round-trip acceptance test.

Proves the CSV schema written by export_csv() is exactly what
import_csv() expects, end to end across two separate data directories
(a fresh "application lifecycle", not just in-memory reuse).
"""

from __future__ import annotations

import datetime
import tempfile
import unittest
from pathlib import Path

from ledger.models import SearchCriteria
from ledger.repository import BudgetRepository, CategoryRepository, TransactionRepository
from ledger.services import LedgerService
from tests.support import ServiceTestMixin

_SEPTEMBER = SearchCriteria(from_date=datetime.date(2026, 9, 1), to_date=datetime.date(2026, 9, 30))


class RoundTripTest(ServiceTestMixin, unittest.TestCase):
    def test_export_then_import_preserves_business_fields(self) -> None:
        source = self.make_service()
        source.add_category("food")
        source.add_category("salary")
        source.add_transaction("expense", "2026-09-01", "food", 1000, "lunch", ["meal", "work"])
        source.add_transaction("income", "2026-09-15", "salary", 500000, "점심", [])
        source.add_transaction("expense", "2026-09-30", "food", 2000, "", ["snack"])
        # outside the exported month — must not appear on the other side
        source.add_transaction("expense", "2026-08-01", "food", 999, "august", [])

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        csv_path = Path(tmp.name) / "export.csv"
        exported_count = source.export_csv(csv_path, month="2026-09")
        self.assertEqual(exported_count, 3)

        # a genuinely separate data directory, standing in for a
        # different "application lifecycle" (fresh repositories).
        target_data_dir = Path(tmp.name) / "target-data"
        target = LedgerService(
            TransactionRepository(target_data_dir),
            CategoryRepository(target_data_dir),
            BudgetRepository(target_data_dir),
        )
        target.add_category("food")
        target.add_category("salary")

        result = target.import_csv(csv_path)
        self.assertEqual(result.imported, 3)
        self.assertEqual(result.skipped, 0)

        def business_fields(transactions):
            return sorted(
                (t.date, t.type, t.category, t.amount, t.memo, tuple(t.tags))
                for t in transactions
            )

        source_fields = business_fields(source.search(_SEPTEMBER))
        target_fields = business_fields(target.transactions.iter_all())
        self.assertEqual(source_fields, target_fields)

        # ids are intentionally NOT expected to match — CSV never
        # carries them, each side assigns its own independently.
        source_ids = {t.id for t in source.search(_SEPTEMBER)}
        target_ids = {t.id for t in target.transactions.iter_all()}
        self.assertEqual(target_ids, {1, 2, 3})
        self.assertTrue(source_ids)  # sanity: source did have ids too


if __name__ == "__main__":
    unittest.main()
