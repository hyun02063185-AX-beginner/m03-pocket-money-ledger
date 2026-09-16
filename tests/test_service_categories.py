"""Sprint 2: LedgerService category management tests, including the
category-in-use removal guard."""

from __future__ import annotations

import unittest

from ledger.errors import CategoryInUseError, CategoryNotFoundError, DuplicateCategoryError, ValidationError
from tests.support import ServiceTestMixin


class CategoryServiceTests(ServiceTestMixin, unittest.TestCase):
    def setUp(self) -> None:
        self.service = self.make_service()

    def test_add_category(self) -> None:
        self.service.add_category("food")
        self.assertEqual(self.service.list_categories(), ["food"])

    def test_add_category_strips_whitespace(self) -> None:
        self.service.add_category("  food  ")
        self.assertEqual(self.service.list_categories(), ["food"])

    def test_add_empty_category_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            self.service.add_category("   ")

    def test_list_categories(self) -> None:
        self.service.add_category("food")
        self.service.add_category("transport")
        self.assertEqual(self.service.list_categories(), ["food", "transport"])

    def test_add_duplicate_category_rejected(self) -> None:
        self.service.add_category("food")
        with self.assertRaises(DuplicateCategoryError):
            self.service.add_category("food")

    def test_remove_unused_category(self) -> None:
        self.service.add_category("food")
        self.service.remove_category("food")
        self.assertEqual(self.service.list_categories(), [])

    def test_remove_used_category_blocked(self) -> None:
        self.service.add_category("food")
        self.service.add_transaction("expense", "2026-09-01", "food", 1000)
        with self.assertRaises(CategoryInUseError):
            self.service.remove_category("food")
        # must not have been removed
        self.assertEqual(self.service.list_categories(), ["food"])

    def test_remove_missing_category_raises(self) -> None:
        with self.assertRaises(CategoryNotFoundError):
            self.service.remove_category("nonexistent")


if __name__ == "__main__":
    unittest.main()
