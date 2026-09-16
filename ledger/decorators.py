"""Cross-cutting decorators — and the error-to-message mapping the one
decorator (plus the interactive add/update retry prompts in cli.py)
both use, so there is exactly one place that owns "[오류]/[힌트]"
wording (docs/m03-architecture-design.md section 42).
"""

from __future__ import annotations

import sys
from functools import wraps
from typing import Callable

from ledger.errors import (
    CategoryInUseError,
    CategoryNotFoundError,
    CSVFormatError,
    DuplicateCategoryError,
    InvalidAmountError,
    InvalidDateError,
    InvalidMonthError,
    InvalidTransactionTypeError,
    LedgerError,
    TransactionNotFoundError,
)

_ERROR_MESSAGES: dict[type[LedgerError], tuple[str, str]] = {
    InvalidDateError: (
        "날짜 형식이 올바르지 않습니다.",
        "YYYY-MM-DD 형식으로 입력하세요. 예: 2026-09-16",
    ),
    InvalidMonthError: (
        "월 형식이 올바르지 않습니다.",
        "YYYY-MM 형식으로 입력하세요. 예: 2026-09",
    ),
    InvalidAmountError: (
        "금액은 0보다 큰 정수여야 합니다.",
        "예: 15000",
    ),
    InvalidTransactionTypeError: (
        "거래 타입이 올바르지 않습니다.",
        "income 또는 expense를 입력하세요.",
    ),
    CategoryNotFoundError: (
        "등록되지 않은 카테고리입니다.",
        "category list로 확인하거나 category add로 먼저 등록하세요.",
    ),
    CategoryInUseError: (
        "사용 중인 카테고리는 삭제할 수 없습니다.",
        "해당 거래의 카테고리를 먼저 수정하세요.",
    ),
    TransactionNotFoundError: (
        "존재하지 않는 거래 ID입니다.",
        "list 명령으로 거래 ID를 확인하세요.",
    ),
    DuplicateCategoryError: (
        "이미 등록된 카테고리입니다.",
        "category list로 기존 카테고리를 확인하세요.",
    ),
    CSVFormatError: (
        "CSV 형식이 올바르지 않습니다.",
        "헤더가 date,type,category,amount,memo,tags 형식인지 확인하세요.",
    ),
}


def describe_error(exc: LedgerError) -> tuple[str, str]:
    """Maps a LedgerError to a (원인, 힌트) pair for CLI display.

    Checked in insertion order, so a subclass listed above its base
    class wins — none of the current entries overlap, but the order is
    kept intentional in case that changes. Falls back to the
    exception's own message when there is no fixed Korean copy for its
    type (e.g. a plain ValidationError from
    LedgerService.list_transactions()'s limit check) — that message is
    already descriptive, just not pre-translated.
    """
    for exc_type, pair in _ERROR_MESSAGES.items():
        if isinstance(exc, exc_type):
            return pair
    return str(exc) or exc.__class__.__name__, "입력값을 다시 확인하세요."


def handle_errors(func: Callable[..., None]) -> Callable[..., int]:
    """Wraps the CLI dispatch boundary (ledger/cli.py::_dispatch): runs
    `func` and, if it raises a LedgerError, prints
    "[오류] ...\\n[힌트] ..." to stderr and returns exit code 1 instead
    of propagating. Returns 0 if `func` completes normally.

    Deliberately narrow: only LedgerError (and its subclasses) is
    caught. Anything else — a real programming bug (KeyError,
    AttributeError, etc.) — is NOT caught here and propagates with its
    traceback, so bugs stay visible during development instead of
    being silently reported as ordinary user mistakes
    (docs/m03-architecture-design.md section 41)."""

    @wraps(func)
    def wrapper(*args, **kwargs) -> int:
        try:
            func(*args, **kwargs)
        except LedgerError as exc:
            message, hint = describe_error(exc)
            print(f"[오류] {message}", file=sys.stderr)
            print(f"[힌트] {hint}", file=sys.stderr)
            return 1
        return 0

    return wrapper
