"""Unit tests for ledger.repository.BudgetRepository."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ledger.errors import BudgetNotFoundError, DataFormatError
from ledger.models import Budget
from ledger.repository import BudgetRepository


class BudgetRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.data_dir = Path(self._tmp.name) / "data"
        self.repo = BudgetRepository(self.data_dir)

    def test_initial_empty(self) -> None:
        self.assertEqual(self.repo.list_all(), [])
        self.assertFalse(self.data_dir.exists())

    def test_set_new_month(self) -> None:
        self.repo.set(Budget(month="2026-09", amount=500000))
        self.assertEqual(self.repo.list_all(), [Budget(month="2026-09", amount=500000)])

    def test_persisted_reload(self) -> None:
        self.repo.set(Budget(month="2026-09", amount=500000))
        other = BudgetRepository(self.data_dir)
        self.assertEqual(other.get("2026-09"), Budget(month="2026-09", amount=500000))

    def test_get_existing(self) -> None:
        self.repo.set(Budget(month="2026-09", amount=500000))
        found = self.repo.get("2026-09")
        assert found is not None
        self.assertEqual(found.amount, 500000)

    def test_get_missing_returns_none(self) -> None:
        self.assertIsNone(self.repo.get("2026-09"))

    def test_set_existing_month_replaces_not_appends(self) -> None:
        self.repo.set(Budget(month="2026-09", amount=500000))
        self.repo.set(Budget(month="2026-09", amount=800000))
        all_budgets = self.repo.list_all()
        self.assertEqual(len(all_budgets), 1)
        self.assertEqual(all_budgets[0].amount, 800000)

    def test_set_different_months_both_kept(self) -> None:
        self.repo.set(Budget(month="2026-08", amount=100000))
        self.repo.set(Budget(month="2026-09", amount=200000))
        months = {b.month for b in self.repo.list_all()}
        self.assertEqual(months, {"2026-08", "2026-09"})

    def test_remove(self) -> None:
        self.repo.set(Budget(month="2026-09", amount=500000))
        self.repo.remove("2026-09")
        self.assertIsNone(self.repo.get("2026-09"))

    def test_remove_missing_raises(self) -> None:
        with self.assertRaises(BudgetNotFoundError):
            self.repo.remove("2026-09")

    def test_malformed_json_raises(self) -> None:
        self.repo.set(Budget(month="2026-09", amount=500000))
        with self.repo.path.open("a", encoding="utf-8") as f:
            f.write("{bad json\n")
        with self.assertRaises(DataFormatError):
            self.repo.list_all()


if __name__ == "__main__":
    unittest.main()
