# M03 — 나만의 용돈 기입장 프로그램 아키텍처 설계

> **Historical/reference document.** 설계 결정과 요구사항 추적을 보존한 상세 기록이다.
> 처음 읽을 문서는 [M03 Hands-on Guide](m03-hands-on-guide.md), 코드 학습 문서는
> [M03 Code Reading Guide](m03-code-reading-guide.md), 요약 참조는 [M03 Reference](m03-reference.md)다.

이 문서는 기능 구현 이전 단계에서 프로젝트 구조와 설계를 확정하기 위한
아키텍처 리뷰다. Sprint 0에서 초안을 만들었고, Sprint 0B에서 공식 원문과
대조해 여러 항목을 정정했다 — **이 문서는 Sprint 0B 기준 최종본이며,
Sprint 0 초안 내용을 대체한다.** 이번 스프린트에서도 CRUD 기능은
구현하지 않는다. 골격 파일은 시그니처/타입힌트/docstring만 가지며 본문은
`raise NotImplementedError`로 유지한다.

## 0. 현재 상태 확인

작업 디렉토리는 Sprint 0에서 생성한 골격이 그대로 남아 있고, 여전히
git 저장소는 초기화되어 있지 않다. Sprint 0B는 기존 파일을 덮어쓰는
대신 대조 결과에 따라 필요한 부분만 수정한다(섹션 30 "골격 정합화" 참고).

## 0.1 Sprint 0B 변경 이력 (Sprint 0 대비)

| 항목 | Sprint 0 | Sprint 0B (최종) | 근거 |
|---|---|---|---|
| 실행 방식 | `python main.py` | `python -m ledger <command>` (canonical) + `python main.py`(동등 보조 진입점) | 공식 권장 실행형이 `python -m <package>` |
| `id` 타입 | 문자열(`t-0001`) | 양의 정수, 1부터 시작, `max(기존 id)+1` | 공식 요구는 "유일성"만, 예시 포맷은 강제 아님 → 가장 단순한 표현 채택 |
| `Transaction.memo/tags` | 필수 | `memo=""`, `tags=[]` 기본값(선택 입력) | 공식: memo/tags optional |
| `Budget` | `category + month + limit_amount` (카테고리별) | `month + amount` (월 전체 총예산) | 공식 정정: budget은 카테고리별이 아니라 월 전체 총액 |
| `categories.json`/`budgets.json` | JSON(배열/객체) | `categories.jsonl`/`budgets.jsonl` (JSONL 통일) | 공식: "JSONL 또는 CSV 중 1개를 선택" — 3개 저장소 포맷 혼용 금지 |
| `edit` 명령 | 옵션 기반 `edit <id> [--amount ...]` | `update --id <id> [필드 옵션...]` (이름만 변경, 옵션 기반 유지) | 공식 커맨드명이 `update` |
| `add` 입력 방식 | 옵션 기반 (`add --type ... --amount ...`) | **대화형 프롬프트 기본** (date→type→category→amount→memo→tags 순 질의) | 공식: "add는 주로 대화형 입력을 사용해야 한다" |
| `search` 필터 | keyword/category/type/date range (5개, 이름 상이) | `--from --to --category --type --q --tag` 정확히 6개로 고정 | 공식 필터 목록과 일치시킴, min/max amount 없음 확인 |
| CSV 스키마 | `id,type,date,amount,category,memo,tags` | `date,type,category,amount,memo,tags` (**id 없음**) | 공식 최소 CSV 스키마에는 id가 없음 — id는 import 시 내부 발급 |
| CSV import 정책 | all-or-nothing | 행 단위 검증, 유효 행만 반영 + 스킵/실패 건수 리포트 | 공식: "invalid rows should be counted as skipped or failed" |
| CSV export 정책 | 무조건 전체 export | 기간 조건(`--month` 또는 `--from/--to`) 필수, 조건 없는 export 금지 | 공식: export는 최소 1개의 필터 조건을 받아야 함 |
| `summary` 기본 기간 | 인자 없으면 전체 | `--month` **필수**, 전체 기간 기본값 없음 | 공식 정정: summary는 월 단위가 기본 |
| exit code 체계 | 0/1/2/3/4/5 (세분화) | 0=성공 / 1=애플리케이션 에러 / 2=argparse 사용법 에러 (단순화) | 공식: "간단하게 유지, 큰 taxonomy 불필요" |
| `--data-dir` | 없음(리포지토리가 경로 하드코딩) | 전역 옵션, 기본값 `./data`, 리포지토리는 `data_dir`을 받아 파일명을 내부에서 결정 | 공식 요구 신규 반영 |
| 카테고리 초기값 | 명시 안 함 | 기본 카테고리 자동 생성 금지(Option B), 없으면 add 시 에러+힌트 | 공식 두 정책 중 하나를 명시적으로 선택 |
| 제너레이터 메서드명 | `iter_transactions()` | `iter_all()` | 공식 문서 표기와 일치 |

## 1. 디렉토리 구조 (최종)

```
m03-pocket-money-ledger/
├── main.py                  # 보조 진입점(ledger.cli.main 위임)
├── ledger/
│   ├── __init__.py
│   ├── __main__.py          # `python -m ledger` 진입점 (canonical)
│   ├── models.py            # Transaction, Budget, SearchCriteria
│   ├── repository.py        # TransactionRepository, CategoryRepository, BudgetRepository
│   ├── services.py          # LedgerService
│   ├── cli.py                # argparse 진입점 + 대화형 add 프롬프트
│   ├── validators.py        # 입력 검증 함수
│   ├── decorators.py        # 에러 처리 데코레이터
│   └── errors.py             # LedgerError 계층
├── data/                     # 기본 데이터 디렉토리 (--data-dir로 변경 가능)
│   ├── transactions.jsonl
│   ├── categories.jsonl
│   └── budgets.jsonl
├── tests/
├── exports/                  # CSV export 기본 출력 위치 (git 미추적)
├── docs/
│   └── m03-architecture-design.md
├── README.md
└── .gitignore
```

## 2. 실행 방식과 패키지 명명 결정

공식 권장 실행형은 `python -m budget_app <command> [options]`다. 이
프로젝트는 Sprint 0에서 이미 패키지명을 `ledger`로 확정했으므로,
`budget_app`으로 리네이밍하지 않고 **`ledger` 패키지명을 유지**한다 —
패키지 이름 자체는 미션의 실질 요구(표준 라이브러리만 사용하는 `-m`
실행 가능한 서브커맨드 CLI)와 무관한 표면적 차이이기 때문이다.

대신 공식 실행형의 실질 요구(`python -m <package>`)는 그대로 충족한다:
`ledger/__main__.py`를 추가해 `python -m ledger <command>`가 canonical
실행 방식이 되도록 한다. Sprint 0의 `main.py`는 동일 동작을 하는 보조
진입점으로 남겨 두 방식 모두 지원한다(`main.py`는 `ledger.cli.main()`을
호출할 뿐 별도 로직이 없으므로 유지 비용이 없다).

```
python -m ledger --help          # canonical
python main.py --help            # 동등 보조 진입점
```

## 3. 모듈 책임

| 모듈 | 책임 | 하지 않는 일 |
|---|---|---|
| `main.py` / `ledger/__main__.py` | 프로세스 진입점, `ledger.cli.main()` 호출 후 `sys.exit()` | 로직 없음 |
| `ledger/models.py` | 계층 간 공유되는 데이터 구조 정의 (dataclass) | 검증, 파일 I/O 없음 |
| `ledger/validators.py` | 원시 문자열 → 정제된 값 검증/변환 (date, month, amount, type) | 저장/조회 없음 |
| `ledger/repository.py` | 파일 단위 읽기/쓰기, 원자적 갱신, `data_dir` 기반 경로 결정 | 비즈니스 규칙(예산 초과 판단, 카테고리 사용중 검사 등) 없음 |
| `ledger/services.py` | 유스케이스 조합 (add/list/search/summary/budget/category/update/delete/import/export) | argparse, 파일 포맷 세부사항 없음 |
| `ledger/cli.py` | argv 파싱, `add`의 대화형 프롬프트, `LedgerService` 호출, 출력 포맷팅 | 파일 직접 접근 없음 |
| `ledger/decorators.py` | 커맨드 핸들러 공통 에러→종료코드 변환 | 비즈니스 로직 없음 |
| `ledger/errors.py` | 예외 계층 정의 | 로직 없음 |

## 4. 주요 클래스와 필드 (최종)

```python
@dataclass
class Transaction:
    id: int                 # 1부터 시작하는 양의 정수, 유일
    type: str                # "income" | "expense"
    date: str                # "YYYY-MM-DD"
    amount: int               # 양의 정수
    category: str
    memo: str = ""            # 선택
    tags: list[str] = field(default_factory=list)  # 선택

@dataclass
class Budget:
    month: str                # "YYYY-MM", 유일 키
    amount: int                # 그 달의 총예산(양의 정수) — 카테고리별 아님

@dataclass
class SearchCriteria:
    from_date: str | None = None
    to_date: str | None = None
    transaction_type: str | None = None
    category: str | None = None
    query: str | None = None    # --q
    tag: str | None = None
```

- **`TransactionRepository`**: `transactions.jsonl` 소유. `iter_all()`
  제너레이터, `get_by_id(id)`, `next_id()`, `add(transaction)`(단순 append,
  중복 id 거부), `update(transaction)`/`delete(id)`(안전한 전체 재작성).
  (Sprint 1에서 `append`/`replace_all`이라는 임시 이름 대신 이 최종
  이름으로 구현했다 — 섹션 0.2 참고. `append_many`는 CSV import를
  아직 구현하지 않아 도입하지 않았고, 필요해지는 시점에 추가한다.)
- **`CategoryRepository`**: `categories.jsonl` 소유. `list_all()`,
  `exists(name)`, `add(name)`(중복 거부), `remove(name)`.
- **`BudgetRepository`**: `budgets.jsonl` 소유. `list_all()`, `get(month)`,
  `set(budget: Budget)`(같은 `month`가 이미 있으면 교체, 없으면 추가),
  `remove(month)`. 파일에는 여러 줄이 있을 수 있지만 같은 `month`는
  항상 유일하도록 `set()`이 보장한다.
- **`LedgerService`**: 유일한 비즈니스 로직 지점. 세 리포지토리를 조합해
  add/list/search/update/delete/summary/budget/category/import/export를
  구현한다.

## 5. 의존성 방향

```
main.py / __main__.py → ledger.cli → ledger.services → ledger.repository → 파일(data/*)
                                            ↑                  ↑
                                       ledger.models     ledger.models
                                       ledger.errors     ledger.errors
                                            ↑
                                       ledger.validators  (repository는 validators를 쓰지 않음)
```

변경 없음 (Sprint 0과 동일). `repository.py`는 여전히 `services.py`/`cli.py`를
역참조하지 않는다.

## 6. 데이터 스키마 (최종)

### `data/transactions.jsonl`

```json
{"id": 1, "type": "expense", "date": "2026-09-16", "amount": 4500, "category": "식비", "memo": "점심", "tags": ["카페"]}
```

`id`는 이제 정수다. 화면 표시용 포맷(`TX-000012`)은 **저장 형식이
아니라 `cli.py`의 출력 단계에서만** 적용되는 표현 방식이다 — 저장소와
서비스 계층은 항상 정수 id로 동작한다.

### `data/categories.jsonl` (한 줄 = JSON 객체 1개)

```json
{"name": "식비"}
{"name": "교통"}
```

배열이 아니라 JSONL로 통일했다(섹션 0.1 근거). 순서는 등록 순서를
유지한다.

### `data/budgets.jsonl`

```json
{"month": "2026-09", "amount": 500000}
```

한 줄 = 한 달의 총예산. `(month)`이 유일 키.

### CSV 스키마 (import/export 공통, id 없음)

```
date,type,category,amount,memo,tags
2026-09-16,expense,식비,4500,점심,"카페,야식"
```

- UTF-8, 헤더 필수, `csv.DictReader`/`DictWriter`만 사용(쉼표 포함 tags는
  자동 quoting으로 처리됨 — 수동 이스케이프 불필요).
