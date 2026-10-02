# B2-1 — 동료평가 대비 가이드

> **Historical/reference document.** 이 문서는 시연 순서와 짧은 답변을 위한 자료다.
> Python 기초 설명은 [B2-1 Code Reading Guide](m03-code-reading-guide.md), 전체 시연 데이터
> 만들기는 [B2-1 Hands-on Guide](m03-hands-on-guide.md)를 먼저 참고한다.

이 문서는 Codyssey B2-1 「나만의 용돈 기입장 프로그램」 동료평가에서
프로젝트 구조와 핵심 Python 개념을 짧고 정확하게 설명하고, 실제로
시연까지 할 수 있도록 준비한 자료다. 모든 설명은 실제 코드
(`ledger/*.py`)와 [README.md](../README.md),
[docs/m03-final-qa-report.md](m03-final-qa-report.md)를 기준으로
작성했다 — 구현에 없는 내용은 쓰지 않았다.

## 1. 프로젝트 한 줄 소개

Python 표준 라이브러리만으로 만든 파일 기반 CLI 용돈 기입장이며,
JSONL 영속 저장 위에 Generator·Decorator·Type Hint·dataclass를
실제 구조 안에서 쓰고 있는 프로젝트.

## 2. 30초 프로젝트 설명

"터미널에서 수입/지출을 기록·조회·요약하는 프로그램입니다. 거래는
`transactions.jsonl`에, 카테고리는 `categories.jsonl`에, 예산은
`budgets.jsonl`에 각각 한 줄에 하나씩 저장해서 프로그램을 껐다 켜도
데이터가 남습니다. CLI → Service → Repository → 파일, 이렇게
4단계로 나눴는데, CLI는 입출력만, Service는 카테고리 존재 확인 같은
비즈니스 규칙만, Repository는 파일 읽고 쓰는 것만 담당하게
분리했습니다. 대량의 거래를 다룰 때 파일 전체를 메모리에 올리지
않도록 Generator를 썼고, 예상 가능한 사용자 에러를 한 곳에서
일관되게 처리하려고 Decorator를 썼습니다."

## 3. 전체 구조

```
CLI (ledger/cli.py)
  ↓
Service (ledger/services.py)
  ↓
Repository (ledger/repository.py)
  ↓
JSONL 파일 (data/*.jsonl)
```

| 모듈 | 존재 이유 |
|---|---|
| `ledger/cli.py` | argparse 파싱, `add`의 대화형 `input()`, 결과 출력 포맷팅. 이 계층만 사용자와 직접 대화한다. |
| `ledger/services.py` | 유일한 비즈니스 로직 지점(`LedgerService`) — 카테고리 존재 확인, 카테고리 사용중 삭제 차단, 검색 필터링, 월간 요약 계산, 예산 계산, CSV import/export 조율. |
| `ledger/repository.py` | 파일 I/O만 — JSONL 읽기(제너레이터), 원자적 재작성. 비즈니스 규칙을 전혀 모른다. |
| `ledger/models.py` | 계층 간에 주고받는 데이터 구조(`Transaction`, `Budget`, `SearchCriteria`, `MonthlySummary`, `ImportResult`). |
| `ledger/validators.py` | 원시 입력값(문자열)을 검증된 값으로 바꾸거나 명확한 예외를 던지는 순수 함수 모음. |
| `ledger/decorators.py` | 유일한 데코레이터 `handle_errors`와, CLI가 함께 쓰는 에러→메시지 매핑. |
| `ledger/errors.py` | `LedgerError` 하위 예외 계층(15개 클래스). |

**왜 이렇게 나눴는가**: 계층마다 "무엇을 몰라야 하는지"를 정했다.
Repository는 "카테고리가 사용 중인지" 같은 비즈니스 규칙을 모른다
(다른 Repository를 참조하지 않으므로). Service는 argparse나
`input()`을 모른다(어디서 호출되든 동일하게 동작해야 하므로). 이
경계 덕분에 Service만 따로 테스트할 수 있고(`tests/test_service_*.py`),
Repository만 따로 테스트할 수 있다(`tests/test_*_repository.py`).

## 4. 핵심 데이터 모델

전부 `ledger/models.py`의 `@dataclass`.

| 클래스 | 목적 | 주요 필드 |
|---|---|---|
| `Transaction` | 거래 1건, `transactions.jsonl`의 한 줄과 1:1 대응 | `id: int, type: str, date: datetime.date, amount: int, category: str, memo: str = "", tags: list[str]` |
| `Budget` | 한 달의 총예산(카테고리별 아님) | `month: str, amount: int` |
| `SearchCriteria` | `search`의 6개 필터를 하나로 묶은 값 객체 | `from_date, to_date, transaction_type, category, query, tag` (전부 `Optional`) |
| `MonthlySummary` | `monthly_summary()`의 계산 결과 | `total_income, total_expense, balance, category_expenses, top_categories, budget_amount, budget_usage_percent, budget_exceeded` 등 |
| `ImportResult` | `import_csv()`의 처리 결과 | `imported: int, skipped: int, errors: list[tuple[int, LedgerError]]` |

**dataclass를 쓴 이유**: 필드 이름 있는 데이터 묶음을 전달할 때
`__init__`/`__repr__`/`__eq__`를 직접 안 써도 되고, 여러 값을 튜플로
순서에만 의존해 주고받지 않아도 된다. 특히 `SearchCriteria`/
`MonthlySummary`/`ImportResult`처럼 CLI 옵션이 늘거나 계산 결과가
많아져도 필드 이름으로 접근하니 함수 시그니처가 안정적으로 유지된다.

## 5. Generator 설명

**실제 위치**: `ledger/repository.py::TransactionRepository.iter_all()`

```python
def iter_all(self) -> Iterator[Transaction]:
    for record in _iter_jsonl(self.path):
        yield Transaction.from_dict(record)
```

`_iter_jsonl()`도 제너레이터로, 파일을 한 줄씩 열어 읽고(`for line_no,
raw_line in enumerate(f, ...)`), 그 줄만 JSON으로 파싱해 즉시
`yield`한다. 전체 파일을 `list()`로 먼저 만드는 코드는 어디에도
없다 — 그래서 파일이 아무리 커도 한 번에 메모리에 올라오는 건
"지금 처리 중인 레코드 1개"뿐이다.

이 제너레이터를 실제로 쓰는 4곳과 각각의 메모리 특성(전부
`ledger/services.py`):

| 사용처 | 메모리 특성 | 이유 |
|---|---|---|
| `list_transactions(limit)` | **O(limit)** | `deque(maxlen=limit)`에 스트리밍하며 채움 — 6번 참고 |
| `search(criteria)` | **O(매칭 수)** | 필터링 자체는 스트리밍하지만, 최신순 출력을 위해 매칭된 레코드만 리스트에 모은 뒤 뒤집음 |
| `monthly_summary()` | 사실상 O(카테고리 수) | 합계만 누적, 원본 레코드를 보관하지 않음 |
| `export_csv()` | **O(1)** | 매칭 레코드를 즉시 `csv.DictWriter.writerow()`로 쓰고 버림 — 순서 요구가 없어 버퍼링 자체가 필요 없음 |

**중요**: "전부 상수 메모리"라고 말하면 틀린 설명이다. `list`는
O(limit), `search`는 O(매칭 수)다 — export만 진짜 O(1)이다. 이
차이를 정확히 설명하는 것 자체가 이 프로젝트의 스트리밍 설계를
이해했다는 증거가 된다.

