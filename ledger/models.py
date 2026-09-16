"""Shared data structures for the ledger.

Sprint 1 made Transaction and Budget real (id/round-trip logic via
to_dict()/from_dict()). Sprint 2 adds MonthlySummary — LedgerService's
computed result type, shared between services.py and the future
cli.py the same way Transaction/Budget are shared between repository.py
and services.py. See docs/m03-architecture-design.md section 4 for
field rationale (id is a plain int, not the display string
"TX-000012"; Budget is a single month-wide total, not per-category)
and section 36 for MonthlySummary's fields and semantics.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field

from ledger.errors import LedgerError


@dataclass
class Transaction:
    """A single income/expense record. One transactions.jsonl line.

    `id` is the internal storage id (positive int, first is 1, next is
    max(existing) + 1). Any "TX-000012"-style display formatting is a
    cli.py presentation concern only — never stored or passed back in.
    `date` is a real datetime.date in memory; to_dict()/from_dict() are
    the only places that know it is persisted as an ISO "YYYY-MM-DD"
    string.
    """

    id: int
    type: str  # "income" | "expense"
    date: datetime.date
    amount: int  # positive integer
    category: str
    memo: str = ""
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "date": self.date.isoformat(),
            "amount": self.amount,
            "category": self.category,
            "memo": self.memo,
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, data: dict) -> Transaction:
        return cls(
            id=int(data["id"]),
            type=str(data["type"]),
            date=datetime.date.fromisoformat(data["date"]),
            amount=int(data["amount"]),
            category=str(data["category"]),
            memo=str(data.get("memo", "")),
            tags=list(data.get("tags", [])),
        )


@dataclass
class Budget:
    """The single total budget for one calendar month (not per-category)."""

    month: str  # "YYYY-MM", unique key
    amount: int  # positive integer

    def to_dict(self) -> dict:
        return {"month": self.month, "amount": self.amount}

    @classmethod
    def from_dict(cls, data: dict) -> Budget:
        return cls(month=str(data["month"]), amount=int(data["amount"]))


@dataclass
class SearchCriteria:
    """Filters for LedgerService.search() — exactly the 6 official
    search options (--from, --to, --category, --type, --q, --tag). No
    min/max amount: not part of Mission Core. All filters are ANDed
    together; any left as None is not applied.

    Match semantics (docs/m03-architecture-design.md section 37):
    from_date/to_date are inclusive bounds on Transaction.date;
    category/transaction_type/tag are exact, case-sensitive matches;
    query is a case-insensitive substring match against memo only.
    """

    from_date: datetime.date | None = None
    to_date: datetime.date | None = None
    transaction_type: str | None = None
    category: str | None = None
    query: str | None = None
    tag: str | None = None


@dataclass
class MonthlySummary:
    """LedgerService.monthly_summary()'s result. A plain computed
    value, never persisted — no to_dict()/from_dict() needed.

    `has_transactions` lets cli.py (a later sprint) print a clear
    "데이터 없음" message without inspecting other fields; the numeric
    fields are still well-defined zeros/empties when it's False rather
    than None, so callers never need a special case just to sum them.

    budget_amount/budget_usage_percent/budget_exceeded are all None
    together when no Budget is set for `month` — budgets are opt-in
    per month, not a "0 = no budget" convention.
    """

    month: str
    has_transactions: bool
    total_income: int
    total_expense: int
    balance: int
    category_expenses: dict[str, int]
    top_categories: list[tuple[str, int]]
    budget_amount: int | None
    budget_usage_percent: float | None
    budget_exceeded: bool | None


@dataclass
class ImportResult:
    """LedgerService.import_csv()'s result (docs/m03-architecture-design.md
    section 48). `errors` holds the raw LedgerError for each skipped
    row (1-indexed by data row, header excluded) rather than a
    pre-formatted string, so cli.py can reuse the exact same
    describe_error() mapping it uses for every other error instead of
    Service building "[건너뜀] ..." text itself."""

    imported: int
    skipped: int
    errors: list[tuple[int, LedgerError]]
