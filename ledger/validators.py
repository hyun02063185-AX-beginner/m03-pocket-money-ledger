"""Input validation helpers — the only place raw, CLI-shaped values
(strings, plain ints) get turned into validated domain values or
rejected with a meaningful ValidationError subclass.

No printing, no input(), no argparse here (docs/m03-architecture-design.md
section 16) — these are pure functions LedgerService calls; cli.py (a
later sprint) will translate the raised exceptions into
"[오류] ...\n[힌트] ..." output.
"""

from __future__ import annotations

import datetime
import re

from ledger.errors import (
    InvalidAmountError,
    InvalidDateError,
    InvalidMonthError,
    InvalidTransactionTypeError,
    ValidationError,
)

_MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
_VALID_TRANSACTION_TYPES = ("income", "expense")


def validate_date(raw: str) -> datetime.date:
    """Must be exactly "YYYY-MM-DD" and a real calendar date. Returns a
    datetime.date, matching Transaction.date's in-memory type.
    date.fromisoformat() is strict about this exact format on
    Python 3.10 (no partial/extended ISO forms), so no extra regex is
    needed here."""
    if not isinstance(raw, str):
        raise InvalidDateError(f"date must be a string, got {raw!r}")
    try:
        return datetime.date.fromisoformat(raw)
    except ValueError as exc:
        raise InvalidDateError(f"invalid date {raw!r}: expected YYYY-MM-DD") from exc


def validate_month(raw: str) -> str:
    """Must be exactly "YYYY-MM" with a zero-padded 01-12 month. Stays a
    str (Budget.month/monthly_summary's `month` are str, not date —
    there is no day component to represent)."""
    if not isinstance(raw, str) or not _MONTH_RE.match(raw):
        raise InvalidMonthError(f"invalid month {raw!r}: expected YYYY-MM")
    return raw


def validate_amount(value: int | str) -> int:
    """Must be a positive integer. Accepts an int as-is (the common
    case — argparse's `type=int` already converts CLI input before
    Service ever sees it) or a numeric string (for a future caller
    like CSV import, which reads raw strings from csv.DictReader)."""
    if isinstance(value, str):
        try:
            value = int(value.strip())
        except ValueError:
            raise InvalidAmountError(f"amount must be an integer, got {value!r}") from None
    if not isinstance(value, int) or isinstance(value, bool):
        raise InvalidAmountError(f"amount must be an integer, got {value!r}")
    if value <= 0:
        raise InvalidAmountError(f"amount must be positive, got {value}")
    return value


def validate_transaction_type(raw: str) -> str:
    """Must be exactly "income" or "expense" — case-sensitive, matching
    the literal strings persisted on disk (no case-folding is applied
    anywhere else in the pipeline, so accepting "Income" here would
    silently diverge from what's actually stored)."""
    if raw not in _VALID_TRANSACTION_TYPES:
        raise InvalidTransactionTypeError(
            f"type must be one of {_VALID_TRANSACTION_TYPES}, got {raw!r}"
        )
    return raw


def validate_category_name(raw: str) -> str:
    """Must be a non-empty string once surrounding whitespace is
    stripped. Returns the stripped name (so "  food  " and "food"
    register as the same category)."""
    if not isinstance(raw, str):
        raise ValidationError(f"category name must be a string, got {raw!r}")
    name = raw.strip()
    if not name:
        raise ValidationError("category name must not be empty")
    return name


def parse_tags(raw: str) -> list[str]:
    """Comma-separated tags: split, strip each segment, drop empty
    segments. " meal, lunch ,, work " -> ["meal", "lunch", "work"]. A
    literal comma inside one tag is not supported.

    Not really "validation" — it never raises, an empty/blank input
    just yields []. It lives here (not in cli.py, where it was first
    written in Sprint 3) because Sprint 4's LedgerService.import_csv()
    needs the exact same parsing and Service must never depend on
    cli.py (docs/m03-architecture-design.md section 49). cli.py's
    interactive `add` prompt and `update --tags` both import this
    same function instead of keeping their own copy."""
    return [segment.strip() for segment in raw.split(",") if segment.strip()]
