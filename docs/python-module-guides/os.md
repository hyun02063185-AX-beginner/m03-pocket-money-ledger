# `os` 안전한 파일 쓰기 흐름

이 문서는 B2-1가 파일에 쓴 데이터가 운영체제 버퍼에만 남지 않게 하고, 완성된 임시 파일을
원본으로 교체하는 Python `os` 기능을 설명한다.

## 1. import와 문법

```python
import os

os.fsync(f.fileno())
os.replace(tmp_path, path)
```

`os`는 운영체제 기능을 Python에서 쓰게 하는 표준 모듈이다. 여기서 중요한 것은
`fsync`, `replace`, `fdopen` 세 가지다.

## 2. B2-1에서 왜 필요한가

`write()`가 끝났다고 즉시 디스크에 모두 기록됐다는 뜻은 아니다. 또 수정·삭제에서
원본을 직접 덮어쓰면 중간 실패가 위험하다. B2-1는 먼저 기록을 밀어 넣고, 완성된 파일만
교체하는 흐름을 쓴다.

## 3. 실제 핵심 기능

```python
# 한 줄 추가 후
f.flush()
os.fsync(f.fileno())

# 임시 파일의 fd를 일반 파일 객체로 열기
with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
    ...
    f.flush()
    os.fsync(f.fileno())

os.replace(tmp_path, path)
```

- `f.fileno()`: 파일 객체에서 운영체제 파일 설명자 번호를 얻는다.
- `os.fsync(...)`: 버퍼의 변경 내용을 디스크에 기록하도록 요청한다.
- `os.fdopen(fd, ...)`: `tempfile.mkstemp()`가 준 파일 설명자를 파일 객체로 감싼다.
- `os.replace(source, target)`: 대상이 있어도 source로 교체한다.

## 4. 동작 순서

```text
JSON/CSV 내용을 파일 객체 f에 write()
↓
flush()  : Python 쪽 버퍼를 운영체제에 보냄
↓
fsync()  : 운영체제에 실제 기록을 요청
↓
replace(): 완성된 임시 파일을 원본 경로로 교체
```

새 JSONL 한 줄을 덧붙이는 `_append_jsonl()`도 `flush()`와 `fsync()`를 쓴다. 전체 교체는
`_atomic_write_jsonl()`과 `export_csv()`가 `replace()`를 쓴다.

## 5. 만들어지는 객체·구조

`os` 자체가 장부 객체를 만들지는 않는다. `fdopen()`은 숫자 `fd`를 `write()`, `flush()`가
가능한 파일 객체 `f`로 바꾼다. `replace()` 뒤에는 `path`가 새 파일 내용을 가리킨다.

## 6. B2-1 코드와 연결

`ledger/repository.py`의 `_append_jsonl()`과 `_atomic_write_jsonl()`에 쓰인다.
`ledger/services.py`의 `export_csv()`도 임시 CSV를 쓴 뒤 `os.replace()`로 출력 파일을
교체한다.

## 외워둘 5줄

```text
os는 운영체제 기능을 쓰는 Python 표준 모듈이다.
flush() 뒤 fsync()는 기록 내용을 디스크에 밀어 넣는 흐름이다.
fdopen()은 숫자 파일 설명자를 파일 객체로 바꾼다.
replace()는 기존 파일이 있어도 새 파일로 교체한다.
B2-1는 tempfile + os.replace()로 안전한 전체 재저장을 한다.
```