- `date/type/category/amount` 필수, `memo/tags` 선택.
- `tags`는 쉼표로 구분된 문자열(예: `"카페,야식"`).
- id는 CSV에 없음 — import 시 `TransactionRepository.next_id()`로 새로
  발급한다(섹션 19).

## 7. CLI 옵션 표기 정책

공식 원문에 "옵션 표기는 `-`로 통일"이라는 문구와, 실제 모든 커맨드
예시(`--limit`, `--from`, `--category` 등)가 이중 하이픈을 쓰는 것이
동시에 존재한다. 이 프로젝트는 **이중 하이픈 롱옵션(`--long-option`)을
표준으로 채택**한다 — 상세 기능 요구사항과 모든 커맨드 예시가 일관되게
`--`를 쓰고, `argparse`의 관용적 스타일과도 일치하기 때문이다. 문제의
문구는 "대시 프리픽스 옵션으로 통일"이라는 일반적 의미로 해석하고,
축약형(`-h`, `-l` 등) 단일 옵션은 이 프로젝트에서 의도적으로 도입하지
않는다(불필요한 표면적 확장).

`--data-dir`은 서브커맨드 이전, 최상위 파서에 위치하는 전역 옵션이다:

```
python -m ledger --data-dir ./mydata list --limit 5
```

## 8. CLI 커맨드 트리 (최종)

```
python -m ledger --help
python -m ledger [--data-dir PATH] add
python -m ledger [--data-dir PATH] list [--limit N]
python -m ledger [--data-dir PATH] search [--from DATE] [--to DATE] [--category C] [--type income|expense] [--q TEXT] [--tag T]
python -m ledger [--data-dir PATH] summary --month YYYY-MM [--top N]
python -m ledger [--data-dir PATH] budget set --month YYYY-MM --amount N
python -m ledger [--data-dir PATH] category add       # prompts for the name
python -m ledger [--data-dir PATH] category list
python -m ledger [--data-dir PATH] category remove     # prompts for the name
python -m ledger [--data-dir PATH] update --id ID [--date ...] [--type ...] [--category ...] [--amount ...] [--memo ...] [--tags ...]
python -m ledger [--data-dir PATH] delete --id ID
python -m ledger [--data-dir PATH] import --from <csv-path>
python -m ledger [--data-dir PATH] export --out <csv-path> (--month YYYY-MM | --from DATE --to DATE)
```

(`category add`/`category remove` and `import` were originally planned as positional-argument commands here; Sprint 3 made `category add`/`remove` interactive for consistency with `add`, and Sprint 4 made `import` use `--from` — this block reflects the actual final CLI, see sections 44 and 46-52.)

`budget status`나 `budget show` 같은 별도 조회 서브커맨드는 두지
않는다 — 예산 사용 현황은 `summary --month`의 출력에 포함되므로
(섹션 15) 중복 커맨드를 만들지 않는다.

## 9. `add` 커맨드 상세 (대화형)

```
python -m ledger add
```

옵션 없이 실행하면 다음 순서로 순차 프롬프트한다: **date → type →
category → amount → memo → tags**. `--help` 외의 옵션은 두지 않는다
— "옵션 주도 설계를 하지 말라"는 공식 지침을 문자 그대로 반영해,
프롬프트를 우회하는 사전 채움 옵션은 이번 설계에 포함하지 않는다
(필요해지면 별도 논의 후 추가).

검증/재프롬프트 정책(필드별로 다르게 결정):

| 필드 | 필수 여부 | 유효성 실패 시 |
|---|---|---|
| date | 필수 | `validators.validate_date` 실패 시 최대 3회 재프롬프트, 이후 `[오류]+[힌트]` 후 종료(exit 1) |
| type | 필수 | income/expense 중 하나가 아니면 재프롬프트 (최대 3회) |
| category | 필수 | `categories.jsonl`에 없으면 재프롬프트 + 힌트(`category add`로 먼저 등록), 다른 필드와 동일하게 최대 3회. 카테고리가 하나도 없는 경우도 별도 분기 없이 같은 재프롬프트 경로를 타며(3회 모두 실패 후 에러 종료), 결과적으로 요구사항(트레이스백 없음, 원인+힌트, non-zero exit)은 동일하게 만족한다(섹션 25 감사에서 실제 CLI로 확인 — Sprint 0B 초안의 "즉시 종료" 문구는 폐기) |
| amount | 필수 | 양의 정수가 아니면 재프롬프트 (최대 3회) |
| memo | 선택 | 빈 입력 허용, 검증 없음 |
| tags | 선택 | 빈 입력 허용, 쉼표 구분 파싱만 수행 |

재프롬프트 횟수를 3회로 제한하는 이유는 무한 루프를 방지하고, 반복
실패 시 "clear error + hint"로 빠져나가는 공식 지침의 두 옵션을 모두
반영하기 위함이다(재프롬프트 우선, 임계 초과 시 에러+힌트).

## 10. ID 정책 (최종)

- 저장 형식: **양의 정수**. 최초 id는 `1`.
- 다음 id: `TransactionRepository.next_id()` = 현재 파일의
  `max(기존 id) + 1` (파일이 비어 있으면 `1`).
- 삭제된 id는 재사용하지 않는다(재계산 시 삭제된 레코드는 이미
  파일에 없으므로 자연히 재사용되지 않음 — 별도 "사용된 id" 추적
  구조가 필요 없다).
- **표시 포맷과 저장 포맷은 분리한다.** `cli.py`가 출력 시에만 선택적으로
  `TX-{id:06d}` 같은 포맷을 적용할 수 있으며, 저장/서비스/리포지토리
  계층은 항상 순수 정수를 사용한다. UUID는 도입하지 않는다(공식
  요구가 "유일성"만 요구하며, 정수 카운터로 충분히 단순하게 만족됨).

## 11. 초기 데이터 정책 — 카테고리 (최종: Option B)

카테고리는 **기본값을 자동 생성하지 않는다.** 앱을 처음 실행해
`categories.jsonl`이 없거나 비어 있어도 "식비/교통/..." 같은 임의
카테고리를 심지 않는다.

카테고리가 하나도 없는 상태에서 `add`(대화형)가 카테고리를 물어보면,
어떤 이름을 입력해도 `service.categories.exists()`가 거짓이므로
자연히 아래와 같은(다른 미등록 카테고리 입력과 동일한) 메시지가
나온다(실제 CLI 실행 결과, `ledger/decorators.py::_ERROR_MESSAGES`
그대로):

```
[오류] 등록되지 않은 카테고리입니다.
[힌트] category list로 확인하거나 category add로 먼저 등록하세요.
```

`transactions.jsonl`/`budgets.jsonl`은 파일이 없으면 최초 쓰기 시점에
빈 파일로 자동 생성한다(카테고리처럼 "내용"을 임의로 채우는 것과는
다른 문제 — 빈 파일 생성 자체는 정책 판단이 필요 없다).

## 12. `list` 커맨드 — 스트리밍/메모리 전략

```
python -m ledger list --limit N        # 기본 --limit 10
```

요구사항: 최신순, 제너레이터 기반, 전체 파일을 메모리에 올리지 않음.
"최신순 출력"과 "append-only 파일 스트리밍"은 그 자체로는 상충한다
(파일은 오래된 것이 앞에 쌓이므로). 이를 `list(iter_all())`로 풀면
전체 레코드를 메모리에 올리게 되어 요구사항을 어긴다.

**채택한 설계**: `iter_all()`로 파일을 한 줄씩 스트리밍하면서
`collections.deque(maxlen=N)`에 밀어넣는다. deque가 가득 찬 뒤
새 레코드가 들어오면 가장 오래된 요소가 자동으로 버려지므로, 순회가
끝난 시점에 deque에는 항상 "파일 내에서 가장 최근 N개"만 남는다.
그 다음 deque를 한 번 `reversed()`로 뒤집어 출력한다.

- **시간 복잡도**: O(전체 레코드 수) — 파일 전체를 한 번은 읽어야
  최신 N개를 알 수 있다(append-only 파일에 역방향 읽기 인덱스가
  없으므로).
- **메모리 복잡도**: O(N) — 전체 레코드가 아니라 보관할 N개만큼만
  버퍼링한다. 이것이 "전체를 메모리에 올리지 않는다"는 요구의
  실질적 의미다.

## 13. `search` 커맨드 — 스트리밍/버퍼링 전략 (정직한 트레이드오프 명시)

```
python -m ledger search [--from DATE] [--to DATE] [--category C] [--type T] [--q TEXT] [--tag T]
```

필터는 정확히 `--from --to --category --type --q --tag` 6개이며
금액 범위(min/max amount)는 Mission Core에 없으므로 포함하지 않는다.
`SearchCriteria`는 이 6개 필드로 축소했다(섹션 4).

**`list`와 달리 `search`에는 `--limit`이 없다** — 조건에 맞는 모든
레코드를 찾아야 하므로 "가장 최근 N개만 유지"하는 `deque(maxlen=N)`
기법을 그대로 쓸 수 없다(결과 집합의 크기를 미리 알 수 없음).

**채택한 설계**: `iter_all()`을 한 번 순회하면서 조건에 맞는 레코드만
그때그때 필터링한다(파일 전체를 리스트로 만들지 않는다는 점에서는
여전히 스트리밍). 다만 "매칭된" 레코드는 최신순으로 뒤집어 출력해야
하므로 **매칭된 레코드만큼은 리스트에 버퍼링한 뒤 마지막에 한 번
`reversed()`한다.**

이 설계의 메모리 특성을 과장하지 않고 명시한다: 원본 파일 전체를
메모리에 올리지는 않지만(비매칭 레코드는 즉시 버려짐), 매칭
결과 집합의 크기에는 비례한다 — 즉 "완전한 상수 메모리 스트리밍"이
아니라 "매칭 건수에 비례하는 버퍼링"이다. `list`(O(N) 고정)와
`search`(O(매칭 수))의 메모리 특성 차이는 문서로 명확히 구분해 둔다.

## 14. `summary` 커맨드 (최종: 월 단위, `--month` 필수)

```
python -m ledger summary --month YYYY-MM [--top N]     # 기본 --top 3
```

Sprint 0의 "인자 없으면 전체 기간" 설계는 공식 정정에 따라 폐기한다.
`--month`는 필수 인자이며, 없으면 `argparse`가 exit code 2로 사용법
에러를 낸다. 해당 월에 데이터가 없으면 예외를 던지지 않고 "데이터
없음"을 나타내는 결과를 정상 출력한다(예: `데이터 없음` 메시지 +
모든 합계 0).

출력 항목:

- 총 수입(income 합)
- 총 지출(expense 합)
- 잔액(수입 − 지출)
- 카테고리별 지출 합계
- 지출 기준 TOP N 카테고리 (기본 N=3)
- (같은 달에 예산이 설정돼 있으면) 예산 사용 현황 — 섹션 15

## 15. 예산(`budget`) 모델과 커맨드 (최종: 월 전체 총액, 카테고리별 아님)

Sprint 0에서는 `Budget`을 카테고리별 한도로 설계했으나, 공식 요구는
**월 전체 총예산** 하나다. 최종 모델은 섹션 4의 `Budget(month, amount)`.

```
python -m ledger budget set --month YYYY-MM --amount N
```

`summary --month`가 같은 달의 예산 정보를 포함해 보여준다:

- 예산 금액
- 지출 금액 (섹션 14의 총 지출과 동일 값)
- 사용률(%) = 지출 / 예산 × 100
- 초과 여부(불리언)
- 초과 시 경고 메시지 (예: `[경고] 이번 달 예산을 12,000원 초과했습니다.`)

**예산 초과는 거래 추가를 막지 않는다** — `add`/`update` 시점에는
예산을 검사하지 않고, 오직 `summary` 조회 시의 리포팅/경고
동작이다. 이 결정은 `LedgerService.add_transaction`/`update_transaction`
docstring에도 명시해 둔다.

## 16. `category` 커맨드와 사용중 규칙

```
python -m ledger category add       # 카테고리명: 프롬프트
python -m ledger category list
python -m ledger category remove     # 삭제할 카테고리명: 프롬프트
```