## 6. `deque(maxlen=N)`을 쓴 이유

- `transactions.jsonl`은 append-only라 파일 순서 = 오래된 것부터.
- 하지만 `list`는 **최신순**으로 보여줘야 한다.
- 전체를 리스트로 만들어 마지막 N개를 슬라이싱하면 요구사항("전체를
  메모리에 올리지 않는다")을 어기게 된다.
- `collections.deque(maxlen=N)`은 꽉 차면 넣을 때마다 가장 오래된
  항목을 자동으로 버린다 — 그래서 파일을 끝까지 스트리밍해도
  버퍼에는 항상 "가장 최근 N개"만 남는다.
- 마지막에 그 N개만 `reversed()`로 뒤집으면 최신순 완성.

**10초 답변**: "전체를 메모리에 올리지 않고 최신 N개만 남기려고
`deque(maxlen=N)`을 썼습니다. 꽉 차면 오래된 게 자동으로 밀려나기
때문에, 파일 끝까지 다 읽어도 메모리엔 N개만 남습니다."

## 7. Decorator 설명

**실제 데코레이터**: `ledger/decorators.py::handle_errors`
**실제 적용 지점**: `ledger/cli.py::_dispatch` (`@handle_errors`, 단 한 곳)

```python
@handle_errors
def _dispatch(args: argparse.Namespace) -> None:
    ...
    if args.command == "add":
        cmd_add(args, service)
    elif args.command == "list":
        cmd_list(args, service)
    ...
```

`add`/`list`/`search`/`summary`/`budget`/`category`/`update`/`delete`/
`import`/`export` 10개 명령 전부 이 `_dispatch` 하나를 거친다 —
그래서 데코레이터 하나로 모든 명령의 에러 처리가 통일된다.

- **하는 일**: `LedgerError` 하위 예외가 올라오면 `[오류]`/`[힌트]`
  두 줄을 stderr에 출력하고 exit code 1을 반환한다. 예외가 없으면
  0을 반환한다.
- **왜 유용한가**: 커맨드 핸들러 10개마다 각자 `try/except`를 반복해
  쓰지 않아도 된다. 에러 처리 로직이 한 곳에 있으니 메시지 형식을
  바꿀 일이 있어도 한 곳만 고치면 된다.
- **예상치 못한 버그를 삼키지 않는 이유**: `except LedgerError`로만
  좁게 잡는다. `KeyError`, `AttributeError` 같은 진짜 프로그래밍
  버그는 잡지 않고 그대로 트레이스백과 함께 튀어나온다 — "예상된
  사용자 실수"와 "프로그램 버그"를 섞으면 실제 버그가 친절한 에러
  메시지 뒤에 숨어버리기 때문이다.

**10초 답변**: "`handle_errors` 데코레이터를 `cli.py`의 `_dispatch`
하나에 적용했습니다. 모든 명령이 거기를 거치기 때문에 에러 처리
코드를 한 곳에만 두면 됩니다."

**30초 답변**: "10개 명령 핸들러가 전부 `_dispatch`라는 함수 하나를
거쳐 호출되는데, 거기에 `@handle_errors`를 붙였습니다. 이 함수는
`LedgerError` 계열 예외만 잡아서 `[오류]`/`[힌트]` 메시지로 바꾸고
exit code 1을 반환합니다. `LedgerError`가 아닌 예외, 그러니까 진짜
버그는 일부러 안 잡습니다 — 안 그러면 코드에 실수가 있어도 사용자
에러처럼 조용히 넘어가서 디버깅이 어려워지기 때문입니다."

## 8. Type Hint 설명

실제 코드에서 가져온 대표 시그니처 4개:

```python
# ledger/repository.py — Optional 반환을 명시해 "없을 수 있음"을 타입으로 드러냄
def get_by_id(self, transaction_id: int) -> Transaction | None: ...

# ledger/services.py — UNSET sentinel까지 타입에 포함시켜 "생략 가능"을 표현
def update_transaction(
    self,
    transaction_id: int,
    *,
    date: str | _UnsetType = UNSET,
    amount: int | _UnsetType = UNSET,
    ...
) -> Transaction: ...

# ledger/repository.py — 제너레이터임을 Iterator[Transaction]으로 명시
def iter_all(self) -> Iterator[Transaction]: ...

# ledger/validators.py — 문자열/정수 둘 다 받되 검증된 int만 반환
def validate_amount(value: int | str) -> int: ...
```

- **입력/출력 계약**: `get_by_id`의 `-> Transaction | None`만 봐도
  "id가 없을 수 있다"는 걸 호출부가 코드를 안 읽고도 안다.
- **가독성**: `update_transaction`의 시그니처만 봐도 어떤 필드가
  선택적인지, 기본값이 무엇인지 바로 보인다.
- **리팩터링/유지보수**: 필드 이름을 바꾸거나 타입을 바꾸면 그
  타입을 쓰는 모든 곳에서 눈에 띄게 드러난다(정적 검사기를 프로젝트에
  포함하진 않았지만, 타입 힌트 자체가 코드 읽는 사람에게 계약
  역할을 한다).
- **동료 리뷰**: 함수 본문을 안 읽어도 시그니처만으로 "무엇을
  넣고 무엇을 받는지" 설명할 수 있다.

## 9. JSONL을 선택한 이유

- 한 줄 = JSON 객체 1개 → 새 레코드는 파일 끝에 한 줄만 추가하면
  됨(append-friendly, `TransactionRepository.add()`가 이 방식).
- 한 줄씩 읽으면 되므로 제너레이터 스트리밍과 자연스럽게 맞물림
  (`_iter_jsonl()`).
- 사람이 텍스트 에디터로 열어도 한 줄 한 줄 읽을 수 있음(사람이
  검사하기 쉬움).
- `json`/`csv` 모두 표준 라이브러리라 별도 설치가 필요 없음.

`data/transactions.jsonl`, `data/categories.jsonl`,
`data/budgets.jsonl` 세 파일 모두 JSONL로 통일했다 — 공식 요구사항이
"JSONL 또는 CSV 중 하나를 선택"이라 세 저장소를 JSON 배열/JSONL을
섞어 쓰지 않고 하나의 포맷으로 통일해야 요구사항을 명확히
만족한다고 판단했다. **JSONL이 CSV보다 항상 우월하다는 뜻은
아니다** — 이 프로젝트는 append 위주 쓰기 패턴과 제너레이터 스트리밍이
잘 맞아서 JSONL을 골랐을 뿐이고, CSV는 오히려 import/export처럼
"교환 포맷"으로 쓸 때 더 적합해서 그 용도로 따로 쓰고 있다(내부
저장 포맷과 교환 포맷을 분리).

## 10. Repository / Service 분리 이유

**Repository가 하는 일**(`ledger/repository.py`):
- 파일 읽기/쓰기 (`_iter_jsonl`, `_append_jsonl`, `_atomic_write_jsonl`)
- 제너레이터 제공 (`iter_all()`)
- 원자적 재작성 (`update`/`delete`/`remove`/`set`)

**Service가 하는 일**(`ledger/services.py`):
- 카테고리 존재 검증 (`add_transaction`이 `categories.exists()` 확인)
- 사용중 카테고리 삭제 차단 (`remove_category`)
- 검색 필터링 (`search`)
- 월간 요약 계산 (`monthly_summary`)
- 예산 계산 (`monthly_summary` 안의 사용률/초과 여부)
- CSV import/export 오케스트레이션 (`import_csv`/`export_csv`)

**예상 질문**: "왜 Repository에서 카테고리 사용 여부를 검사하지
않았나요?"

**답변**: `CategoryRepository`가 그 규칙을 검사하려면
`TransactionRepository`를 알아야 하는데, 그러면 Repository끼리
서로 참조하게 되어 "Repository는 파일 하나만 책임진다"는 경계가
무너진다. 그 검사는 두 Repository를 조합해야 하는 일이므로, 둘 다
이미 들고 있는 `LedgerService.remove_category()`가 맡는 게 자연스럽다
(`ledger/services.py:299`).

## 11. 원자적 update/delete

**실제 흐름**(`ledger/repository.py::_atomic_write_jsonl`, 그리고
`update()`/`delete()`가 이를 호출):

```
원본 파일
→ 같은 디렉터리에 임시 파일 생성 (tempfile.mkstemp)
→ 변경된 전체 내용을 임시 파일에 씀
→ flush()
→ os.fsync()
→ os.replace(임시파일, 원본경로)
```

- **왜 직접 원본을 고치면 안 되는가**: 쓰는 도중 프로그램이
  죽으면(정전, 강제종료 등) 파일이 반쯤 쓰인 상태로 남아 다음 실행
  때 깨진 JSON을 읽게 된다.
- **왜 완전히 다 쓴 뒤에만 교체하는가**: `os.replace()`는 원자적
  연산이라 "교체 전"과 "교체 후" 둘 중 하나만 존재한다 — 중간
  상태가 없다.
- **대상 id가 없을 때**: `update()`/`delete()` 둘 다 대상을 못
  찾으면 `TransactionNotFoundError`를 던지고 **아무것도 쓰지 않는다**
  — 원본이 그대로 남는다(`ledger/repository.py:153-154`,
  `171-172`).

## 12. UNSET sentinel

**문제**: `update`는 "필드를 생략함(기존 값 유지)"과 "필드를 빈
값으로 명시함(지움)"을 구분해야 하는데, 기본값으로 `None`을 쓰면
이 둘을 구분할 수 없다.

```bash
python -m ledger update --id 1 --memo ""   # memo를 명시적으로 지움
python -m ledger update --id 1 --amount 5000   # memo 옵션 자체를 생략 → memo 그대로 유지
```

`--tags ""`도 동일하게 태그를 비운다. 옵션 자체를 안 쓰면 태그는
그대로 유지된다.

`ledger/services.py`에 전용 sentinel 클래스를 만들어 해결했다:

```python
class _UnsetType:
    def __repr__(self) -> str:
        return "UNSET"

UNSET = _UnsetType()

def update_transaction(self, transaction_id: int, *, memo: str | _UnsetType = UNSET, ...):
    new_memo = existing.memo if memo is UNSET else memo
```

`memo is UNSET`으로 비교하므로 `None`/`""`/`[]` 등 어떤 "정상적인"
값과도 절대 충돌하지 않는다.

**이것은 동료평가 핵심 질문 중 하나다** — "왜 `None`을 기본값으로
안 썼나요?"에 정확히 이 예시(`--memo ""`)로 답할 수 있어야 한다.

## 13. CSV import/export 설계

**스키마**(`ledger/services.py::CSV_FIELDNAMES`):

```
date,type,category,amount,memo,tags
```

**내부 거래 id는 CSV에 없다.** id는 사용자가 관리하는 값이 아니라
프로그램이 내부적으로 발급하는 값이기 때문이다 — CSV에 id를 넣으면
"이 id로 강제로 저장해달라"는 의미가 되어 기존 거래와 충돌하거나
`next_id()` 정책(양의 정수, 최댓값+1)을 우회하게 된다. 그래서 export는
id를 쓰지 않고, import는 있어도 무시하며 매 행마다 새 id를 발급한다.

**Import**:
- 유효한 행 하나하나가 `LedgerService.add_transaction()`을 그대로
  호출한다 — 대화형 `add`와 **완전히 같은 검증 로직**을 재사용
  (`ledger/services.py:360`).
- 잘못된 행(날짜 오류, 미등록 카테고리 등)은 건너뛰고 계속 진행,
  개수를 센다(`ImportResult.skipped`).
- 파일 자체를 못 열거나 헤더가 없거나 필수 컬럼이 빠지면 **명령
  전체가 실패**한다(행 처리를 시작조차 하지 않음).

**Export**:
- `--month` 또는 `--from`+`--to` 중 정확히 하나의 기간 조건이
  필요하다(조건 없는 export 금지).
- id를 쓰지 않는다.
- `iter_all()`을 직접 순회하며 즉시 쓴다(섹션 5의 O(1) 사례).

## 14. 카테고리 삭제 정책

- 어떤 거래라도 그 카테고리를 참조하고 있으면 삭제를 차단한다.
- 검사는 **Service 계층**에서, `CategoryRepository`를 건드리기
  전에 `TransactionRepository.iter_all()`을 스트리밍하며 확인한다
  (`ledger/services.py:299-309`).
- 캐스케이드 삭제(관련 거래도 같이 지움) 없음, 자동 치환(다른
  카테고리로 바꿔치기) 없음 — 사용자가 먼저 거래를 수정/삭제하도록
  유도한다.

## 15. 예산(Budget) 설계

- **월 전체 총예산**이다 — 카테고리별 예산이 아니다
  (`Budget(month: str, amount: int)`, `ledger/models.py:65-70`).
- `summary --month`가 같은 달의 예산이 설정돼 있으면 사용률(%)과
  초과 여부를 함께 보여준다.
- **예산 초과가 거래 추가를 막지 않는다** — `add_transaction()`/
  `update_transaction()` 어디에도 예산 검사가 없다. 예산은 순전히
  `monthly_summary()`에서의 리포팅/경고 기능이다.

## 16. "최신순"의 의미

**중요한 설계 결정**: "최신"은 **입력한(파일에 기록된) 순서**를
뜻하며, `Transaction.date` 값으로 다시 정렬한 것이 아니다.

- `transactions.jsonl`은 append-only라 파일 순서 = 입력 순서.
- `list_transactions()`는 이 순서를 그대로 뒤집어 보여준다.
- 예: 오늘 9월 1일 거래를 입력하고, 내일 지난주(8월 20일) 영수증을
  나중에 입력하면 — 8월 20일 거래가 "최신"으로 `list` 맨 위에
  나온다. 날짜가 더 과거인데도 그렇다.
- 만약 `date` 기준으로 다시 정렬하려면 파일 전체를 메모리에 올려
  정렬해야 해서 `deque(maxlen=N)` 스트리밍 전략(섹션 6)과 충돌한다.

이 한계를 숨기지 않고 README와 설계 문서에 명시해 두었다.

**예상 질문**: "list의 최신순은 거래 날짜 기준인가요?"

**답변**: "아니요, 파일에 기록된(입력한) 순서 기준입니다. 거래
날짜로 재정렬하면 전체 파일을 메모리에 올려 정렬해야 해서, 최신
N개만 유지하는 `deque` 스트리밍 방식과 충돌하기 때문에 의도적으로
입력 순서를 '최신'으로 정의했습니다."

---

## 17. 코드를 읽기 위한 Python·CLI 기초 배경지식

지금까지(1~16번)는 "이 프로젝트가 왜 이렇게 설계됐는가"를
설명했다. 이 섹션은 그 설명을 읽는 데 필요한 더 기초적인 Python/CLI
개념을 정리한 것이다. Python이나 CLI가 처음이라면 여기부터 읽고,
이미 익숙하다면 바로 예상 질문 섹션으로 건너뛰어도 된다. 흐름은
전부 동일하다: **개념이 무엇인지 → B2-1 어디에 썼는지 → 코드를 볼 때
무엇을 보면 되는지.**

### 17.1 `python3 -m ledger` 명령 한 줄 분해

실제 실행 예:

```bash
python3 -m ledger --data-dir ./test-data list --limit 5
```

| 토큰 | 의미 |
|---|---|
| `python3` | Python 실행 프로그램 자체 |
| `-m` | Python 자체 옵션. "뒤에 오는 이름을 module/package로 실행하라"는 뜻 |
| `ledger` | 이 프로젝트의 Python package(`ledger/` 디렉터리). `-m ledger`로 실행하면 `ledger/__main__.py`가 진입점이 된다 |
| `--data-dir ./test-data` | B2-1에서 `ledger/cli.py`가 직접 정의한 전역 CLI 옵션 |
| `list` | B2-1에서 정의한 subcommand |
| `--limit 5` | `list` subcommand에만 정의된 option과 그 값 |

**`python3 main.py`와 `python3 -m ledger`의 차이**:

- `python3 main.py` — [main.py](../main.py)라는 파일을 직접 실행. 파일 하나만 있으면 되고, 그 안에서 `ledger.cli.main()`을 불러 쓴다.
- `python3 -m ledger` — `ledger` package를 module로 실행. Python이 `ledger/__main__.py`를 찾아 실행한다.
- 이 프로젝트는 두 방식 모두 결과적으로 같은 [ledger/cli.py](../ledger/cli.py)의 `main()`을 호출하도록 만들어져 있지만, **현재 B2-1의 정식(canonical) 실행 방식은 `python -m ledger`다.**

관련 실제 파일: [main.py](../main.py), [ledger/\_\_main\_\_.py](../ledger/__main__.py), [ledger/cli.py](../ledger/cli.py).

### 17.2 package / module / file의 차이

- `main.py` — Python 파일 하나 = **module** 한 개.
- `ledger/` — 여러 module을 묶어 놓은 **package**.
- `ledger/cli.py`, `ledger/services.py`, `ledger/repository.py`, `ledger/models.py`, `ledger/validators.py`, `ledger/decorators.py`, `ledger/errors.py` — package 안에 들어 있는 각각의 module.
- `ledger/__init__.py` — 이 디렉터리가 그냥 폴더가 아니라 "package로 취급되는 영역"임을 나타내는 파일(현재는 한 줄짜리 설명 문자열만 있다).
- `ledger/__main__.py` — `python -m ledger`로 실행했을 때 Python이 자동으로 찾아 실행하는 진입점 파일.

이 이상으로 Python import 시스템 내부까지 들어갈 필요는 없다 —
동료평가에서는 "무엇이 파일이고 무엇이 폴더(package)인지"만
정확히 구분하면 충분하다.

### 17.3 CLI란 무엇인가

CLI = Command-Line Interface(명령줄 인터페이스). GUI와 대비하면
쉽다.

| | 사용 방식 |
|---|---|
| GUI | 버튼을 클릭하고 마우스로 조작한다 |
| CLI | 터미널에 명령어와 옵션을 문자로 입력한다 |

B2-1은 화면(GUI) 없이 터미널 자체를 사용자 인터페이스로 쓴다:

```bash
python -m ledger list --limit 5
```

관련 기술 영역 이름: CLI 개발(command-line interface design),
argument parsing(인자 파싱).

### 17.4 Command / Subcommand / Option / Argument

실제 예:

```bash
python -m ledger search --category food --type expense
```

| 구성 요소 | 값 | 역할 |
|---|---|---|
| subcommand | `search` | 어떤 동작을 할지 |
| option | `--category` | 어떤 조건을 줄지 |
| option value | `food` | 그 조건의 값 |
| option | `--type` | 또 다른 조건 |
| option value | `expense` | 그 조건의 값 |

현재 B2-1의 subcommand 10개: `add`, `list`, `search`, `summary`,
`budget`, `category`, `update`, `delete`, `import`, `export`.

이 중 `budget`, `category`는 그 아래에 다시 subcommand를 갖는
**nested subcommand** 구조다: `budget set`, `category list`,
`category add`, `category remove`. 실제 정의는
[ledger/cli.py](../ledger/cli.py)의 `build_parser()`를 참고.

### 17.5 `--옵션` 이름은 누가 정하는가

두 층위를 구분해야 한다.

**이미 존재하는 관례**: `--옵션이름` 형태(long option) 자체는
Unix/Linux 계열 CLI 프로그램에서 널리 쓰이는 관례다. `--help`,
`--version` 같은 이름은 이 관례를 따른 것.

**개발자가 직접 정의하는 부분**: `--data-dir`, `--limit`,
`--month`, `--category`처럼 정확히 어떤 이름을 쓸지, 무슨 뜻으로
쓸지는 이 프로그램을 만든 사람이 정한다. B2-1에서는 기능
요구사항을 바탕으로 이름을 정했고, 실제 등록은
[ledger/cli.py](../ledger/cli.py)의 `argparse` 설정(`add_argument()`
호출들)에서 이루어진다.

즉, **문서가 옵션을 만드는 것이 아니라, `cli.py`의 argparse 정의가
실제 프로그램 동작의 source of truth(근거 자료)다.** 문서와 코드가
어긋나면 코드가 맞다.

### 17.6 argparse란 무엇인가

`argparse`는 Python **표준 라이브러리**다(별도 설치 불필요).
역할:

- 커맨드라인 문자열(`sys.argv`)을 command/subcommand/option으로 파싱
- 필수 옵션이 빠졌는지 검사
- `type=int` 같은 지정으로 문자열 → 숫자 등 기본 형식 변환
- `--help`를 자동으로 만들어 줌
- 사용법이 잘못되면 usage 메시지를 출력하고 **exit code 2**로 종료

B2-1에서 `--data-dir`, `--limit`, `--month`, `--id` 등을 정의하는
곳이 전부 [ledger/cli.py](../ledger/cli.py)의 `build_parser()`다.
`--help`는 우리가 직접 구현한 게 아니라 argparse가 기본으로
제공하는 기능이다.

### 17.7 `--data-dir`의 의미

- 기본값: `./data`
- 사용 예: `python -m ledger --data-dir ./test-data list`
- 의미: "이번 실행에서는 데이터를 `./test-data`에서 읽고 쓰라."

**장점**: 실제 운영 데이터와 테스트용 데이터를 분리할 수 있고,
여러 독립된 데이터셋을 동시에 쓸 수 있으며, 테스트 코드가 매번
임시 디렉터리를 만들어 격리된 상태로 검증하기 쉬워진다. 즉
Repository가 특정 폴더 하나에 고정돼 있지 않다.

이 옵션은 Python 자체가 제공하는 옵션이 아니라, B2-1에서
argparse로 직접 정의한 **전역 옵션**이다([ledger/cli.py](../ledger/cli.py)
`build_parser()`의 `parser.add_argument("--data-dir", ...)`). 전역
옵션이라 subcommand보다 **앞**에 와야 한다:

```bash
python -m ledger --data-dir ./test-data list   # 올바른 사용
python -m ledger list --data-dir ./test-data   # 현재 구현에서는 잘못된 사용
```

### 17.8 B2-1에서 DB를 사용했는가?

**결론: 사용하지 않았다.** MySQL, PostgreSQL은 물론 SQLite 기반
저장도 쓰지 않았다.

현재 구조와 일반적인 DB 애플리케이션 구조를 나란히 놓으면:

```
B2-1:        CLI → Service → Repository → JSONL 파일
일반 DB 앱:  CLI → Service → Repository → Database
```

즉 B2-1에서는 Database가 있어야 할 자리에 JSONL 파일이 있다고
이해하면 된다.

**왜 DB를 쓰지 않았는가**: 미션 요구사항이 파일 기반 저장(JSONL
또는 CSV)을 요구했고, 파일 I/O 자체를 학습하는 것과 Python 표준
라이브러리만으로 구현하는 것이 미션의 목적이었기 때문이다.

Repository 계층을 Service와 분리해 둔 덕분에(섹션 10 참고), 저장
방식이 바뀌어도 Service 쪽 코드는 영향을 덜 받는 구조이긴 하다.
다만 **"DB로 즉시 교체 가능하다"처럼 과장해서 설명하지는 않는다** —
실제로 DB 어댑터를 만들어 검증한 적은 없다.

### 17.9 표준 라이브러리 vs Python 언어 기능

초심자가 자주 헷갈리는 구분이다.

| 구분 | B2-1 사례 | 의미 |
|---|---|---|
| Python 언어 기능 | Generator / `yield` | Python 문법 자체(설치 불필요, 언어에 내장) |
| Python 언어 기능 | Type Hint 문법(`int \| None` 등) | Python 코드에 타입을 표기하는 문법 |
| 표준 라이브러리 | `argparse` | CLI 파싱 |
| 표준 라이브러리 | `dataclasses` | 데이터 클래스 |
| 표준 라이브러리 | `collections.deque` | 최대 길이를 가진 큐 |
| 표준 라이브러리 | `tempfile` | 임시 파일 생성 |
| 표준 라이브러리 | `os` | 파일시스템/OS 관련 기능 |
| 표준 라이브러리 | `csv` | CSV 처리 |
| 표준 라이브러리 | `json` | JSON 처리 |
| 표준 라이브러리 | `datetime` | 날짜 처리 |
| 표준 라이브러리 | `pathlib` | 경로(Path) 처리 |
| 표준 라이브러리 | `unittest` | 테스트 작성/실행 |

**표준 라이브러리**는 Python을 설치하면 자동으로 함께 들어 있는
모듈들이라 `pip install` 같은 별도 설치가 필요 없다. B2-1은 이
표준 라이브러리만으로 구현됐다(섹션 23의 예상 질문 참고).

### 17.10 dataclass, 초심자용 보충 설명 (→ 4번 섹션과 함께 읽기)

가장 쉬운 설명: **"관련된 데이터를 하나의 정해진 양식으로 묶는
클래스."**

예를 들어 `Transaction`은 이런 필드들을 묶어 놓은 양식이다:

```
Transaction
├─ id
├─ type
├─ date
├─ amount
├─ category
├─ memo
└─ tags
```

일반 class를 쓰면 `__init__`, `__repr__`, `__eq__` 같은 반복되는
코드를 직접 다 작성해야 하는데, `@dataclass`를 붙이면 필드
선언만으로 이 코드들이 자동으로 만들어진다.

dict와 비교하면 감이 온다:

```python
transaction["amount"]   # dict라면 이렇게 키로 접근
transaction.amount      # dataclass는 속성으로 접근
```

B2-1에서 dataclass의 역할: **저장 기술이 아니다. DB도 아니다.**
거래 하나(또는 예산, 검색 조건 등)의 "형태(shape)"를 코드로
표현한 것뿐이다. 실제 저장은 여전히 JSONL 파일이 담당한다.

**코드 리뷰 포인트**:
- `@dataclass`가 붙은 클래스가 어떤 데이터를 표현하는가?
- 필드 이름과 타입은 무엇인가?
- 기본값이 있는 필드는 무엇인가?

자세한 목록과 실제 필드는 4번 섹션 표를 참고.

### 17.11 `deque(maxlen=N)`, 초심자용 보충 설명 (→ 6번 섹션과 함께 읽기)

`deque`는 "덱"이라고 읽는다. 일반적으로는 양쪽 끝에서 넣고 뺄 수
있는 큐 자료구조지만, B2-1에서 중요한 건 그 자체보다
`deque(maxlen=N)` 옵션이다.

`maxlen=3`인 deque에 1, 2, 3, 4, 5를 순서대로 넣으면:

```
1 → [1]
2 → [1, 2]
3 → [1, 2, 3]
4 → [2, 3, 4]   (꽉 차서 가장 오래된 1이 자동으로 밀려남)
5 → [3, 4, 5]
```

즉 **"최근 N개만 자동으로 기억하는 대기열"**이다. B2-1의
`list --limit 3`이 정확히 이 동작과 연결된다(실제 위치와 이유는
6번 섹션 참고).

전체를 리스트로 만든 뒤 마지막 N개를 슬라이싱하는 방식과
비교하면:

| 방식 | 시간 | 메모리 |
|---|---|---|
| 전체 `list` 후 슬라이싱 | O(N) | O(N) |
| Generator + `deque(maxlen=N)` | O(N) | O(limit) |

**주의**: Generator와 deque를 썼다고 해서 "파일을 덜 읽는다"는
뜻은 아니다. 시간은 여전히 파일 전체 크기(N)에 비례한다 — 줄어드는
건 메모리다. 이 구분은 17.13에서 더 자세히 다룬다.

### 17.12 Generator / `yield`, 초심자용 보충 설명 (→ 5번 섹션과 함께 읽기)

Generator는 라이브러리가 아니라 **Python 언어 자체의 문법**이다.

일반 함수:

```python
def values():
    return [1, 2, 3]   # 결과를 한 번에 다 만들어서 반환
```

Generator 함수:

```python
def values():
    yield 1
    yield 2
    yield 3
```

- `return` — 결과를 반환하고 함수를 완전히 종료한다.
- `yield` — 값을 하나 내보내고, 함수의 실행 상태를 그 자리에 잠시
  "보존"한다. 다음에 값을 요청받으면 멈췄던 지점부터 이어서
  실행한다.

B2-1에서는 이런 식으로 한 건씩 받아 처리한다:

```python
for transaction in repository.iter_all():
    ...
```

실제 구현 위치와 코드는 5번 섹션 참고.

### 17.13 Generator를 쓰면 정확히 무엇이 좋아지는가

**흔한 오해**: "Generator를 쓰면 무조건 더 빨라진다."

**정확한 설명**: Generator의 주된 장점은 속도가 아니라, **전체
데이터를 한 번에 메모리에 올리지 않고 필요한 순간에 하나씩
처리할 수 있다**는 것이다.

| | 전체 로드 | Generator |
|---|---|---|
| 100만 건을 읽을 때 | 100만 건을 전부 메모리에 올린 뒤 처리 | 1건 읽기 → 처리 → 다음 1건 읽기 → 처리 → ... |

B2-1의 실제 사례로 시간(time)과 메모리(memory)를 나눠서 보면:

- `list --limit 5` — 시간은 파일 전체를 읽으므로 O(N), 메모리는
  `deque`에 5개만 보관하므로 O(5).
- `summary` — 한 건씩 읽으며 합계만 누적. 원본 거래 전체를
  저장할 필요가 없다.
- `export` — 한 건 읽기 → 조건 확인 → 바로 CSV에 기록 → 버림 →
  다음 건.

그래서 정확한 한 줄 요약은: **"Generator는 속도 최적화라기보다
스트리밍과 메모리 효율을 위한 기술이다."** (시간 복잡도별 정확한
차이는 5번 섹션 표 참고 — `list`/`search`/`summary`/`export`가
전부 같은 메모리 특성을 갖는 건 아니다.)

