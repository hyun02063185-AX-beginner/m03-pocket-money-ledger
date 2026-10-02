"""ledger의 예외 계층 구조.

사용자에게 노출되는 모든 실패는 이 중 하나를 발생시켜야 한다. 모든
LedgerError 하위 클래스는 handle_errors를 통해 동일한 종료 코드(1)로
매핑된다 — 이들은 사용자에게 보여줄 메시지/힌트 문구를 구분하기 위해
존재하는 것이지, 별도의 종료 코드를 고르기 위한 것이 아니다 (자세한
내용은 docs/m03-architecture-design.md, 23번 섹션 참고).

Sprint 1에서는 ledger/repository.py가 발생시키는 영속성 계층 하위
클래스를 추가했다. Sprint 2에서는 ledger/validators.py와
ledger/services.py가 발생시키는 검증/업무 규칙 하위 클래스를
추가한다. Sprint 1의 일부 클래스는 새 클래스로 감싸지 않고 Service
경계에서 그대로 재사용하도록 의도적으로 설계되었다 — 어떤 클래스가
해당하고 그 이유는 docs/m03-architecture-design.md 35번 섹션 참고.
Sprint 4는 CSVFormatError를 처음으로 사용하며(CSV 스키마/헤더 문제),
CSV 파일 입출력 문제(파일 없음, 읽기 불가, 올바른 UTF-8 아님)에는
PersistenceError를 그대로 재사용한다 — 파일 단위 오류와 행 단위
오류의 구분은 48번 섹션 참고.
"""


class LedgerError(Exception):
    """모든 예상된 ledger 오류의 기반 클래스. 이 계층에 속하지 않는
    예외는 프로그래밍 버그이므로 그대로 전파되어야 한다."""


class ValidationError(LedgerError):
    """사용자 입력이 검증에 실패했을 때 발생한다(잘못된 금액, 날짜 등).
    아래의 더 구체적인 필드 검증기들의 기반 클래스이며, 별도의 하위
    클래스를 둘 필요가 없는 검증 실패(예: 빈 카테고리 이름)에도 직접
    사용된다."""


class InvalidDateError(ValidationError):
    """validators.validate_date()가 형식이 잘못되었거나 ISO 형식이
    아닌 날짜에 대해 발생시킨다."""


class InvalidMonthError(ValidationError):
    """validators.validate_month()가 YYYY-MM 형식이 아닌 문자열에
    대해 발생시킨다."""


class InvalidAmountError(ValidationError):
    """validators.validate_amount()가 양의 정수가 아닌 금액에 대해
    발생시킨다."""


class InvalidTransactionTypeError(ValidationError):
    """validators.validate_transaction_type()이 "income" 또는
    "expense"가 아닌 값에 대해 발생시킨다."""


class NotFoundError(LedgerError):
    """'참조한 id/이름이 존재하지 않음' 오류들의 기반 클래스."""


class PersistenceError(LedgerError):
    """데이터 파일을 읽거나 쓰는 데 실패했을 때, 또는 파일의 디스크
    상태를 신뢰할 수 없을 때(예: 중복된 id) 발생한다."""


class DataFormatError(PersistenceError):
    """JSONL의 한 줄을 올바른 JSON으로 파싱할 수 없을 때 발생한다."""


class DuplicateTransactionIdError(PersistenceError):
    """TransactionRepository.add()가 주어진 id가 이미 존재할 때
    발생시킨다."""


class TransactionNotFoundError(NotFoundError):
    """TransactionRepository.update()/delete()가 알 수 없는 id에
    대해 발생시키며, LedgerService.update_transaction()/
    delete_transaction()에서도 그대로 재사용된다 — 별도 변환이
    필요 없으며, Service 경계에서도 이미 도메인적으로 의미 있는
    오류이기 때문이다."""


class DuplicateCategoryError(PersistenceError):
    """CategoryRepository.add()가 이름이 이미 존재할 때 발생시키며,
    LedgerService.add_category()에서도 그대로 재사용된다."""


class CategoryNotFoundError(NotFoundError):
    """CategoryRepository.remove()가 알 수 없는 이름에 대해
    발생시키며, Transaction이 등록되지 않은 카테고리를 참조할 때
    (add/update) LedgerService에서도 발생시킨다 — "이름이 존재하지
    않는다"는 두 상황 모두 하나의 클래스로 처리한다."""


class CategoryInUseError(LedgerError):
    """LedgerService.remove_category()가 하나 이상의 거래가 여전히
    해당 카테고리를 참조할 때 발생시킨다. NotFoundError가 아니고
    (카테고리는 존재함) ValidationError도 아니다(*삭제 요청* 자체는
    형식상 올바른 입력이다) — 이미 존재하는 두 상태 간의 업무 규칙
    충돌이므로 LedgerError의 독립된 직계 하위 클래스로 둔다."""


class BudgetNotFoundError(NotFoundError):
    """BudgetRepository.remove()가 예산이 설정되지 않은 월에 대해
    발생시킨다."""


class CSVFormatError(LedgerError):
    """LedgerService.import_csv()가 스키마 수준의 문제(헤더 행
    누락, 필수 컬럼 누락)에 대해 발생시킨다 — 개별 데이터 행 하나가
    잘못된 경우(예외를 발생시키지 않고 건너뛰고 집계됨)와는 구분되는
    파일 전체 단위의 실패다."""
