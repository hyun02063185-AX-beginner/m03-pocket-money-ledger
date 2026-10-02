# `pathlib.Path` 사용 흐름

이 문서는 B2-1가 `from pathlib import Path`로 가져온 **경로 객체**가 데이터·CSV 파일을
어떻게 가리키는지만 따라간다.

## 1. import와 문법

```python
from pathlib import Path

data_dir = Path("data")
transactions_path = data_dir / "transactions.jsonl"
```

`Path`는 Python 표준 라이브러리의 경로 객체다. `/`는 여기서 나누기가 아니라 경로를
이어 붙이는 연산이다. `Path`는 Python이 제공하고, `TransactionRepository`는 B2-1가
만든 클래스다.

## 2. B2-1에서 왜 필요한가

CLI의 `--data-dir`, `import --from`, `export --out`은 모두 파일 위치를 받는다.
문자열을 직접 이어 붙이는 대신 `Path`로 표현하면 운영체제에 맞는 경로 처리를 맡길 수
있고, 파일을 여는 기능도 같은 객체에서 쓸 수 있다.

## 3. 실제 핵심 기능

```python
# ledger/repository.py
self.data_dir = Path(data_dir)
self.path = self.data_dir / self.FILENAME

if not path.exists():
    return
with path.open("r", encoding="utf-8") as f:
    ...
```

- `Path(data_dir)`: 받은 값이 이미 `Path`여도 경로 객체로 통일한다.
- `data_dir / "transactions.jsonl"`: 데이터 파일 위치를 만든다.
- `path.exists()`: 파일이 없는지 확인한다. B2-1에서는 빈 장부로 취급한다.
- `path.open(...)`: 그 경로의 파일을 연다.
- `path.parent`: 파일을 담을 폴더다. 저장 전 `path.parent.mkdir(...)`에 쓴다.
- `path.name`: 파일명만 얻는다. 임시 파일 접두사에 쓴다.

## 4. 동작 순서

```text
python -m ledger --data-dir my-data list
↓ argparse의 type=Path
Path("my-data")
↓ _build_service(data_dir)
TransactionRepository(data_dir)
↓
data_dir / "transactions.jsonl"
↓
my-data/transactions.jsonl을 exists()·open()으로 읽음
```

`argparse`의 `type=Path`도 입력 글자를 `Path` 객체로 바꾸는 Python 기능이다.

## 5. 만들어지는 객체·구조

`Path("data")`는 단순 문자열이 아니라 `exists()`, `open()`, `parent`를 가진 `Path`
객체다. Repository는 `self.path`에 그 객체를 보관한다. 파일 내용 자체는 이후
`_iter_jsonl()`이 읽는다.

## 6. B2-1 코드와 연결

- `ledger/cli.py`: 기본 데이터 폴더 `Path("data")`, CSV 옵션 `type=Path`.
- `ledger/repository.py`: 세 JSONL 파일의 위치, 읽기·쓰기 경로.
- `ledger/services.py`: `import_csv(path: Path)`, `export_csv(path: Path)`.

## 외워둘 5줄

```text
Path는 Python이 제공하는 파일·폴더 위치 객체다.
path / "file.txt"는 경로를 결합한다.
exists()는 파일 존재 여부, open()은 파일 열기다.
parent는 부모 폴더, name은 파일명이다.
B2-1의 Repository는 Path로 JSONL 파일 위치를 기억한다.
```
