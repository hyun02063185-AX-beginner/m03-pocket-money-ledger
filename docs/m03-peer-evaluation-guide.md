# M03 — 동료평가 대비 가이드

이 문서는 Codyssey M03 「나만의 용돈 기입장 프로그램」 동료평가에서
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
