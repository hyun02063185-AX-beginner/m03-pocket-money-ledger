# Generator와 `yield` 사용 흐름

이 문서는 `TransactionRepository.iter_all()`이 모든 거래를 list로 만들지 않고, JSONL을
한 줄씩 읽어 `Transaction`을 보내는 이유를 설명한다.

## 1. 문법: `yield`가 있으면 Generator 함수

```python
def iter_all(self) -> Iterator[Transaction]:
    for record in _iter_jsonl(self.path):
        yield Transaction.from_dict(record)
```

함수 본문에 `yield`가 있으면 Python은 일반 함수처럼 한 번에 `return`하지 않는다. 호출할
때 **Generator 객체**를 만들고, `next()`나 `for`가 다음 값을 요청할 때까지 실행을 멈춘다.
`yield`와 Generator는 Python 기능이고, `iter_all()`과 `_iter_jsonl()`은 M03가 만든 함수다.

## 2. M03에서 왜 필요한가

거래 파일은 커질 수 있다. `list`나 `summary`가 `list(self.iter_all())`처럼 먼저 전부
읽으면 메모리에 모든 거래를 올려야 한다. M03는 필요한 처리와 함께 한 줄씩 읽어
Generator의 장점을 쓴다.

## 3. JSONL에서 Transaction까지

```python
# ledger/repository.py
def _iter_jsonl(path: Path) -> Iterator[dict]:
    with path.open("r", encoding="utf-8") as f:
        for raw_line in f:
            ...
            yield json.loads(line)

def iter_all(self) -> Iterator[Transaction]:
    for record in _iter_jsonl(self.path):
        yield Transaction.from_dict(record)
```

```text
JSONL 한 줄 (문자열)
↓ json.loads()
dict
↓ Transaction.from_dict()
Transaction 객체
↓ yield
호출한 쪽의 for 문
```

JSONL은 한 줄에 JSON 객체 하나인 파일 형식이라, 한 줄씩 스트리밍하기에 잘 맞는다.

## 4. Generator, Iterator, `next`, `for`

```python
stream = repo.iter_all()       # 아직 모든 파일을 읽지 않음
first = next(stream)           # 첫 Transaction 하나를 요청
for transaction in stream:     # 남은 것을 하나씩 요청
    ...
```

Generator는 Iterator의 한 종류다. Iterator는 `next()`로 다음 값을 얻을 수 있는 객체이고,
`for`는 내부에서 `next()`를 반복 호출한다. 더 이상 값이 없으면 반복이 끝난다.

## 5. list와 비교

```text
list:       호출 시 모든 항목을 저장해 즉시 접근·여러 번 순회가 쉬움
Generator:  요청할 때 하나씩 만들므로 메모리가 적게 들지만 한 번 소비하면 끝남
```

M03의 `list_transactions()`는 Generator 전체를 저장하지 않고 `deque(maxlen=limit)`에 최근
N건만 둔다. 반면 `search()`는 모든 일치 결과를 최신순으로 돌려줘야 하므로 일치한 항목을
list에 모은다. Generator가 항상 list보다 좋은 것이 아니라 목적에 맞게 고른 것이다.

## 6. 실제 M03 코드와 연결

`iter_all()`을 다음 코드가 소비한다.

- `next_id()`, `get_by_id()`, update/delete: 필요한 거래를 찾는다.
- `list_transactions()`: `deque`와 결합해 최근 N건을 유지한다.
- `search()`, `monthly_summary()`, `remove_category()`: 읽는 즉시 조건·집계를 한다.
- `export_csv()`: 거래 한 건씩 CSV 행으로 쓴다.

## 외워둘 5줄

```text
yield가 있는 함수는 호출 시 Generator 객체를 돌려준다.
Generator는 Iterator이므로 next()와 for로 하나씩 소비한다.
M03는 JSONL 한 줄을 dict, 이어서 Transaction으로 바꿔 yield한다.
모든 거래를 list로 만들지 않아 큰 파일에서도 메모리를 아낀다.
Generator는 한 번 소비하면 끝나며, 필요한 경우에만 list나 deque로 모은다.
```

