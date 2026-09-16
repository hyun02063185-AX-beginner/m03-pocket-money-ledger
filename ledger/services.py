"""Business logic layer — the real Sprint 2 implementation.

LedgerService is the only place cross-repository business rules live
(category must exist before a transaction references it, a category
in use can't be removed, budgets are reporting-only). Repositories
stay persistence-only (docs/m03-architecture-design.md section 26).

Service never prints, never calls input(), never touches argparse or
sys.exit() — it returns values or raises a ledger.errors.LedgerError
subclass. cli.py (a later sprint) is the only place that talks to the
user (section 16).
"""

from __future__ import annotations

import csv
import os
import tempfile
from collections import deque
from pathlib import Path

from ledger.errors import (
    CategoryInUseError,
    CategoryNotFoundError,
    CSVFormatError,
    LedgerError,
    PersistenceError,
    TransactionNotFoundError,
    ValidationError,
)
from ledger.models import Budget, ImportResult, MonthlySummary, SearchCriteria, Transaction
from ledger.repository import BudgetRepository, CategoryRepository, TransactionRepository
from ledger.validators import (
    parse_tags,
    validate_amount,
    validate_category_name,
    validate_date,
    validate_month,
    validate_transaction_type,
)

#: The exchange-format CSV schema (docs/m03-architecture-design.md
#: section 46) — fixed column order, used by both import and export.
#: Deliberately does NOT include the internal transaction id (Sprint 4
#: canonical decision: CSV never controls ids).
CSV_FIELDNAMES = ["date", "type", "category", "amount", "memo", "tags"]


class _UnsetType:
    """Sentinel type for update_transaction()'s "field not supplied"
    default — distinct from any real value, including None, "" or [].
    See docs/m03-architecture-design.md section 38 for why a sentinel
    (rather than None) is required here: memo="" and tags=[] must mean
    "clear this field", not "leave it alone"."""

    def __repr__(self) -> str:  # pragma: no cover - debugging aid only
        return "UNSET"


UNSET = _UnsetType()


