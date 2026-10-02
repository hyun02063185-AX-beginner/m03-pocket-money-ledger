"""파일 기반 repository들 — Sprint 1의 실제 영속성 계층.

여기서 구현하는 계약들(JSONL 저장 방식, 제너레이터 기반 읽기,
data_dir 기준 경로 해석, 파일/디렉터리가 없을 때의 빈 상태 동작,
update/delete/remove/set에 쓰이는 안전한 재작성(임시 파일 +
os.replace()) 전략)은 docs/m03-architecture-design.md의 6, 10, 11,
21, 24번 섹션을 참고하라.

Repository는 오직 영속성 인프라만 담당한다. 저장 계층의 정합성
(중복 id 없음, 잘못된 JSON이 조용히 받아들여지지 않음)은 강제하지만,
도메인을 넘나드는 업무 규칙("추가 전에 카테고리가 존재해야 한다",
"사용 중인 카테고리", "예산 초과" 등)은 전혀 다루지 않는다 — 이들은
모두 이후 스프린트에서 LedgerService가 담당한다(20번 섹션).
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Iterable, Iterator

from ledger.errors import (
    BudgetNotFoundError,
    CategoryNotFoundError,
    DataFormatError,
    DuplicateCategoryError,
    DuplicateTransactionIdError,
    TransactionNotFoundError,
)
from ledger.models import Budget, Transaction


def _iter_jsonl(path: Path) -> Iterator[dict]:
    """`path`의 비어 있지 않은 각 줄을 파싱해 하나씩 JSON 객체로
    스트리밍한다.

    파일이 없으면 아무것도 내놓지 않는다 — 빈 데이터셋은 오류가
    아니며(docs/m03-architecture-design.md 10번 섹션), 읽기 동작이
    파일이나 디렉터리를 만들어내는 일도 없다. 전체 파일을 리스트로
    먼저 읽어들이는 일은 결코 없다: 각 줄은 파싱되는 즉시 하나씩
    반환된다.
    """
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as f:
        for line_no, raw_line in enumerate(f, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise DataFormatError(f"{path}:{line_no}: malformed JSON line ({exc})") from exc


def _append_jsonl(path: Path, record: dict) -> None:
    """레코드 하나를 새 줄로 추가한다. 처음 사용할 때 상위 디렉터리
    (parents=True)와 파일 자체를 생성한다; 기존 줄은 절대 다시 쓰지
    않는다 — 파일 전체를 다시 쓰는 것이 아니라 O(1) I/O다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="") as f:
        f.write(json.dumps(record, ensure_ascii=False))
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())