(`add`/`remove`가 위치 인자 `<name>`을 받는 것으로 원래 설계했으나,
Sprint 3에서 `add`의 대화형 스타일과 일관성을 맞추기 위해 대화형
프롬프트로 변경했다 — 섹션 44/54 참고.)

**삭제 정책**: 어떤 거래라도 해당 카테고리를 참조 중이면 삭제를
차단한다. 캐스케이드 삭제나 자동 치환은 하지 않는다.

```
[오류] 사용 중인 카테고리는 삭제할 수 없습니다.
[힌트] 해당 거래의 카테고리를 먼저 수정하세요.
```

**적용 계층**: `LedgerService.remove_category()`가 `TransactionRepository.iter_all()`을
스트리밍하며 해당 카테고리를 참조하는 레코드가 있는지 확인한 **뒤에만**
`CategoryRepository`의 삭제를 호출한다. 이 검사는 서비스 계층의
책임이다 — `repository.py`는 이 규칙을 모르며, `CategoryRepository`가
`TransactionRepository`를 참조하는 상위 계층 역의존은 만들지 않는다
(섹션 5 의존성 방향 유지).

## 17. `update` 커맨드 (최종: Option A, 옵션 기반)

```
python -m ledger update --id ID [--date ...] [--type ...] [--category ...] [--amount ...] [--memo ...] [--tags ...]
```

대화형(Option B) 대신 **옵션 기반(Option A)**을 채택한다. 이유:
CLI 계약이 명확해 동료 평가와 자동화된 테스트가 쉽고, 지정한 필드만
변경하면 되므로 `add`처럼 매번 전체 필드를 다시 물어볼 필요가 없다
(부분 수정이 자연스러운 유스케이스).

- `--id`는 항상 필수.
- `--id` 외 필드 옵션 중 **최소 1개**가 있어야 한다 — `argparse`
  선언만으로는 "여러 선택 옵션 중 최소 1개"를 표현할 수 없으므로,
  이 검증은 `cli.py`의 커맨드 핸들러(파싱 이후)에서 수행하고, 위반 시
  `ValidationError`(exit 1)로 처리한다.
- 지정하지 않은 필드는 기존 값을 유지한다(부분 갱신).
- 대상 `id`가 없으면 `NotFoundError`(exit 1) + 힌트.

## 18. `delete` 커맨드

```
python -m ledger delete --id ID
```

