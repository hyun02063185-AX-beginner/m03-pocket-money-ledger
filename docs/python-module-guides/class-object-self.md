# `class`, object(instance), `self` 사용 흐름

이 문서는 `Transaction`, `TransactionRepository`를 예로 Python class와 객체, 메서드의
`self`를 읽는 법을 설명한다.

## 1. 문법

```python
class TransactionRepository:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir)
        self.path = self.data_dir / self.FILENAME

    def iter_all(self) -> Iterator[Transaction]:
        for record in _iter_jsonl(self.path):
            yield Transaction.from_dict(record)
```

`class`는 같은 종류의 객체를 만들기 위한 설계도다. 실제로 만든 값 하나를 object 또는
instance라고 한다. `self`는 메서드를 호출한 **그 객체 자신**을 가리키는 관례 이름이다.

## 2. B2-1에서 왜 필요한가

장부는 거래 하나의 정보와 파일 저장소의 상태를 분리해야 한다. `Transaction` 객체는 한
거래의 필드와 변환 규칙을 가진다. `TransactionRepository` 객체는 어느 데이터 폴더와
파일을 쓰는지를 기억한다. 둘은 B2-1가 만든 사용자 정의 class다.

## 3. `repo.iter_all()`에서 `self`

```python
repo = TransactionRepository(Path("data"))
stream = repo.iter_all()
```

호출을 풀어 쓰면 개념적으로 다음과 같다.

```python
TransactionRepository.iter_all(repo)
```

즉 `iter_all()` 안에서 `self`는 `repo` 객체다. 그래서 `self.path`는 이 Repository가
만들 때 저장해 둔 `data/transactions.jsonl` 경로다. Python이 메서드 호출 때 첫 번째
인자로 객체를 자동으로 넣어 준다.

## 4. 객체가 만들어지는 흐름

```text
TransactionRepository(Path("data"))
↓ __init__(self, data_dir)
repo.data_dir, repo.path 설정
↓
repo.iter_all()
↓ self는 repo
_iter_jsonl(self.path)
↓
Transaction.from_dict(record)
↓ Transaction 객체 하나
```

`LedgerService`도 Transaction·Category·Budget Repository 객체 세 개를 받아
`self.transactions`, `self.categories`, `self.budgets`에 보관한다.

## 5. `dict`와 `Transaction`의 차이

```python
record["amount"]             # 저장·전달용 dict
transaction.amount            # 업무에서 쓰는 Transaction 객체
Transaction.from_dict(record) # dict → 객체
transaction.to_dict()         # 객체 → dict
```

dict는 키와 값을 자유롭게 담는 Python 기본 자료구조다. Transaction은 필드가 정해진 B2-1
class로, `to_dict()`·`from_dict()` 같은 거래 전용 동작도 함께 가진다.

## 6. B2-1 코드와 연결

- `ledger/models.py`: `Transaction`, `Budget`, `SearchCriteria`, `MonthlySummary`, `ImportResult`.
- `ledger/repository.py`: 세 Repository class와 각 `self.path`.
- `ledger/services.py`: `LedgerService`가 Repository 객체를 조합한다.
- `ledger/cli.py`: `_build_service()`가 실제 객체들을 만든다.

## 외워둘 5줄

```text
class는 객체를 만들기 위한 설계도다.
object(instance)는 class로 만든 실제 값 하나다.
self는 메서드를 호출한 그 객체 자신이다.
repo.iter_all() 안에서 self는 repo다.
dict는 범용 자료구조, Transaction은 B2-1의 거래 전용 객체다.
```
