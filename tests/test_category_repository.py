"""Unit tests for ledger.repository.CategoryRepository."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ledger.errors import CategoryNotFoundError, DataFormatError, DuplicateCategoryError
from ledger.repository import CategoryRepository


class CategoryRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.data_dir = Path(self._tmp.name) / "data"
        self.repo = CategoryRepository(self.data_dir)

    def test_initial_empty(self) -> None:
        self.assertEqual(self.repo.list_all(), [])
        self.assertFalse(self.data_dir.exists())

    def test_add_persists(self) -> None:
        self.repo.add("식비")
        self.assertEqual(self.repo.list_all(), ["식비"])

    def test_persisted_reload(self) -> None:
        self.repo.add("식비")
        other = CategoryRepository(self.data_dir)
        self.assertEqual(other.list_all(), ["식비"])

    def test_duplicate_add_raises(self) -> None:
        self.repo.add("식비")
        with self.assertRaises(DuplicateCategoryError):
            self.repo.add("식비")

    def test_exists(self) -> None:
        self.repo.add("식비")
        self.assertTrue(self.repo.exists("식비"))
        self.assertFalse(self.repo.exists("교통"))

    def test_remove(self) -> None:
        self.repo.add("식비")
        self.repo.add("교통")
        self.repo.remove("식비")
        self.assertEqual(self.repo.list_all(), ["교통"])

    def test_remove_missing_raises(self) -> None:
        with self.assertRaises(CategoryNotFoundError):
            self.repo.remove("없음")

    def test_blank_lines_ignored(self) -> None:
        self.repo.add("식비")
        with self.repo.path.open("a", encoding="utf-8") as f:
            f.write("\n")
        self.assertEqual(self.repo.list_all(), ["식비"])

    def test_malformed_json_raises(self) -> None:
        self.repo.add("식비")
        with self.repo.path.open("a", encoding="utf-8") as f:
            f.write("{bad json\n")
        with self.assertRaises(DataFormatError):
            self.repo.list_all()


if __name__ == "__main__":
    unittest.main()
