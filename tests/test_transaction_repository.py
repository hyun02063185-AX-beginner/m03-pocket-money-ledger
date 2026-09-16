"""Unit tests for ledger.repository.TransactionRepository.

Every test uses tempfile.TemporaryDirectory() — never the project's
own ./data — per docs/m03-architecture-design.md section "Data
directory policy".
"""

from __future__ import annotations

import datetime
import tempfile
import types
import unittest
from pathlib import Path

from ledger.errors import DataFormatError, DuplicateTransactionIdError, TransactionNotFoundError
from ledger.models import Transaction
from ledger.repository import TransactionRepository


def make_transaction(id_: int, amount: int = 1000, category: str = "food") -> Transaction:
    return Transaction(
        id=id_,
        type="expense",
        date=datetime.date(2026, 9, 16),
        amount=amount,
        category=category,
        memo="test",
        tags=["t"],
    )


class TransactionRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.data_dir = Path(self._tmp.name) / "data"
        self.repo = TransactionRepository(self.data_dir)

    # -- empty state / directory handling -----------------------------------

    def test_missing_directory_reads_as_empty(self) -> None:
        self.assertEqual(list(self.repo.iter_all()), [])
        self.assertFalse(self.data_dir.exists(), "reading must not create the data directory")

    def test_directory_and_file_created_on_first_write(self) -> None:
        self.repo.add(make_transaction(1))
        self.assertTrue(self.data_dir.exists())
        self.assertTrue(self.repo.path.exists())

    # -- next_id --------------------------------------------------------------

    def test_first_next_id_is_one(self) -> None:
        self.assertEqual(self.repo.next_id(), 1)

    def test_next_id_uses_max_plus_one(self) -> None:
        self.repo.add(make_transaction(1))
        self.repo.add(make_transaction(2))
        self.repo.add(make_transaction(5))
        self.assertEqual(self.repo.next_id(), 6)

    def test_deleted_id_not_reused_while_higher_ids_remain(self) -> None:
        self.repo.add(make_transaction(1))
        self.repo.add(make_transaction(2))
        self.repo.add(make_transaction(5))
        self.repo.delete(2)
        self.assertEqual(self.repo.next_id(), 6)

    # -- add / duplicates -------------------------------------------------------

    def test_add_persists(self) -> None:
        self.repo.add(make_transaction(1, amount=4500))
        found = self.repo.get_by_id(1)
        assert found is not None
        self.assertEqual(found.amount, 4500)

    def test_reconstruction_sees_persisted_data(self) -> None:
        self.repo.add(make_transaction(1))
        other = TransactionRepository(self.data_dir)
        self.assertIsNotNone(other.get_by_id(1))

    def test_duplicate_id_raises(self) -> None:
        self.repo.add(make_transaction(1))
        with self.assertRaises(DuplicateTransactionIdError):
            self.repo.add(make_transaction(1))

    # -- iter_all ---------------------------------------------------------------

    def test_iter_all_returns_transaction_objects(self) -> None:
        self.repo.add(make_transaction(1))
        results = list(self.repo.iter_all())
        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], Transaction)

    def test_iter_all_is_generator_based(self) -> None:
        self.assertIsInstance(self.repo.iter_all(), types.GeneratorType)

    def test_blank_lines_are_ignored(self) -> None:
        self.repo.add(make_transaction(1))
        with self.repo.path.open("a", encoding="utf-8") as f:
            f.write("\n")
            f.write("   \n")
        self.assertEqual(len(list(self.repo.iter_all())), 1)

    def test_malformed_json_raises_data_format_error(self) -> None:
        self.repo.add(make_transaction(1))
        with self.repo.path.open("a", encoding="utf-8") as f:
            f.write("{not valid json\n")
        with self.assertRaises(DataFormatError):
            list(self.repo.iter_all())

    # -- get_by_id ----------------------------------------------------------------

    def test_get_existing_id(self) -> None:
        self.repo.add(make_transaction(3))
        found = self.repo.get_by_id(3)
        assert found is not None
        self.assertEqual(found.id, 3)

    def test_get_missing_id_returns_none(self) -> None:
        self.repo.add(make_transaction(1))
        self.assertIsNone(self.repo.get_by_id(999))

    # -- update -----------------------------------------------------------------

    def test_update_existing(self) -> None:
        self.repo.add(make_transaction(1, amount=1000))
        updated = make_transaction(1, amount=2000)
        self.repo.update(updated)
        found = self.repo.get_by_id(1)
        assert found is not None
        self.assertEqual(found.amount, 2000)

    def test_update_missing_raises(self) -> None:
        with self.assertRaises(TransactionNotFoundError):
            self.repo.update(make_transaction(999))

    def test_update_persists_after_reconstruction(self) -> None:
        self.repo.add(make_transaction(1, amount=1000))
        self.repo.update(make_transaction(1, amount=7000))
        other = TransactionRepository(self.data_dir)
        found = other.get_by_id(1)
        assert found is not None
        self.assertEqual(found.amount, 7000)

    def test_update_leaves_other_records_untouched(self) -> None:
        self.repo.add(make_transaction(1, amount=1000))
        self.repo.add(make_transaction(2, amount=2000))
        self.repo.update(make_transaction(1, amount=9999))
        other = self.repo.get_by_id(2)
        assert other is not None
        self.assertEqual(other.amount, 2000)

    # -- delete -------------------------------------------------------------------

    def test_delete_existing(self) -> None:
        self.repo.add(make_transaction(1))
        self.repo.delete(1)
        self.assertIsNone(self.repo.get_by_id(1))

    def test_delete_missing_raises(self) -> None:
        with self.assertRaises(TransactionNotFoundError):
            self.repo.delete(999)

    def test_delete_persists_after_reconstruction(self) -> None:
        self.repo.add(make_transaction(1))
        self.repo.add(make_transaction(2))
        self.repo.delete(1)
        other = TransactionRepository(self.data_dir)
        ids = {t.id for t in other.iter_all()}
        self.assertEqual(ids, {2})


if __name__ == "__main__":
    unittest.main()
