# Type Hint 기본 읽기

이 문서는 B2-1 코드에 붙은 `name: str`, `amount: int`, `-> Budget` 같은 type hint를
초심자 관점에서 읽는 법을 설명한다.

## 1. 문법

```python
name: str
amount: int

def set_budget(self, month: str, amount: int) -> Budget:
    ...

def iter_all(self) -> Iterator[Transaction]:
    ...
```

`:` 뒤는 변수·매개변수에 기대하는 타입이고, `->` 뒤는 함수가 돌려주는 타입이다.
`str`, `int`는 Python 기본 타입, `Budget`과 `Transaction`은 B2-1가 정의한 class다.
`Iterator`의 자세한 뜻은 [typing-iterator.md](typing-iterator.md)를 보자.

## 2. 이것이 무엇인가

Type Hint는 코드에 붙이는 타입 설명이다. 예를 들어 `amount: int`는 “여기에는 정수가
와야 한다”는 의도를 나타낸다. 편집기의 자동완성·오류 탐지 도구와 다른 개발자가 코드를
읽는 데 도움을 준다.

## 3. B2-1에서 왜 필요한가

B2-1는 입력 글자, JSON `dict`, 날짜 객체, Transaction 객체를 오간다. 타입 표기가 있으면
어느 함수가 무엇을 받아 무엇을 주는지 빠르게 파악할 수 있다.

```python
def validate_date(raw: str) -> datetime.date: ...
def add_transaction(...) -> Transaction: ...
def list_transactions(self, limit: int) -> list[Transaction]: ...
```

위 표기만으로도 날짜 검증은 글자를 받아 `date` 객체를 만들고, 목록은 Transaction들의
list를 돌려준다는 흐름을 알 수 있다.

## 4. runtime 강제와의 차이

Type Hint만으로 Python이 모든 값을 막지는 않는다. 예를 들어 `amount: int`라고 적어도
함수 내부에서 실제 검증은 별도로 필요하다. B2-1는 `validate_amount()`가 양의 정수인지
검사한다.

```python
p_list.add_argument("--limit", type=int)
```

여기의 `type=int`는 hint가 아니다. `argparse`가 터미널의 `"5"`를 실행 중에 숫자 `5`로
변환하는 규칙이다.

## 5. 만들어지는 객체·구조

Type Hint는 보통 새 Runtime 객체를 만들지 않는다. `Budget(...)`을 실제 호출할 때 Budget
객체가 만들어지고, `Iterator[Transaction]` 표기는 `iter_all()` 결과를 설명할 뿐이다.
`from __future__ import annotations`는 이런 표기를 나중에 해석하도록 도와 class 정의
순서에 덜 얽매이게 한다.

## 6. B2-1 코드와 연결

`ledger/models.py`, `repository.py`, `services.py`, `validators.py`, `cli.py` 전반에 있다.
특히 `TransactionRepository.iter_all() -> Iterator[Transaction]`은 Generator 기반 읽기와
연결되고, `LedgerService.set_budget() -> Budget`은 반환 객체를 분명히 한다.

## 외워둘 5줄

```text
x: T는 x에 기대하는 타입 T를 적는 표기다.
-> T는 함수 결과에 기대하는 타입 T를 적는 표기다.
Type Hint는 기본적으로 실행 중 값을 자동 검증하지 않는다.
str·int는 Python 기본 타입, Transaction·Budget은 B2-1의 class다.
argparse type=int는 입력 변환 규칙이며 type hint가 아니다.
```