class LedgerService:
    """Coordinates repositories to implement every Mission Core
    operation: add/list/search/update/delete transactions, monthly
    summary with budget usage, category management, and CSV
    import/export."""

    def __init__(
        self,
        transactions: TransactionRepository,
        categories: CategoryRepository,
        budgets: BudgetRepository,
    ) -> None:
        self.transactions = transactions
        self.categories = categories
        self.budgets = budgets

    # -- transactions -----------------------------------------------------------

    def add_transaction(
        self,
        type_: str,
        date: str,
        category: str,
        amount: int,
        memo: str = "",
        tags: list[str] | None = None,
    ) -> Transaction:
        """Validates every field, confirms `category` is registered
        (never silently creates one), assigns the next id, and
        persists. Does not check the budget — budget is reporting-only,
        applied in monthly_summary(), and never blocks add/update."""
        validated_type = validate_transaction_type(type_)
        validated_date = validate_date(date)
        validated_amount = validate_amount(amount)
        if not self.categories.exists(category):
            raise CategoryNotFoundError(f"category {category!r} not found")

        transaction = Transaction(
            id=self.transactions.next_id(),
            type=validated_type,
            date=validated_date,
            amount=validated_amount,
            category=category,
            memo=memo,
            tags=list(tags) if tags is not None else [],
        )
        return self.transactions.add(transaction)

    def list_transactions(self, limit: int) -> list[Transaction]:
        """Newest-first, bounded O(limit) memory: streams via
        TransactionRepository.iter_all() into a
        collections.deque(maxlen=limit), then reverses just that
        deque (docs/m03-architecture-design.md section 12).

        "Newest" means most recently *added* (== highest id, since ids
        only increase) — the last `limit` lines of the file, not the
        `limit` transactions with the latest `date` field. Sorting by
        date would require buffering the whole file; this project
        treats "recent" as "recently entered", matching the
        append-order deque strategy already locked in for this
        method (section 39)."""
        if limit <= 0:
            raise ValidationError(f"limit must be positive, got {limit}")
        recent: deque[Transaction] = deque(maxlen=limit)
        for transaction in self.transactions.iter_all():
            recent.append(transaction)
        return list(reversed(recent))

    def search(self, criteria: SearchCriteria) -> list[Transaction]:
        """Filters while streaming iter_all(), but must buffer every
        matching record (memory O(match count), not O(file size)) to
        produce newest-first output — no --limit exists for search
        (docs/m03-architecture-design.md section 13). As with
        list_transactions(), "newest first" reverses file/insertion
        order, it does not re-sort by the `date` field.

        Match semantics — see SearchCriteria's docstring: from_date/
        to_date are inclusive; category/transaction_type/tag are exact
        case-sensitive matches; query is a case-insensitive substring
        match against memo only."""
        matches: list[Transaction] = []
        for transaction in self.transactions.iter_all():
            if criteria.from_date is not None and transaction.date < criteria.from_date:
                continue
            if criteria.to_date is not None and transaction.date > criteria.to_date:
                continue
            if criteria.category is not None and transaction.category != criteria.category:
                continue
            if (
                criteria.transaction_type is not None
                and transaction.type != criteria.transaction_type
            ):
                continue
            if criteria.query is not None and criteria.query.lower() not in transaction.memo.lower():
                continue
            if criteria.tag is not None and criteria.tag not in transaction.tags:
                continue
            matches.append(transaction)
        matches.reverse()
        return matches

    def update_transaction(
        self,
        transaction_id: int,
        *,
        date: str | _UnsetType = UNSET,
        transaction_type: str | _UnsetType = UNSET,
        category: str | _UnsetType = UNSET,
        amount: int | _UnsetType = UNSET,
        memo: str | _UnsetType = UNSET,
        tags: list[str] | _UnsetType = UNSET,
    ) -> Transaction:
        """Partial update: a field left as UNSET keeps its existing
        value; a field explicitly passed (including memo="" or
        tags=[]) replaces it — see the UNSET sentinel's docstring for
        why None can't play this role. Only supplied fields are
        validated. Raises TransactionNotFoundError (reused directly
        from the persistence layer — it is already domain-meaningful,
        no translation needed) if `transaction_id` doesn't exist, and
        CategoryNotFoundError if a supplied `category` isn't
        registered."""
        existing = self.transactions.get_by_id(transaction_id)
        if existing is None:
            raise TransactionNotFoundError(f"transaction id {transaction_id} not found")

        new_date = existing.date if date is UNSET else validate_date(date)
        new_type = (
            existing.type if transaction_type is UNSET else validate_transaction_type(transaction_type)
        )
        if category is UNSET:
            new_category = existing.category
        else:
            if not self.categories.exists(category):
                raise CategoryNotFoundError(f"category {category!r} not found")
            new_category = category
        new_amount = existing.amount if amount is UNSET else validate_amount(amount)
        new_memo = existing.memo if memo is UNSET else memo
        new_tags = existing.tags if tags is UNSET else list(tags)

        updated = Transaction(
            id=existing.id,
            type=new_type,
            date=new_date,
            amount=new_amount,
            category=new_category,
            memo=new_memo,
            tags=new_tags,
        )
        return self.transactions.update(updated)

    def delete_transaction(self, transaction_id: int) -> None:
        """TransactionRepository.delete() already raises
        TransactionNotFoundError for an unknown id — that is already
        the correct domain error, so it is not caught/re-raised here."""
        self.transactions.delete(transaction_id)

    # -- summary / budget ---------------------------------------------------------

    def monthly_summary(self, month: str, top: int) -> MonthlySummary:
        """Streams every transaction once, keeping only those whose
        `date` falls in `month`. Aggregates category totals from
        expense transactions only (income has no "category expense"
        meaning). Includes budget usage for the same month if one is
        set — budget never blocks a transaction, this is reporting
        only (docs/m03-architecture-design.md section 15)."""
        validated_month = validate_month(month)
        if top <= 0:
            raise ValidationError(f"top must be positive, got {top}")

        total_income = 0
        total_expense = 0
        category_expenses: dict[str, int] = {}
        has_transactions = False

        for transaction in self.transactions.iter_all():
            if transaction.date.strftime("%Y-%m") != validated_month:
                continue
            has_transactions = True
            if transaction.type == "income":
                total_income += transaction.amount
            else:
                total_expense += transaction.amount
                category_expenses[transaction.category] = (
                    category_expenses.get(transaction.category, 0) + transaction.amount
                )

        top_categories = sorted(
            category_expenses.items(), key=lambda item: item[1], reverse=True
        )[:top]

        budget = self.budgets.get(validated_month)
        if budget is None:
            budget_amount = None
            budget_usage_percent = None
            budget_exceeded = None
        else:
            budget_amount = budget.amount
            # budget.amount is validated positive by set_budget(), but
            # guard anyway rather than trust data that could have been
            # hand-edited on disk.
            budget_usage_percent = (total_expense / budget.amount * 100) if budget.amount else 0.0
            budget_exceeded = total_expense > budget.amount

        return MonthlySummary(
            month=validated_month,
            has_transactions=has_transactions,
            total_income=total_income,
            total_expense=total_expense,
            balance=total_income - total_expense,
            category_expenses=category_expenses,
            top_categories=top_categories,
            budget_amount=budget_amount,
            budget_usage_percent=budget_usage_percent,
            budget_exceeded=budget_exceeded,
        )

    def set_budget(self, month: str, amount: int) -> Budget:
        """Builds a Budget(month, amount) and delegates to
        BudgetRepository.set(), which replaces any existing record for
        that month rather than appending a duplicate."""
        validated_month = validate_month(month)
        validated_amount = validate_amount(amount)
        return self.budgets.set(Budget(month=validated_month, amount=validated_amount))

    # -- categories ---------------------------------------------------------------

    def add_category(self, name: str) -> None:
        """Duplicate protection is delegated to CategoryRepository.add()
        (it already raises DuplicateCategoryError) rather than
        re-checked here."""
        validated_name = validate_category_name(name)
        self.categories.add(validated_name)

    def list_categories(self) -> list[str]:
        return self.categories.list_all()

    def remove_category(self, name: str) -> None:
        """Streams TransactionRepository.iter_all() to check whether
        any transaction still references `name` *before* touching
        CategoryRepository. Raises CategoryInUseError if so — no
        cascade delete, no silent replacement. If nothing uses it,
        delegates removal to CategoryRepository (which raises
        CategoryNotFoundError if `name` isn't registered at all)."""
        in_use = any(transaction.category == name for transaction in self.transactions.iter_all())
        if in_use:
            raise CategoryInUseError(f"category {name!r} is in use by at least one transaction")
        self.categories.remove(name)

    # -- CSV import/export ---------------------------------------------------------

    def import_csv(self, path: Path) -> ImportResult:
        """Reads `path` as UTF-8 CSV with the CSV_FIELDNAMES header
        (extra columns are ignored, all 6 required ones must be
        present). File/schema-level problems — missing file, unreadable,
        not valid UTF-8, missing header, missing a required column —
        raise (PersistenceError or CSVFormatError) and abort before any
        row is processed: nothing is written in that case
        (docs/m03-architecture-design.md section 48).

        Once the header is valid, each data row is turned into an
        add_transaction() call — the exact same validation and
        category-existence rules as interactive add, not a duplicate
        implementation. A row that fails validation is skipped and
        counted, not the whole import (section 48). CSV never supplies
        an id; every imported row gets a fresh one via the normal
        add_transaction()/next_id() path, so existing transactions are
        never touched or overwritten."""
        try:
            handle = path.open("r", encoding="utf-8", newline="")
        except OSError as exc:
            raise PersistenceError(f"cannot open {path}: {exc}") from exc

        imported = 0
        skipped = 0
        errors: list[tuple[int, LedgerError]] = []

        try:
            with handle:
                reader = csv.DictReader(handle)
                fieldnames = reader.fieldnames
                if not fieldnames:
                    raise CSVFormatError(f"{path}: missing header row")
                missing_headers = [h for h in CSV_FIELDNAMES if h not in fieldnames]
                if missing_headers:
                    raise CSVFormatError(
                        f"{path}: missing required column(s): {', '.join(missing_headers)}"
                    )

                for row_number, row in enumerate(reader, start=1):
                    date = row.get("date") or ""
                    type_ = row.get("type") or ""
                    category = row.get("category") or ""
                    memo = row.get("memo") or ""
                    tags_raw = row.get("tags") or ""
                    try:
                        amount = validate_amount(row.get("amount") or "")
                        tags = parse_tags(tags_raw)
                        self.add_transaction(type_, date, category, amount, memo, tags)
                    except LedgerError as exc:
                        skipped += 1
                        errors.append((row_number, exc))
                        continue
                    imported += 1
        except UnicodeDecodeError as exc:
            raise PersistenceError(f"{path}: not valid UTF-8 ({exc})") from exc

        return ImportResult(imported=imported, skipped=skipped, errors=errors)

    def export_csv(
        self,
        path: Path,
        month: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> int:
        """Exactly one of `month` or (`from_date` and `to_date`) must be
        given — validated here (not only in cli.py) so LedgerService
        stays the single source of truth for the rule. Streams
        TransactionRepository.iter_all() directly into csv.DictWriter:
        no buffering, no reordering (unlike search(), export has no
        ordering requirement — file/insertion order is preserved) — O(1)
        extra memory regardless of file size (section 51). Internal ids
        are never written. Writes via a same-directory temp file +
        os.replace() (the same pattern as repository.py) so a failed
        export never leaves a half-written file at `path`; `path`'s
        parent directory is created if needed, and an existing file at
        `path` is overwritten on success."""
        has_month = month is not None
        has_range = from_date is not None or to_date is not None
        if has_month and has_range:
            raise ValidationError("export cannot combine --month with --from/--to")
        if has_month:
            validated_month = validate_month(month)
            validated_from = validated_to = None
        elif has_range:
            if from_date is None or to_date is None:
                raise ValidationError("export --from and --to must both be given together")
            validated_from = validate_date(from_date)
            validated_to = validate_date(to_date)
            if validated_from > validated_to:
                raise ValidationError("export --from must not be after --to")
            validated_month = None
        else:
            raise ValidationError("export requires --month or both --from and --to")

        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            tmp_fd, tmp_name = tempfile.mkstemp(
                dir=path.parent, prefix=f"{path.name}.", suffix=".tmp"
            )
        except OSError as exc:
            raise PersistenceError(f"cannot create output file near {path}: {exc}") from exc

        tmp_path = Path(tmp_name)
        count = 0
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
                writer.writeheader()
                for transaction in self.transactions.iter_all():
                    if validated_month is not None:
                        if transaction.date.strftime("%Y-%m") != validated_month:
                            continue
                    else:
                        if transaction.date < validated_from or transaction.date > validated_to:
                            continue
                    writer.writerow(
                        {
                            "date": transaction.date.isoformat(),
                            "type": transaction.type,
                            "category": transaction.category,
                            "amount": transaction.amount,
                            "memo": transaction.memo,
                            "tags": ",".join(transaction.tags),
                        }
                    )
                    count += 1
            os.replace(tmp_path, path)
        except BaseException:
            tmp_path.unlink(missing_ok=True)
            raise

        return count