### 17.14 tempfile / os, 초심자용 보충 설명 (→ 11번 섹션과 함께 읽기)

둘 다 Python **표준 라이브러리**다.

**`tempfile`**: 안전하게 임시 파일을 만들기 위한 모듈. B2-1에서는
원본 거래 파일을 바로 덮어쓰지 않고, 새 내용을 먼저 임시 파일에
작성하기 위해 쓴다.

**`os`**: 운영체제(Operating System) 관련 기능을 제공하는 모듈.
B2-1에서 핵심적으로 쓰는 두 함수:

- `os.fsync()` — 파일 내용이 저장장치(디스크)에 실제로 반영되도록
  운영체제에 요청한다. (그 앞에 호출되는 `flush()`는 Python
  프로그램 쪽 쓰기 버퍼를 운영체제 쪽으로 넘기는 것이고,
  `os.fsync()`는 그 다음 단계다.)
- `os.replace()` — 다 작성된 임시 파일을 원본 파일 위치로
  교체한다.

너무 깊은 OS 내부 동작까지 설명할 필요는 없다 — "쓰기 버퍼를
비우고(flush) → 디스크에 반영을 요청하고(fsync) → 완성된 파일로
교체한다(replace)"는 순서만 이해하면 된다.

### 17.15 왜 원본 파일을 바로 수정하지 않았는가 (→ 11번 섹션과 함께 읽기)

