# B2-1 — Final QA Report (Sprint 5)

> **Historical/reference document.** 이 문서는 당시의 QA 증거를 보존한다.
> 현재 학습 경로와 최신 문서 진입점은 [B2-1 Reference](m03-reference.md)를 참고한다.

이 문서는 Sprint 5(최종 감사)의 결과물이다. 새 기능을 구현하지
않았고, 코드는 문서 정확성 때문에 수정한 두 군데(섹션 "발견된
불일치와 조치" 참고)를 제외하면 전혀 손대지 않았다. 모든 검증은
`python -m ledger`를 실제 서브프로세스로 실행해서 수행했다 —
`LedgerService`를 직접 호출하지 않았다.

## Executive status

**PASS.**

## 공식 요구사항 감사

| 구분 | 요구사항 | 상태 | 근거 |
|---|---|---|---|
| Application | Python 3.10+ | PASS | `from __future__ import annotations`, `X \| None` 등 3.10+ 문법 전역 사용 |
| Application | 표준 라이브러리만 사용 | PASS | 전체 소스 import 검토(아래 "표준 라이브러리 전용 감사" 참고), 의존성 매니페스트 파일 전혀 없음 |
| Application | 터미널 CLI | PASS | `python -m ledger`로 실제 실행 확인 |
| Application | `python -m ledger <command>` | PASS | `ledger/__main__.py`가 canonical entry point, 실제 실행으로 확인 |
| Application | `--help` | PASS | 루트 + 10개 서브커맨드 전부 `--help` exit 0 확인(아래 "루트/서브커맨드 --help" 참고) |
| Commands | add/list/search/summary/budget/category/update/delete/import/export | PASS | 10개 전부 실제 CLI로 end-to-end 실행 확인(아래 "수동 CLI 인수 테스트" 참고) |
| Persistence | 재시작 후에도 유지 | PASS | 모든 시나리오를 독립된 `python -m ledger` 프로세스 여러 번으로 실행 — 각 호출이 완전히 별도 OS 프로세스이므로 "재시작"을 그대로 증명 |
| Persistence | 데이터 파일 3개 이상 | PASS | `transactions.jsonl`/`categories.jsonl`/`budgets.jsonl` |
| Persistence | JSONL 또는 CSV 중 하나로 통일 | PASS | 세 저장 파일 전부 JSONL(`ledger/repository.py`) |
| Persistence | data directory 지원 + `--data-dir` override | PASS | 전역 옵션, 커스텀 경로로 전 시나리오 실행 확인 |
| Structure | 클래스 2개 이상 | PASS | 비-예외 클래스 10개(`Transaction, Budget, SearchCriteria, MonthlySummary, ImportResult, TransactionRepository, CategoryRepository, BudgetRepository, _UnsetType, LedgerService`) + 예외 클래스 15개 |
| Structure | 모듈 3개 이상 | PASS | `ledger/{models,repository,services,cli,validators,decorators,errors}.py` 7개(`__init__.py`/`__main__.py` 제외) |
| Structure | Model/Repository/Service/CLI 분리 | PASS | 의존 방향 `cli → services → repository → file`이 코드 리뷰로 확인됨(레포지토리가 상위 계층을 import하지 않음) |
| Structure | 의미 있는 타입 힌트 | PASS | 공개 함수/메서드/필드 전수 코드 리뷰(정적 타입 검사기는 표준 라이브러리 제약상 미사용) |
| Python concepts | 진짜 Generator | PASS | `TransactionRepository.iter_all()`이 `yield`를 쓰는 제너레이터 함수, `types.GeneratorType`로 테스트 확인 |
| Python concepts | 진짜 Decorator | PASS | `ledger/decorators.py::handle_errors`, `@` 문법으로 정의 |
| Python concepts | Decorator 실제 적용 | PASS | `ledger/cli.py::_dispatch`에 `@handle_errors` 적용, `__wrapped__` 존재 + 실제 오류 경로에서 호출되는 것을 스파이로 확인(`tests/test_cli_decorator.py`) |
| Error behavior | 예상된 에러에 트레이스백 없음 | PASS | 12가지 에러 시나리오 전부 확인(아래 "에러 시나리오" 참고) |
| Error behavior | 원인 + 힌트 | PASS | 전 시나리오에서 `[오류]`/`[힌트]` 두 줄 확인 |
| Error behavior | 에러 시 non-zero exit | PASS | 애플리케이션 에러 exit 1, argparse 사용법 에러 exit 2 |
| Documentation | README에 실행/저장/명령 예시/CSV 스키마 포함 | PASS | README의 모든 예시 명령을 실제로 실행해 결과 일치 확인(아래 "README 검증" 참고) |

**BLOCKED 항목 없음.**

## 자동 검증

```
python -m compileall .          # 통과, 에러 없음
python -m unittest discover -s tests -t . -v   # Ran 217 tests ... OK
```

- 실행 결과: **217 tests, 217 passed, 0 failed, 0 errors.**
- Sprint 5에서 코드를 바꾸지 않았으므로(문서만 수정) 테스트 개수도
  동일하게 217개로 유지됨 — 회귀 없음.

## 루트/서브커맨드 `--help`

`python -m ledger --help`: exit 0, 10개 명령(`add, list, search,
summary, budget, category, update, delete, import, export`) 전부
표시됨. `add/list/search/summary/budget/category/update/delete/
import/export` 각각의 `--help`도 전부 exit 0 확인. `python -m ledger
frobnicate`(알 수 없는 명령)와 인자 없는 `python -m ledger`는 각각
exit 2.

## 수동 CLI 인수 테스트 (Sprint 5 실제 실행 로그 기반 요약)

실행은 전부 임시 디렉터리(`--data-dir`)를 대상으로 했고, 프로젝트의
실제 `./data`는 건드리지 않았다.

| 시나리오 | 명령 | 결과 |
|---|---|---|
| 빈 상태 category list | `category list` (빈 디렉터리) | `[안내] 등록된 카테고리가 없습니다.`, exit 0, 디렉터리 미생성 |
| 카테고리 0개에서 add | `add` | 날짜/타입까지 통과 후 카테고리 프롬프트에서 3회 재시도 모두 실패 → `[오류] 등록되지 않은 카테고리입니다.` / `[힌트] ...`, exit 1, 트레이스백 없음 |
| 카테고리 생명주기 | `category add`→중복 add→`list`→거래에서 사용→`remove`(차단)→`list`(여전히 존재)→거래 delete→`remove`(성공)→`list`(빈 목록)→재실행(영속 확인) | 전부 문서대로 동작 |
| add 재시도 | 잘못된 날짜/타입/금액/카테고리 각각 1회 오입력 후 정상값 | 매번 `[오류]/[힌트]` 출력 후 재프롬프트, 최종 저장 성공, 트레이스백 없음 |
| ID 정책 | id=4(당시 최댓값) 삭제 후 재추가 → 4 재발급(정상, max+1 특성) / id=2(비최댓값) 삭제 후 재추가 → 5 발급(2는 재사용 안 됨) | 문서화된 max+1 정책과 일치 |
| summary 필수 `--month` | `summary`(옵션 없음) | argparse 자체 에러, exit 2 |
| summary/budget | 수입/지출 추가 → `budget set` → `summary` | 총수입/총지출/잔액/TOP N/예산/사용률/초과여부 전부 정확, 거래 추가는 예산 초과와 무관하게 계속 허용됨 |
| update | `--id`만 지정(거부) / `--memo ""`(비움) / `--tags ""`(비움) / 존재하지 않는 카테고리(거부) / 존재하지 않는 id(거부) | 전부 `[오류]/[힌트]` + exit 1, 생략 필드는 유지됨 확인 |
| delete | 존재 id 삭제 성공 / 재삭제 시도(존재하지 않음) | 성공 후 `[삭제 완료]`, 재삭제는 `[오류] 존재하지 않는 거래 ID입니다.` |
| export 필터 조합 5종 | 조건 없음 / `--from`만 / `--to`만 / `--month`+`--from/--to` 동시 / `--from > --to` | 5가지 전부 거부(exit 1, 원인+힌트), 유효한 `--month`는 정확한 레코드 수로 성공 |
| import 파일/스키마 에러 | 존재하지 않는 파일 / 필수 컬럼 누락 헤더 | 둘 다 exit 1, `[오류]/[힌트]`, 아무 것도 반영되지 않음 |
| import 행 단위 스킵 | 유효 1행 + 잘못된 금액 1행 혼합 CSV | `[건너뜀] row=1: ...` 출력 후 `[완료] imported=1, skipped=1` |
| round trip | export(카테고리 있는 데이터) → 별도 data-dir에 카테고리 등록 후 import | date/type/category/amount/memo/tags 전부 원본과 일치(한글 메모 포함), id만 다름(설계대로) |
| 전체 사용자 여정(14단계) | `--help`→category add→add(수입)→add(지출)→list→search→budget set→summary→update→export→delete→import→list→category remove(사용중, 차단) | 14단계 전부 문서와 일치하는 출력/종료코드 |

## 에러 UX 검증 (트레이스백 없음 확인 12종)

아래 전부 `assertNotIn("Traceback", err)`에 해당하는 실행 결과를
Sprint 5에서 실제 CLI로 재확인했다(자동화 테스트에도 동일 항목이
있음: `tests/test_cli_errors.py` 외):

1. 잘못된 날짜 (`update --date not-a-date`)
2. 잘못된 월 (`budget set --month 2026-9`)
3. 잘못된 금액 (`budget set --amount -1`, `add`의 음수 금액)
4. 잘못된 타입 (`search --type spending`)
5. 존재하지 않는 카테고리 (`add`/`update`/CSV import 행)
6. 사용 중인 카테고리 삭제 시도
7. 존재하지 않는 거래 id (`update`/`delete`)
8. `update`에 필드 옵션 없이 `--id`만 지정
9. 존재하지 않는 import 소스 파일
10. 잘못된 CSV 헤더(필수 컬럼 누락)
11. 기간 조건 없는 export
12. `--from > --to`인 export

모두 exit 1, `[오류]`/`[힌트]` 두 줄, 트레이스백 없음을 확인했다.
argparse 자체 사용법 에러(예: `summary`에 `--month` 누락, `update`에
`--id` 누락)는 exit 2이며 이 역시 트레이스백이 아니라 argparse의
표준 usage 메시지임을 확인했다.

## 스트리밍 증거

- `TransactionRepository.iter_all()`은 `yield`를 쓰는 제너레이터
  함수다(파일을 한 줄씩 읽어 그 자리에서 `Transaction`으로 변환해
  넘긴다) — 전체 파일을 리스트로 먼저 만드는 코드는 어디에도 없다.
- `list_transactions(limit)`: `collections.deque(maxlen=limit)`에
  스트리밍하며 채움 → O(limit) 메모리.
- `search(criteria)`: 필터링은 스트리밍하지만 매칭된 레코드만
  리스트에 모아 최신순으로 뒤집음 → O(매칭 수) 메모리(상수 메모리라고
  주장하지 않음 — 설계 문서에도 명시).
- `export_csv()`: `for transaction in self.transactions.iter_all():
  ... writer.writerow(...)` — 매칭 레코드를 리스트에 모으지 않고
  즉시 쓰고 버림 → O(1) 메모리(세 소비자 중 가장 강한 스트리밍
  특성).

## 영속성 증거

- 재시작 검증: 이 QA 세션의 모든 시나리오가 `python -m ledger`를
  **여러 번의 독립된 서브프로세스**로 실행했다 — 프로세스가 끝날
  때마다 메모리 상태는 완전히 사라지므로, 다음 호출이 이전 호출의
  결과를 파일에서 다시 읽어 보여주는 것 자체가 "재시작 후 유지"의
  직접적 증거다(예: 카테고리 생명주기 시나리오의 10번째 단계,
  전체 사용자 여정의 각 단계).
- 원자적 쓰기: `update`/`delete`(transactions), `category remove`,
  `budget set` 전부 같은 디렉터리에 임시 파일을 만들어 전체를 쓰고
  `flush`+`fsync` 후 `os.replace()`로 교체한다(`ledger/repository.py`
  의 `_atomic_write_jsonl()`, `ledger/services.py`의 `export_csv()`가
  동일 패턴 재사용). 대상을 찾지 못하면(예: 존재하지 않는 id) 예외를
  던지고 **아무것도 쓰지 않아** 원본이 그대로 남는다 — Sprint 1
  테스트(`test_update_missing_raises` 등)와 이번 감사의 수동 실행
  둘 다로 확인.

## README 검증

README에 있는 모든 예시 명령(`category add`, `add`, `list --limit
5`, `search --category 식비 --from ... --to ...`, `summary --month
2026-09 --top 3`, `budget set ...`, `update --id N --amount ...
--memo ...`, `delete --id N`, `export --out ... --month ...`, `import
--from ...`, `--data-dir` 사용 예)를 Sprint 5에서 실제로 순서대로
실행해 문서에 쓰인 그대로 동작함을 확인했다. 불일치 없음 —
README를 다시 고칠 필요가 없었다.

## 발견된 불일치와 조치 (코드는 변경하지 않음)

Sprint 5 지시 문서의 "구현이 이미 공식 요구사항과 일치하면 문서를
고쳐라" 원칙에 따라, **구현이 이미 올바르므로 문서 2곳만 수정**했다:

1. `docs/m03-architecture-design.md` 섹션 8·16의 CLI 트리 예시가
   `category add <name>`/`category remove <name>`(위치 인자)과
   `import <csv-path>`(위치 인자)로 남아 있었다 — Sprint 3/4에서
   각각 대화형 프롬프트와 `--from` 옵션으로 바뀐 뒤 예시 블록을
   갱신하지 않았던 것. 실제 `--help` 출력과 일치하도록 고쳤다.
2. 섹션 9·11의 "카테고리 0개면 재프롬프트 없이 즉시 종료"라는
   Sprint 0B 초안 문구가 실제 구현(다른 필드와 동일하게 최대 3회
   재시도 후 종료)과 달랐다. 실제 동작도 공식 요구(트레이스백 없음,
   원인+힌트, non-zero exit)를 그대로 만족하므로 문서만 실제 동작에
   맞게 고쳤다.

이 두 가지 모두 **동작 자체는 처음부터 요구사항을 만족**하고
있었다 — 순수 문서 정확성 문제였다.

## 알려진 제약 (제출을 막지 않는, 정당한 단순화)

- 태그에 리터럴 쉼표를 쓸 수 없다(이스케이프 없음) — 대화형 입력과
  CSV 둘 다 동일한 제약, README에 명시.
- `list`/`search`의 "최신순"은 입력(파일 기록) 순서 기준이며
  `date` 필드로 재정렬하지 않는다 — 의도된 설계 결정이며 README·
  설계 문서에 근거와 함께 명시.
- CSV import/export에 의미적 중복 검출이 없다 — 의도된 단순화,
  설계 문서에 명시.
- `category add`/`category remove`에 카테고리가 하나도 없는 상태의
  "즉시 실패" 최적화는 구현하지 않았다(범용 재시도 루프로 동일한
  최종 결과를 얻음) — 요구사항을 만족하므로 이번 스프린트에서
  코드를 바꾸지 않았다(위 "발견된 불일치와 조치" 참고).
- 정적 타입 검사기(`mypy` 등)를 프로젝트에 포함하지 않았다 — 표준
  라이브러리 전용 제약과 Mission Core 범위를 이유로 코드 리뷰로
  타입 힌트 존재를 확인.

## 제출 차단 요소 (Submission blockers)

**없음.**
