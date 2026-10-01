# `re` 정규표현식 사용 흐름

이 문서는 M03가 월 입력 `YYYY-MM`의 **모양**을 먼저 확인하는 방식을 설명한다.

## 1. import와 문법

```python
# ledger/validators.py
import re

_MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
```

`re`는 Python 표준 정규표현식 모듈이다. 정규표현식은 글자가 정한 패턴과 맞는지 검사하는
규칙이다. `_MONTH_RE`은 M03가 만든 변수이고, `re.compile()`은 Python이 제공한다.

## 2. M03에서 왜 필요한가

예산 설정과 월별 요약은 날짜 전체가 아니라 `2026-09`처럼 달만 받는다. `datetime.date`는
일이 필요하므로 그대로 쓰지 않고, 정규표현식으로 연 4자리·하이픈·01~12월인지 확인한다.

## 3. 실제 핵심 기능

```python
def validate_month(raw: str) -> str:
    if not isinstance(raw, str) or not _MONTH_RE.match(raw):
        raise InvalidMonthError(...)
    return raw
```

- `r"..."`: 백슬래시를 그대로 쓰기 편한 raw 문자열이다.
- `^`, `$`: 문자열 처음부터 끝까지 맞아야 한다.
- `\d{4}`: 숫자 네 자리다.
- `(0[1-9]|1[0-2])`: `01`부터 `12`만 허용한다.
- `match(raw)`: 시작 부분이 규칙과 맞는지 검사한다. `^`와 `$`가 있어 전체 검사다.

## 4. 동작 순서

```text
summary --month 2026-09
↓ LedgerService.monthly_summary()
↓ validate_month("2026-09")
_MONTH_RE.match(...) 성공
↓
"2026-09" 문자열을 그대로 월별 비교에 사용
```

`2026-9`, `2026-00`, `2026-13`, `2026-09-extra`는 통과하지 못한다. 통과해도 실제 일자가
검증된 것은 아니다. 날짜 전체는 `validate_date()`와 `datetime`이 담당한다.

## 5. 만들어지는 객체·구조

`re.compile()`은 재사용 가능한 패턴 객체를 만든다. `validate_month()`는 통과한 입력을
새 객체로 바꾸지 않고 `str` 그대로 반환한다.

## 6. M03 코드와 연결

`ledger/validators.py`에서만 `re`를 import한다. `LedgerService.monthly_summary()`,
`set_budget()`, `export_csv(month=...)`가 `validate_month()`를 통해 같은 규칙을 공유한다.

## 외워둘 5줄

```text
re는 문자열 패턴을 검사하는 Python 표준 모듈이다.
compile()은 반복해서 쓸 패턴 객체를 만든다.
^와 $는 문자열 전체가 맞는지 확인하게 한다.
M03의 월 패턴은 YYYY-MM과 01~12월만 허용한다.
정규표현식은 글자 모양을, datetime은 실제 날짜를 확인한다.
```