코드 리뷰 관점에서 중요한 질문이다.

**안전하지 않은 방식**(B2-1이 쓰지 않은 방식):

```
원본 파일을 쓰기 모드(w)로 연다
→ 기존 내용이 즉시 지워진다
→ 새 내용을 쓰는 도중 오류가 나면
→ 원본도 이미 손상된 상태로 남는다
```

**B2-1이 실제로 쓰는 방식**:

```
원본은 그대로 둔다
 ↓
임시 파일에 새 내용을 전부 작성한다
 ↓
정상적으로 다 썼다면
 ↓
flush + os.fsync()로 디스크에 반영
 ↓
os.replace()로 임시 파일을 원본 위치로 교체
```

핵심 목적은 **"수정 도중 실패했을 때 원본 데이터가 손상될
위험을 줄이는 것"**이다. 실제 구현과 예외 처리는 11번 섹션 참고.

### 17.16 코드 리뷰할 때 무엇을 보면 되는가 — 파일 지도

이 표는 "어디부터 봐야 할지 모르겠다"는 초심자를 위한 시작점이다.

| 궁금한 내용 | 볼 파일 | 볼 코드 |
|---|---|---|
| 명령/옵션 정의 | [ledger/cli.py](../ledger/cli.py) | `build_parser()`, `add_argument()` |
| `python -m ledger` 진입점 | [ledger/\_\_main\_\_.py](../ledger/__main__.py) | `main()` 호출 |
| 거래 데이터 구조 | [ledger/models.py](../ledger/models.py) | `Transaction` `@dataclass` |
| Generator | [ledger/repository.py](../ledger/repository.py) | `iter_all()`, `_iter_jsonl()` |
| 최근 N건 처리 | [ledger/services.py](../ledger/services.py) | `deque(maxlen=limit)` |
| 비즈니스 규칙 | [ledger/services.py](../ledger/services.py) | `LedgerService` |
| 파일 저장 | [ledger/repository.py](../ledger/repository.py) | `_append_jsonl`, `_atomic_write_jsonl` |
| 안전한 수정/삭제 | [ledger/repository.py](../ledger/repository.py) | `tempfile.mkstemp`, `os.fsync`, `os.replace` |
| CLI 공통 오류 처리 | [ledger/decorators.py](../ledger/decorators.py) | `handle_errors` |
| CSV 처리 | [ledger/services.py](../ledger/services.py) | `import_csv`, `export_csv` |
| 입력 검증 | [ledger/validators.py](../ledger/validators.py) | `validate_date`, `validate_amount`, `validate_transaction_type` 등 |

