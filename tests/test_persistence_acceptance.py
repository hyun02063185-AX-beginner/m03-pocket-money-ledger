"""End-to-end persistence acceptance test (Sprint 1, section 23):
proves data survives across repository-object lifecycle boundaries,
not just within one repository instance's lifetime.
"""

from __future__ import annotations

import datetime
import tempfile
import unittest
from pathlib import Path

from ledger.models import Budget, Transaction
from ledger.repository import BudgetRepository, CategoryRepository, TransactionRepository


class PersistenceAcceptanceTest(unittest.TestCase):
    def test_data_survives_repository_reconstruction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp) / "data"

            # 1-2. create TemporaryDirectory + construct repositories
            transactions = TransactionRepository(data_dir)
            categories = CategoryRepository(data_dir)
            budgets = BudgetRepository(data_dir)

            # 3. confirm empty
            self.assertEqual(list(transactions.iter_all()), [])
            self.assertEqual(categories.list_all(), [])
            self.assertEqual(budgets.list_all(), [])
            self.assertFalse(data_dir.exists())

            # 4. add category
            categories.add("식비")

            # 5. add transaction
            transaction = Transaction(
                id=transactions.next_id(),
                type="expense",
                date=datetime.date(2026, 9, 16),
                amount=4500,
                category="식비",
                memo="점심",
                tags=["카페"],
            )
            transactions.add(transaction)

            # 6. set budget
            budgets.set(Budget(month="2026-09", amount=500000))

            # 7. destroy/reconstruct repository objects
            del transactions, categories, budgets
            transactions2 = TransactionRepository(data_dir)
            categories2 = CategoryRepository(data_dir)
            budgets2 = BudgetRepository(data_dir)

            # 8. verify all three values still exist
            reloaded = transactions2.get_by_id(transaction.id)
            self.assertIsNotNone(reloaded)
            assert reloaded is not None
            self.assertEqual(reloaded.amount, 4500)
            self.assertEqual(reloaded.category, "식비")

            self.assertIn("식비", categories2.list_all())

            reloaded_budget = budgets2.get("2026-09")
            self.assertIsNotNone(reloaded_budget)
            assert reloaded_budget is not None
            self.assertEqual(reloaded_budget.amount, 500000)


if __name__ == "__main__":
    unittest.main()
