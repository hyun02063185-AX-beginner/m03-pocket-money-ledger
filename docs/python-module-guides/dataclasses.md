# `dataclasses`와 모델 객체 사용 흐름

이 문서는 `@dataclass`가 M03의 `Transaction`, `Budget`, `MonthlySummary` 같은 모델을
어떻게 만드는지 설명한다.

## 1. import와 문법

```python
# ledger/models.py
from dataclasses import dataclass, field

@dataclass
class Transaction:
    id: int
    type: str
    date: datetime.date
    amount: int
    category: str
    memo: str = ""
    tags: list[str] = field(default_factory=list)
```

`dataclass`는 Python이 제공하는 class 작성 도우미다. 필드를 선언하면 객체를 만들기 위한
`__init__`과 보기 좋은 표현·비교 같은 기본 기능을 만들어 준다. `Transaction`은 M03가
정의한 사용자 모델이다.

## 2. M03에서 왜 필요한가

거래를 일반 `dict`로만 다루면 키 이름을 계속 문자열로 써야 하고, `"date"`가 날짜인지
금액인지 코드가 덜 분명해진다. `Transaction`은 `transaction.amount`, `transaction.date`
처럼 의미 있는 필드로 거래를 다루게 한다. 저장 파일과 주고받을 때만 `to_dict()`/
`from_dict()`를 사용한다.

## 3. 실제 핵심 기능

```python
transaction = Transaction(id=1, type="expense", date=validated_date,
                          amount=12000, category="food")
record = transaction.to_dict()
restored = Transaction.from_dict(record)
```

- `@dataclass`: 선언한 필드를 받는 생성 방식을 만든다.
- `field(default_factory=list)`: 새 Transaction마다 **새 빈 목록**을 만든다.
- `to_dict()`: `date`를 ISO 문자열로 바꿔 저장용 `dict`를 만든다.
- `from_dict()`: JSONL에서 읽은 `dict`를 Transaction으로 복원한다.

## 4. 동작 순서

```text
CLI/CSV의 입력
↓ LedgerService.add_transaction()
검증된 값
↓
Transaction(...) 객체 생성
↓ Transaction.to_dict()
JSONL 저장용 dict
↓
나중에 _iter_jsonl() → Transaction.from_dict()
↓
다시 Transaction 객체
```

## 5. 만들어지는 객체·구조

- `Transaction`: 한 건의 수입·지출. JSONL 한 줄과 대응한다.
- `Budget`: 한 달의 총 예산. `month`, `amount`를 가진다.
- `SearchCriteria`: 검색 조건을 모은 객체다.
- `MonthlySummary`: Service가 계산한 결과이며 파일에 저장하지 않는다.
- `ImportResult`: CSV 가져오기 성공·건너뜀·오류 정보를 담는다.

## 6. M03 코드와 연결

`ledger/models.py`가 모델을 정의한다. `LedgerService.add_transaction()`과
`update_transaction()`이 Transaction을 만들고, `TransactionRepository`가 `to_dict()`과
`from_dict()`으로 JSONL 경계를 넘는다.

## 외워둘 5줄

```text
@dataclass는 필드 중심의 class를 편하게 만든다.
Transaction은 Python 기본 내장형이 아니라 M03가 만든 사용자 정의 class다.
객체 안에서는 transaction.date처럼 필드를 사용한다.
저장할 때는 to_dict(), 읽을 때는 from_dict()를 쓴다.
default_factory=list는 객체마다 독립된 tags 목록을 만든다.
```

