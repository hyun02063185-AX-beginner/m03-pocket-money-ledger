"""Sprint 2: LedgerService.monthly_summary() tests, including budget
integration."""

from __future__ import annotations

import unittest

from ledger.errors import InvalidMonthError, ValidationError
from tests.support import ServiceTestMixin


class MonthlySummaryTests(ServiceTestMixin, unittest.TestCase):
    def setUp(self) -> None:
        self.service = self.make_service()
        self.service.add_category("food")
        self.service.add_category("transport")
        self.service.add_category("rent")

    def _seed_september(self) -> None:
        self.service.add_transaction("income", "2026-09-01", "food", 300000, "salary")
        self.service.add_transaction("expense", "2026-09-02", "food", 20000, "groceries")
        self.service.add_transaction("expense", "2026-09-05", "food", 10000, "snacks")
        self.service.add_transaction("expense", "2026-09-10", "transport", 15000, "bus")
        self.service.add_transaction("expense", "2026-09-15", "rent", 500000, "rent")
        # different month — must be excluded
        self.service.add_transaction("expense", "2026-08-01", "food", 999999, "august")

    def test_totals_income_expense_balance(self) -> None:
        self._seed_september()
        summary = self.service.monthly_summary("2026-09", top=3)
        self.assertEqual(summary.total_income, 300000)
        self.assertEqual(summary.total_expense, 545000)
        self.assertEqual(summary.balance, 300000 - 545000)

    def test_excludes_other_months(self) -> None:
        self._seed_september()
        summary = self.service.monthly_summary("2026-09", top=3)
        self.assertNotIn(999999, summary.category_expenses.values())

    def test_category_aggregation_expense_only(self) -> None:
        self._seed_september()
        summary = self.service.monthly_summary("2026-09", top=3)
        self.assertEqual(summary.category_expenses["food"], 30000)
        self.assertEqual(summary.category_expenses["transport"], 15000)
        self.assertEqual(summary.category_expenses["rent"], 500000)
        # income transaction's category must not appear as an expense total
        self.assertEqual(
            summary.category_expenses["food"], 20000 + 10000, "income of 300000 leaked into expenses"
        )

    def test_top_n_categories(self) -> None:
        self._seed_september()
        summary = self.service.monthly_summary("2026-09", top=2)
        self.assertEqual(summary.top_categories, [("rent", 500000), ("food", 30000)])

    def test_no_data_month(self) -> None:
        summary = self.service.monthly_summary("2026-01", top=3)
        self.assertFalse(summary.has_transactions)
        self.assertEqual(summary.total_income, 0)
        self.assertEqual(summary.total_expense, 0)
        self.assertEqual(summary.balance, 0)
        self.assertEqual(summary.category_expenses, {})
        self.assertEqual(summary.top_categories, [])

    def test_budget_absent(self) -> None:
        self._seed_september()
        summary = self.service.monthly_summary("2026-09", top=3)
        self.assertIsNone(summary.budget_amount)
        self.assertIsNone(summary.budget_usage_percent)
        self.assertIsNone(summary.budget_exceeded)

    def test_budget_usage_under(self) -> None:
        self._seed_september()
        self.service.set_budget("2026-09", 1000000)
        summary = self.service.monthly_summary("2026-09", top=3)
        self.assertEqual(summary.budget_amount, 1000000)
        self.assertAlmostEqual(summary.budget_usage_percent, 54.5)
        self.assertFalse(summary.budget_exceeded)

    def test_budget_exceeded(self) -> None:
        self._seed_september()
        self.service.set_budget("2026-09", 100000)
        summary = self.service.monthly_summary("2026-09", top=3)
        self.assertGreater(summary.budget_usage_percent, 100)
        self.assertTrue(summary.budget_exceeded)

    def test_invalid_month_raises(self) -> None:
        with self.assertRaises(InvalidMonthError):
            self.service.monthly_summary("2026-9", top=3)
        with self.assertRaises(InvalidMonthError):
            self.service.monthly_summary("not-a-month", top=3)

    def test_invalid_top_raises(self) -> None:
        with self.assertRaises(ValidationError):
            self.service.monthly_summary("2026-09", top=0)


if __name__ == "__main__":
    unittest.main()
