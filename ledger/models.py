"""ledger에서 공유되는 데이터 구조.

Sprint 1에서 Transaction과 Budget을 실제로 구현했다(to_dict()/
from_dict()를 통한 id/왕복 변환 로직). Sprint 2에서는
MonthlySummary를 추가한다 — LedgerService가 계산한 결과 타입으로,
Transaction/Budget이 repository.py와 services.py 사이에서 공유되는
것과 같은 방식으로 services.py와 (이후 작성될) cli.py 사이에서
공유된다. 필드 설계 근거(id는 표시 문자열 "TX-000012"가 아니라
단순 int이며, Budget은 카테고리별이 아니라 월 전체 단위의 총액이라는
점)는 docs/m03-architecture-design.md 4번 섹션을, MonthlySummary의
필드와 의미는 36번 섹션을 참고하라.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field

from ledger.errors import LedgerError


@dataclass
class Transaction:
    """하나의 수입/지출 기록. transactions.jsonl의 한 줄에 대응한다.

    `id`는 내부 저장용 id다(양의 정수이며 처음은 1, 다음은
    max(기존 값) + 1). "TX-000012" 형태의 표시용 포맷팅은 전적으로
    cli.py의 표현 관심사일 뿐이며, 저장되거나 다시 전달되는 값이 아니다.
    `date`는 메모리상에서는 실제 datetime.date이며, 이를 ISO
    "YYYY-MM-DD" 문자열로 저장한다는 사실을 아는 곳은 to_dict()/
    from_dict()뿐이다.
    """

    id: int
    type: str  # "income" 또는 "expense"
    date: datetime.date
    amount: int  # 양의 정수
    category: str
    memo: str = ""
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "date": self.date.isoformat(),
            "amount": self.amount,
            "category": self.category,
            "memo": self.memo,
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, data: dict) -> Transaction:
        return cls(
            id=int(data["id"]),
            type=str(data["type"]),
            date=datetime.date.fromisoformat(data["date"]),
            amount=int(data["amount"]),
            category=str(data["category"]),
            memo=str(data.get("memo", "")),
            tags=list(data.get("tags", [])),
        )


@dataclass
class Budget:
    """한 달 전체에 대한 단일 총 예산(카테고리별이 아님)."""

    month: str  # "YYYY-MM" 형식, 고유 키
    amount: int  # 양의 정수

    def to_dict(self) -> dict:
        return {"month": self.month, "amount": self.amount}

    @classmethod
    def from_dict(cls, data: dict) -> Budget:
        return cls(month=str(data["month"]), amount=int(data["amount"]))


@dataclass
class SearchCriteria:
    """LedgerService.search()에 사용되는 필터 — 공식 검색 옵션 6개
    (--from, --to, --category, --type, --q, --tag)와 정확히 대응한다.
    최소/최대 금액은 없음: Mission Core 범위에 포함되지 않는다. 모든
    필터는 AND로 결합되며, None으로 남겨둔 필터는 적용되지 않는다.

    매칭 규칙(docs/m03-architecture-design.md 37번 섹션):
    from_date/to_date는 Transaction.date에 대한 경계값을 포함한다
    (inclusive); category/transaction_type/tag는 대소문자를 구분하는
    완전 일치이며; query는 memo에 대해서만 대소문자를 구분하지 않는
    부분 문자열 매칭이다.
    """

    from_date: datetime.date | None = None
    to_date: datetime.date | None = None
    transaction_type: str | None = None
    category: str | None = None
    query: str | None = None
    tag: str | None = None


@dataclass
class MonthlySummary:
    """LedgerService.monthly_summary()의 결과. 단순히 계산된 값이며
    저장되지 않으므로 to_dict()/from_dict()가 필요 없다.

    `has_transactions`는 (이후 작성될) cli.py가 다른 필드를 살피지
    않고도 명확하게 "데이터 없음" 메시지를 출력할 수 있게 해준다;
    이 값이 False여도 숫자 필드들은 None이 아니라 잘 정의된 0/빈 값으로
    남아 있으므로, 호출자가 합산을 위해 별도의 분기 처리를 할 필요가
    없다.

    `month`에 대해 설정된 Budget이 없으면 budget_amount/
    budget_usage_percent/budget_exceeded는 모두 None이다 — 예산은
    "0이면 예산 없음"이라는 관례가 아니라, 월 단위로 선택적으로
    설정하는 값이기 때문이다.
    """

    month: str
    has_transactions: bool
    total_income: int
    total_expense: int
    balance: int
    category_expenses: dict[str, int]
    top_categories: list[tuple[str, int]]
    budget_amount: int | None
    budget_usage_percent: float | None
    budget_exceeded: bool | None


@dataclass
class ImportResult:
    """LedgerService.import_csv()의 결과
    (docs/m03-architecture-design.md 48번 섹션). `errors`는 건너뛴
    각 행에 대해 미리 포맷된 문자열이 아니라 원본 LedgerError를
    그대로 담는다(헤더를 제외한 데이터 행 기준 1부터 시작하는 번호).
    이렇게 하면 Service가 직접 "[건너뜀] ..." 텍스트를 만들지 않고도
    cli.py가 다른 모든 오류에 사용하는 것과 동일한 describe_error()
    매핑을 재사용할 수 있다."""

    imported: int
    skipped: int
    errors: list[tuple[int, LedgerError]]
