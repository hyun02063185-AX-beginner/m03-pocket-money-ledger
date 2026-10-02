"""업무 로직 계층 — Sprint 2의 실제 구현.

여러 repository를 넘나드는 업무 규칙이 존재하는 곳은 LedgerService
뿐이다(거래가 참조하기 전에 카테고리가 존재해야 함, 사용 중인
카테고리는 삭제할 수 없음, 예산은 보고용일 뿐임). Repository들은
오직 영속성만 담당한다(docs/m03-architecture-design.md 26번 섹션).

Service는 절대 print를 하지 않고, input()을 호출하지 않으며,
argparse나 sys.exit()을 건드리지 않는다 — 값을 반환하거나
ledger.errors.LedgerError의 하위 클래스를 발생시킬 뿐이다.
(이후 스프린트의) cli.py만이 사용자와 직접 소통하는 유일한
곳이다(16번 섹션).
"""

from __future__ import annotations

import csv
import os
import tempfile
from collections import deque
from pathlib import Path

from ledger.errors import (
    CategoryInUseError,
    CategoryNotFoundError,
    CSVFormatError,
    LedgerError,
    PersistenceError,
    TransactionNotFoundError,
    ValidationError,
)
from ledger.models import Budget, ImportResult, MonthlySummary, SearchCriteria, Transaction
from ledger.repository import BudgetRepository, CategoryRepository, TransactionRepository
from ledger.validators import (
    parse_tags,
    validate_amount,
    validate_category_name,
    validate_date,
    validate_month,
    validate_transaction_type,
)

#: 교환 형식 CSV 스키마(docs/m03-architecture-design.md 46번 섹션)
#: — import와 export 모두에서 사용되는 고정된 컬럼 순서다.
#: 내부 거래 id는 의도적으로 포함하지 않는다(Sprint 4의 공식
#: 결정: CSV는 절대 id를 좌우하지 않는다).
CSV_FIELDNAMES = ["date", "type", "category", "amount", "memo", "tags"]


class _UnsetType:
    """update_transaction()의 "필드가 전달되지 않음" 기본값을 나타내는
    sentinel 타입 — None, "", [] 등 어떤 실제 값과도 구분된다. 왜
    여기서 (None이 아니라) sentinel이 필요한지는
    docs/m03-architecture-design.md 38번 섹션을 참고하라: memo=""와
    tags=[]는 "이 필드를 건드리지 않는다"가 아니라 "이 필드를
    비운다"는 의미여야 하기 때문이다."""

    def __repr__(self) -> str:  # pragma: no cover - 디버깅 보조용일 뿐
        return "UNSET"


UNSET = _UnsetType()


