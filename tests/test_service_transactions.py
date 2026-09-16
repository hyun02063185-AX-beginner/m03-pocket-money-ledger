"""Sprint 2: LedgerService tests for add / list / search / update / delete."""

from __future__ import annotations

import datetime
import unittest

from ledger.errors import (
    CategoryNotFoundError,
    InvalidAmountError,
    InvalidDateError,
    InvalidTransactionTypeError,
    TransactionNotFoundError,
    ValidationError,
)
from ledger.models import SearchCriteria
from ledger.services import LedgerService
from tests.support import ServiceTestMixin


def add(
    service: LedgerService,
    date: str,
    type_: str = "expense",
    category: str = "food",
    amount: int = 1000,
    memo: str = "",
    tags: list[str] | None = None,
):
    return service.add_transaction(type_, date, category, amount, memo, tags)


class AddTransactionTests(ServiceTestMixin, unittest.TestCase):
    def setUp(self) -> None:
        self.service = self.make_service()
        self.service.add_category("food")

    def test_valid_transaction_added_and_persists(self) -> None:
        created = add(self.service, "2026-09-16", amount=4500, memo="lunch", tags=["cafe"])
        reloaded = self.service.transactions.get_by_id(created.id)
        assert reloaded is not None
        self.assertEqual(reloaded.amount, 4500)
        self.assertEqual(reloaded.memo, "lunch")
        self.assertEqual(reloaded.tags, ["cafe"])

    def test_ids_are_sequential(self) -> None:
        first = add(self.service, "2026-09-01")
        second = add(self.service, "2026-09-02")
        self.assertEqual(first.id, 1)
        self.assertEqual(second.id, 2)

    def test_unknown_category_rejected(self) -> None:
        with self.assertRaises(CategoryNotFoundError):
            add(self.service, "2026-09-01", category="unregistered")

    def test_non_positive_amount_rejected(self) -> None:
        with self.assertRaises(InvalidAmountError):
            add(self.service, "2026-09-01", amount=0)
        with self.assertRaises(InvalidAmountError):
            add(self.service, "2026-09-01", amount=-500)

    def test_invalid_type_rejected(self) -> None:
        with self.assertRaises(InvalidTransactionTypeError):
            add(self.service, "2026-09-01", type_="spending")

    def test_invalid_date_rejected(self) -> None:
        with self.assertRaises(InvalidDateError):
            add(self.service, "2026/09/01")


class ListTransactionsTests(ServiceTestMixin, unittest.TestCase):
    def setUp(self) -> None:
        self.service = self.make_service()
        self.service.add_category("food")

    def test_empty(self) -> None:
        self.assertEqual(self.service.list_transactions(10), [])

    def test_newest_first(self) -> None:
        first = add(self.service, "2026-09-01", amount=100)
        second = add(self.service, "2026-09-02", amount=200)
        results = self.service.list_transactions(10)
        self.assertEqual([t.id for t in results], [second.id, first.id])

    def test_limit_honored_with_larger_fixture(self) -> None:
        for i in range(1, 21):  # ids 1..20
            add(self.service, "2026-09-01", amount=i)
        results = self.service.list_transactions(5)
        self.assertEqual([t.id for t in results], [20, 19, 18, 17, 16])

    def test_non_positive_limit_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            self.service.list_transactions(0)
        with self.assertRaises(ValidationError):
            self.service.list_transactions(-1)