---

# 동료평가 예상 질문

## 핵심 질문 (10초/30초 답변 + 코드 위치)

**1. 왜 JSONL인가?**
- 10초: "한 줄에 객체 하나라 append와 스트리밍에 유리하고, `json`이
  표준 라이브러리라 추가 설치가 필요 없어서 골랐습니다."
- 30초: "공식 요구가 JSONL이나 CSV 중 하나로 통일하라는 것이어서,
  거래를 계속 추가하는 append 위주 쓰기 패턴과 한 줄씩 읽는 제너레이터
  스트리밍에 더 잘 맞는 JSONL로 세 파일(`transactions`/`categories`/
  `budgets`)을 통일했습니다. CSV는 대신 import/export 교환 포맷으로
  따로 씁니다."
- 코드: `ledger/repository.py`

**2. Generator를 어디서 썼나?**
- 10초: "`TransactionRepository.iter_all()`이 `yield`로 파일을 한
  줄씩 읽어 넘깁니다."
- 코드: `ledger/repository.py:102-108`

**3. `yield`와 `return`의 차이는?**
- 10초: "`return`은 함수를 끝내고 값 하나를 돌려주지만, `yield`는
  함수를 일시정지하고 값을 하나 내보낸 뒤, 다음 호출 때 그 지점부터
  다시 이어서 실행합니다. 그래서 전체 결과를 한 번에 안 만들고
  하나씩 만들어 낼 수 있습니다."

