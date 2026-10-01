# `json` 모듈 사용 흐름

이 문서는 `ledger/repository.py` 전체를 설명하지 않는다. M03가
`import json`으로 가져온 기능이 **파일의 한 줄을 어떻게 Transaction으로 읽고,
반대로 어떻게 저장하는지**만 따라간다.

## 1. `import`와 M03에서의 역할

```python
# ledger/repository.py
import json
```

`json`은 JSON 형식의 글자와 Python 데이터를 서로 바꾸는 Python 표준 모듈이다.
별도로 설치할 필요가 없다.

M03는 거래·카테고리·예산을 데이터 폴더의 JSONL 파일에 저장한다. JSONL은
**한 줄에 JSON 객체 하나**를 놓는 형식이다. 예를 들어 거래 파일의 한 줄은
다음처럼 생긴다.

```json
{"id": 1, "type": "expense", "date": "2026-09-01", "amount": 12000, "category": "food", "memo": "점심", "tags": ["평일"]}
```

M03는 파일의 이 글자를 그대로 업무에 쓰지 않는다. 읽을 때는 Python `dict`와
`Transaction`으로 바꾸고, 저장할 때는 반대 방향으로 바꾼다.

## 2. M03가 실제로 꺼내 쓰는 기능

### `json.loads()` — JSON 한 줄을 Python `dict`로 읽기

```python
# ledger/repository.py: _iter_jsonl()
yield json.loads(line)
```

`loads`의 입력은 문자열(`str`)이다. 예를 들어 파일에서 읽은 JSON 글자는
다음의 Python `dict`가 된다.

```text
'{"id": 1, "amount": 12000}'
            ↓ json.loads()
{"id": 1, "amount": 12000}
```

왼쪽은 파일에서 온 글자이고, 오른쪽은 `record["amount"]`처럼 값을 꺼낼 수 있는
Python 딕셔너리다.

### `json.dumps()` — Python `dict`를 JSON 한 줄로 만들기

```python
# ledger/repository.py: _append_jsonl(), _atomic_write_jsonl()
f.write(json.dumps(record, ensure_ascii=False))
```

`dumps`는 반대 방향이다. Python `dict`를 파일에 쓸 JSON 문자열로 바꾼다.
`ensure_ascii=False`는 한글 메모나 카테고리를 `\u...` 형태 대신 읽을 수 있는
한글로 저장하도록 한다.

## 3. 읽기: JSONL 한 줄에서 `Transaction`까지

`TransactionRepository.iter_all()`은 거래 파일을 읽을 때 `_iter_jsonl()`을 쓴다.

```python
# ledger/repository.py
def iter_all(self) -> Iterator[Transaction]:
    for record in _iter_jsonl(self.path):
        yield Transaction.from_dict(record)
```

```text
data/transactions.jsonl의 한 줄
↓  파일에서 읽은 문자열(raw_line)
line = raw_line.strip()
↓
json.loads(line)
↓
dict  (record)
↓
Transaction.from_dict(record)
↓
Transaction 객체
↓
LedgerService가 목록·검색·요약 등에 사용
```

`Transaction.from_dict()`은 `ledger/models.py`에 있다. 이 메서드는 저장용
`dict`의 날짜 글자를 `datetime.date`로 되돌리고, 각 값을 `Transaction`의 필드로
넣는다. 즉 Repository는 JSON을 읽고, Model은 M03가 사용할 거래 객체를 복원한다.

파일의 한 줄이 깨져 JSON으로 읽을 수 없다면, `_iter_jsonl()`은
`json.JSONDecodeError`를 잡아 M03의 `DataFormatError`로 바꿔 알려 준다. 잘못된
파일 내용을 조용히 건너뛰지 않기 위한 연결이다.

## 4. 쓰기: `Transaction`에서 JSONL 한 줄까지

새 거래를 저장하는 핵심 연결은 다음과 같다.

```python
# ledger/repository.py: TransactionRepository.add()
_append_jsonl(self.path, transaction.to_dict())
```

```text
LedgerService.add_transaction()
↓
Transaction 객체
↓
transaction.to_dict()
↓
dict  (날짜도 "YYYY-MM-DD" 문자열로 바뀜)
↓
_append_jsonl(path, record)
↓
json.dumps(record, ensure_ascii=False)
↓
JSON 문자열
↓  "\n"을 하나 더 씀
data/transactions.jsonl의 새 한 줄
```

`_append_jsonl()`은 새 거래·카테고리를 파일 끝에 한 줄 추가할 때 사용한다.
수정·삭제처럼 파일 전체를 다시 쓸 때는 `_atomic_write_jsonl()`이 같은
`json.dumps()`를 각 `record`에 적용한다. 어느 경우든 **dict 하나가 JSONL 한 줄
하나**가 되는 규칙은 같다.

## 5. M03 코드에서 기억할 연결점

```python
# ledger/models.py
"date": self.date.isoformat(),

# Transaction.from_dict() 안
date=datetime.date.fromisoformat(data["date"]),
```

`json`은 `dict`까지만 다룬다. `Transaction`을 만들거나 날짜를 되돌리는 규칙은
`Transaction.to_dict()`와 `Transaction.from_dict()`가 맡는다. 이 분리 덕분에
저장 파일은 JSONL이라는 단순한 글자 형식을 유지하면서도, 프로그램 안에서는
`transaction.date`처럼 날짜 객체를 사용할 수 있다.

## 외워둘 5줄

```text
JSONL = 한 줄에 JSON 객체 하나를 저장하는 파일 형식이다.
json.loads() = 파일에서 읽은 JSON 문자열을 Python dict로 바꾼다.
json.dumps() = Python dict를 파일에 쓸 JSON 문자열로 바꾼다.
Transaction.from_dict() = 읽은 dict를 M03의 Transaction 객체로 복원한다.
Transaction.to_dict() = Transaction을 저장할 dict로 바꾼다.
```