def _atomic_write_jsonl(path: Path, records: Iterable[dict]) -> None:
    """`path`를 처음부터 다시 쓴다: 모든 레코드를 같은 디렉터리의
    임시 파일에 쓰고 flush한 뒤, os.replace()로 원본 위에 덮어쓴다.
    os.replace() 이전에 뭔가가 예외를 던지면 원본 파일은 그대로 남고
    임시 파일은 삭제된다(docs/m03-architecture-design.md 24번 섹션).
    아래의 모든 update/delete/remove/set 연산이 이 함수를 공유하므로,
    재작성 구현은 정확히 하나만 신경 쓰면 된다.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f"{path.name}.", suffix=".tmp")
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False))
                f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise


class TransactionRepository:
    """<data_dir>/transactions.jsonl을 소유한다."""

    FILENAME = "transactions.jsonl"

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir)
        self.path = self.data_dir / self.FILENAME

    def iter_all(self) -> Iterator[Transaction]:
        """진짜 제너레이터다: transactions.jsonl을 한 줄씩 읽어 각 줄이
        파싱될 때마다 Transaction을 반환한다. 모든 레코드를 리스트로
        먼저 만들지 않는다 — 파일 크기와 무관하게 전체 내용이 메모리에
        한꺼번에 올라가는 일은 없다."""
        for record in _iter_jsonl(self.path):
            yield Transaction.from_dict(record)

    def get_by_id(self, transaction_id: int) -> Transaction | None:
        """iter_all()을 통해 스트리밍한다; 일치하는 항목이 없을 때는
        예외를 던지지 않고 None을 반환한다(단순 조회 실패에 대해 예외를
        요구하는 기존 계약은 없다)."""
        for transaction in self.iter_all():
            if transaction.id == transaction_id:
                return transaction
        return None

    def next_id(self) -> int:
        """max(기존 id들) + 1을 반환하며, 저장소가 비어 있으면 1을
        반환한다. 한 번의 스트리밍 스캔이 필요하다 — Mission Core
        규모에서는 허용 가능한 수준이다(docs/m03-architecture-design.md
        11번 섹션 참고)."""
        max_id = 0
        for transaction in self.iter_all():
            if transaction.id > max_id:
                max_id = transaction.id
        return max_id + 1

    def add(self, transaction: Transaction) -> Transaction:
        """`transaction`을 그대로 추가한다 — 호출자가 먼저 next_id()를
        통해 `transaction.id`를 지정할 책임이 있다(Sprint 0B의 계약;
        Service가 이후 스프린트에서 이 역할을 한다). 해당 id가 이미
        존재하면 아무것도 쓰지 않고 DuplicateTransactionIdError를
        발생시킨다."""
        if self.get_by_id(transaction.id) is not None:
            raise DuplicateTransactionIdError(f"transaction id {transaction.id} already exists")
        _append_jsonl(self.path, transaction.to_dict())
        return transaction

    def update(self, transaction: Transaction) -> Transaction:
        """안전한 재작성: 기존의 모든 레코드를 스트리밍하면서 id가
        `transaction.id`와 일치하는 레코드만 교체한 뒤, 임시 파일 +
        os.replace()를 통해 결과를 쓴다. 해당 id를 가진 레코드가 없으면
        아무것도 쓰지 않고 TransactionNotFoundError를 발생시킨다."""
        records: list[dict] = []
        found = False
        for existing in self.iter_all():
            if existing.id == transaction.id:
                records.append(transaction.to_dict())
                found = True
            else:
                records.append(existing.to_dict())
        if not found:
            raise TransactionNotFoundError(f"transaction id {transaction.id} not found")
        _atomic_write_jsonl(self.path, records)
        return transaction

    def delete(self, transaction_id: int) -> None:
        """안전한 재작성: 기존의 모든 레코드를 스트리밍하면서
        `transaction_id`와 일치하는 레코드만 제외하고, 나머지를 임시
        파일 + os.replace()를 통해 쓴다. 해당 id를 가진 레코드가 없으면
        아무것도 쓰지 않고(원본 파일은 그대로 유지) TransactionNotFoundError를
        발생시킨다."""
        records: list[dict] = []
        found = False
        for existing in self.iter_all():
            if existing.id == transaction_id:
                found = True
                continue
            records.append(existing.to_dict())
        if not found:
            raise TransactionNotFoundError(f"transaction id {transaction_id} not found")
        _atomic_write_jsonl(self.path, records)


class CategoryRepository:
    """<data_dir>/categories.jsonl을 소유한다(한 줄에 {"name": ...}
    객체 하나). 오직 저장 역할만 한다 — "카테고리가 거래에서 사용 중"
    이라는 규칙은 (이후 스프린트의) LedgerService에 있다. 이를
    강제하려면 TransactionRepository와 협력해야 하는데, repository
    클래스들은 서로 의존해서는 안 되기 때문이다."""

    FILENAME = "categories.jsonl"

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir)
        self.path = self.data_dir / self.FILENAME

    def list_all(self) -> list[str]:
        return [record["name"] for record in _iter_jsonl(self.path)]

    def exists(self, name: str) -> bool:
        return name in self.list_all()

    def add(self, name: str) -> None:
        """`name`이 이미 등록되어 있으면 아무것도 쓰지 않고
        DuplicateCategoryError를 발생시킨다."""
        if self.exists(name):
            raise DuplicateCategoryError(f"category {name!r} already exists")
        _append_jsonl(self.path, {"name": name})

    def remove(self, name: str) -> None:
        """`name`이 등록되어 있지 않으면 아무것도 쓰지 않고
        CategoryNotFoundError를 발생시킨다."""
        names = self.list_all()
        if name not in names:
            raise CategoryNotFoundError(f"category {name!r} not found")
        remaining = [{"name": n} for n in names if n != name]
        _atomic_write_jsonl(self.path, remaining)


class BudgetRepository:
    """<data_dir>/budgets.jsonl을 소유한다. 월마다 레코드 하나이며
    month가 고유 키다(카테고리별이 아니라 월 전체 단위의 총 예산 —
    docs/m03-architecture-design.md 15번 섹션 참고). 사용률이나 초과
    여부는 계산하지 않는다 — 그것은 LedgerService의 몫이다."""

    FILENAME = "budgets.jsonl"

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir)
        self.path = self.data_dir / self.FILENAME

    def list_all(self) -> list[Budget]:
        return [Budget.from_dict(record) for record in _iter_jsonl(self.path)]

    def get(self, month: str) -> Budget | None:
        for budget in self.list_all():
            if budget.month == month:
                return budget
        return None

    def set(self, budget: Budget) -> Budget:
        """새로운 월에 대한 예산을 추가하거나, 해당 월의 기존 레코드를
        교체한다 — 같은 월에 대해 두 번째 행을 추가하는 일은 절대 없다
        (이를 보장하려면 전체 재작성이 필요하다)."""
        remaining = [b.to_dict() for b in self.list_all() if b.month != budget.month]
        remaining.append(budget.to_dict())
        _atomic_write_jsonl(self.path, remaining)
        return budget

    def remove(self, month: str) -> None:
        """`month`에 설정된 예산이 없으면 아무것도 쓰지 않고
        BudgetNotFoundError를 발생시킨다."""
        budgets = self.list_all()
        if not any(b.month == month for b in budgets):
            raise BudgetNotFoundError(f"no budget set for month {month!r}")
        remaining = [b.to_dict() for b in budgets if b.month != month]
        _atomic_write_jsonl(self.path, remaining)