class SearchTransactionsTests(ServiceTestMixin, unittest.TestCase):
    def setUp(self) -> None:
        self.service = self.make_service()
        self.service.add_category("food")
        self.service.add_category("transport")
        self.t1 = add(
            self.service,
            "2026-09-01",
            category="food",
            amount=1000,
            memo="Lunch at cafe",
            tags=["work"],
        )
        self.t2 = add(
            self.service,
            "2026-09-10",
            type_="income",
            category="transport",
            amount=50000,
            memo="salary",
            tags=["monthly"],
        )
        self.t3 = add(
            self.service,
            "2026-09-20",
            category="food",
            amount=2000,
            memo="dinner",
            tags=["work", "team"],
        )

    def test_from_filter(self) -> None:
        results = self.service.search(SearchCriteria(from_date=datetime.date(2026, 9, 10)))
        self.assertEqual({t.id for t in results}, {self.t2.id, self.t3.id})

    def test_to_filter(self) -> None:
        results = self.service.search(SearchCriteria(to_date=datetime.date(2026, 9, 10)))
        self.assertEqual({t.id for t in results}, {self.t1.id, self.t2.id})

    def test_category_filter(self) -> None:
        results = self.service.search(SearchCriteria(category="food"))
        self.assertEqual({t.id for t in results}, {self.t1.id, self.t3.id})

    def test_type_filter(self) -> None:
        results = self.service.search(SearchCriteria(transaction_type="income"))
        self.assertEqual({t.id for t in results}, {self.t2.id})

    def test_query_matches_memo_case_insensitive(self) -> None:
        results = self.service.search(SearchCriteria(query="LUNCH"))
        self.assertEqual({t.id for t in results}, {self.t1.id})

    def test_tag_filter(self) -> None:
        results = self.service.search(SearchCriteria(tag="team"))
        self.assertEqual({t.id for t in results}, {self.t3.id})

    def test_combined_filters(self) -> None:
        results = self.service.search(SearchCriteria(category="food", tag="work"))
        self.assertEqual({t.id for t in results}, {self.t1.id, self.t3.id})

    def test_newest_first_ordering(self) -> None:
        results = self.service.search(SearchCriteria(category="food"))
        self.assertEqual([t.id for t in results], [self.t3.id, self.t1.id])

    def test_no_matches_returns_empty(self) -> None:
        results = self.service.search(SearchCriteria(category="nonexistent"))
        self.assertEqual(results, [])


class UpdateTransactionTests(ServiceTestMixin, unittest.TestCase):
    def setUp(self) -> None:
        self.service = self.make_service()
        self.service.add_category("food")
        self.service.add_category("transport")
        self.original = add(
            self.service,
            "2026-09-01",
            category="food",
            amount=1000,
            memo="lunch",
            tags=["work"],
        )

    def test_single_field_update(self) -> None:
        updated = self.service.update_transaction(self.original.id, amount=5000)
        self.assertEqual(updated.amount, 5000)
        self.assertEqual(updated.category, "food")
        self.assertEqual(updated.memo, "lunch")

    def test_multiple_field_update(self) -> None:
        updated = self.service.update_transaction(
            self.original.id, amount=5000, category="transport", memo="taxi"
        )
        self.assertEqual(updated.amount, 5000)
        self.assertEqual(updated.category, "transport")
        self.assertEqual(updated.memo, "taxi")

    def test_unspecified_fields_preserved(self) -> None:
        updated = self.service.update_transaction(self.original.id, amount=9999)
        self.assertEqual(updated.date, self.original.date)
        self.assertEqual(updated.type, self.original.type)
        self.assertEqual(updated.category, self.original.category)
        self.assertEqual(updated.memo, self.original.memo)
        self.assertEqual(updated.tags, self.original.tags)

    def test_missing_id_raises(self) -> None:
        with self.assertRaises(TransactionNotFoundError):
            self.service.update_transaction(999, amount=100)

    def test_nonexistent_new_category_rejected(self) -> None:
        with self.assertRaises(CategoryNotFoundError):
            self.service.update_transaction(self.original.id, category="unregistered")

    def test_memo_cleared_intentionally(self) -> None:
        updated = self.service.update_transaction(self.original.id, memo="")
        self.assertEqual(updated.memo, "")

    def test_memo_omitted_keeps_original(self) -> None:
        updated = self.service.update_transaction(self.original.id, amount=42)
        self.assertEqual(updated.memo, "lunch")

    def test_tags_cleared_intentionally(self) -> None:
        updated = self.service.update_transaction(self.original.id, tags=[])
        self.assertEqual(updated.tags, [])

    def test_tags_omitted_keeps_original(self) -> None:
        updated = self.service.update_transaction(self.original.id, amount=42)
        self.assertEqual(updated.tags, ["work"])

    def test_update_persists(self) -> None:
        self.service.update_transaction(self.original.id, amount=7777)
        reloaded = self.service.transactions.get_by_id(self.original.id)
        assert reloaded is not None
        self.assertEqual(reloaded.amount, 7777)


class DeleteTransactionTests(ServiceTestMixin, unittest.TestCase):
    def setUp(self) -> None:
        self.service = self.make_service()
        self.service.add_category("food")

    def test_delete_existing(self) -> None:
        created = add(self.service, "2026-09-01")
        self.service.delete_transaction(created.id)
        self.assertIsNone(self.service.transactions.get_by_id(created.id))

    def test_delete_missing_raises(self) -> None:
        with self.assertRaises(TransactionNotFoundError):
            self.service.delete_transaction(999)


if __name__ == "__main__":
    unittest.main()
