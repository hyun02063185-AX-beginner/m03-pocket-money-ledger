"""File-backed repositories — the real Sprint 1 persistence layer.

See docs/m03-architecture-design.md sections 6, 10, 11, 21 and 24 for
the contracts implemented here: JSONL storage, generator-based reads,
data_dir-based path resolution, empty-state behavior for missing
files/directories, and the safe-rewrite (temp file + os.replace())
strategy for update/delete/remove/set.

Repository is persistence infrastructure only. It enforces storage-
level integrity (no duplicate ids, no malformed JSON silently
accepted) but never cross-domain business rules — "category must
exist before add", "category in use", "budget exceeded" etc. all
belong to LedgerService in a later sprint (section 20).
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Iterable, Iterator

from ledger.errors import (
    BudgetNotFoundError,
    CategoryNotFoundError,
    DataFormatError,
    DuplicateCategoryError,
    DuplicateTransactionIdError,
    TransactionNotFoundError,
)
from ledger.models import Budget, Transaction


def _iter_jsonl(path: Path) -> Iterator[dict]:
    """Stream one parsed JSON object per nonblank line of `path`.

    A missing file yields nothing — an empty dataset is not an error
    (docs/m03-architecture-design.md section 10) and reading never
    creates the file or its directory. Never reads the whole file into
    a list before yielding: each line is parsed and yielded in turn.
    """
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as f:
        for line_no, raw_line in enumerate(f, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise DataFormatError(f"{path}:{line_no}: malformed JSON line ({exc})") from exc


def _append_jsonl(path: Path, record: dict) -> None:
    """Append one record as a new line. Creates the parent directory
    (parents=True) and the file itself on first use; never rewrites
    existing lines — O(1) I/O, not a full-file rewrite."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="") as f:
        f.write(json.dumps(record, ensure_ascii=False))
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())


