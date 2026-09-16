"""Shared test helpers for Sprint 2 Service-layer tests.

Not named test_*.py on purpose so unittest discovery skips it.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from ledger.repository import BudgetRepository, CategoryRepository, TransactionRepository
from ledger.services import LedgerService


class ServiceTestMixin:
    """Mixin (combine with unittest.TestCase) providing a LedgerService
    backed by real, tempdir-backed repositories. Sprint 2 tests must
    prove Service and Repository work together, not mock repositories
    away — see docs/m03-architecture-design.md section 18."""

    def make_service(self) -> LedgerService:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)  # type: ignore[attr-defined]
        data_dir = Path(tmp.name) / "data"
        return LedgerService(
            TransactionRepository(data_dir),
            CategoryRepository(data_dir),
            BudgetRepository(data_dir),
        )
