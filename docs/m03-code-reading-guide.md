# B2-1 코드 읽기 가이드

이 문서는 [Hands-on Guide](m03-hands-on-guide.md)로 명령을 실행한 **다음** 읽는다.
Python 전체 입문서가 아니라, 내가 방금 본 화면을 B2-1 코드에서 따라가며 필요한
Python만 배우는 안내서다.

```text
내 명령 → 화면 결과 → 처리 파일 → 데이터 이동 → 그 코드의 Python 개념
```

## 이 미션에서 무엇을 배우라고 하는가

현재 저장소의 공식 요구사항 추적표와 QA 기록을 기준으로 구분했다. 원문 요구와 이
프로젝트가 선택한 구현을 섞어 외울 필요는 없다.

| 공식적으로 강조된 학습 대상 | 이 구현에서 추가로 선택한 기술 |
|---|---|
| 터미널 CLI, 파일 I/O, CRUD, 검색, 월 요약·예산, CSV import/export | dataclass, JSONL, Repository/Service 분리 |
| Generator, Decorator, Type Hint, 오류+힌트, `python -m` | deque, tempfile, `os.replace`, UNSET sentinel |

근거와 PASS 증거는 [B2-1 Reference](m03-reference.md#요구사항-대응)에 모아 두었다.

## 1. Python 프로그램은 어떻게 시작될까?

Hands-on에서 실행한 명령:

```bash
python3 -m ledger list --limit 5
```

```text
터미널
↓
Python 인터프리터 (python3)
↓  -m ledger
ledger/__main__.py
↓
ledger/cli.py의 main()
```

### 먼저 보는 프로젝트 구조

```text
m03-pocket-money-ledger/
├── main.py
└── ledger/
    ├── __init__.py
    ├── __main__.py
    ├── cli.py
    ├── services.py
    ├── repository.py
    ├── models.py
    └── validators.py
```

- **Python 파일** 하나는 보통 **module**이다. 예: `cli.py`는 `ledger.cli` module.
- Python module을 묶은 폴더가 **package**다. `ledger/` 안의 `__init__.py`가
  Python에게 이 폴더를 package로 인식하게 한다.
- `-m`은 B2-1 옵션이 아니라 Python 옵션으로, 파일 경로가 아닌 module/package 이름을
  실행하라는 뜻이다.
- package를 `-m`으로 실행하면 Python은 그 안의 `__main__.py`를 찾는다. 그래서
  폴더처럼 보이는 `ledger`를 실행할 수 있다.

`ledger/__main__.py`는 `from ledger.cli import main`으로 `cli.py`의 `main()`을
가져와 `sys.exit(main(sys.argv[1:]))`를 실행한다. `import`는 다른 module의 이름을
가져와 쓸 수 있게 하는 문법이다. `sys.argv[1:]`은 명령 이름 뒤의 단어들, 즉
`list --limit 5`다.

### `python3 main.py`와 다른 점

둘 다 현재 프로젝트에서는 `ledger.cli.main()`을 호출하므로 기능 결과는 같다.
그러나 `python3 main.py`는 **파일을 직접 실행**하고, `python3 -m ledger`는
**package 실행 규칙**으로 `__main__.py`를 찾는다. 이 프로젝트의 권장 진입점은 후자다.

> TODO: infographic asset — main.py vs __main__.py

### 외워둘 4줄

```text
Module  = Python 파일 하나
Package = Python module을 묶은 폴더
__main__.py = package 실행 시작점
-m = module/package로 실행하라는 Python 옵션
```

## 2. CLI는 어떻게 명령을 이해할까?

다시 같은 명령을 따라간다.

```text
__main__.py
↓
cli.py main(argv)
↓
build_parser() / argparse
↓
parse_args(argv)
↓
_dispatch(args)
↓
cmd_list(args, service)
```

**CLI**는 터미널 글자로 프로그램을 조작하는 방식이다. `argparse`는 Python 표준
라이브러리로, `list` 같은 command, `--limit` 같은 option, `5` 같은 값을 해석한다.
`budget set`처럼 command 안에 subcommand도 있을 수 있다.

`build_parser()`의 `add_argument("--limit", type=int, default=10)`은 parser에게
이 옵션의 이름과 규칙을 등록한다. 따라서 사용자가 입력한 문자열 `"5"`를 int `5`로
바꾸고 `args.limit`에 넣는다. `args.limit`의 점은 args 객체의 limit 값을 꺼낸다는 뜻이다.

`--help`는 parser가 사용자에게 보여 주는 안내다. `--data-dir`은 B2-1의 전역 옵션이고
서브명령보다 앞에 둔다. parser가 거부한 사용법은 Service까지 가지 않으며 exit code 2다.

### argparse, Type Hint, Validator는 서로 다르다

| 항목 | 누구를 위한가 | B2-1 예 |
|---|---|---|
| CLI help | 프로그램 사용자 | `--amount`의 도움말 |
| `argparse type=int` | 터미널 문자열 변환 | `"500000" → 500000` |
| Type Hint | 코드 독자·도구 | `amount: int` |
| Validator | 실제 규칙 검사 | 양수 금액·올바른 날짜 |

```python
def set_budget(month: str, amount: int) -> Budget:
```

위 화살표와 `: int`는 명세다. 실제 값 검사는 `validate_amount()` 같은 실행 코드가 한다.

### 외워둘 4줄

```text
CLI는 조작 방식이고 argparse는 입력 해석 도구다.
-m은 Python 옵션, --limit은 B2-1 옵션이다.
Type Hint는 자동 검증기가 아니다.
Validator가 실제 값 규칙을 검사한다.
```

## 3. add를 따라가며 데이터가 바뀌는 모습을 본다

Hands-on Scenario 5의 입력을 기억해 보자.

```text
"12000" (터미널 입력)
↓
12000 (Python int)
↓
Transaction.amount
↓
"amount": 12000 (JSONL 한 줄)
```

```text
cli.py: cmd_add(), input()
↓
validators.py: 날짜·타입·금액 검사
↓
services.py: add_transaction()
↓
models.py: Transaction 만들기
↓
repository.py: JSON으로 변환해 transactions.jsonl 끝에 추가
```

**함수**는 이름 붙인 작업 묶음이고, 괄호 안의 값은 **매개변수**, `return` 뒤로
돌려주는 것은 **반환값**이다. `add_transaction()`은 카테고리가 등록됐는지 확인하고
정수 ID를 만든 뒤 `Transaction`을 Repository에 전달한다.

`Transaction`은 거래 한 건의 값들을 묶은 **객체**다. `@dataclass`는 constructor,
표시, 비교처럼 반복되는 클래스를 Python이 만들게 돕는 decorator다. 날짜는 메모리에서
`datetime.date`, 파일에서는 `YYYY-MM-DD` 문자열이다. `to_dict()`는 저장용 dict를,
`from_dict()`는 읽은 dict에서 객체를 만든다.

JSON은 `{"key": value}` 형태의 텍스트 데이터다. JSONL은 **한 줄에 JSON 객체 하나**다.
그래서 새 거래는 파일 끝에 한 줄만 덧붙일 수 있다.

### 외워둘 4줄

```text
함수는 입력을 받아 작업하고 값을 반환할 수 있다.
Transaction은 거래 한 건을 묶은 dataclass 객체다.
Validator는 값 하나, Service는 기능 규칙, Repository는 파일을 맡는다.
JSONL은 한 줄에 JSON 객체 하나라서 순서대로 읽고 추가하기 좋다.
```

## 4. list로 Generator와 deque를 배운다

Hands-on Scenario 9:

```bash
python3 -m ledger list --limit 5
```

```text
cli.py
↓
LedgerService.list_transactions()
↓
TransactionRepository.iter_all()
↓
transactions.jsonl 한 줄
↓ json.loads()
dict
↓ Transaction
yield
↓ deque(maxlen=5)
↓ reversed()
CLI 출력
```

`iter_all()` 안에는 `yield Transaction.from_dict(record)`가 있다. 함수에 `yield`가
있으면 호출 결과는 **Generator 객체**다. Generator는 라이브러리 이름이 아니라 Python
언어 기능이다. 함수 호출만으로 파일 전체를 읽지 않고, 소비자가 `next()`로 다음 값을
요청할 때 한 건을 만들고 `yield`에서 멈춘다. `for`는 `next()`와 끝의 `StopIteration`을
대신 처리한다.

```python
def numbers():
    yield 1
    yield 2

g = numbers()  # 아직 전부 만들지 않음
next(g)        # 1
next(g)        # 2
```

B2-1의 Generator는 많은 데이터를 “더 빨리 찾는” 기능이 아니다. 파일은 끝까지 읽는다.
대신 전체 Transaction을 한꺼번에 메모리에 올리지 않고 한 건씩 처리한다. 10만 줄이라도
list의 보관량은 limit 기준이다.

`deque(maxlen=5)`는 최근 다섯 개만 남기는 양끝 컨테이너다.

```text
[1] → [1,2] → [1,2,3] → [1,2,3,4] → [1,2,3,4,5] → [2,3,4,5,6]
```

마지막에 `reversed()`하여 최근에 입력한 거래부터 보인다. 즉 시간은 파일 전체 N건을
읽는 O(N), 추가 저장 공간은 O(limit)이다.

### 외워둘 4줄

```text
yield가 있는 함수는 Generator 함수를 만든다.
next()는 다음 값 하나를 요청하고 for가 이를 반복한다.
Generator는 전체 데이터를 한꺼번에 보관하지 않는다.
deque(maxlen=N)는 최근 N개만 유지한다.
```

> TODO: infographic asset — generator pipeline and generator + deque

## 5. search, summary, export는 같은 데이터를 다르게 소비한다

세 명령은 모두 `iter_all()`로 한 건씩 받지만, 받은 뒤의 행동이 다르다.

| 명령 | 한 거래를 받은 뒤 | 추가 메모리 |
|---|---|---|
| `list` | deque에 최근 N개 유지 | O(limit) |
| `search` | 조건 일치 거래만 모아 마지막에 reverse | O(매칭 수) |
| `summary` | 수입·지출·카테고리 합계만 누적 | O(카테고리 수) |
| `export` | 기간이 맞으면 즉시 CSV 행 기록 | 매우 작음(거래 전체를 모으지 않음) |

검색의 `continue`는 현재 거래를 건너뛰고 다음 거래로 간다는 뜻이다. summary의 `+=`는
기존 합계에 값을 더한다. export는 파일 순서대로 바로 쓰므로 출력 전체를 저장할 필요가 없다.

> TODO: infographic asset — search / summary / export comparison

## 6. 오류를 통해 Decorator를 배운다

```bash
python3 -m ledger delete --id 999999
```

```text
CLI → _dispatch → Service → LedgerError 발생
                         ↓
                  @handle_errors
                         ↓
                 [오류] / [힌트], exit code 1
```

`cli.py`의 `_dispatch` 바로 위에 `@handle_errors`가 있다. 이는
`_dispatch = handle_errors(_dispatch)`와 거의 같은 의미다. `handle_errors`는
함수를 받아 `wrapper`라는 새 함수를 돌려준다. `wrapper`는 원래 함수를 `try`로 실행하고
`LedgerError`라면 공통 메시지와 1을 돌려준다.

`@`는 Python 문법이다. `@handle_errors`는 이 프로젝트가 만든 decorator이고,
`@dataclass`는 표준 라이브러리 decorator다. `wrapper`라는 단어는 예약어가 아니라 만든
사람이 붙인 이름이다. `functools.wraps`는 wrapper를 쓰더라도 원래 함수 이름·docstring
같은 메타데이터를 보존하는 데 도움을 준다.

Decorator가 없으면 각 command handler가 같은 `try/except`, 오류 출력, 종료 코드
코드를 반복해야 한다. 이 decorator는 예상된 `LedgerError`만 처리하고, 개발 버그를
전부 감추지 않는다. argparse 오류(exit 2)도 별도 경로다.

### 외워둘 4줄

```text
Decorator는 함수·클래스에 기능을 덧붙이는 Python 문법이다.
@handle_errors는 B2-1 명령의 공통 오류 처리를 붙인다.
@dataclass도 같은 @ 문법이지만 역할은 다르다.
예상된 앱 오류는 1, argparse 사용법 오류는 2다.
```

## 7. 프로그램을 껐다 켜도 왜 남을까? — Persistence

```text
Transaction → Repository → JSON 변환 → transactions.jsonl → 프로그램 종료

다음 실행: transactions.jsonl → Repository → Transaction 복원
```

메모리 객체는 프로세스가 끝나면 사라지지만 파일은 남는다. 이를 **영속 저장**이라고 한다.
B2-1은 아래 세 파일을 기본 `data/`에 둔다.

| 파일 | 한 줄의 내용 |
|---|---|
| `transactions.jsonl` | 거래의 id, 날짜, 타입, 금액, 카테고리, memo, tags |
| `categories.jsonl` | 카테고리 name |
| `budgets.jsonl` | month, amount |

`json.loads()`는 파일 문자열을 dict로, `json.dumps()`는 dict를 저장 문자열로 바꾼다.
최초 쓰기에서만 폴더·파일을 만든다.

## 8. update / delete의 안전 저장

```text
원본 JSONL
↓
tempfile로 임시 파일 생성
↓
새 전체 내용 작성 → flush → os.fsync
↓
os.replace로 원본 교체
```

원본 파일을 바로 쓰다가 중간 실패하면 비어 있거나 깨질 수 있다. 그래서 B2-1은 임시 파일을
먼저 완성한 뒤 바꿔치기한다. `os.replace()`는 같은 파일시스템에서 성공한 교체 시 중간
파일 내용이 보이지 않게 돕는다. 이는 백업, 동시 쓰기 잠금, 모든 전원 장애 보장과는 다르다.

부분 수정에 쓰는 `UNSET`은 “옵션을 주지 않았다”는 특별한 표시(sentinel)다. `memo is
UNSET`이면 기존 값 유지, `memo=""`이면 빈 문자열로 수정된다. 빈 값도 실제 수정값이라
`None`만으로는 구별할 수 없다.

## 표준 라이브러리 빠른 참조

| Library | B2-1에서 하는 일 | 주요 파일 |
|---|---|---|
| `argparse` | CLI 명령·옵션 해석 | `cli.py` |
| `dataclasses` | Transaction 등 데이터 구조 | `models.py` |
| `datetime` | 날짜 처리 | `models.py`, `validators.py` |
| `pathlib` | 파일 경로 | `cli.py`, `repository.py` |
| `json` | JSONL 읽기·쓰기 | `repository.py` |
| `csv` | CSV import/export | `services.py` |
| `collections.deque` | 최근 N건 유지 | `services.py` |
| `tempfile`, `os` | 임시 파일·안전 교체 | `repository.py` |
| `functools.wraps` | Decorator 메타데이터 보존 | `decorators.py` |
| `re`, `typing` | 형식 검사·Type Hint | `validators.py`, 여러 module |

## 그림 자산

현재 저장소와 이전 Codex 산출물에서 실제 인포그래프 파일은 발견되지 않았다. 존재하지 않는
이미지 링크를 만들지 않았다. 필요한 목록은 [asset manifest](assets/m03/README.md)에 있다.

다음: [설계 근거·QA·동료평가용 Reference](m03-reference.md).