def _atomic_write_jsonl(path: Path, records: Iterable[dict]) -> None:
    """Rewrite `path` from scratch: write every record to a same-
    directory temp file, flush it, then os.replace() it over the
    original. If anything raises before os.replace(), the original
    file is untouched and the temp file is removed
    (docs/m03-architecture-design.md section 24). Shared by every
    update/delete/remove/set operation below so there is exactly one
    rewrite implementation to reason about.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f"{path.name}.", suffix=".tmp")
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False))
                f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise


class TransactionRepository:
    """Owns <data_dir>/transactions.jsonl."""

    FILENAME = "transactions.jsonl"

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir)
        self.path = self.data_dir / self.FILENAME

    def iter_all(self) -> Iterator[Transaction]:
        """True generator: reads transactions.jsonl one line at a time
        and yields a Transaction as each line is parsed. Never builds
        a list of every record first — the file is never fully
        resident in memory here, regardless of its size."""
        for record in _iter_jsonl(self.path):
            yield Transaction.from_dict(record)

    def get_by_id(self, transaction_id: int) -> Transaction | None:
        """Streams via iter_all(); returns None rather than raising
        when nothing matches (no established contract requires an
        exception for a simple lookup miss)."""
        for transaction in self.iter_all():
            if transaction.id == transaction_id:
                return transaction
        return None

    def next_id(self) -> int:
        """max(existing ids) + 1, or 1 if the store is empty. Requires
        one streaming scan — acceptable for Mission Core scale (see
        docs/m03-architecture-design.md section 11)."""
        max_id = 0
        for transaction in self.iter_all():
            if transaction.id > max_id:
                max_id = transaction.id
        return max_id + 1

    def add(self, transaction: Transaction) -> Transaction:
        """Appends `transaction` as given — the caller is responsible
        for assigning `transaction.id` via next_id() first (the
        Sprint 0B contract; Service will do this in a later sprint).
        Raises DuplicateTransactionIdError without writing anything if
        that id is already present."""
        if self.get_by_id(transaction.id) is not None:
            raise DuplicateTransactionIdError(f"transaction id {transaction.id} already exists")
        _append_jsonl(self.path, transaction.to_dict())
        return transaction

    def update(self, transaction: Transaction) -> Transaction:
        """Safe rewrite: stream every existing record, substitute the
        one whose id matches `transaction.id`, then write the result
        via temp file + os.replace(). Raises TransactionNotFoundError
        (and writes nothing) if no record has that id."""
        records: list[dict] = []
        found = False
        for existing in self.iter_all():
            if existing.id == transaction.id:
                records.append(transaction.to_dict())
                found = True
            else:
                records.append(existing.to_dict())
        if not found:
            raise TransactionNotFoundError(f"transaction id {transaction.id} not found")
        _atomic_write_jsonl(self.path, records)
        return transaction

    def delete(self, transaction_id: int) -> None:
        """Safe rewrite: stream every existing record, omit the one
        matching `transaction_id`, write the rest via temp file +
        os.replace(). Raises TransactionNotFoundError (and writes
        nothing, leaving the original file intact) if no record has
        that id."""
        records: list[dict] = []
        found = False
        for existing in self.iter_all():
            if existing.id == transaction_id:
                found = True
                continue
            records.append(existing.to_dict())
        if not found:
            raise TransactionNotFoundError(f"transaction id {transaction_id} not found")
        _atomic_write_jsonl(self.path, records)


class CategoryRepository:
    """Owns <data_dir>/categories.jsonl (one {"name": ...} object per
    line). Storage only — the "category in use by a transaction" rule
    lives in LedgerService (a later sprint), because enforcing it
    requires coordinating with TransactionRepository, and repository
    classes must not depend on each other."""

    FILENAME = "categories.jsonl"

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir)
        self.path = self.data_dir / self.FILENAME

    def list_all(self) -> list[str]:
        return [record["name"] for record in _iter_jsonl(self.path)]

    def exists(self, name: str) -> bool:
        return name in self.list_all()

    def add(self, name: str) -> None:
        """Raises DuplicateCategoryError without writing anything if
        `name` is already registered."""
        if self.exists(name):
            raise DuplicateCategoryError(f"category {name!r} already exists")
        _append_jsonl(self.path, {"name": name})

    def remove(self, name: str) -> None:
        """Raises CategoryNotFoundError (and writes nothing) if `name`
        is not registered."""
        names = self.list_all()
        if name not in names:
            raise CategoryNotFoundError(f"category {name!r} not found")
        remaining = [{"name": n} for n in names if n != name]
        _atomic_write_jsonl(self.path, remaining)


class BudgetRepository:
    """Owns <data_dir>/budgets.jsonl. One record per month; month is
    the unique key (a month-wide total budget, not per-category — see
    docs/m03-architecture-design.md section 15). Does not compute
    usage percentage or exceeded state — that is LedgerService's job."""

    FILENAME = "budgets.jsonl"

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir)
        self.path = self.data_dir / self.FILENAME

    def list_all(self) -> list[Budget]:
        return [Budget.from_dict(record) for record in _iter_jsonl(self.path)]

    def get(self, month: str) -> Budget | None:
        for budget in self.list_all():
            if budget.month == month:
                return budget
        return None

    def set(self, budget: Budget) -> Budget:
        """Insert the budget for a new month, or replace the existing
        record for that month — never appends a second row for the
        same month (a full rewrite is required to guarantee that)."""
        remaining = [b.to_dict() for b in self.list_all() if b.month != budget.month]
        remaining.append(budget.to_dict())
        _atomic_write_jsonl(self.path, remaining)
        return budget

    def remove(self, month: str) -> None:
        """Raises BudgetNotFoundError (and writes nothing) if no
        budget is set for `month`."""
        budgets = self.list_all()
        if not any(b.month == month for b in budgets):
            raise BudgetNotFoundError(f"no budget set for month {month!r}")
        remaining = [b.to_dict() for b in budgets if b.month != month]
        _atomic_write_jsonl(self.path, remaining)
