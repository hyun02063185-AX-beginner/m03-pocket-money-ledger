"""Sprint 2: LedgerService.set_budget() tests."""

from __future__ import annotations

import unittest

from ledger.errors import InvalidAmountError, InvalidMonthError
from tests.support import ServiceTestMixin


class SetBudgetTests(ServiceTestMixin, unittest.TestCase):
    def setUp(self) -> None:
        self.service = self.make_service()

    def test_set_new_month(self) -> None:
        budget = self.service.set_budget("2026-09", 500000)
        self.assertEqual(budget.month, "2026-09")
        self.assertEqual(budget.amount, 500000)
        self.assertEqual(self.service.budgets.get("2026-09").amount, 500000)

    def test_set_replaces_existing_month(self) -> None:
        self.service.set_budget("2026-09", 500000)
        self.service.set_budget("2026-09", 800000)
        all_budgets = self.service.budgets.list_all()
        self.assertEqual(len(all_budgets), 1)
        self.assertEqual(all_budgets[0].amount, 800000)

    def test_invalid_amount_rejected(self) -> None:
        with self.assertRaises(InvalidAmountError):
            self.service.set_budget("2026-09", 0)
        with self.assertRaises(InvalidAmountError):
            self.service.set_budget("2026-09", -100)

    def test_invalid_month_rejected(self) -> None:
        with self.assertRaises(InvalidMonthError):
            self.service.set_budget("2026-9", 500000)
        with self.assertRaises(InvalidMonthError):
            self.service.set_budget("September", 500000)


if __name__ == "__main__":
    unittest.main()
