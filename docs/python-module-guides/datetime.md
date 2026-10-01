# `datetime` 날짜 처리 흐름

이 문서는 M03가 날짜 글자를 실제 날짜 객체로 바꾸고, 월별 조건과 저장 문자열로 쓰는
과정을 설명한다.

## 1. import와 문법

```python
# ledger/validators.py, ledger/models.py
import datetime

datetime.date.fromisoformat("2026-09-16")
```

`datetime`은 Python 표준 모듈이다. M03에서 `datetime.date`는 시각 없이 연·월·일만 가진
날짜 객체다. `Transaction`은 날짜를 이 객체로 보관한다.

## 2. M03에서 왜 필요한가

`"2026-02-30"`처럼 모양은 맞아도 없는 날짜를 막고, 검색 범위에서 날짜를 정확히 비교해야
한다. 단순 글자보다 `date` 객체가 이 일을 안전하게 한다.

## 3. 실제 핵심 기능

```python
# validators.py
return datetime.date.fromisoformat(raw)

# models.py
"date": self.date.isoformat()
date=datetime.date.fromisoformat(data["date"])
```

- `date.fromisoformat(raw)`: `YYYY-MM-DD` 문자열을 실제 날짜로 파싱한다.
- `date.isoformat()`: 날짜 객체를 저장·CSV용 `YYYY-MM-DD` 문자열로 바꾼다.
- `transaction.date.strftime("%Y-%m")`: 월별 요약·내보내기에서 `YYYY-MM`을 얻는다.
- `<`, `>`: 검색 범위에서 날짜를 비교한다.

## 4. 동작 순서

```text
"2026-09-16" (CLI/CSV 글자)
↓ validate_date()
datetime.date(2026, 9, 16)
↓ Transaction.date
검색·월별 요약에 사용
↓ isoformat()
"2026-09-16" (JSONL/CSV 저장 글자)
```

`validate_date()`는 M03가 만든 함수이고, `date.fromisoformat()`은 Python의 기능이다.
`ValueError`가 나면 M03는 `InvalidDateError`로 바꿔 사용자에게 알려 준다.

## 5. 만들어지는 객체·구조

입력은 `str`, 검증 후 Transaction의 `date` 필드는 `datetime.date`다. 반면 `Budget.month`와
`MonthlySummary.month`는 일이 없는 `"YYYY-MM"` 문자열이다.

## 6. M03 코드와 연결

`ledger/validators.py`의 `validate_date()`가 입구다. `ledger/models.py`의
`Transaction.to_dict()`/`from_dict()`가 파일 경계의 변환을 담당하고,
`ledger/services.py`가 검색·월별 요약·CSV 기간 필터에서 날짜를 비교한다.

## 외워둘 5줄

```text
datetime.date는 시간 없는 실제 달력 날짜 객체다.
fromisoformat()은 YYYY-MM-DD 글자를 날짜로 바꾼다.
isoformat()은 날짜를 저장하기 좋은 YYYY-MM-DD 글자로 바꾼다.
Transaction.date는 date 객체이고 Budget.month는 문자열이다.
날짜 객체가 있어야 잘못된 달력 날짜와 범위 비교를 처리할 수 있다.
```

