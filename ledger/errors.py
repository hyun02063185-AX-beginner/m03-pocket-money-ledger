"""Exception hierarchy for the ledger.

Every user-facing failure should raise one of these. All LedgerError
subclasses map to the same exit code (1) via handle_errors — they
exist to shape the user-facing message/hint text, not to select a
distinct exit code (see docs/m03-architecture-design.md, section 23).

Sprint 1 added the persistence-level subclasses raised by
ledger/repository.py. Sprint 2 adds the validation and business-rule
subclasses raised by ledger/validators.py and ledger/services.py.
Several Sprint 1 classes are deliberately reused as-is at the Service
boundary rather than wrapped in a new class — see
docs/m03-architecture-design.md section 35 for which ones and why.
Sprint 4 puts CSVFormatError to use for the first time (CSV
schema/header problems) and reuses PersistenceError as-is for CSV
file I/O problems (file missing, unreadable, not valid UTF-8) — see
section 48 for the file-level-vs-row-level distinction.
"""


class LedgerError(Exception):
    """Base class for all expected ledger errors. Any exception NOT in
    this hierarchy is a programming bug and must propagate unhandled."""


class ValidationError(LedgerError):
    """Raised when user input fails validation (bad amount, date, etc.).
    Base class for the more specific field validators below; also
    raised directly for validation that doesn't warrant its own
    subclass (e.g. an empty category name)."""


class InvalidDateError(ValidationError):
    """Raised by validators.validate_date() for a malformed/non-ISO date."""


class InvalidMonthError(ValidationError):
    """Raised by validators.validate_month() for a non-YYYY-MM string."""


class InvalidAmountError(ValidationError):
    """Raised by validators.validate_amount() for a non-positive or
    non-integer amount."""


class InvalidTransactionTypeError(ValidationError):
    """Raised by validators.validate_transaction_type() for anything
    other than "income" or "expense"."""


class NotFoundError(LedgerError):
    """Base class for 'referenced id/name does not exist' errors."""


class PersistenceError(LedgerError):
    """Raised when reading or writing a data file fails, or when the
    file's on-disk state can't be trusted (e.g. a duplicate id)."""


class DataFormatError(PersistenceError):
    """Raised when a JSONL line cannot be parsed as valid JSON."""


class DuplicateTransactionIdError(PersistenceError):
    """Raised by TransactionRepository.add() when the given id already exists."""


class TransactionNotFoundError(NotFoundError):
    """Raised by TransactionRepository.update()/delete() for an unknown
    id, and reused as-is by LedgerService.update_transaction()/
    delete_transaction() — no translation needed, it is already a
    domain-meaningful error at the Service boundary."""


class DuplicateCategoryError(PersistenceError):
    """Raised by CategoryRepository.add() when the name already exists,
    and reused as-is by LedgerService.add_category()."""


class CategoryNotFoundError(NotFoundError):
    """Raised by CategoryRepository.remove() for an unknown name, and
    also by LedgerService when a Transaction references a category
    that isn't registered (add/update) — one class covers both "the
    name doesn't exist" situations."""


class CategoryInUseError(LedgerError):
    """Raised by LedgerService.remove_category() when at least one
    transaction still references the category. Not a NotFoundError
    (the category exists) and not a ValidationError (the *removal
    request* is well-formed input) — it's a business-rule conflict
    between two pieces of existing state, so it gets its own direct
    LedgerError subclass."""


class BudgetNotFoundError(NotFoundError):
    """Raised by BudgetRepository.remove() for a month with no budget set."""


class CSVFormatError(LedgerError):
    """Raised by LedgerService.import_csv() for a schema-level problem
    (missing header row, missing a required column) — a whole-file
    failure, distinct from a single invalid data row (which is
    skipped and counted, not raised as an exception)."""