- `--id` 누락: `argparse` 자체가 사용법 에러로 처리(exit 2, "missing
  required argument" 메시지 — 스택트레이스 아님, argparse 기본 동작).
- `--id`는 있으나 존재하지 않는 id: `NotFoundError` → `handle_errors`가
  `[오류]`+`[힌트]` 출력 후 exit 1. 원시 스택트레이스는 노출하지 않는다.

## 19. CSV import (최종: id 없는 스키마, 행 단위 스킵 정책)

스키마는 섹션 6 참고(`date,type,category,amount,memo,tags`, id 없음).

**정책 변경(Sprint 0 대비)**: all-or-nothing을 폐기하고, **행 단위
검증 + 유효 행만 반영**으로 바꾼다 — 공식 요구가 "invalid rows should
be counted as skipped or failed"라고 명시해 부분 반영을 전제하기
때문이다.

처리 절차:

1. `csv.DictReader`로 전체 행을 순회하며 각 행을 `validators`로 검증한다.
2. 유효한 행만 새 `Transaction`으로 변환한다 — id는 CSV 값을 쓰지
   않고 `TransactionRepository.next_id()`를 행마다 순차 증가시켜
   새로 발급한다(즉 CSV는 id를 전혀 통제하지 않는다).
3. 유효 행을 `TransactionRepository.add()`로 반영한다. Sprint 1에는
   CSV import가 범위 밖이라 배치 전용 메서드(`append_many` 등)를
   아직 만들지 않았다 — "부분 반영을 허용"하는 것은 잘못된 행을
   건너뛴다는 의미이지, 파일 쓰기 자체를 여러 번 나눠 실행해 중간
   상태를 노출해도 된다는 의미는 아니므로, CSV import를 실제 구현할
   Sprint에서 유효 행 전체를 한 번에 반영하는 배치 메서드를
   `TransactionRepository`에 추가할지(있으면 원자성이 더 강해짐)
   판단한다.
4. 처리 결과를 리포트한다: `{"imported": N, "skipped": M, "errors": [...]}`
   형태로 몇 번째 행이 왜 실패했는지 포함한다.

## 20. CSV export (최종: 기간 조건 필수)

```
python -m ledger export --out <csv-path> --month YYYY-MM
python -m ledger export --out <csv-path> --from DATE --to DATE
```

`--out` 없는 export는 없다(파일 경로 필수). 그리고 기간 조건이
**정확히 하나의 형태**로 있어야 한다:

- A: `--month`만 사용
- B: `--from`과 `--to`를 함께 사용(둘 다 있어야 함, 하나만은 불가)
- A와 B를 동시에 지정하거나, 아무 조건도 주지 않는 것은 `ValidationError`

`export --out all.csv`처럼 조건 없는 무제한 export는 금지한다(공식
요구). 매칭 레코드는 `iter_all()`을 필터링하며 바로 `csv.DictWriter`로
흘려보낸다(export 대상 자체를 리스트로 모으지 않음 — `search`와 달리
export는 순서 요구가 없으므로 완전한 스트리밍이 가능하다는 점도
명시해 둔다).

## 21. 제너레이터 사용 지점 (최종)

`TransactionRepository.iter_all() -> Iterator[Transaction]`이 유일한
제너레이터 지점이며 파일을 한 줄씩 읽어 yield한다. 소비하는 지점별
메모리 특성을 명확히 구분한다:

| 소비 지점 | 메모리 특성 |
|---|---|
| `list_transactions` | O(N) — `deque(maxlen=N)` (섹션 12) |
| `search` | O(매칭 수) — 필터링은 스트리밍, 결과는 버퍼링 후 역순 출력 (섹션 13) |
| `monthly_summary` | O(카테고리 수) — 합계만 누적하므로 사실상 상수에 가까운 소량 상태만 유지, 원본 레코드를 보관하지 않음 |
| `export_csv` | O(1) — 매칭 레코드를 즉시 `csv.DictWriter`에 쓰고 버리므로 순서 요구가 없어 완전한 스트리밍 |
| `update`/`delete`(재작성) | O(N) 한시적 — `TransactionRepository.update()`/`delete()`가 내부적으로 기존 레코드를 모두 순회해 임시 파일에 다시 쓰는 동안 |

전체 파일을 먼저 리스트로 만든 뒤 그 리스트에서 `yield`하는 방식은
어디에도 쓰지 않는다.

## 22. 데코레이터 사용 지점

`ledger/decorators.py::handle_errors`가 유일한 데코레이터이며
`cli.py`의 각 커맨드 핸들러(`cmd_add`, `cmd_list`, `cmd_search`,
`cmd_update`, `cmd_delete`, `cmd_summary`, `cmd_budget_set`,
`cmd_category_*`, `cmd_import`, `cmd_export`)에 적용한다.

- **제거하는 관심사**: 각 핸들러마다 반복될 "`LedgerError` 하위 예외를
  잡아 `[오류]`/`[힌트]` 형식으로 출력하고 종료 코드로 변환"하는
  로직을 한 곳으로 모은다.
- **왜 데코레이터가 적절한가**: 모든 핸들러에 동일한 형태로, 함수
  본문을 건드리지 않고 적용 가능한 전형적인 횡단 관심사이기 때문.
- **버그를 과도하게 숨기지 않음**: `handle_errors`는 `LedgerError`
  하위 클래스만 잡는다. 그 외 예외(프로그래밍 버그, 예: `KeyError`,
  `AttributeError`)는 잡지 않고 그대로 전파되어 스택트레이스와 함께
  비정상 종료한다 — "예상된 사용자 에러"와 "프로그램 버그"를 섞지
  않기 위한 의도적 설계다.

데코레이터를 하나만 두고 다른 관심사(로깅 등)에 추가로 적용하지
않는 이유는 Sprint 0 문서(구 섹션 8)와 동일 — 프로젝트 규모 대비
장식적 추상화를 늘리지 않기 위함이다.

## 23. 에러 / 종료 코드 정책 (최종: 단순화)

Sprint 0의 세분화된 5단계 매핑(1~5)을 폐기하고 단순화한다:

| 상황 | 종료 코드 |
|---|---|
| 성공 | 0 |
| `LedgerError`의 모든 하위 클래스(`ValidationError`, `NotFoundError`,
  `PersistenceError`, `CSVFormatError`, 및 Sprint 1에서 추가된
  `DataFormatError`/`DuplicateTransactionIdError`/`TransactionNotFoundError`/
  `DuplicateCategoryError`/`CategoryNotFoundError`/`BudgetNotFoundError`
  등 세부 하위 클래스) — 애플리케이션/도메인 에러 | 1 |
| `argparse` 자체 파싱 실패(필수 옵션 누락, 알 수 없는 옵션 등) | 2 |

`errors.py`의 예외 하위 클래스들은 그대로 유지한다 — 다만 이제
**종료 코드를 구분하기 위한 것이 아니라, 사용자에게 보여줄
메시지/힌트 문구를 구분하기 위한 목적**으로만 쓰인다. 모든
`LedgerError`는 `handle_errors`를 통해 동일하게 exit code 1로
수렴한다. 이 결정은 "큰 exit-code taxonomy를 만들지 말라"는 공식
지침을 반영한 것이다.

원칙은 유지: 예상된 사용자 에러는 원시 스택트레이스 없이
`[오류] 원인` + `[힌트] 조치`만 출력하고, 프로그래밍 버그는 그대로
전파해 숨기지 않는다.

## 24. 안전한 파일 재작성 전략

Sprint 0과 동일하게 유지한다(공식 문서도 이 설계를 Core 단계의
안정성 고려사항으로, bonus에서는 더 강한 원자적 영속성으로 언급함):

1. `iter_all()`로 기존 레코드를 순회하며 변경분을 반영해 같은
   디렉토리의 임시 파일에 기록한다.
2. 쓰기가 모두 성공한 뒤에만
3. `os.replace(tmp_path, original_path)`로 원자적 교체한다.

`update`/`delete`(transactions), `category remove`, `budget set/remove`
모두 이 절차를 공유하며, Sprint 1에서 `ledger/repository.py`의
`_atomic_write_jsonl()` 헬퍼 하나로 실제 구현했다(섹션 30.2). CSV
`import`는 아직 범위 밖이라 이 절차를 아직 쓰지 않는다 — 구현될
때 같은 헬퍼를 재사용할지, 별도 배치 메서드가 필요할지는 그때
결정한다.

## 25. README 예약 섹션

`README.md`는 이번 스프린트에서 완성하지 않되, 다음 섹션 제목을
미리 예약해 둔다(Sprint 1에서 내용 채움):

- 설치/실행 요구사항 (Python 버전, 표준 라이브러리만 사용)
- 실행 방법 (`python -m ledger ...`)
- 데이터 파일 위치와 기본 경로
- 저장 포맷 (JSONL 통일)
- 주요 명령 예시
- `--data-dir` 사용 예시
- CSV import/export 스키마
- update 방식 결정 (옵션 기반)
- 카테고리 초기화 정책 (기본 카테고리 없음)

## 26. 아키텍처 책임 매핑 (재확인)

```
CLI → Service → Repository → File
```

- **CLI**: argparse, `add`의 대화형 입력, 출력 포맷팅, 종료 처리.
- **Service**: 비즈니스 규칙, 여러 리포지토리에 걸친 검증(카테고리
  사용중 여부 등), 검색 조건 적용, summary/budget 계산, import/export
  오케스트레이션.
- **Repository**: 파일 영속화, 제너레이터 읽기, 원자적 재작성,
  기본적인 저장소 수준 에러.
- **Models**: `Transaction`, `Budget`, `SearchCriteria`.
- **Validators**: date, month, amount, type 등 재사용 가능한 입력
  검증 헬퍼.
- **Decorators**: 실제로 사용되는 횡단 관심사 1개 이상(`handle_errors`).
- **Errors**: 의미 있는 소규모 예외 계층.

## 27. 요구사항 추적 매트릭스 (Sprint 5 감사로 재확인됨)

"상태"는 코드가 존재한다는 이유만으로 PASS를 주지 않는다 — 실제로
통과하는 테스트나 수동 검증이 있을 때만 PASS로 표시한다(Sprint 4
지시 문서 섹션 35 원칙). Sprint 5에서 아래 표의 명령 관련 행 전부를
`python -m ledger`(실제 서브프로세스, Service를 직접 부르지 않음)로
다시 한 번 수동 실행해 재확인했다 — 자동화 테스트가 놓칠 수 있는
"진짜 CLI 프로세스에서의 동작"까지 확인한 결과이며, 상세 근거는
[docs/m03-final-qa-report.md](m03-final-qa-report.md)에 있다.

| 공식 요구사항 | 채택한 프로젝트 정책 | 대상 모듈/클래스 | 검증 방법 | 상태 |
|---|---|---|---|---|
| `add` 대화형 입력 | date→type→category→amount→memo→tags 순 프롬프트, 3회 재시도 | `ledger/cli.py::cmd_add` | `tests/test_cli_add.py` 9개 + 섹션 32 수동 스모크 | **PASS** |
| `list --limit` | `deque(maxlen=N)` 스트리밍, 기본 `--limit 10` | `LedgerService.list_transactions` | `tests/test_service_transactions.py::ListTransactionsTests`, `tests/test_cli_list.py` | **PASS** |
| 최신순 출력 | list: deque+reverse, search: 매칭 결과 buffer+reverse (파일/삽입 순서 기준) | 섹션 12, 13, 39 | `test_newest_first*` 단위테스트(Service+CLI 양쪽) | **PASS** |
| 제너레이터 스트리밍 | `iter_all()` 단일 지점, 소비자별 메모리 특성 문서화 | `TransactionRepository.iter_all` | `test_iter_all_is_generator_based`(타입 확인) + `test_source_file_not_modified` 등 간접 확인 | **PASS** |
| `search` 필터 6종 | `--from --to --category --type --q --tag`, min/max amount 제외 | `SearchCriteria`, `LedgerService.search` | `tests/test_service_transactions.py::SearchTransactionsTests` 9개 + `tests/test_cli_search.py` 8개 | **PASS** |
| 월간 `summary` | `--month` 필수, `--top` 기본 3 | `LedgerService.monthly_summary` | `tests/test_service_summary.py` 10개 + `tests/test_cli_summary.py` 6개 | **PASS** |
| 월 총예산 `budget` | `Budget(month, amount)`, `budget set` | `Budget`, `BudgetRepository`, `LedgerService.set_budget` | `tests/test_service_budget.py`, `tests/test_cli_budget.py` | **PASS** |
| 예산 사용률/초과 경고 | summary 출력에 포함, 거래 추가는 막지 않음 | `LedgerService.monthly_summary` | `test_budget_usage_under`/`test_budget_exceeded`(Service+CLI) | **PASS** |
| `category add/list/remove` | 3개 서브커맨드(add/remove는 대화형) | `CategoryRepository`, `LedgerService` | `tests/test_service_categories.py`, `tests/test_cli_category.py` | **PASS** |
| 카테고리 사용중 삭제 차단 | 서비스 계층에서 사전 검사, 차단(캐스케이드 없음) | `LedgerService.remove_category` | `test_remove_used_category_blocked`(Service+CLI 양쪽) | **PASS** |
| `update` 방식 | 옵션 기반(Option A), `--id` 필수 + 필드 옵션 1개 이상, UNSET sentinel | `LedgerService.update_transaction`, `cli.py::cmd_update` | `tests/test_service_transactions.py::UpdateTransactionTests` 10개 + `tests/test_cli_update.py` 7개 | **PASS** |
| `delete --id` | 없는 id → `TransactionNotFoundError`, `--id` 누락 → argparse exit 2 | `LedgerService.delete_transaction` | `tests/test_service_transactions.py::DeleteTransactionTests`, `tests/test_cli_delete.py` | **PASS** |
| CSV import | id 없는 스키마, 파일 수준 에러는 전체 실패, 행 수준 에러는 스킵+카운트 | `LedgerService.import_csv` | `tests/test_service_import.py` 19개 + `tests/test_cli_import.py` 5개 | **PASS** |
| CSV export | `--out` + (`--month` 또는 `--from/--to`) 필수, 무조건 export 금지 | `LedgerService.export_csv` | `tests/test_service_export.py` 13개 + `tests/test_cli_export.py` 4개 | **PASS** |
| export 필터 필수 | 섹션 50 조합 규칙(Service가 검증, CLI는 그대로 전달) | `LedgerService.export_csv` | `test_missing_period_rejected`/`test_from_only_rejected`/`test_to_only_rejected`/`test_reversed_range_rejected`/`test_month_and_range_combination_rejected` | **PASS** |
| import/export 스키마 고정 | `CSV_FIELDNAMES` 상수 하나가 유일한 정의(섹션 46) | `ledger/services.py` | `test_header_exists_and_id_column_absent`, round-trip 테스트 | **PASS** |
| export의 제너레이터 재사용 | `list(iter_all())` 없이 `for ... in iter_all()`로 직접 스트리밍(섹션 51) | `LedgerService.export_csv` | 코드 리뷰(정적 확인 — 런타임 메모리 프로파일링은 하지 않음) | **PASS(코드 확인)**, 메모리 프로파일링은 미실시 |
| export→import round trip | id를 제외한 모든 비즈니스 필드가 왕복 보존됨 | `tests/test_round_trip.py` | 서로 다른 `data_dir` 두 개로 export→import 후 필드 비교 | **PASS** |
| CSV UTF-8/헤더 처리 | UTF-8 강제, 헤더 필수, 헤더 누락 시 exit 1 | `LedgerService.import_csv`/`export_csv` | `test_utf8_korean_memo`, `test_header_missing_raises`, `test_required_header_missing_raises` | **PASS** |
| 영속 파일 3개 이상 | `transactions.jsonl`, `categories.jsonl`, `budgets.jsonl` | `ledger/repository.py` | `tests/test_persistence_acceptance.py` + 파일 존재 확인 | **PASS** |
| `--data-dir` | 전역 옵션, 기본 `./data`, 리포지토리가 `data_dir` 수신 | `cli.py` 최상위 파서, 각 Repository `__init__` | `tests/test_cli_root.py::test_custom_data_dir_is_used_and_not_created_by_reads` | **PASS** |
| 클래스 2개 이상 | `Transaction, Budget, SearchCriteria, MonthlySummary, ImportResult, TransactionRepository, CategoryRepository, BudgetRepository, LedgerService` (9개) | `ledger/models.py`, `repository.py`, `services.py` | 코드 리뷰 | **PASS** |
| 모듈 3개 이상 | 8개 모듈(`main.py`/`__main__.py` 제외) | `ledger/*.py` | 코드 리뷰 | **PASS** |
| 데코레이터 실사용 | `handle_errors`를 `cli.py::_dispatch` 한 곳에 적용, 모든 커맨드가 경유 | `ledger/decorators.py`, `cli.py` | `tests/test_cli_decorator.py`(`__wrapped__` 확인 + 실제 경로 스파이 확인) | **PASS** |
| 타입 힌트 | 모든 공개 함수/메서드/필드 | 전체 | 코드 리뷰(`mypy` 등 정적 검사기는 실행하지 않음 — 표준 라이브러리만 허용이라 프로젝트에 포함하지 않음) | **PASS(코드 확인)** |
| `--help` | `argparse` 기본 제공 + 하위 명령별 help 문자열, `import`/`export` 포함 10개 전부 | `cli.py::build_parser` | `tests/test_cli_root.py::test_subcommand_help_exits_zero`(10개 명령 전부) | **PASS** |
| 에러 시 원인+힌트, non-zero exit, 트레이스백 없음 | 섹션 23, 41 | `errors.py`, `decorators.py` | `tests/test_cli_errors.py` 10개(모두 `assertNotIn("Traceback", err)`) | **PASS** |
| 표준 라이브러리만 사용 | `argparse, json, csv, dataclasses, pathlib, tempfile, os, functools, typing, collections, re, datetime, sys, io, unittest` 외 미사용 | 전체 | 전체 소스 import 문 수동 검토(Sprint 1~4 각 스프린트에서 반복 확인) | **PASS** |
| README 요구 섹션 | 섹션 25의 9개 제목 예약 → Sprint 4에서 실제 내용 작성 | `README.md` | 섹션 존재 + 내용 확인 | **PASS**(Sprint 4에서 채움) |

## 28. 과설계/요구사항 리스크 (갱신)

- **`SearchCriteria`를 여전히 dataclass로 유지할 것인가**: 필드가
  6개로 소폭 늘었지만 여전히 단순 값 객체 수준. 유지 — CLI 옵션이
  더 늘어나도 서비스 시그니처를 안정적으로 유지하기 위함(Sprint 0
  근거와 동일).
- **id를 정수로 바꾸며 생기는 표시 포맷 이원화**: 저장은 정수, 화면은
  `TX-000012` 같은 포맷을 선택적으로 적용할 수 있다는 설계가 "저장
  계층과 표시 계층이 다르다"는 사실을 명시적으로 몰라야 하는 개발자
  실수 위험(예: CLI가 실수로 포맷된 문자열을 서비스에 다시 넘기는
  버그)을 만들 수 있다. Sprint 1에서 포맷팅 함수는 `cli.py`에만
  두고 다른 계층에서 절대 호출하지 않도록 리뷰 시 명시적으로
  확인한다.
- **CSV import를 all-or-nothing에서 행 단위 스킵으로 바꾸며 생기는
  복잡도**: "몇 번째 행이 왜 스킵됐는지" 리포트 구조가 필요해져
  Sprint 0보다 구현 범위가 늘었다. 그러나 이는 과설계가 아니라 공식
  요구를 정확히 반영하기 위한 필수 변경이다 — 리포트 구조는
  `{"imported": N, "skipped": M, "errors": [(row_no, reason), ...]}`
  정도의 단순 dict/list로 제한하고 별도 클래스를 만들지 않는다.
- **`budget status`를 별도 커맨드로 만들지 않은 것이 기능 축소로
  보일 위험**: 공식 요구가 "summary가 예산 정보를 포함해야 한다"고
  명시하므로 별도 조회 커맨드는 중복이라 판단해 의도적으로 뺐다.
  동료 평가 시 "왜 budget status가 없냐"는 질문에는 이 문서 섹션
  8/15로 답한다.
- **`update` 필드 옵션 "최소 1개" 검증이 argparse 선언만으로는
  안 됨**: `cli.py`의 핸들러 코드에서 수행해야 하므로, CLI 계층에
  "약간의" 검증 로직이 들어간다. 이것이 섹션 3의 "cli.py는 로직을
  갖지 않는다" 원칙과 긴장 관계에 있음을 인지한다 — 다만 이는
  argparse 표현력의 한계에 대응하는 파싱 후 형태 검증이지 비즈니스
  규칙은 아니므로 `cli.py`에 두는 것이 적절하다고 판단한다(비즈니스
  규칙인 "카테고리 사용중 삭제 차단"은 여전히 `services.py`에 있음,
  섹션 16).

## 29. 남은 모호성 (Sprint 0B 조정 후 실제로 남은 것만)

1. **update 시 category 변경**: 새 카테고리가 `categories.jsonl`에
   없으면 어떻게 할지(재프롬프트 개념이 없는 옵션 기반 커맨드이므로
   즉시 `ValidationError`로 처리하는 것이 자연스러워 보이나, 문서에
   명시적으로 고정할 필요가 있음).
2. **CSV import 시 형식 자체가 깨진 파일**(헤더 누락, 컬럼 수 불일치
   등 행 단위가 아니라 파일 단위 문제)을 "0건 처리 + 에러"로 볼지,
   아예 `CSVFormatError`로 즉시 중단할지.
3. ~~`--data-dir`로 지정한 경로가 존재하지 않을 때 자동 생성할지~~
   — **Sprint 1에서 해결**: `data_dir.mkdir(parents=True, exist_ok=True)`로
   쓰기 시점에 자동 생성한다(섹션 32 참고). 읽기 전용 동작은 디렉토리를
   만들지 않고 빈 데이터셋으로 취급한다.
4. **tags에 쉼표(,)가 포함된 경우** 대화형 `add`에서 사용자가
   구분자와 리터럴 쉼표를 구분할 방법(예: 이스케이프 문법 없음 —
   CSV처럼 quoting 처리를 할 수 없는 단순 프롬프트 입력이므로).

## 30. 골격 정합화 (Sprint 0B에서 실제로 변경한 코드)

기존 시그니처가 위 정정 사항과 충돌하는 부분만 최소 수정했다
(필드/시그니처/타입힌트/docstring만, 함수 본문은 여전히
`NotImplementedError`):

- `models.py`: `Transaction.id: int`로 변경, `memo`/`tags` 기본값 추가,
  `Budget`을 `month + amount`로 축소, `SearchCriteria` 필드를
  공식 6개 필터명으로 교체.
- `repository.py`: 생성자가 `path: Path` 대신 `data_dir: Path`를
  받고 클래스별 `FILENAME` 상수로 실제 경로를 내부에서 계산하도록
  변경. `iter_transactions` → `iter_all`로 개명. `next_id()`,
  `append_many()` 추가. `BudgetRepository`를 `get`/`set` 중심으로 변경.
- `services.py`: `edit_transaction` → `update_transaction` 개명,
  `list_transactions`/`search_transactions` → `list_recent`/`search`로
  개명(섹션 12·13 전략을 시그니처 docstring에 명시), `summarize` →
  `monthly_summary(month, top)`로 개명(월 필수 반영), `check_budget`
  제거하고 `set_budget`만 유지(예산 조회는 summary에 통합),
  `import_csv`/`export_csv` 시그니처에 새 정책 반영.
- `cli.py`: `--data-dir` 전역 옵션, `edit`→`update` 개명, CSV
  서브커맨드를 `import-csv`/`export-csv`→`import`/`export`로 개명,
  `export`에 `--out`/`--month`/`--from`/`--to` 추가, `add`를
  옵션 없는 대화형 서브커맨드로 변경.
- `ledger/__main__.py` 신규 추가(`python -m ledger` 지원).
- `decorators.py`/`errors.py`: docstring을 섹션 22·23의 단순화된
  정책에 맞게 갱신(클래스 구조 자체는 유지).
- `validators.py`: `validate_month` 추가.

기능 본문(실제 파일 읽기/쓰기, 검증 로직, CSV 처리 등)은 이번
스프린트에서도 구현하지 않는다.

## 31. Sprint 0B 완료 시점 판단 (역사적 기록)

**가능.** 공식 원문과의 주요 불일치(실행 방식, id 타입, Budget 모델,
저장 포맷 통일, add 입력 방식, search 필터, CSV 스키마/정책,
summary 기간, export 필터 필수, exit code 단순화, `--data-dir`,
카테고리 초기화 정책)를 모두 대조·정정했고 골격 파일도 이에 맞춰
갱신했다. 섹션 29의 4개 항목은 해당 기능(각각 update, import,
`--data-dir` 처리, add의 tags 파싱) 구현 직전에만 확인하면 되며
전체 설계를 막는 항목은 아니다. **Model + Persistence 구현
(Sprint 1)을 시작해도 안전하다.** (이후 Sprint 1에서 실제로 이
작업을 완료했다 — 섹션 32 이하 참고.)

## 32. Sprint 1 구현 현황 — Model + JSONL 영속 계층

Sprint 1은 섹션 31의 판단에 따라 실제 동작하는 데이터 모델과
리포지토리 계층을 구현했다. Service(`services.py`)와 CLI(`cli.py`)는
여전히 시그니처만 있는 골격(`raise NotImplementedError`)이다 —
이번 스프린트의 범위가 아니다.

### 32.1 실제 구현된 것

- `ledger/models.py`: `Transaction`(`date: datetime.date` — 문자열이
  아니라 실제 날짜 객체, `to_dict()`/`from_dict()`로만 ISO 문자열과
  왕복), `Budget`(`to_dict()`/`from_dict()` 추가), `SearchCriteria`
  (여전히 미사용 계획 객체, `from_date`/`to_date`도 `datetime.date`로
  통일).
- `ledger/repository.py`: 세 리포지토리 전부 실제 동작. 공유 헬퍼
  3개(`_iter_jsonl`, `_append_jsonl`, `_atomic_write_jsonl`)로
  중복을 줄였다(섹션 21의 "작은 private 헬퍼는 허용" 지침 반영).
- `ledger/errors.py`: `PersistenceError`/`DataFormatError`/
  `DuplicateTransactionIdError`/`TransactionNotFoundError`/
  `DuplicateCategoryError`/`CategoryNotFoundError`/`BudgetNotFoundError`
  추가(전부 실제로 raise됨). `ValidationError`/`CSVFormatError`는
  여전히 미사용(Service/CSV 구현 Sprint까지 보류).
- `tests/`: `unittest` 기반 41개 테스트, 전부 `tempfile.TemporaryDirectory()`
  사용(섹션 34 참고).

### 32.2 Sprint 0B 골격 대비 API 개명 (아키텍처 정합화)

Sprint 0B 골격에 있던 임시 메서드 이름 중 일부를 실제 구현 시점에
다음과 같이 확정했다 — "구체적 이유 없이 공개 메서드 이름을 바꾸지
않는다"는 원칙에 따라 아래 이유로만 변경했다:

| Sprint 0B 골격 | Sprint 1 최종 | 이유 |
|---|---|---|
| `TransactionRepository.append()` | `add()` | Sprint 1 지시 문서(section 8)가 명시적으로 요구한 이름 |
| `TransactionRepository.replace_all()` | 별도 메서드 없이 `update()`/`delete()`가 각각 내부에서 재작성 수행 | `replace_all(전체 리스트)`를 서비스가 조립해 넘기는 대신, "어떤 트랜잭션을 바꿀지/지울지"를 리포지토리가 직접 알고 처리하는 편이 "존재하지 않는 id" 에러를 리포지토리 경계에서 바로 낼 수 있어 더 단순함 |
| `TransactionRepository.append_many()` | (아직 없음) | CSV import가 이번 스프린트 범위 밖이라 실제 사용처가 없는 채로 만들면 과설계 — 필요해지는 시점에 추가 |
| (없음) | `TransactionRepository.get_by_id()` | Sprint 1 지시 문서가 명시적으로 요구, `update`/`delete`의 사전 검사에도 재사용 |
| `CategoryRepository.load()`/`save()` | `list_all()`/`exists()`/`add()`/`remove()` | "통째 로드 후 저장"이 아니라 개별 연산 단위 API로 바꿔 중복 이름 추가 검사를 리포지토리가 스스로 보장(호출부가 매번 목록을 불러와 직접 배열을 조작할 필요 없음) |
| `BudgetRepository.set(month, amount)` | `set(budget: Budget)` | Sprint 1 지시 문서(section 17) 명시 — 값 객체를 그대로 주고받아 `Budget.to_dict()`/`from_dict()`를 리포지토리 내부에서 재사용 가능 |
| `errors.StorageError` | `errors.PersistenceError` | Sprint 1 지시 문서(section 19)가 이 이름을 명시 — 의미는 동일(파일 읽기/쓰기 실패) |

Service/CLI 계층(`services.py`/`cli.py`)은 이 개명을 아직 반영해
호출하지 않는다(본문이 없으므로) — Sprint 2에서 실제로 이 리포지토리
API를 호출하는 코드를 작성할 때 그대로 사용하면 된다.

### 32.3 data directory 정책 (신규 확정)

- 쓰기 연산(모든 리포지토리의 `add`/`update`/`delete`/`remove`/`set`)은
  대상 파일의 부모 디렉터리를 `Path.mkdir(parents=True, exist_ok=True)`로
  필요 시 생성한다.
- 읽기 전용 연산(`iter_all`/`get_by_id`/`next_id`/`list_all`/`get`)은
  디렉터리나 파일이 없어도 절대 생성하지 않고 빈 데이터셋으로
  응답한다(`iter_all()` → 빈 제너레이터, `list_all()` → `[]`,
  `get(...)` → `None`).
- 프로덕션 데이터 파일은 리포지토리가 필요할 때만 만든다 — 앱 시작
  시점에 세 파일을 미리 만들어두는 초기화 코드는 두지 않는다.
- 테스트는 예외 없이 `tempfile.TemporaryDirectory()`를 쓴다(섹션 34).

## 33. 남은 모호성 갱신 (Sprint 1 이후)

섹션 29의 항목 3은 이번 스프린트에서 해결했다(취소선 표시). 나머지
1, 2, 4는 Service/CLI/CSV가 실제로 구현되는 Sprint에서 확인하면
되는 사안으로 그대로 남아 있다. Sprint 1에서 새로 드러난 항목은
없다 — 구현 중 스펙과 충돌한 지점은 모두 섹션 32.2의 개명으로
흡수했다.

## 34. Sprint 1 완료 시점 판단 (역사적 기록)

**가능.** `Transaction`/`Budget`/`SearchCriteria` 모델과 세 리포지토리가
실제로 동작하며(41개 unittest 통과, `python -m compileall .` 통과),
`data_dir` 주입·빈 상태 처리·원자적 재작성·제너레이터 스트리밍이
모두 검증됐다. Sprint 2는 `services.py`의 비즈니스 로직(add의
카테고리 존재 검사, update/delete의 부분 갱신, monthly_summary의
집계·예산 경고, category 사용중 차단 등)과 CSV import/export를
구현하면 된다 — 그 다음에야 `cli.py`의 argparse/대화형 입력을
완성한다. Service 구현 시 섹션 32.2의 최종 리포지토리 API
이름(`add`/`update`/`delete`/`get_by_id`/`next_id`,
`list_all`/`exists`/`add`/`remove`, `list_all`/`get`/`set`/`remove`)을
그대로 사용한다. (이후 Sprint 2에서 CSV import/export를 제외한
나머지를 실제로 구현했다 — 섹션 35 이하 참고.)

## 35. Sprint 2 구현 현황 — Service 계층과 비즈니스 규칙

Sprint 2는 섹션 34의 판단에 따라 `services.py`를 실제로 구현했다.
`cli.py`(argparse, 대화형 입력, 출력 포맷팅)와 CSV import/export,
그리고 `decorators.py`의 실제 CLI 적용은 여전히 범위 밖이다 —
`import_csv`/`export_csv`는 `services.py`에 `raise NotImplementedError`
그대로 남겨뒀다.

### 35.1 실제 구현된 것

- `ledger/validators.py`: `validate_date`, `validate_month`,
  `validate_amount`, `validate_transaction_type`,
  `validate_category_name` 전부 실제 동작. 어디에도 `print()`/`input()`이
  없다(섹션 16 요구).
- `ledger/services.py`: `LedgerService`의 모든 메서드가 실제
  동작한다 — `add_transaction`, `list_transactions`, `search`,
  `update_transaction`, `delete_transaction`, `monthly_summary`,
  `set_budget`, `add_category`, `list_categories`, `remove_category`.
  `import_csv`/`export_csv`만 여전히 미구현.
- `ledger/errors.py`: `InvalidDateError`/`InvalidMonthError`/
  `InvalidAmountError`/`InvalidTransactionTypeError`(전부
  `ValidationError` 하위)와 `CategoryInUseError`(직접 `LedgerError`
  하위) 추가 — 전부 실제로 raise됨(섹션 40).
- `ledger/models.py`: `MonthlySummary` dataclass 추가(섹션 36).
- `tests/`: `unittest` 72개 신규 테스트(검증기 20개, Service 52개) +
  Sprint 1의 41개 = **총 113개**, 전부 실제 `TemporaryDirectory` 기반
  리포지토리로 Service와 Repository가 함께 동작하는 것을 검증한다
  (모킹하지 않음 — 섹션 18 요구).

### 35.2 API 개명 (Sprint 0B/1 골격 대비, 구체적 이유와 함께)

| 이전 이름 | 최종 이름 | 이유 |
|---|---|---|
| `LedgerService.list_recent(limit)` | `list_transactions(limit)` | Sprint 2 지시 문서 섹션 6이 이 이름을 리터럴로 명시(다른 모든 Service 메서드 이름은 이미 골격과 일치했음 — `list_transactions`만 유일하게 다르게 표기돼 있어 의도적 개명으로 판단) |
| `LedgerService.update_transaction(id, **changes)` (제네릭 `**changes` dict) | `update_transaction(id, *, date=UNSET, ...)` (명시적 키워드 인자 + UNSET sentinel) | `**changes` 딕셔너리는 "필드 생략"과 "필드를 빈 값으로 명시"를 구분할 수 없다(`changes.get("memo", 기존값)`이 `changes={"memo": ""}`와 `changes={}`를 구분 못 함) — 섹션 38 |
| `validators.validate_type(raw)` | `validate_transaction_type(raw)` | Sprint 2 지시 문서 섹션 3이 이 이름을 리터럴로 명시. `SearchCriteria.transaction_type` 필드명과도 통일되어 일관성이 좋아짐 |
| (없음) | `validators.validate_category_name(raw)` | Sprint 2 지시 문서 섹션 3이 "if appropriate"로 제안 — `add_category`가 빈 문자열/공백만 있는 이름을 막으려면 필요해 채택 |

`services.py`의 다른 모든 메서드(`add_transaction`, `search`,
`delete_transaction`, `monthly_summary`, `set_budget`, `add_category`,
`list_categories`, `remove_category`)는 Sprint 0B/1 골격 시그니처를
그대로 유지했다 — 개명할 구체적 이유가 없었기 때문이다.

## 36. `MonthlySummary` 결과 구조

`monthly_summary()`는 딕셔너리 대신 `ledger/models.py`의
`MonthlySummary` dataclass를 반환한다(섹션 9의 "Service/CLI 경계가
명확해지면 추가해도 된다" 지침에 따라 채택). 필드:

```python
@dataclass
class MonthlySummary:
    month: str
    has_transactions: bool
    total_income: int
    total_expense: int
    balance: int
    category_expenses: dict[str, int]      # 지출 거래만 집계 (수입 제외)
    top_categories: list[tuple[str, int]]  # category_expenses를 금액 내림차순 정렬 후 top N
    budget_amount: int | None
    budget_usage_percent: float | None
    budget_exceeded: bool | None
```

- `has_transactions=False`일 때도 숫자 필드는 `None`이 아니라 `0`/`{}`/`[]`다
  — `cli.py`(다음 스프린트)가 "데이터 없음"을 판단하는 용도로만
  `has_transactions`를 보고, 합계 계산 시 별도 분기 없이 그대로
  더해도 안전하게 만들기 위함.
- `budget_amount`/`budget_usage_percent`/`budget_exceeded`는 예산이
  없으면 **셋 다 함께** `None`이다("0이면 예산 없음"이 아니라 "그 달에
  예산이 설정되지 않음"을 명시적으로 표현).
- `budget_usage_percent` 계산 시 `budget.amount == 0` 방어 코드를
  넣었다(`set_budget`이 항상 양수만 저장하도록 보장하지만, 파일을
  손으로 편집했을 가능성까지 방어).

## 37. `search` 매칭 의미론 (확정)

- `from_date`/`to_date`: `Transaction.date`에 대한 **포함(inclusive)**
  경계 — `>=`/`<=`.
- `category`/`transaction_type`/`tag`: **완전 일치, 대소문자 구분**.
  저장된 문자열 그대로 비교한다(카테고리/타입은 애초에 고정된
  값 집합이라 대소문자 구분이 자연스럽고, tag도 사용자가 등록한
  철자를 그대로 보존해야 하므로).
- `query`: memo 필드에 대한 **대소문자 무시 부분 문자열** 일치만
  수행한다(자유 텍스트 검색이므로 대소문자를 맞추라고 요구하는 것은
  사용성이 떨어짐). category/tag는 대소문자를 접지 않는다는 점과
  의도적으로 다르다 — 이 차이를 사용자가 혼동하지 않도록 문서화해
  둔다.
- 금액 범위 필터는 없다(Mission Core 범위 밖, Sprint 0B에서 이미 확정).

## 38. `update_transaction`의 UNSET sentinel 전략

`update_transaction`은 "필드를 생략함(기존 값 유지)"과 "필드를 빈
값으로 명시함(예: `memo=""`, `tags=[]`로 지움)"을 구분해야 한다.
`None`을 기본값으로 쓰면 이 둘을 구분할 수 없다 — `memo=None`이
"생략"인지 "None으로 설정"인지 모호해지기 때문이다(특히 `memo`/`tags`는
`None`이 아니라 `""`/`[]`가 "비어 있음"의 정상 표현이라 더 혼란스러움).

`ledger/services.py`에 작은 sentinel 클래스 `_UnsetType`과 그 유일한
인스턴스 `UNSET`을 정의해 모든 선택적 키워드 인자의 기본값으로 쓴다:

```python
class _UnsetType:
    def __repr__(self) -> str:
        return "UNSET"

UNSET = _UnsetType()

def update_transaction(self, transaction_id: int, *, date: str | _UnsetType = UNSET, ...):
    ...
    new_date = existing.date if date is UNSET else validate_date(date)
```

`is UNSET`으로 비교하므로 `None`/`""`/`[]` 등 어떤 "정상적인" 값과도
절대 충돌하지 않는다. 이보다 더 무거운 구조(별도 Update DTO 클래스,
`dataclasses.replace` 기반 패치 객체 등)는 이 프로젝트 규모에서
과설계로 판단해 채택하지 않았다("Prefer a small sentinel over
overengineering" 지침 반영).

## 39. `list_transactions`/`search`의 "최신순" 의미 (명확화)

두 메서드 모두 "최신순"을 **파일에 기록된 순서(= 추가된 순서 = id
오름차순)의 역순**으로 정의한다 — `Transaction.date` 필드 값으로 다시
정렬하는 것이 아니다. 즉 "최신"은 "가장 최근에 *입력된*" 거래를
뜻하며, "가장 최근 날짜의" 거래를 뜻하지 않는다.

이 결정의 이유: 과거 날짜의 거래를 나중에 입력하는 것(예: 지난주
영수증을 오늘 등록)이 흔한 사용 패턴인데, `date` 필드로 재정렬하면
방금 입력한 항목이 목록 맨 위에 나타나지 않아 "방금 추가한 게 어디
갔지?"라는 혼란을 준다. 또한 `date`로 재정렬하려면 전체 매칭 결과를
정렬해야 해 `list_transactions`의 `deque(maxlen=N)` 전략(섹션 12)과
충돌한다 — 파일 순서 역순은 정렬 없이 그대로 얻어진다.

`search`도 동일한 정의를 따른다: 매칭된 레코드를 파일에서 만난
순서대로 리스트에 모은 뒤 `list.reverse()` 한 번으로 최신순을 만든다
(섹션 13의 "매칭 수에 비례한 버퍼링" 특성은 그대로 유지, 추가 정렬
비용 없음).

## 40. Sprint 2 에러 재사용 전략

Sprint 1에서 만든 영속 계층 예외 중 다음 두 개는 **새 클래스로
감싸지 않고 Service 경계에서 그대로 재사용**한다:

- `TransactionRepository.update()`/`delete()`가 던지는
  `TransactionNotFoundError` → `LedgerService.update_transaction()`/
  `delete_transaction()`이 그대로 전파. "존재하지 않는 거래 id"라는
  의미가 영속 계층과 서비스 계층에서 완전히 동일하므로 번역이
  불필요.
- `CategoryRepository.add()`가 던지는 `DuplicateCategoryError` →
  `LedgerService.add_category()`가 그대로 전파. 마찬가지로 "이미
  등록된 카테고리 이름"이라는 의미가 두 계층에서 동일.
- `CategoryRepository.remove()`가 던지는 `CategoryNotFoundError`는
  두 가지 경로에서 재사용된다: (a) `remove_category()`가 존재하지
  않는 이름을 지우려 할 때 리포지토리에서 그대로 전파, (b)
  `add_transaction()`/`update_transaction()`이 등록되지 않은
  카테고리를 참조하려 할 때 Service가 **직접** 발생시킴(리포지토리를
  거치지 않음 — 거래를 추가/수정하기 전에 미리 검사하므로). 두
  상황 모두 "이 카테고리 이름은 등록되어 있지 않다"는 같은 의미라
  하나의 클래스로 충분하다고 판단했다.

새로 추가한 예외(`InvalidDateError`, `InvalidMonthError`,
`InvalidAmountError`, `InvalidTransactionTypeError`,
`CategoryInUseError`)는 섹션 15 지시에 따른 컴팩트한 계층을 유지한다
— 검증 실패마다 별도 클래스를 만들지 않고, "어떤 필드가 잘못됐는지"
구분이 실제로 유용한 4개 필드 검증기에만 전용 클래스를 뒀다.
`validate_category_name`의 실패는 전용 클래스 없이 `ValidationError`를
직접 쓴다(검증 실패가 "비어 있음" 한 가지뿐이라 구분할 이유가 없음).

## 41. 데코레이터 실제 적용과 "버그를 숨기지 않는다" 원칙

`handle_errors`(섹션 42)는 `ledger/cli.py::_dispatch`에 **한 곳에만**
적용한다(`@handle_errors` 데코레이터 문법 그대로). `_dispatch`는
`main()`이 argparse 파싱을 마친 뒤 호출하는 단일 진입점이며, 10개
커맨드 핸들러(`cmd_add`, `cmd_list`, ... `cmd_delete`) 전부가 이
함수를 거쳐 호출된다 — 각 핸들러에 개별적으로 `try/except`를
반복하지 않고, `LedgerError` 하위 예외가 핸들러에서 던져지면
자연스럽게 `_dispatch`까지 전파된 뒤 데코레이터가 한 번에 잡는다.

**의도적으로 좁게 잡는다**: `except LedgerError`만 잡고 그 외
예외(`KeyError`, `AttributeError`, `TypeError` 등 프로그래밍 버그)는
전혀 건드리지 않는다 — 그대로 전파되어 스택트레이스와 함께
비정상 종료한다. 예상된 사용자 에러(`LedgerError` 계열)와 프로그램
버그를 섞어서 "친절한 에러 메시지"로 뭉개버리면, 실제 버그가
조용히 숨어버려 동료 평가/디버깅 단계에서 원인을 찾기 어려워진다.
`tests/test_cli_decorator.py::test_dispatch_is_wrapped_by_handle_errors`가
`functools.wraps`가 남긴 `__wrapped__` 속성으로 데코레이터가 실제로
적용됐음을 확인하고, `test_real_error_path_goes_through_the_decorator`가
실제 `main()` 호출 경로에서 `ledger.decorators.describe_error`가
호출되는 것을 스파이로 확인한다(단위 테스트로 데코레이터 함수만
따로 부르는 것이 아니라, 실제 CLI 경로를 통과시켜 증명).

## 42. 에러 → 메시지 매핑의 소유권

"[오류]/[힌트]" 텍스트를 만드는 로직(`_ERROR_MESSAGES` 딕셔너리와
`describe_error()`)은 `ledger/decorators.py`에 둔다 — `cli.py`가
아니다. 이유:

- `handle_errors`(최종 에러 처리 지점)와 `add`의 대화형 재프롬프트
  루프(`_prompt_date`/`_prompt_type`/`_prompt_amount`/`_prompt_category`,
  중간 실패 시에도 같은 문구를 보여줘야 함)가 **같은 매핑을
  공유**해야 하므로, 한쪽 모듈에만 두고 다른 쪽이 import하는 구조가
  필요하다.
- `decorators.py`를 선택한 이유는 순환 임포트를 피하기 위해서다:
  `cli.py`가 `decorators.py`에서 `handle_errors`와 `describe_error`를
  둘 다 가져오는 단방향 의존만 있으면 되고, `decorators.py`는
  `cli.py`를 전혀 모른다(반대 방향으로 뒀다면 `decorators.py`가
  `cli.py`를 import해야 해서 순환이 생긴다 — `cli.py`가 이미
  `decorators.py`의 `handle_errors`를 쓰고 있으므로).
- `errors.py`의 예외 클래스 자체에는 한국어 문구를 넣지 않는다
  (Sprint 2 섹션 15 원칙 유지) — 표시 문구는 어디까지나 표시 계층의
  책임이라는 경계를 지킨다.

매핑되지 않은 `LedgerError`(예: `list_transactions`의 순수
`ValidationError("limit must be positive, got 0")`)는 그 예외의
`str(exc)` 메시지를 그대로 원인으로 보여주는 폴백을 쓴다 — 이미
설명적인 메시지이므로 별도 한국어 번역이 없어도 "원인 + 힌트" 구조는
유지된다.

## 43. CLI 책임 경계 (실제 구현 확인)

섹션 26에서 이미 정한 경계를 실제 구현이 지켰는지 확인:

- `cli.py`는 어떤 필드도 자체적으로 검증하지 않는다 — 대화형
  재프롬프트조차 `ledger.validators`의 함수를 그대로 호출해 예외
  발생 여부만 보고 판단한다(알고리즘을 다시 구현하지 않음).
- `search`의 `--from`/`--to`/`--type`은 `cli.py`가
  `validate_date`/`validate_transaction_type`으로 변환한 뒤
  `SearchCriteria`에 넣는다 — 이는 "검증 로직 복제"가 아니라
  `SearchCriteria`가 타입화된 `datetime.date`를 요구하기 때문에
  어차피 어딘가에서 문자열→도메인 값 변환이 필요해서이고, 그
  변환은 validators의 함수를 그대로 재사용한다(직접 파싱 코드를
  쓰지 않음).
- `monthly_summary`/`search`/`list_transactions`의 계산·필터링·정렬
  로직은 전부 `LedgerService`에 있다 — `cli.py`는 반환된
  `MonthlySummary`/`list[Transaction]`을 그대로 출력 포맷팅만 한다.
- `update`의 "필드 최소 1개" 검사만 예외적으로 `cli.py`(`cmd_update`)에
  있다 — argparse가 표현할 수 없는 "여러 선택 옵션 중 최소 1개"
  조건의 파싱 후 검증이며, 비즈니스 규칙이 아니다(섹션 28 원칙
  유지).

## 44. 대화형 태그 입력 정책 (확정)

쉼표로 구분한 값을 받는다: `parse_tags()`가 `,`로 split → 각 조각
`strip()` → 빈 조각 제거. 예: `" meal, lunch ,, work "` →
`["meal", "lunch", "work"]`. 태그 안에 리터럴 쉼표를 넣는 것은
지원하지 않는다(이스케이프 문법 없음) — CSV의 quoting 같은 처리를
사람이 직접 타이핑하는 대화형 입력에 요구하는 것은 이 프로젝트
규모에서 과설계이고, 섹션 6의 "학습자가 설명 가능한 단순한 구현"
원칙과도 맞지 않는다. `update --tags`도 같은 `parse_tags()`를
재사용한다(로직 두 곳에 중복 구현하지 않음). 이 정책으로 Sprint 0B
섹션 29의 마지막 미해결 항목이 해결됐다.

## 45. `main()` 반환값과 종료 코드 최종 정책

`main(argv) -> int`는 **자기 자신은 `sys.exit()`를 호출하지 않는다**
— 정수를 반환할 뿐이다. `ledger/__main__.py`와 `main.py`가
`sys.exit(main(sys.argv[1:]))`로 감싸는 지점에서만 실제 프로세스
종료 코드가 된다. 이렇게 나눈 이유는 테스트 가능성이다:
`main([...])`을 프로세스 안에서 직접 호출해 반환값을 `assertEqual`로
바로 검사할 수 있다(`subprocess`를 띄우지 않아도 됨).

세 가지 종료 경로:

- **0 (성공)**: `_dispatch()`가 예외 없이 끝나면 `handle_errors`가
  `0`을 반환 → `main()`이 그대로 반환.
- **1 (애플리케이션 에러)**: `_dispatch()`에서 `LedgerError`가
  발생하면 `handle_errors`가 잡아 `[오류]`/`[힌트]`를 출력하고
  `1`을 반환.
- **2 (argparse 사용법 에러/`--help`)**: `parser.parse_args(argv)`
  자체가 `SystemExit(2)`(사용법 오류) 또는 `SystemExit(0)`(`--help`)를
  던진다 — `main()`은 이를 가로채지 않고 그대로 전파시킨다. argparse
  가 이미 종료 코드를 스스로 결정하는 영역이므로 `main()`이
  대신 판단하지 않는다.

테스트에서는 0/1 경로를 `main([...])`의 반환값으로, 2/`--help`
경로를 `with self.assertRaises(SystemExit) as cm: main([...])`로
구분해서 검증한다(섹션 24 전체가 이 패턴을 따름).

## 46. CSV 스키마 최종 확정

`ledger/services.py::CSV_FIELDNAMES = ["date", "type", "category",
"amount", "memo", "tags"]`가 import/export가 공유하는 유일한 스키마
정의다 — 헤더 이름과 순서를 이 리스트 하나로 고정하고, `csv.DictReader`/
`csv.DictWriter`가 이 이름들로 딕셔너리 키를 주고받으므로 `line.split(",")`
같은 수동 파싱은 어디에도 없다.

```
date,type,category,amount,memo,tags
2026-09-16,expense,food,15000,점심,"meal,lunch"
2026-09-17,income,salary,3000000,급여,
```

**내부 거래 id는 CSV에 없다** — export가 절대 쓰지 않고, import도
읽지 않는다(있어도 무시, 섹션 47). Sprint 0B 시절 설계했던
`id,type,date,amount,category,memo,tags` 스키마는 이 시점에 완전히
폐기됐다(공식 최소 스키마에 id가 없다는 Sprint 0B의 정정을 그대로
따름 — 섹션 19 원본 결정과 일치).

## 47. 필수 헤더와 확장 컬럼 정책

`CSV_FIELDNAMES`의 6개 헤더는 **전부** 있어야 한다 — `memo`/`tags`
값이 행마다 비어 있어도 되는 것이지, 헤더 자체가 없어도 되는 것은
아니다. 하나라도 빠지면 `CSVFormatError`로 파일 전체를 거부한다
(섹션 48).

CSV에 우리가 모르는 **추가 컬럼**(예: 사용자가 직접 만든 `id` 컬럼)이
있어도 막지 않는다 — `csv.DictReader`가 헤더 행을 그대로
`reader.fieldnames`로 채택하므로, 필수 6개 컬럼이 모두 존재하는지만
확인하고 나머지 컬럼은 단순히 읽지 않는다(코드를 추가로 쓸 필요가
없다 — "존재 여부만 검사"가 자연히 "그 외는 무시"를 구현한다).
`tests/test_service_import.py::test_extra_column_is_ignored`가 `id`
컬럼이 있는 CSV를 import해도 내부 id는 여전히
`TransactionRepository.next_id()`가 발급한 값이 된다는 것을 확인한다.

## 48. Import — 파일 수준 에러 vs 행 수준 스킵 (최종 구분)

`LedgerService.import_csv()`는 두 계층의 실패를 명확히 구분한다:

| 문제 | 처리 |
|---|---|
| 소스 파일이 없음/열 수 없음(`OSError`) | `PersistenceError` — **전체 명령 실패**, 아무 행도 처리하지 않음 |
| UTF-8로 디코딩할 수 없음(`UnicodeDecodeError`, 헤더든 데이터 행이든) | `PersistenceError` — **전체 명령 실패** |
| 헤더 행 자체가 없음 | `CSVFormatError` — **전체 명령 실패** |
| 필수 6개 컬럼 중 하나라도 없음 | `CSVFormatError` — **전체 명령 실패** |
| (헤더가 유효한 뒤) 개별 데이터 행의 날짜/타입/금액/카테고리 검증 실패 | 해당 행만 **스킵하고 계속 진행** — `ImportResult.errors`에 `(행 번호, 예외)` 기록 |

파일/스키마 문제는 "아직 읽기 시작조차 할 수 없는 상태"이므로 즉시
예외를 던져 명령 전체를 실패시킨다(exit 1) — 헤더가 검증되기 *전에는*
어떤 행도 처리하지 않는다(`tests/test_service_import.py::test_header_missing_writes_nothing`로
확인). 헤더가 유효하다고 판단된 *이후*의 개별 행 문제는 공식 요구
("invalid rows should be counted as skipped or failed")를 그대로
따라 건너뛰고 카운트만 한다 — Sprint 0B의 원래 결정을 실제로
구현했다.

**행 번호는 1부터 시작하는 데이터 행 번호**다(헤더 행은 세지 않음) —
CSV를 스프레드시트로 열어 보는 사용자 입장에서 "몇 번째 데이터가
문제였는지"가 "파일의 몇 번째 줄인지"보다 직관적이라고 판단했다.

`ImportResult`(`ledger/models.py`)는 `imported`/`skipped`/`errors`
세 필드만 갖는다. `errors`는 `(row_number, LedgerError)` 튜플의
리스트로, **원본 예외 객체를 그대로** 담는다 — Service가 한국어
메시지를 직접 조립하지 않고, `cli.py`가 이미 갖고 있는
`describe_error()` 매핑(섹션 42)을 그대로 재사용해 `[건너뜀] row=N: ...`을
만든다. 매핑에 없는 에러는 `str(exc)` 폴백이 그대로 쓰인다(예:
`InvalidAmountError`의 "금액은 0보다 큰 정수여야 합니다." 같은
고정 문구, 또는 매핑 안 된 에러의 원본 메시지).

## 49. 태그 파싱 함수의 위치 이동 (`cli.py` → `validators.py`)

Sprint 3에서 `parse_tags()`는 `cli.py`에만 있었다(대화형 `add`와
`update --tags`가 씀). Sprint 4의 CSV import도 **정확히 같은 규칙**
(쉼표 split → strip → 빈 조각 제거)으로 `tags` 컬럼을 파싱해야 하는데,
`LedgerService.import_csv()`가 `cli.py`의 함수를 import하면 의존성
방향이 `services.py → cli.py`가 되어 섹션 5(`repository`는
`cli`/`services`를 모른다, 그리고 재차 `services`도 `cli`를 몰라야
한다는 동일 원칙)를 정면으로 어기게 된다.

그래서 `parse_tags()`를 `ledger/validators.py`로 옮겼다 — 이미
"재사용 가능한 입력 정형화 헬퍼"를 모아두는 모듈이고, `cli.py`와
`services.py` 둘 다 이미 이 모듈에 의존하고 있어(`cli.py`는 검증
재프롬프트용으로, `services.py`는 `add_transaction` 내부 검증용으로)
새로운 의존성을 추가하지 않는다. `cli.py`는 이제 자기 것을 따로 갖는
대신 `from ledger.validators import parse_tags`로 가져다 쓴다 — 로직
중복이 한 곳도 남지 않는다. 엄밀히는 "검증"이 아니라 "파싱"(실패하지
않음, 항상 리스트를 반환)이지만, 이 모듈의 "raw 입력 → 정형화된 값"
역할에는 들어맞는다고 판단했다.

## 50. Export 필터 조합 검증 (Service가 최종 권위)

`export --month`와 `export --from/--to`는 상호 배타적이며, 후자는
둘 다 있어야 한다는 규칙(섹션 20)을 `cli.py`가 아니라
**`LedgerService.export_csv()` 안에서** 검증한다:

- `month`와 (`from_date` 또는 `to_date`)가 동시에 있으면 거부
- `from_date`만 있거나 `to_date`만 있으면 거부
- 어느 쪽도 없으면 거부
- `from_date > to_date`(역순 범위)면 거부

전부 `ValidationError`. `cli.py::cmd_export`는 이 검증을 전혀
반복하지 않고 argparse가 파싱한 값을 그대로 넘기기만 한다 —
`LedgerService`가 규칙의 유일한 권위여야 한다는 섹션 26 원칙을 CLI가
아니라 Service 안에 검증 로직을 두는 것으로 지켰다(Sprint 3의
`update`의 "필드 최소 1개" 검사가 CLI에 있는 것과 대비된다 — 그건
argparse가 표현 못 하는 "파싱 후 인자 형태" 문제였고, 이건 명백한
비즈니스 규칙이라 Service에 둔다).

## 51. Export의 제너레이터 재사용 (동료 평가용 핵심 근거)

`export_csv()`는 `list(self.transactions.iter_all())`을 쓰지 않는다.
대신:

```python
for transaction in self.transactions.iter_all():
    if <조건에 맞음>:
        writer.writerow(...)
```

`iter_all()`이 반환하는 제너레이터를 그대로 순회하며, 조건에 맞는
레코드는 즉시 `csv.DictWriter.writerow()`로 쓰고 버린다 — 매칭된
레코드를 리스트에 모으지 않는다. `search()`(섹션 13)와 달리 export는
**출력 순서 요구가 없다**(섹션 21 — "파일/삽입 순서를 그대로 유지,
최신순 등으로 재정렬하지 않음")고 이미 확정돼 있었기 때문에, 버퍼링
없이 완전한 스트리밍이 가능하다. 메모리는 대상 파일 크기와 무관하게
O(1)(정확히는 현재 처리 중인 레코드 1개 + 작은 로컬 변수들)이다 —
`list_transactions()`의 O(limit), `search()`의 O(매칭 수)보다 한 단계
더 강한 스트리밍 특성이며, 이 프로젝트에서 제너레이터 재사용이 가장
분명하게 드러나는 지점이다.

## 52. Import/Export의 안전한 파일 처리

- **Import는 항상 읽기 전용**이다 — 소스 CSV 파일을 열 때 `"r"` 모드만
  쓰고, 쓰기/이동/삭제를 하는 코드 경로가 아예 없다
  (`tests/test_service_import.py::test_source_file_not_modified`가
  import 전후 바이트가 동일함을 확인).
- **Export는 `ledger/repository.py`의 `_atomic_write_jsonl()`과 같은
  패턴**을 쓴다: `--out` 경로와 같은 디렉터리에 임시 파일을 만들어
  전체 CSV를 다 쓴 뒤(`flush`+`fsync`), `os.replace()`로 교체한다 —
  쓰다가 실패해도 기존 `--out` 파일(있었다면)이 반쯤 쓰인 내용으로
  덮이지 않는다. 임시 파일 생성 전에 `path.parent.mkdir(parents=True,
  exist_ok=True)`로 상위 디렉터리를 자동 생성한다(사용자가 명시적으로
  지정한 출력 경로이므로 — 섹션 22 정책). `--out`이 이미 존재하는
  파일을 가리키면 명시적으로 덮어쓴다(문서화된 동작 — 사용자가 직접
  지정한 출력 대상이므로 무조건 실패시키는 것보다 덮어쓰기가
  Mission Core 단순성에 더 맞는다고 판단).
- **중복 검출은 하지 않는다**(섹션 12) — 동일한
  date/type/category/amount/memo/tags를 가진 행이 CSV에 여러 번
  있어도(혹은 이미 존재하는 거래와 우연히 값이 같아도) 각각 새
  거래로 등록한다. 의미적 중복 판단은 이 프로젝트 범위 밖의 과설계로
  간주했다.

## 53. Sprint 2 완료 시점 판단 (역사적 기록)

**가능.** `LedgerService`의 CSV import/export를 제외한 모든 메서드가
실제로 동작하며 113개 unittest(Sprint 1의 41개 + Sprint 2의 72개)가
전부 통과한다(`python -m compileall .`도 통과). Service는 어디에서도
`print()`/`input()`/`sys.exit()`/argparse를 쓰지 않는다 — 순수하게
값을 반환하거나 `ledger.errors.LedgerError` 하위 예외를 던진다.

Sprint 3는 다음 중 하나 이상을 다룬다: (a) `services.py`의
`import_csv`/`export_csv` 실제 구현(섹션 19·20의 정책을 그대로
따르면 됨), (b) `cli.py`의 argparse 파서 완성 + `add`의 대화형
입력 + 출력 포맷팅(섹션 8·9), (c) `decorators.py::handle_errors`를
실제 커맨드 핸들러에 적용(섹션 22). 셋 다 이번에 확정된
`LedgerService` 공개 API(`add_transaction`, `list_transactions`,
`search`, `update_transaction`, `delete_transaction`,
`monthly_summary`, `set_budget`, `add_category`, `list_categories`,
`remove_category`)를 그대로 호출하면 된다 — Service 시그니처 변경은
필요하지 않다. (이후 Sprint 3에서 (b)와 (c)를 실제로 구현했다 —
섹션 41 이하 참고. (a) CSV import/export만 Sprint 4로 남았다.)

## 54. Sprint 3 완료 시점 판단 (역사적 기록)

### 54.1 실제 구현된 것 (Sprint 3 시점)

- `ledger/cli.py`: `build_parser()`가 `add`/`list`/`search`/`summary`/
  `budget set`/`category add|list|remove`/`update`/`delete` 전부를
  실제 동작하는 서브커맨드로 제공한다. `import`/`export`는 의도적으로
  노출하지 않는다(Sprint 3 Option A — `--help`에 미완성 명령을
  보여주지 않기 위함, 이후 Sprint 4에서 실제로 추가됐다 — 섹션 46
  이하 참고). `ledger/__main__.py`가 canonical entry point,
  `main.py`는 동일 동작의 보조 진입점.
- `ledger/decorators.py`: `handle_errors`가 실제로 `_dispatch` 하나에
  적용되어 있고(섹션 41), `describe_error`가 8개 구체적
  예외 타입에 대해 고정 한국어 문구를 반환하며 나머지는
  `str(exc)` 폴백을 쓴다(섹션 42, Sprint 4에서 CSVFormatError 1개
  추가돼 9개가 됨).
- `id -> "TX-000012"` 표시 포맷은 `cli.py::format_transaction_id()`
  하나에서만 이뤄지며, `LedgerService`/리포지토리 어디에도 이
  포맷 문자열이 등장하지 않는다.
- `tests/`: CLI 관련 신규 테스트 62개 + 기존 113개 = **총 175개**,
  전부 `unittest.mock.patch`로 `input()`과 `sys.stdout`/`sys.stderr`를
  가로채는 방식으로 실제 프로세스를 띄우지 않고(`subprocess` 미사용)
  `main(argv)`를 직접 호출해 검증한다.

### 54.2 Sprint 4 착수 가능 여부 (Sprint 3 시점의 판단)

**가능.** 10개 Mission Core 명령이 전부 실제 터미널에서 동작하며,
175개 unittest가 전부 통과하고 `python -m compileall .`도 통과한다.
예상된 사용자 에러는 어디에서도 원시 스택트레이스를 노출하지 않고
`[오류]`/`[힌트]` + 0이 아닌 종료 코드로 처리된다.

Sprint 4는 `LedgerService.import_csv`/`export_csv`의 실제 구현과,
그것을 노출하는 `cli.py`의 `import`/`export` 서브커맨드 추가만
남았다. 다른 어떤 명령도, `LedgerService`의 다른 어떤 공개 API도
변경할 필요가 없다. (이후 Sprint 4에서 실제로 구현했다 — 섹션 46
이하 참고.)

## 55. Sprint 4 구현 현황 요약과 Sprint 5 착수 가능 여부

### 55.1 실제 구현된 것

- `ledger/services.py`: `import_csv()`/`export_csv()` 실제 동작(섹션
  46-52). `CSV_FIELDNAMES` 상수가 스키마의 유일한 정의.
- `ledger/cli.py`: `import --from <path>`(`dest="source"`로 Python
  키워드 `from`과의 충돌 회피), `export --out <path> [--month |
  --from --to]` 서브커맨드 추가. `cmd_import`가 `ImportResult.errors`를
  `describe_error()`로 포맷해 `[건너뜀] row=N: ...`을 출력하고 마지막에
  `[완료] imported=N, skipped=M`을 출력. `cmd_export`가
  `[완료] <path> (N records)`를 출력. 둘 다 `_dispatch`를 거치므로
  기존 `handle_errors` 데코레이터를 그대로 통과한다 — 별도 에러
  처리 경로를 만들지 않았다(섹션 25 요구 충족).
- `ledger/validators.py`: `parse_tags()`가 `cli.py`에서 이동해 왔다
  (섹션 49) — CSV import와 대화형 `add`/`update --tags`가 완전히
  같은 함수를 공유한다.
- `ledger/errors.py`: 새 예외 클래스를 만들지 않았다 — Sprint 1이
  이미 만들어 둔 `PersistenceError`(파일 I/O)와 Sprint 0B/1부터
  예약만 돼 있던 `CSVFormatError`(스키마 문제)를 그대로 재사용했다
  (섹션 24 지시 — "큰 CSV 예외 계층을 만들지 말라"를 문자 그대로
  지킴).
- `tests/`: `test_service_import.py`(19개), `test_service_export.py`
  (13개), `test_round_trip.py`(1개), `test_cli_import.py`(5개),
  `test_cli_export.py`(4개) 신규 42개 + 기존 175개 = **총 217개**.

### 55.2 Sprint 5 착수 가능 여부

**가능.** 공식 Mission Core의 10개 명령(add/list/search/summary/
budget/category/update/delete/import/export)이 전부 실제 터미널에서
동작하며, 섹션 32(수동 스모크 테스트 — category add → add ×3 →
export --month → 다른 data-dir에 import → list로 확인, 그리고
손상된 행/누락 파일/조건 없는 export 각각의 에러 케이스)로 실제
동작을 확인했다. 217개 unittest가 전부 통과하고
`python -m compileall .`도 통과한다. Mission Core 기능 구현은 이
시점에 전부 완료됐다 — Sprint 5는 통합 QA, 공식 요구사항 감사,
README 최종 검증, 제출 준비만 남았다(섹션 36 scope protection에
따라 backup/반복거래/GUI/SQLite 등은 범위 밖으로 유지).

## 56. Sprint 5 — 최종 감사 결과 (기능 변경 없음)

Sprint 5는 새 기능을 추가하지 않았다. `python -m ledger`(실제
서브프로세스)로 10개 Mission Core 명령 전부를 다시 실행해 문서와
실제 동작을 대조했고, **코드 동작 자체는 전부 요구사항을
만족했다** — 고친 것은 실제 구현을 따라가지 못한 설계 문서 두
군데뿐이다:

1. 섹션 8·16의 CLI 커맨드 트리 예시가 `category add <name>`/
   `category remove <name>`(위치 인자)와 `import <csv-path>`(위치
   인자)로 남아 있었다 — Sprint 3이 `category add/remove`를 대화형으로,
   Sprint 4가 `import`를 `--from` 옵션으로 바꾼 뒤에도 이 예시
   블록을 갱신하지 않았던 것. 실제 `--help` 출력과 일치하도록
   수정했다(코드는 이미 옳았음 — 문서만 뒤처져 있었다).
2. 섹션 9·11의 "카테고리가 하나도 없으면 재프롬프트 없이 즉시
   에러 종료"라는 Sprint 0B 초안 문구가 실제 구현(다른 필드와
   동일하게 3회 재시도 후 종료)과 달랐다. 실제 동작도 공식 요구
   (트레이스백 없음, 원인+힌트, non-zero exit)를 동일하게 만족하므로
   — 즉 실제 구현이 이미 요구사항과 일치하므로 — 코드가 아니라
   문서 쪽을 실제 동작에 맞게 고쳤다(Sprint 5 지시 문서 섹션 25의
   "구현이 이미 공식 요구사항과 맞으면 문서를 고쳐라" 원칙 그대로
   적용).

그 외에는 실제 CLI 실행(사용법 예시 전부, 오류 시나리오 12종,
빈 상태 시나리오, 카테고리 생명주기, 예산 초과, CSV
import/export/round-trip)에서 트레이스백·잘못된 종료 코드·문서와
다른 동작을 하나도 발견하지 못했다 — 그래서 그 외 코드는 전혀
건드리지 않았다("PASS에 영향을 주는 실제 문제만 수정한다" 원칙).
전체 감사 절차와 명령별 증거는
[docs/m03-final-qa-report.md](m03-final-qa-report.md)에 정리했다.
