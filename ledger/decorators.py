"""여러 곳에서 공통으로 쓰이는 데코레이터 — 그리고 이 데코레이터와
(cli.py의 대화형 add/update 재시도 프롬프트)가 함께 사용하는
오류-메시지 매핑. 그래서 "[오류]/[힌트]" 문구를 책임지는 곳이
정확히 한 곳만 존재한다(docs/m03-architecture-design.md 42번
섹션).
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
    """LedgerError를 CLI 출력을 위한 (원인, 힌트) 쌍으로 매핑한다.

    등록된 순서대로 검사하므로, 기반 클래스보다 위에 적힌 하위
    클래스가 우선 적용된다 — 현재 항목들은 서로 겹치지 않지만,
    나중에 겹치게 될 경우를 대비해 이 순서는 의도적으로 유지한다.
    해당 타입에 대해 고정된 한국어 문구가 없는 경우(예:
    LedgerService.list_transactions()의 limit 검사에서 나오는 평범한
    ValidationError)에는 예외 자체의 메시지로 대체한다 — 그 메시지는
    이미 충분히 설명적이지만, 미리 번역해 두지 않았을 뿐이다.
    """
    for exc_type, pair in _ERROR_MESSAGES.items():
        if isinstance(exc, exc_type):
            return pair
    return str(exc) or exc.__class__.__name__, "입력값을 다시 확인하세요."


def handle_errors(func: Callable[..., None]) -> Callable[..., int]:
    """CLI 디스패치 경계(ledger/cli.py::_dispatch)를 감싼다: `func`를
    실행하고, LedgerError가 발생하면 전파하는 대신 stderr에
    "[오류] ...\\n[힌트] ..."를 출력하고 종료 코드 1을 반환한다.
    `func`가 정상적으로 끝나면 0을 반환한다.

    의도적으로 범위를 좁게 잡았다: LedgerError(와 그 하위 클래스)만
    잡는다. 그 외의 것 — 진짜 프로그래밍 버그(KeyError, AttributeError
    등) — 는 여기서 잡히지 않고 트레이스백과 함께 그대로 전파된다.
    그래야 버그가 평범한 사용자 실수로 조용히 처리되지 않고 개발
    중에도 눈에 보이게 된다(docs/m03-architecture-design.md 41번
    섹션)."""

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
