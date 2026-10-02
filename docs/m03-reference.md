# B2-1 Reference

이 문서는 첫 실습용 문서가 아니다. [Hands-on Guide](m03-hands-on-guide.md)와
[Code Reading Guide](m03-code-reading-guide.md)를 마친 뒤, 설계 근거·검증 증거·
동료평가 답변을 빠르게 찾기 위한 참고서다.

## 요구사항 대응

| 요구사항 | 현재 구현과 증거 |
|---|---|
| Python 3.10+, 표준 라이브러리만 사용 | `README.md`, [Final QA Report](m03-final-qa-report.md)의 감사 표 |
| `python -m ledger`, CLI help | `ledger/__main__.py`, `ledger/cli.py`, 10개 command 도움말 |
| add/list/search/summary/budget/category/update/delete/import/export | `LedgerService`와 CLI dispatch, QA의 수동 CLI 검증 |
| 파일 영속 저장과 `--data-dir` | JSONL 3파일, `DEFAULT_DATA_DIR = Path("data")` |
| Generator | `TransactionRepository.iter_all()`의 실제 `yield` |
| Decorator와 실제 적용 | `decorators.py::handle_errors`, `cli.py::_dispatch`의 `@handle_errors` |
| Type Hint와 오류·힌트 | 공개 API annotation, `LedgerError` 처리와 exit code |

공식 요구사항은 **무엇을 충족해야 하는가**이고, 아래는 구현에서 선택한 방법이다.

| 구현 선택 | 이유 |
|---|---|
| JSONL | 한 줄씩 읽는 Generator와 append 저장에 알맞고 세 데이터 저장소 형식을 통일한다. |
| `Repository → Service → CLI` | 파일 접근, 기능 규칙, 사용자 입출력을 분리한다. |
| `deque(maxlen=limit)` | list가 최근 N개만 메모리에 유지한다. |
| 월 전체 예산 | `summary --month`에서 지출과 비교하는 보고 기준이다. 거래 추가를 막지 않는다. |
| tempfile + fsync + replace | update/delete의 원본 파일 직접 덮어쓰기 위험을 낮춘다. |
| `UNSET` | 부분 수정의 ‘생략’과 ‘빈 값으로 변경’을 구분한다. |

더 자세한 공식 요구사항 매트릭스와 PASS 근거는 기존
[Architecture Design](m03-architecture-design.md#27-요구사항-추적-매트릭스-sprint-5-감사로-재확인됨),
[Final QA Report](m03-final-qa-report.md)에 보존되어 있다.

## 설계 한눈에 보기

```text
사용자
↓
cli.py (argparse, prompt, 출력)
↓
services.py (업무 규칙, 계산)
↓
repository.py (JSONL 읽기·쓰기)
↓
data/transactions.jsonl, categories.jsonl, budgets.jsonl
```

`models.py`는 계층 사이를 오가는 Transaction, Budget, SearchCriteria 등의 형태를,
`validators.py`는 날짜·금액·타입 같은 값 규칙을, `decorators.py`는 공통 오류 처리를
담는다. 자세한 코드 흐름은 [Code Reading Guide](m03-code-reading-guide.md)를 우선한다.

## QA 증거와 알려진 한계

현재 문서 작업 시작 시점의 저장소 QA 기록은 **217 tests, OK**이며, 실제 CLI 기반
검증도 [Final QA Report](m03-final-qa-report.md)에 남아 있다. 이번 변경은 문서만
대상으로 하고 코드·테스트는 바꾸지 않는다.

알려진 단순화:

- `list`/`search`의 최신순은 날짜순이 아니라 입력(파일) 순서의 역순이다.
- CSV import는 중복을 찾지 않는다. 같은 CSV를 다시 import하면 새 거래가 추가된다.
- 태그 속 쉼표 자체는 지원하지 않고 쉼표를 태그 구분자로 쓴다.
- 안전 교체는 백업·동시 쓰기 잠금·모든 장애 상황 보장을 의미하지 않는다.

## 동료평가 빠른 답변

| 질문 | 10초 답변 | 코드 위치 |
|---|---|---|
| 왜 `python -m ledger`가 되나? | `ledger`가 package이고 Python이 `__main__.py`를 찾아 CLI main을 실행한다. | `ledger/__main__.py` |
| Generator는 왜 썼나? | JSONL을 한 줄씩 Transaction으로 만들어 전체를 한꺼번에 보관하지 않는다. | `repository.py::iter_all` |
| list 최근 5건은 어떻게 처리하나? | Generator가 공급하고 `deque(maxlen=5)`가 최근 5개만 남긴 뒤 뒤집는다. | `services.py::list_transactions` |
| Decorator 역할은? | `_dispatch`의 예상된 LedgerError를 공통 오류·힌트와 exit 1로 바꾼다. | `decorators.py`, `cli.py` |
| 데이터가 왜 남나? | Repository가 JSONL 파일에 저장하고 다음 실행에서 다시 Transaction으로 읽는다. | `repository.py` |
| update/delete가 안전한 이유는? | 임시 파일을 완성한 뒤 `os.replace`로 원본을 교체한다. | `repository.py::_atomic_write_jsonl` |

30초 시연은 `list --limit 5 → search --tag lunch → summary --month 2026-09 → export` 순서가
좋다. 더 짧은 시연 스크립트는 [Peer Evaluation Guide](m03-peer-evaluation-guide.md)를 쓴다.

## 관련 문서의 역할

| 필요 | 문서 |
|---|---|
| 프로그램을 실제로 처음 사용 | [Hands-on Guide](m03-hands-on-guide.md) |
| 방금 실행한 코드와 Python 개념 이해 | [Code Reading Guide](m03-code-reading-guide.md) |
| 상세 설계의 역사와 원문 매트릭스 | [Architecture Design](m03-architecture-design.md) |
| CLI QA와 테스트 근거 | [Final QA Report](m03-final-qa-report.md) |
| 발표용 답변·시연 | [Peer Evaluation Guide](m03-peer-evaluation-guide.md) |
| 기존 단계별 사용 설명 | [User Guide](m03-user-guide.md) |
