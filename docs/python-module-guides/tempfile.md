# `tempfile` 안전 저장 흐름

이 문서는 거래 수정·삭제, 카테고리·예산 변경, CSV 내보내기가 기존 파일을 어떻게 안전하게
바꾸는지 설명한다.

## 1. import와 문법

```python
import tempfile

fd, tmp_name = tempfile.mkstemp(
    dir=path.parent, prefix=f"{path.name}.", suffix=".tmp"
)
```

`tempfile`은 Python 표준 모듈이다. `mkstemp()`는 고유한 임시 파일을 만들고, 열린 파일
설명자 `fd`와 그 파일명의 문자열을 돌려준다. `tmp_path = Path(tmp_name)`으로 B2-1는 경로
객체로 바꾼다.

## 2. B2-1에서 왜 필요한가

수정·삭제는 JSONL 파일 전체를 다시 써야 한다. 원본을 바로 비우고 쓰다가 오류가 나면
데이터가 반쯤만 남을 수 있다. 그래서 먼저 임시 파일에 완성본을 만들고, 다 쓴 뒤에만
원본과 교체한다.

## 3. 실제 핵심 기능

```python
# ledger/repository.py: _atomic_write_jsonl()
fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f"{path.name}.", suffix=".tmp")
tmp_path = Path(tmp_name)
try:
    with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
        ...  # 새 JSONL 전체를 임시 파일에 씀
    os.replace(tmp_path, path)
except BaseException:
    tmp_path.unlink(missing_ok=True)
    raise
```

임시 파일은 `path.parent`, 즉 대상 파일과 같은 폴더에 만든다. 이후 `os.replace()`가 같은
파일 시스템 안에서 원본을 바꾸도록 하기 위해서다.

## 4. 동작 순서

```text
기존 transactions.jsonl
↓ update()/delete()가 새 records를 준비
같은 폴더에 transactions.jsonl.XXXX.tmp 생성
↓
임시 파일에 새 전체 내용 작성·flush·fsync
↓ 성공했을 때만
os.replace(임시 파일, 원본 파일)
↓
새 transactions.jsonl
```

작성 또는 교체 전에 예외가 나면 `except`가 임시 파일을 지운다. 원본은 교체 전까지
손대지 않았으므로 그대로 남는다.

## 5. 만들어지는 객체·구조

`mkstemp()`는 `(fd, tmp_name)` 튜플을 돌려준다. `fd`는 숫자 파일 설명자이고,
`tmp_path`는 B2-1의 지역 변수에 담긴 Python `Path` 객체다. 임시 파일 내용은 최종 JSONL
또는 CSV의 후보본이다.

## 6. B2-1 코드와 연결

`ledger/repository.py`의 `_atomic_write_jsonl()`은 Transaction update/delete,
Category remove, Budget set/remove가 공유한다. `ledger/services.py`의 `export_csv()`도
같은 패턴으로 CSV를 만든다. 새 거래·카테고리 추가는 파일 끝에 한 줄을 붙이면 되므로
`_append_jsonl()`을 쓴다.

## 외워둘 5줄

```text
tempfile.mkstemp()는 고유한 임시 파일을 만든다.
전체를 다시 쓰는 작업은 원본 대신 임시 파일에서 먼저 끝낸다.
임시 파일은 대상 파일과 같은 폴더에 만든다.
성공하면 os.replace()로 한 번에 원본을 바꾼다.
실패하면 임시 파일을 지우고 원본을 보존한다.
```
