# M03 Python 읽기 가이드

이 폴더는 파일 하나를 처음부터 끝까지 해설하는 문서가 아니다. M03 소스에서 만나는
`import X` 또는 Python 문법 하나를 골라, **Python이 제공한 것**과 **M03가 만든 것**을
나누고 실제 실행 흐름을 따라간다. `Transaction`, `iter_all()`, `_iter_jsonl()`은 M03가
만든 이름이고, `Path`, `Iterator`, `yield`는 Python이 제공한 기능이다.

## 추천 학습 순서

1. [`argparse`](argparse.md) — 터미널 명령을 `args` 객체로 읽는다.
2. [`pathlib.Path`](pathlib-path.md) — 파일·폴더 경로를 안전하게 다룬다.
3. [`json`](json.md) — JSONL 한 줄과 Python `dict`를 오간다.
4. [`dataclass와 Transaction`](dataclasses.md) — 거래 정보를 전용 객체로 표현한다.
5. [`Type Hint와 Iterator`](typing-iterator.md) — `-> Iterator[Transaction]`을 읽는 법이다.
6. [`Generator와 yield`](generator-yield.md) — JSONL을 한 줄씩 읽어 보내는 흐름이다.
7. [`collections.deque`](collections-deque.md) — 최근 N건만 메모리에 유지한다.
8. [`csv`](csv.md) — CSV 행, `dict`, `Transaction` 사이를 변환한다.
9. [`datetime`](datetime.md) / [`re`](re.md) — 날짜·월 입력을 검증한다.
10. [`tempfile`](tempfile.md) / [`os`](os.md) — 수정·삭제·내보내기를 안전하게 저장한다.
11. [`Decorator`](decorator.md) / [`functools.wraps`](functools-wraps.md) — 공통 오류 처리를 감싼다.

함께 읽으면 좋은 언어 기초 문서:

- [`class, object, self`](class-object-self.md) — `repo.iter_all()`의 `self`가 무엇인지.
- [`type hint`](type-hint.md) — `name: str`, `-> Budget`처럼 붙은 설명을 읽는 법.

