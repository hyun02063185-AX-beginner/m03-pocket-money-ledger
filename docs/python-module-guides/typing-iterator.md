# Type Hint와 `Iterator[Transaction]` 읽기

이 문서는 `iter_all(self) -> Iterator[Transaction]`을 읽는 데 필요한 type hint와
`Iterator`의 출처를 설명한다.

## 1. import와 문법

```python
# ledger/repository.py
from typing import Iterable, Iterator

def iter_all(self) -> Iterator[Transaction]:
    ...
```

`Iterator`는 Python의 `typing` 모듈이 제공하는 타입 표기다. `Transaction`은 Python에
원래 있는 타입이 아니라 `ledger.models`에서 M03가 만든 class다.

## 2. Type Hint란 무엇인가

```python
name: str
amount: int
def set_budget(...) -> Budget:
def iter_all(...) -> Iterator[Transaction]:
```

콜론 뒤는 값의 예상 타입, `->` 뒤는 함수가 돌려주는 값의 예상 타입을 적는다. Python은
기본적으로 이를 실행 중에 강제하지 않는다. 사람·편집기·타입 검사 도구가 코드를 이해하는
설명에 가깝다.

`argparse`의 `type=int`와 혼동하지 말자. 그것은 CLI 입력 글자 `"5"`를 실제 `int`로
변환하는 **실행 기능**이고, `amount: int`는 값이 정수여야 한다는 **타입 표기**다.

## 3. `Iterator[Transaction]`의 뜻

```text
Iterator        = next()로 다음 값을 하나씩 꺼낼 수 있는 Python의 반복 객체
[Transaction]   = 꺼낼 값의 예상 타입이 M03 Transaction 객체
```

따라서 `iter_all()`은 Transaction 목록을 즉시 만드는 함수가 아니라, 다음 거래를 요청할
때마다 하나씩 내놓는 반복 객체를 돌려준다는 뜻이다.

## 4. 실제 흐름

```python
def iter_all(self) -> Iterator[Transaction]:
    for record in _iter_jsonl(self.path):
        yield Transaction.from_dict(record)
```

```text
_iter_jsonl()이 dict 하나를 제공
↓
Transaction.from_dict(record)
↓
Transaction 하나
↓ yield
Iterator[Transaction]을 쓰는 for 문으로 전달
```

`Iterable[dict]`는 `_atomic_write_jsonl()`이 받을 수 있는 “dict를 차례로 제공하는 값”의
표기다. list도 Generator도 iterable일 수 있다.

## 5. 만들어지는 객체·구조

호출 결과는 `Iterator[Transaction]`이라는 type hint에 맞는 Generator 객체다. 실제 거래는
호출 직후 전부 생성되지 않고, 반복할 때 `Transaction` 객체 하나씩 만들어진다.

## 6. M03 코드와 연결

`ledger/repository.py`의 `_iter_jsonl()`은 `Iterator[dict]`, `iter_all()`은
`Iterator[Transaction]`으로 표기한다. `LedgerService`의 목록·검색·요약·CSV 내보내기는
모두 이 반복 결과를 `for`로 소비한다.

## 외워둘 5줄

```text
Type Hint는 Python 코드의 예상 타입을 적는 설명이다.
-> T는 함수가 T를 돌려준다는 뜻이다.
Iterator는 next()나 for로 값을 하나씩 꺼내는 Python 반복 객체다.
Transaction은 M03가 만든 사용자 정의 class다.
argparse type=int는 실행 변환이고 amount: int는 타입 표기다.
```