**4. 왜 list 전체를 메모리에 올리지 않았나?**
- 10초: "파일이 커지면 메모리도 같이 커지는 걸 피하려고요. 제너레이터로
  한 줄씩만 처리합니다."
- 코드: `ledger/repository.py::_iter_jsonl`

**5. `deque`를 왜 썼나?**
- 섹션 6 참고. 코드: `ledger/services.py:126`

**6. search는 정말 streaming인가?**
- 30초: "필터링 자체는 `iter_all()`을 스트리밍하면서 하나씩
  검사합니다. 다만 최신순으로 보여줘야 해서 조건에 맞는 레코드만
  리스트에 모았다가 마지막에 뒤집습니다. 그래서 메모리가 전체 파일
  크기가 아니라 '매칭된 개수'에 비례합니다 — 완전한 상수 메모리는
  아니고, `list`보다는 느슨한 스트리밍입니다."
- 코드: `ledger/services.py:131-162`

**7. Decorator를 왜 썼나?**
- 섹션 7 참고.

**8. Decorator가 실제 어디에 적용됐나?**
- 10초: "`ledger/cli.py`의 `_dispatch` 함수 하나에 `@handle_errors`로
  적용했습니다. 모든 명령이 이 함수를 거칩니다."
- 코드: `ledger/cli.py:330`

**9. Type Hint 장점은?**
- 섹션 8 참고.

**10. dataclass를 왜 썼나?**
- 10초: "`__init__`/`__repr__`/`__eq__`를 직접 안 써도 되고, 필드
  이름으로 값을 주고받아서 함수 시그니처가 안정적으로 유지됩니다."
- 코드: `ledger/models.py`

**11. Service와 Repository 차이는?**
- 섹션 10 참고.

