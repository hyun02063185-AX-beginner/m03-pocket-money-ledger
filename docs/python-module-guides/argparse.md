# `argparse` 모듈 사용 흐름

이 문서는 `ledger/cli.py` 전체를 설명하지 않는다. B2-1가
`import argparse`로 가져온 기능이 **명령을 어떻게 읽고, 어떤 구조를 만들며,
어느 코드로 이어지는지**만 따라간다.

## 1. `import`와 B2-1에서의 역할

```python
# ledger/cli.py
import argparse
```

`argparse`는 터미널에 입력한 글자를 명령과 옵션으로 해석하는 Python 표준 모듈이다.
별도로 설치할 필요가 없다.

B2-1에는 `list`, `summary`, `category add` 같은 여러 명령과 `--limit`,
`--month` 같은 옵션이 있다. 프로그램은 처음에는 이들을 모두 단순한 글자로
받는다. `argparse`는 그 글자를 B2-1 코드가 꺼내 쓸 수 있는 `args` 객체로 바꾼다.

```text
python3 -m ledger list --limit 5
                     ↓
             "list", "--limit", "5"  (입력 글자)
                     ↓  argparse
             args.command = "list"
             args.limit   = 5
```

## 2. B2-1가 실제로 꺼내 쓰는 기능

### `ArgumentParser()` — CLI의 전체 틀 만들기

```python
# ledger/cli.py: build_parser()
parser = argparse.ArgumentParser(
    prog="ledger",
    description="Personal pocket money ledger (income/expense tracker).",
)
```

`parser`는 아직 사용자의 명령을 읽은 결과가 아니다. 먼저 **“ledger라는
프로그램은 어떤 명령을 받을 수 있는가?”**를 기록해 둘 설계도다. `--help`를
입력했을 때 보여 줄 기본 도움말도 이 틀을 바탕으로 만들어진다.

### `add_subparsers()` — 명령 묶음 만들기

```python
subparsers = parser.add_subparsers(dest="command", required=True)
```

`list`나 `summary`처럼 선택할 명령들을 넣을 자리를 만든다.

- `dest="command"`: 선택한 명령의 이름을 나중에 `args.command`에 저장한다.
- `required=True`: 명령을 하나도 쓰지 않으면 사용법 오류로 처리한다.

### `add_parser()` — 한 개의 명령 등록하기

```python
p_list = subparsers.add_parser("list", help="list recent transactions, newest first")
```

이 한 줄로 `list`라는 하위 명령의 규칙 상자가 생긴다. B2-1는 같은 방식으로
`add`, `search`, `summary`, `budget`, `category`, `update`, `delete`, `import`,
`export`도 등록한다. `budget`과 `category`는 그 안에 다시 하위 명령을 둔다.
예를 들어 `budget set`의 구조도 `add_subparsers()`와 `add_parser("set")`로 만든다.

### `add_argument()` — 옵션의 이름과 규칙 등록하기

```python
p_list.add_argument("--limit", type=int, default=DEFAULT_LIST_LIMIT)
```

`list` 명령에 `--limit` 옵션을 붙인다.

- `type=int`: 입력한 `"5"`를 숫자 `5`로 바꾼다.
- `default=DEFAULT_LIST_LIMIT`: `--limit`을 생략하면 기본값 `10`을 넣는다.

전역 옵션도 같은 방식이다. 다만 프로그램 전체에 적용되는 `--data-dir`은
명령보다 앞에서 읽어야 하므로 최상위 `parser`에 등록되어 있다.

```python
parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
```

### `parse_args()` — 지금 입력한 명령을 실제로 해석하기

```python
# ledger/cli.py: main()
parser = build_parser()
args = parser.parse_args(argv)
return _dispatch(args)
```

`build_parser()`가 설계도를 만들었다면, `parse_args(argv)`는 **이번 실행의 실제
입력**을 그 설계도에 맞춰 읽는다. 해석한 결과인 `args`를 `_dispatch()`로 넘긴다.

## 3. 실제 명령을 따라가기

```bash
python3 -m ledger list --limit 5
```

```text
ledger/__main__.py
↓  main(sys.argv[1:])
ledger/cli.py: main(["list", "--limit", "5"])
↓  build_parser()
ArgumentParser()                    CLI 전체 틀
↓
add_subparsers(dest="command")      명령을 넣을 자리
↓
add_parser("list")                  list 명령의 규칙 상자
↓
add_argument("--limit", type=int)  --limit 값은 정수라고 등록
↓
parse_args(["list", "--limit", "5"])
↓
args.command == "list"
args.limit == 5
↓
_dispatch(args)
↓
cmd_list(args, service)
↓
service.list_transactions(args.limit)
```

`_dispatch()`는 `args.command`를 보고 어느 명령 함수를 부를지 고른다.
이번 경우에는 `cmd_list()`가 선택되고, `args.limit`의 숫자 `5`가 서비스로
전달된다.

## 4. 결국 만들어지는 CLI 구조

`build_parser()`에 등록한 내용이 다음과 같은 사용자용 명령 구조가 된다.

```text
ledger [--data-dir 폴더] <명령> [그 명령의 옵션]
                         ├── add
                         ├── list [--limit 정수]
                         ├── search [--from 날짜] [--to 날짜] ...
                         ├── summary --month YYYY-MM [--top 정수]
                         ├── budget set --month YYYY-MM --amount 정수
                         ├── category {list, add, remove}
                         ├── update --id 정수 [바꿀 옵션]
                         ├── delete --id 정수
                         ├── import --from CSV파일
                         └── export --out CSV파일 [기간 옵션]
```

이 구조는 문서가 따로 만드는 것이 아니다. `cli.py`의 `add_subparsers()`,
`add_parser()`, `add_argument()` 호출들이 실행될 때 만들어지고,
`parse_args()`가 실제 입력과 비교해 사용한다.

## 5. B2-1 코드에서 기억할 연결점

```python
def cmd_list(args: argparse.Namespace, service: LedgerService) -> None:
    transactions = service.list_transactions(args.limit)
```

`argparse.Namespace`는 `parse_args()`가 돌려준 `args`의 데이터 모양을 나타낸다.
여기서는 `args.limit`을 꺼내 사용한다. `argparse`는 터미널 글자를 정수로 바꾸고
명령을 고르는 데까지 담당한다. 실제 거래 목록을 읽는 일은
`LedgerService.list_transactions()`와 Repository가 담당한다.

## 외워둘 5줄

```text
ArgumentParser() = CLI 전체 설계도를 만든다.
add_subparsers() = list, summary 같은 명령을 넣을 자리를 만든다.
add_parser() = 명령 하나의 규칙 상자를 만든다.
add_argument() = --limit 같은 옵션의 이름·기본값·형식을 등록한다.
parse_args() = 실제 입력을 args.command, args.limit 같은 값으로 바꾼다.
```
