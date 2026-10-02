"""입력 검증 헬퍼 — CLI 형태의 원시 값(문자열, 단순 int)을 검증된
도메인 값으로 바꾸거나, 의미 있는 ValidationError 하위 클래스로
거부하는 유일한 곳이다.

여기에는 print도, input()도, argparse도 전혀 없다
(docs/m03-architecture-design.md 16번 섹션) — 모두 LedgerService가
호출하는 순수 함수들이며, 발생한 예외를
"[오류] ...\n[힌트] ..." 출력으로 변환하는 일은 (이후 스프린트의)
cli.py가 담당한다.
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
    """정확히 "YYYY-MM-DD" 형식이면서 실제로 존재하는 날짜여야 한다.
    Transaction.date의 메모리상 타입과 맞게 datetime.date를
    반환한다. Python 3.10의 date.fromisoformat()은 이 정확한 형식만
    엄격하게 허용하므로(부분적인/확장된 ISO 형식은 허용하지 않음),
    여기서 별도의 정규식이 필요 없다."""
    if not isinstance(raw, str):
        raise InvalidDateError(f"date must be a string, got {raw!r}")
    try:
        return datetime.date.fromisoformat(raw)
    except ValueError as exc:
        raise InvalidDateError(f"invalid date {raw!r}: expected YYYY-MM-DD") from exc


def validate_month(raw: str) -> str:
    """정확히 "YYYY-MM" 형식이며, 월은 01-12 범위로 0으로 패딩되어야
    한다. str 그대로 유지한다(Budget.month와 monthly_summary의
    `month`는 date가 아니라 str이다 — 표현할 일(day) 요소가 없기
    때문이다)."""
    if not isinstance(raw, str) or not _MONTH_RE.match(raw):
        raise InvalidMonthError(f"invalid month {raw!r}: expected YYYY-MM")
    return raw


def validate_amount(value: int | str) -> int:
    """양의 정수여야 한다. int를 그대로 받아들이거나(일반적인 경우 —
    argparse의 `type=int`가 Service에 도달하기 전에 이미 CLI 입력을
    변환해 둔다), 숫자로 이루어진 문자열을 받아들인다(csv.DictReader가
    원시 문자열을 읽어오는 CSV import 같은 향후 호출자를 위함)."""
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
    """정확히 "income" 또는 "expense"여야 한다 — 디스크에 그대로
    저장되는 문자열과 일치하도록 대소문자를 구분한다(파이프라인
    어디에서도 대소문자를 통일하지 않으므로, 여기서 "Income"을
    받아들이면 실제로 저장되는 값과 조용히 달라지게 된다)."""
    if raw not in _VALID_TRANSACTION_TYPES:
        raise InvalidTransactionTypeError(
            f"type must be one of {_VALID_TRANSACTION_TYPES}, got {raw!r}"
        )
    return raw


def validate_category_name(raw: str) -> str:
    """둘러싼 공백을 제거했을 때 비어 있지 않은 문자열이어야 한다.
    공백이 제거된 이름을 반환한다(그래야 "  food  "와 "food"가 같은
    카테고리로 등록된다)."""
    if not isinstance(raw, str):
        raise ValidationError(f"category name must be a string, got {raw!r}")
    name = raw.strip()
    if not name:
        raise ValidationError("category name must not be empty")
    return name


def parse_tags(raw: str) -> list[str]:
    """쉼표로 구분된 태그: 분리하고, 각 조각의 공백을 제거하고, 빈
    조각은 버린다. " meal, lunch ,, work " -> ["meal", "lunch",
    "work"]. 태그 하나 안에 쉼표 문자를 그대로 쓰는 것은 지원하지
    않는다.

    엄밀히 말해 "검증"은 아니다 — 절대 예외를 던지지 않으며,
    비어 있거나 공백뿐인 입력은 그냥 []를 반환한다. 이 함수가 (Sprint
    3에서 처음 작성되었던) cli.py가 아니라 여기에 있는 이유는 Sprint
    4의 LedgerService.import_csv()가 정확히 같은 파싱 로직을
    필요로 하고, Service는 절대 cli.py에 의존해서는 안 되기
    때문이다(docs/m03-architecture-design.md 49번 섹션). cli.py의
    대화형 `add` 프롬프트와 `update --tags`도 각자 복사본을 두지
    않고 이 함수를 그대로 가져와 사용한다."""
    return [segment.strip() for segment in raw.split(",") if segment.strip()]