**12. 카테고리 삭제를 왜 막았나?**
- 10초: "삭제하면 그 카테고리를 참조하는 거래들이 존재하지 않는
  카테고리를 가리키게 돼서, 데이터 무결성이 깨지기 때문입니다."
- 코드: `ledger/services.py:299-309`

**13. update/delete는 파일을 어떻게 안전하게 수정하나?**
- 섹션 11 참고.

**14. `os.replace`를 왜 썼나?**
- 10초: "원자적 연산이라 교체 도중 중간 상태가 존재하지 않기
  때문입니다. 프로그램이 중간에 죽어도 원본 아니면 새 파일, 둘 중
  하나만 남습니다."

**15. UNSET sentinel은 왜 필요한가?**
- 섹션 12 참고 — 가장 자주 나오는 질문 중 하나.

**16. CSV에 id가 왜 없나?**
- 섹션 13 참고.

**17. import에서 잘못된 한 행이 있으면 어떻게 되나?**
- 10초: "그 행만 건너뛰고 계속 처리합니다. 마지막에 `imported=N,
  skipped=M`으로 몇 건 성공/실패했는지 보여줍니다."
- 코드: `ledger/services.py:351-365`

**18. budget 초과 시 거래 저장을 왜 막지 않나?**
- 10초: "예산은 경고/리포팅 목적이지 통제 목적이 아니라고
  판단했습니다. 초과해도 계속 기록할 수 있어야 실제 지출을 놓치지
  않습니다."
- 코드: `ledger/services.py::add_transaction`(예산 검사 없음),
  `monthly_summary`(경고만 계산)

**19. `--data-dir`는 왜 필요한가?**
- 10초: "테스트나 다른 용도로 여러 데이터셋을 분리해서 쓸 수
  있어야 하기 때문입니다. 기본값은 `./data`입니다."
- 코드: `ledger/cli.py:45-50`

**20. 프로그램 종료 후 데이터가 왜 유지되나?**
- 10초: "매 명령이 실행될 때마다 파일에서 읽고 파일에 씁니다.
  메모리에만 있는 상태가 없어서, 프로세스가 끝나도 다음 실행이 파일을
  다시 읽으면 그대로 이어집니다."

**21. exit code 0/1/2 차이는?**
- 10초: "0은 성공, 1은 애플리케이션 에러(`LedgerError`), 2는
  argparse 사용법 에러(옵션 누락 등)입니다."
- 코드: `ledger/decorators.py::handle_errors`(exit 1),
  argparse 자체(exit 2)

**22. 예상 가능한 오류에서 traceback을 왜 숨기나?**
- 10초: "사용자 실수(날짜 형식 오류 등)에 파이썬 내부 스택트레이스를
  보여주는 건 불친절하고 원인 파악에도 안 도움이 됩니다. `handle_errors`가
  `LedgerError`만 잡아 `[오류]`/`[힌트]`로 바꿔 보여줍니다."

**23. 외부 라이브러리를 왜 안 썼나?**
- 10초: "미션 요구사항이 표준 라이브러리만 쓰는 것이었고, `argparse`/
  `csv`/`json`/`dataclasses`만으로 충분히 구현 가능했습니다."

**24. 최신순은 date 기준인가?**
- 섹션 16 참고 — 아니오, 입력 순서 기준.

**25. 테스트는 무엇을 검증했나?**
- 10초: "217개 단위/통합 테스트가 Repository, Service, CLI 세
  계층을 각각, 그리고 CSV round-trip까지 검증합니다. 실제 임시
  디렉터리를 쓰는 리포지토리로 동작하고 모킹을 최소화했습니다."
- 근거: [docs/m03-final-qa-report.md](m03-final-qa-report.md)

## 기초 배경지식 질문 (17번 섹션 연결)

**26. `python -m ledger`는 어떤 구조로 실행되나요?**
- 10초: "`-m`은 뒤에 오는 이름을 module/package로 실행하라는
  Python 자체 옵션입니다. `ledger`는 이 프로젝트의 package라서,
  `-m ledger`로 실행하면 `ledger/__main__.py`가 진입점이 됩니다."
- 30초: "`python3 main.py`는 파일 하나를 직접 실행하는 방식이고,
  `python3 -m ledger`는 `ledger` package를 module로 실행하는
  방식입니다. `-m`을 쓰면 Python이 `ledger` 디렉터리 안의
  `__main__.py`를 찾아서 실행합니다. 두 방식 모두 결과적으로
  `ledger/cli.py`의 `main()`을 호출하지만, 이 프로젝트의 정식
  실행 방식은 `python -m ledger`입니다."
- 코드: [main.py](../main.py), [ledger/\_\_main\_\_.py](../ledger/__main__.py)

**27. `ledger`는 파일인가요, 폴더인가요?**
- 10초: "폴더(package)입니다. 그 안에 `cli.py`, `services.py`
  같은 여러 module 파일이 들어 있습니다."
- 코드: `ledger/` 디렉터리 전체, [ledger/\_\_init\_\_.py](../ledger/__init__.py)

**28. CLI / argparse / option은 서로 어떤 관계인가요?**
- 30초: "CLI는 터미널에 명령어를 입력해서 프로그램을 조작하는
  방식 자체를 뜻합니다. `argparse`는 그 명령어 문자열을
  command/subcommand/option으로 쪼개 주는 Python 표준
  라이브러리이고, `--data-dir`, `--limit` 같은 구체적인 option
  이름과 의미는 이 프로그램을 만든 사람이 정해서
  `ledger/cli.py`의 `build_parser()` 안에서 `add_argument()`로
  등록합니다. 즉 argparse는 파싱 엔진이고, 실제 옵션 목록은
  코드가 곧 근거 자료(source of truth)입니다."
- 코드: [ledger/cli.py](../ledger/cli.py) `build_parser()`

**29. `--data-dir`는 Python이 원래 제공하는 옵션인가요?**
- 10초: "아니요. Python 자체 옵션이 아니라 B2-1에서 argparse로
  직접 만든 전역 옵션입니다. Python이 원래 제공하는 옵션은
  `-m`처럼 `python` 명령 자체에 붙는 것들입니다."
- 코드: [ledger/cli.py](../ledger/cli.py) `build_parser()`의
  `parser.add_argument("--data-dir", ...)`

**30. `--option`처럼 `--`로 시작하는 옵션 형식은 누가 정하나요?**
- 10초: "`--이름` 형태(long option) 자체는 Unix/Linux 계열 CLI의
  오래된 관례입니다. 하지만 `--data-dir`, `--limit`처럼 정확히
  어떤 이름을 쓸지는 이 프로그램을 만든 우리가 정하고,
  `cli.py`의 argparse 설정에 등록해야 실제로 동작합니다."

**31. argparse는 무엇을 하는 라이브러리인가요?**
- 10초: "커맨드라인 입력을 명령어와 옵션으로 파싱하고, 필수 옵션
  누락을 검사하고, 문자열을 숫자로 변환하고, `--help`를 자동으로
  만들어 주는 Python 표준 라이브러리입니다."
- 코드: [ledger/cli.py](../ledger/cli.py) `build_parser()`

**32. 이 프로젝트는 데이터베이스를 사용했나요?**
- 30초: "사용하지 않았습니다. MySQL, PostgreSQL은 물론 SQLite도
  쓰지 않았습니다. 대신 `CLI → Service → Repository → JSONL
  파일` 구조로, 일반적인 DB 애플리케이션에서 Database가 있을
  자리에 JSONL 파일이 들어가 있습니다. 미션 요구사항이 파일 기반
  저장을 요구했고, 파일 I/O와 표준 라이브러리 학습이 목적이었기
  때문입니다. Repository를 분리해 뒀지만 'DB로 바로 교체
  가능하다'는 뜻은 아닙니다 — 실제로 검증한 적은 없습니다."
- 코드: [ledger/repository.py](../ledger/repository.py)

**33. `dataclass`/`deque`/`tempfile`/`os`는 각각 무엇인가요?**
- 10초: "`dataclass`는 데이터 형태를 묶는 클래스를 쉽게 만들어
  주는 표준 라이브러리, `deque`는 `maxlen`을 주면 오래된 항목을
  자동으로 밀어내는 큐, `tempfile`은 임시 파일을 안전하게 만드는
  모듈, `os`는 `fsync`/`replace`처럼 운영체제 파일 조작 기능을
  제공하는 모듈입니다. 넷 다 Python 표준 라이브러리입니다."
- 코드: 17.9~17.14 섹션 참고

**34. Generator를 쓰면 처리 속도가 빨라지나요?**
- 30초: "아니요, Generator의 핵심 장점은 속도가 아니라
  메모리입니다. 전체 파일을 읽어야 하는 시간(예: `list`의 시간
  복잡도 O(N))은 Generator를 쓰든 안 쓰든 똑같습니다. 달라지는
  건 메모리로, 전체를 리스트로 만들지 않고 한 건씩 처리하기 때문에
  `list --limit 5`처럼 메모리는 O(limit)만 씁니다. '빨라진다'가
  아니라 '한 번에 메모리에 다 올리지 않아도 된다'가 정확한
  설명입니다."
- 코드: 17.13 섹션, [ledger/repository.py](../ledger/repository.py) `iter_all()`

**35. `tempfile`/`os`는 파일 안전성에 어떻게 기여하나요?**
- 30초: "원본 파일을 직접 열어 덮어쓰면, 쓰는 도중 프로그램이
  죽었을 때 원본이 반쯤 쓰인 상태로 손상될 수 있습니다. B2-1은
  대신 `tempfile.mkstemp()`로 같은 디렉터리에 임시 파일을 만들어
  새 내용을 전부 쓴 뒤, `flush()`와 `os.fsync()`로 디스크에
  반영을 확인하고, 마지막에 `os.replace()`로 임시 파일을 원본
  위치로 교체합니다. `os.replace()`는 원자적 연산이라 교체
  전/후 중 하나만 존재하고 중간 상태가 없습니다."
- 코드: [ledger/repository.py](../ledger/repository.py) `_atomic_write_jsonl`

---

# 동료평가 시연 순서

아래 명령은 전부 실제 `argparse` 파서와 일치한다(문서에만 있고
파서에 없는 명령은 없음). 임시 데이터 디렉터리로 시연할 것을
권장한다: `python -m ledger --data-dir ./demo-data <command>`.

| 순서 | 명령 | 기대 결과 | 증명하는 요구사항 |
|---|---|---|---|
| 1 | `python -m ledger --help` | 10개 명령 전부 표시, exit 0 | `--help`, CLI 진입점 |
| 2 | `python -m ledger --data-dir ./demo-data category add` → `식비` 입력 | `[저장 완료] 카테고리 '식비' 등록` | category 관리, 대화형 입력 |
| 3 | `python -m ledger --data-dir ./demo-data add` → `2026-09-16` / `expense` / `식비` / `15000` / `점심` / `meal,lunch` | `[저장 완료] id=TX-000001` | add, 대화형, id 발급 |
| 4 | `python -m ledger --data-dir ./demo-data add` → `2026-09-01` / `income` / `식비` / `300000` / `용돈` / (Enter) | `[저장 완료] id=TX-000002` | add, income 타입 |
| 5 | `python -m ledger --data-dir ./demo-data list` | 최신순(id 2, 1 순서)으로 2건 출력 | list, 제너레이터+deque |
| 6 | `python -m ledger --data-dir ./demo-data search --category 식비` | 2건 출력 | search 필터 |
| 7 | `python -m ledger --data-dir ./demo-data budget set --month 2026-09 --amount 20000` | `[저장 완료] 2026-09 예산 20000원` | budget, 월 총예산 |
| 8 | `python -m ledger --data-dir ./demo-data summary --month 2026-09` | 총수입/총지출/잔액/TOP N/예산/사용률/초과 경고 | summary, 예산 계산 |
| 9 | `python -m ledger --data-dir ./demo-data update --id 1 --amount 18000` | `[수정 완료] id=TX-000001` | update, 부분 수정 |
| 10 | `python -m ledger --data-dir ./demo-data export --out ./demo-data/export.csv --month 2026-09` | `[완료] ...export.csv (2 records)` | export, CSV, 제너레이터 재사용 |
| 11 | `python -m ledger --data-dir ./demo-data delete --id 2` | `[삭제 완료] id=TX-000002` | delete |
| 12 | `python -m ledger --data-dir ./demo-data import --from ./demo-data/export.csv` | `[완료] imported=2, skipped=0` | import, round-trip |
| 13 | `python -m ledger --data-dir ./demo-data list` | 방금 import된 거래까지 포함해 출력 | 영속성 확인 |

여유가 있으면 에러 시나리오 하나를 추가로 보여주는 것을 권장한다:
`python -m ledger --data-dir ./demo-data delete --id 999` →
`[오류] 존재하지 않는 거래 ID입니다.` / `[힌트] list 명령으로 거래
ID를 확인하세요.` (exit 1, 트레이스백 없음).

---

# 동료평가 PASS 체크리스트

아래는 [docs/m03-final-qa-report.md](m03-final-qa-report.md)에서
검증된 실제 증거를 근거로 한다.

- [x] 프로그램이 실행된다 (`python -m ledger`)
- [x] `--help` 동작 (루트 + 10개 서브커맨드)
- [x] 10개 명령 전부 동작 (add/list/search/summary/budget/category/update/delete/import/export)
- [x] 데이터 파일 3개 (`transactions.jsonl`, `categories.jsonl`, `budgets.jsonl`)
- [x] 영속성 (프로세스 재시작 후에도 데이터 유지)
- [x] Generator 실사용 (`TransactionRepository.iter_all()`)
- [x] Decorator 실사용 (`handle_errors` → `cli.py::_dispatch`)
- [x] Type Hint (공개 함수/메서드/필드 전체)
- [x] 클래스 2개 이상 (비-예외 클래스 10개 + 예외 클래스 15개)
- [x] 모듈 3개 이상 (`ledger/` 내 7개 모듈)
- [x] CRUD (add/update/delete + list/search 조회)
- [x] search (6개 필터: `--from --to --category --type --q --tag`)
- [x] summary (월간 요약, TOP N, 예산 현황)
- [x] budget (월 총예산, 사용률, 초과 경고, 거래는 계속 허용)
- [x] category 무결성 (사용중 삭제 차단)
- [x] CSV import/export (id 없는 스키마, 행 단위 스킵, 기간 필터 필수)
- [x] 에러 시 non-zero exit (1 또는 2)
- [x] 원인 + 힌트 메시지 (`[오류]`/`[힌트]`)
- [x] README (설치/실행/명령 예시/CSV 스키마 전부 포함)
- [x] 테스트 (217개, 전부 PASS)

**현재 근거**: 217 tests PASS, 공식 요구사항 감사 28 PASS / 0 BLOCKED
(둘 다 [docs/m03-final-qa-report.md](m03-final-qa-report.md)에서 확인됨).
