# `collections.deque` 사용 흐름

이 문서는 `list --limit N`이 큰 JSONL 파일에서도 최근 N건만 유지하는 방식을 설명한다.

## 1. import와 문법

```python
from collections import deque

recent: deque[Transaction] = deque(maxlen=limit)
```

`deque`는 Python이 제공하는 양쪽 끝에서 빠르게 넣고 뺄 수 있는 컨테이너다.
`deque(maxlen=N)`은 최대 N개만 보관하며, 새 항목이 들어와 꽉 차면 가장 오래된 항목을
자동으로 버린다.

## 2. M03에서 왜 필요한가

`LedgerService.list_transactions(limit)`은 전체 거래를 읽어야 마지막 입력 N건을 알 수
있지만, 전체를 list에 쌓을 필요는 없다. JSONL을 한 줄씩 주는 `iter_all()`과 `deque`를
합치면 메모리에는 최근 N개의 Transaction만 남는다.

## 3. 실제 핵심 기능

```python
# ledger/services.py
recent: deque[Transaction] = deque(maxlen=limit)
for transaction in self.transactions.iter_all():
    recent.append(transaction)
return list(reversed(recent))
```

`append()`가 11번째 항목을 넣을 때 `maxlen=10`이면 첫 항목이 자동으로 빠진다.
마지막에는 `reversed(recent)`로 최근 입력부터 보이게 뒤집고, CLI가 출력하기 쉬운 list로
바꾼다.

## 4. 동작 순서

```text
iter_all()이 Transaction을 파일 순서대로 하나씩 yield
↓
deque(maxlen=3)에 append
[1] → [1, 2] → [1, 2, 3] → [2, 3, 4]
↓
reversed(...)
[4, 3, 2]  (화면에 보낼 최근 3건)
```

여기서 `iter_all()`/`Transaction`은 M03의 코드, `deque`/`reversed`/`list`는 Python 기능이다.

## 5. 만들어지는 객체·구조

반복 중 `recent`는 `deque[Transaction]`이고 최대 길이는 `limit`이다. 반환 직전에는
`list[Transaction]`이 된다. `limit <= 0`이면 M03는 `ValidationError`를 낸다.

## 6. M03 코드와 연결

이 사용처는 `ledger/services.py`의 `list_transactions()` 한 곳이다. “최근”은 날짜가 가장
늦은 거래가 아니라 JSONL에 가장 나중에 추가된 거래(가장 큰 id)라는 뜻이다.

## 외워둘 5줄

```text
deque(maxlen=N)는 최대 N개를 보관한다.
꽉 찬 deque에 append하면 가장 오래된 항목이 자동으로 빠진다.
M03는 Generator가 주는 Transaction을 하나씩 deque에 넣는다.
그래서 list --limit N의 추가 메모리는 N건에 비례한다.
마지막 reversed()는 최신 입력을 먼저 보여 주기 위한 것이다.
```