class LedgerService:
    """여러 repository를 조율해 Mission Core의 모든 동작을
    구현한다: 거래 추가/목록/검색/수정/삭제, 예산 사용률을 포함한
    월별 요약, 카테고리 관리, CSV import/export."""

    def __init__(
        self,
        transactions: TransactionRepository,
        categories: CategoryRepository,
        budgets: BudgetRepository,
    ) -> None:
        self.transactions = transactions
        self.categories = categories
        self.budgets = budgets

    # -- 거래 -----------------------------------------------------------

    def add_transaction(
        self,
        type_: str,
        date: str,
        category: str,
        amount: int,
        memo: str = "",
        tags: list[str] | None = None,
    ) -> Transaction:
        """모든 필드를 검증하고, `category`가 등록되어 있는지 확인하며
        (조용히 새로 만들지 않는다), 다음 id를 부여한 뒤 저장한다. 예산은
        확인하지 않는다 — 예산은 monthly_summary()에서 적용되는 보고용
        값일 뿐, add/update를 절대 막지 않는다."""
        validated_type = validate_transaction_type(type_)
        validated_date = validate_date(date)
        validated_amount = validate_amount(amount)
        if not self.categories.exists(category):
            raise CategoryNotFoundError(f"category {category!r} not found")

        transaction = Transaction(
            id=self.transactions.next_id(),
            type=validated_type,
            date=validated_date,
            amount=validated_amount,
            category=category,
            memo=memo,
            tags=list(tags) if tags is not None else [],
        )
        return self.transactions.add(transaction)

    def list_transactions(self, limit: int) -> list[Transaction]:
        """최신순, 메모리 사용량은 O(limit)로 제한된다:
        TransactionRepository.iter_all()을 통해 스트리밍하며
        collections.deque(maxlen=limit)에 담은 뒤, 그 deque만 뒤집는다
        (docs/m03-architecture-design.md 12번 섹션).

        여기서 "최신"이란 가장 최근에 *추가된* 것을 의미한다(id는 계속
        증가하기만 하므로 == 가장 큰 id) — `date` 필드가 가장 최근인
        `limit`개의 거래가 아니라, 파일의 마지막 `limit`줄이다. 날짜
        기준으로 정렬하려면 파일 전체를 버퍼링해야 하므로, 이 프로젝트는
        "최근"을 "최근에 입력된 것"으로 간주하며, 이는 이 메서드에 이미
        확정된 추가 순서 기반 deque 전략과 일치한다(39번 섹션)."""
        if limit <= 0:
            raise ValidationError(f"limit must be positive, got {limit}")
        recent: deque[Transaction] = deque(maxlen=limit)
        for transaction in self.transactions.iter_all():
            recent.append(transaction)
        return list(reversed(recent))

    def search(self, criteria: SearchCriteria) -> list[Transaction]:
        """iter_all()을 스트리밍하면서 필터링하지만, 최신순 결과를
        만들어내려면 일치하는 모든 레코드를 버퍼에 담아야 한다(메모리는
        파일 크기가 아니라 O(일치 개수)) — search에는 --limit이 없다
        (docs/m03-architecture-design.md 13번 섹션). list_transactions()와
        마찬가지로 "최신순"은 파일/입력 순서를 뒤집는 것이지, `date`
        필드로 다시 정렬하는 것이 아니다.

        매칭 규칙은 SearchCriteria의 docstring 참고: from_date/to_date는
        경계값을 포함하며; category/transaction_type/tag는 대소문자를
        구분하는 완전 일치이고; query는 memo에 대해서만 대소문자를
        구분하지 않는 부분 문자열 매칭이다."""
        matches: list[Transaction] = []
        for transaction in self.transactions.iter_all():
            if criteria.from_date is not None and transaction.date < criteria.from_date:
                continue
            if criteria.to_date is not None and transaction.date > criteria.to_date:
                continue
            if criteria.category is not None and transaction.category != criteria.category:
                continue
            if (
                criteria.transaction_type is not None
                and transaction.type != criteria.transaction_type
            ):
                continue
            if criteria.query is not None and criteria.query.lower() not in transaction.memo.lower():
                continue
            if criteria.tag is not None and criteria.tag not in transaction.tags:
                continue
            matches.append(transaction)
        matches.reverse()
        return matches

    def update_transaction(
        self,
        transaction_id: int,
        *,
        date: str | _UnsetType = UNSET,
        transaction_type: str | _UnsetType = UNSET,
        category: str | _UnsetType = UNSET,
        amount: int | _UnsetType = UNSET,
        memo: str | _UnsetType = UNSET,
        tags: list[str] | _UnsetType = UNSET,
    ) -> Transaction:
        """부분 수정: UNSET으로 남겨둔 필드는 기존 값을 유지하고,
        명시적으로 전달된 필드(memo=""나 tags=[] 포함)는 교체된다 — None이
        왜 이 역할을 할 수 없는지는 UNSET sentinel의 docstring 참고.
        전달된 필드만 검증한다. `transaction_id`가 존재하지 않으면
        TransactionNotFoundError를(영속성 계층에서 그대로 재사용한다 —
        이미 도메인적으로 의미가 있어 별도 변환이 필요 없다), 전달된
        `category`가 등록되어 있지 않으면 CategoryNotFoundError를
        발생시킨다."""
        existing = self.transactions.get_by_id(transaction_id)
        if existing is None:
            raise TransactionNotFoundError(f"transaction id {transaction_id} not found")

        new_date = existing.date if date is UNSET else validate_date(date)
        new_type = (
            existing.type if transaction_type is UNSET else validate_transaction_type(transaction_type)
        )
        if category is UNSET:
            new_category = existing.category
        else:
            if not self.categories.exists(category):
                raise CategoryNotFoundError(f"category {category!r} not found")
            new_category = category
        new_amount = existing.amount if amount is UNSET else validate_amount(amount)
        new_memo = existing.memo if memo is UNSET else memo
        new_tags = existing.tags if tags is UNSET else list(tags)

        updated = Transaction(
            id=existing.id,
            type=new_type,
            date=new_date,
            amount=new_amount,
            category=new_category,
            memo=new_memo,
            tags=new_tags,
        )
        return self.transactions.update(updated)

    def delete_transaction(self, transaction_id: int) -> None:
        """TransactionRepository.delete()는 이미 알 수 없는 id에 대해
        TransactionNotFoundError를 발생시킨다 — 이는 이미 올바른 도메인
        오류이므로 여기서 따로 잡았다가 다시 발생시키지 않는다."""
        self.transactions.delete(transaction_id)

    # -- 요약 / 예산 ---------------------------------------------------------

    def monthly_summary(self, month: str, top: int) -> MonthlySummary:
        """모든 거래를 한 번씩 스트리밍하며 `date`가 `month`에 속하는
        것만 남긴다. 카테고리별 합계는 지출 거래에서만 집계한다(수입에는
        "카테고리별 지출"이라는 의미가 없다). 해당 월에 예산이 설정되어
        있으면 예산 사용률도 포함한다 — 예산은 절대 거래를 막지 않으며,
        이는 보고용일 뿐이다(docs/m03-architecture-design.md 15번
        섹션)."""
        validated_month = validate_month(month)
        if top <= 0:
            raise ValidationError(f"top must be positive, got {top}")

        total_income = 0
        total_expense = 0
        category_expenses: dict[str, int] = {}
        has_transactions = False

        for transaction in self.transactions.iter_all():
            if transaction.date.strftime("%Y-%m") != validated_month:
                continue
            has_transactions = True
            if transaction.type == "income":
                total_income += transaction.amount
            else:
                total_expense += transaction.amount
                category_expenses[transaction.category] = (
                    category_expenses.get(transaction.category, 0) + transaction.amount
                )

        top_categories = sorted(
            category_expenses.items(), key=lambda item: item[1], reverse=True
        )[:top]

        budget = self.budgets.get(validated_month)
        if budget is None:
            budget_amount = None
            budget_usage_percent = None
            budget_exceeded = None
        else:
            budget_amount = budget.amount
            # budget.amount는 set_budget()에서 양수임이 검증되지만, 디스크에서
            # 직접 수정되었을 수도 있는 데이터를 그대로 신뢰하지 않고 방어적으로
            # 한 번 더 확인한다.
            budget_usage_percent = (total_expense / budget.amount * 100) if budget.amount else 0.0
            budget_exceeded = total_expense > budget.amount

        return MonthlySummary(
            month=validated_month,
            has_transactions=has_transactions,
            total_income=total_income,
            total_expense=total_expense,
            balance=total_income - total_expense,
            category_expenses=category_expenses,
            top_categories=top_categories,
            budget_amount=budget_amount,
            budget_usage_percent=budget_usage_percent,
            budget_exceeded=budget_exceeded,
        )

    def set_budget(self, month: str, amount: int) -> Budget:
        """Budget(month, amount)을 만들어 BudgetRepository.set()에
        위임한다. set()은 중복으로 추가하는 대신 해당 월의 기존 레코드를
        교체한다."""
        validated_month = validate_month(month)
        validated_amount = validate_amount(amount)
        return self.budgets.set(Budget(month=validated_month, amount=validated_amount))

    # -- 카테고리 ---------------------------------------------------------------

    def add_category(self, name: str) -> None:
        """중복 방지는 CategoryRepository.add()에 위임한다(이미
        DuplicateCategoryError를 발생시키므로 여기서 다시 검사하지
        않는다)."""
        validated_name = validate_category_name(name)
        self.categories.add(validated_name)

    def list_categories(self) -> list[str]:
        return self.categories.list_all()

    def remove_category(self, name: str) -> None:
        """CategoryRepository를 건드리기 *전에*
        TransactionRepository.iter_all()을 스트리밍하여 어떤 거래가
        여전히 `name`을 참조하는지 확인한다. 참조하는 거래가 있으면
        CategoryInUseError를 발생시킨다 — 연쇄 삭제도, 조용한 대체도
        없다. 아무도 사용하지 않으면 삭제를 CategoryRepository에
        위임한다(`name`이 아예 등록되어 있지 않으면
        CategoryNotFoundError를 발생시킨다)."""
        in_use = any(transaction.category == name for transaction in self.transactions.iter_all())
        if in_use:
            raise CategoryInUseError(f"category {name!r} is in use by at least one transaction")
        self.categories.remove(name)

    # -- CSV import/export ---------------------------------------------------------

    def import_csv(self, path: Path) -> ImportResult:
        """`path`를 CSV_FIELDNAMES 헤더를 가진 UTF-8 CSV로 읽는다(추가
        컬럼은 무시되며, 필수 6개 컬럼은 모두 존재해야 한다). 파일/스키마
        수준의 문제 — 파일 없음, 읽기 불가, 올바른 UTF-8이 아님, 헤더
        누락, 필수 컬럼 누락 — 가 있으면 (PersistenceError 또는
        CSVFormatError를) 발생시키고 어떤 행도 처리하기 전에 중단한다:
        이 경우 아무것도 기록되지 않는다(docs/m03-architecture-design.md
        48번 섹션).

        헤더가 유효하면, 각 데이터 행은 add_transaction() 호출로
        변환된다 — 대화형 add와 완전히 동일한 검증 및 카테고리 존재
        규칙이며, 별도로 중복 구현하지 않는다. 검증에 실패한 행은 전체
        import를 중단시키지 않고 건너뛰어진 뒤 집계된다(48번 섹션). CSV는
        id를 절대 지정하지 않는다; import되는 모든 행은 일반적인
        add_transaction()/next_id() 경로를 통해 새 id를 받으므로, 기존
        거래는 절대 건드려지거나 덮어써지지 않는다."""
        try:
            handle = path.open("r", encoding="utf-8", newline="")
        except OSError as exc:
            raise PersistenceError(f"cannot open {path}: {exc}") from exc

        imported = 0
        skipped = 0
        errors: list[tuple[int, LedgerError]] = []

        try:
            with handle:
                reader = csv.DictReader(handle)
                fieldnames = reader.fieldnames
                if not fieldnames:
                    raise CSVFormatError(f"{path}: missing header row")
                missing_headers = [h for h in CSV_FIELDNAMES if h not in fieldnames]
                if missing_headers:
                    raise CSVFormatError(
                        f"{path}: missing required column(s): {', '.join(missing_headers)}"
                    )

                for row_number, row in enumerate(reader, start=1):
                    date = row.get("date") or ""
                    type_ = row.get("type") or ""
                    category = row.get("category") or ""
                    memo = row.get("memo") or ""
                    tags_raw = row.get("tags") or ""
                    try:
                        amount = validate_amount(row.get("amount") or "")
                        tags = parse_tags(tags_raw)
                        self.add_transaction(type_, date, category, amount, memo, tags)
                    except LedgerError as exc:
                        skipped += 1
                        errors.append((row_number, exc))
                        continue
                    imported += 1
        except UnicodeDecodeError as exc:
            raise PersistenceError(f"{path}: not valid UTF-8 ({exc})") from exc

        return ImportResult(imported=imported, skipped=skipped, errors=errors)

    def export_csv(
        self,
        path: Path,
        month: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> int:
        """`month`와 (`from_date`와 `to_date`) 중 정확히 하나만 주어져야
        한다 — 이 규칙에 대해 LedgerService가 유일한 기준점으로 남도록
        (cli.py뿐 아니라) 여기서도 검증한다.
        TransactionRepository.iter_all()을 csv.DictWriter로 바로
        스트리밍한다: 버퍼링도, 재정렬도 하지 않는다(search()와 달리
        export에는 순서 요구 사항이 없다 — 파일/입력 순서가 그대로
        유지된다) — 파일 크기와 무관하게 추가 메모리는 O(1)이다(51번
        섹션). 내부 id는 절대 기록되지 않는다. (repository.py와 동일한
        패턴으로) 같은 디렉터리의 임시 파일 + os.replace()를 통해
        기록하므로, export가 실패해도 `path`에 절반만 작성된 파일이
        남지 않는다; 필요하면 `path`의 상위 디렉터리를 생성하며, 성공하면
        `path`에 있던 기존 파일은 덮어써진다."""
        has_month = month is not None
        has_range = from_date is not None or to_date is not None
        if has_month and has_range:
            raise ValidationError("export cannot combine --month with --from/--to")
        if has_month:
            validated_month = validate_month(month)
            validated_from = validated_to = None
        elif has_range:
            if from_date is None or to_date is None:
                raise ValidationError("export --from and --to must both be given together")
            validated_from = validate_date(from_date)
            validated_to = validate_date(to_date)
            if validated_from > validated_to:
                raise ValidationError("export --from must not be after --to")
            validated_month = None
        else:
            raise ValidationError("export requires --month or both --from and --to")

        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            tmp_fd, tmp_name = tempfile.mkstemp(
                dir=path.parent, prefix=f"{path.name}.", suffix=".tmp"
            )
        except OSError as exc:
            raise PersistenceError(f"cannot create output file near {path}: {exc}") from exc

        tmp_path = Path(tmp_name)
        count = 0
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
                writer.writeheader()
                for transaction in self.transactions.iter_all():
                    if validated_month is not None:
                        if transaction.date.strftime("%Y-%m") != validated_month:
                            continue
                    else:
                        if transaction.date < validated_from or transaction.date > validated_to:
                            continue
                    writer.writerow(
                        {
                            "date": transaction.date.isoformat(),
                            "type": transaction.type,
                            "category": transaction.category,
                            "amount": transaction.amount,
                            "memo": transaction.memo,
                            "tags": ",".join(transaction.tags),
                        }
                    )
                    count += 1
            os.replace(tmp_path, path)
        except BaseException:
            tmp_path.unlink(missing_ok=True)
            raise

        return count
