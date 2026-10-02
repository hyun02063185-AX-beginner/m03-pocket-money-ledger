# `functools.wraps` 사용 흐름

이 문서는 B2-1의 오류 처리 decorator가 원래 함수의 이름·문서·추적 정보를 잃지 않게 하는
`wraps`를 설명한다.

## 1. import와 문법

```python
from functools import wraps

def handle_errors(func):
    @wraps(func)
    def wrapper(*args, **kwargs) -> int:
        ...
    return wrapper
```

`wraps`는 Python 표준 라이브러리 `functools`의 decorator다. `func`의 메타데이터를
`wrapper`에 복사하도록 만든다. `handle_errors`와 `_dispatch`는 B2-1가 만든 함수다.

## 2. B2-1에서 왜 필요한가

`@handle_errors`를 붙이면 실제 호출되는 함수는 `_dispatch` 본문을 감싼 `wrapper`다.
`wraps`가 없으면 이름, docstring, `__wrapped__` 같은 정보가 `wrapper` 중심으로 바뀌어
테스트·디버깅·도구가 원래 함수를 찾기 어려워진다.

## 3. 실제 핵심 기능

```python
# ledger/decorators.py
@wraps(func)
def wrapper(*args, **kwargs) -> int:
    try:
        func(*args, **kwargs)
    except LedgerError as exc:
        ...
        return 1
    return 0
```

`@wraps(func)`는 `wrapper = wraps(func)(wrapper)`와 같은 decorator 문법이다. 이로 인해
`_dispatch.__name__` 같은 정보가 원래 `_dispatch`를 나타내고,
`_dispatch.__wrapped__`로 감싸기 전 함수를 확인할 수 있다.

## 4. 동작 순서

```text
handle_errors(_dispatch 원본 함수)
↓ wraps가 원본 정보를 wrapper에 연결
wrapper를 반환
↓
@handle_errors가 붙은 _dispatch 이름은 wrapper를 가리킴
↓ 호출 시
wrapper → 원본 func(args) → LedgerError면 메시지 출력·1 반환
```

`wraps`는 오류를 잡는 기능이 아니다. 오류를 잡는 것은 wrapper 안의 `try/except`이고,
`wraps`는 감싼 뒤에도 원래 함수 정보를 보존하는 기능이다.

## 5. 만들어지는 객체·구조

`handle_errors`는 함수 하나를 받아 새 함수 `wrapper`를 돌려준다. `wraps` 적용 뒤에도
그 새 함수에는 원본 함수의 이름·문서·`__wrapped__` 연결이 남는다.

## 6. B2-1 코드와 연결

`ledger/decorators.py`에서 `handle_errors()` 내부에 있다. `ledger/cli.py`는
`@handle_errors`를 `_dispatch()` 한 곳에만 붙여 모든 명령의 `LedgerError`를 한 방식으로
처리한다.

## 외워둘 5줄

```text
wraps는 decorator가 원래 함수의 정보를 보존하게 한다.
wrapper는 실제 호출되는 새 함수다.
func는 감싸기 전 원래 함수다.
오류 처리는 try/except가 하고, wraps는 메타데이터를 보존한다.
B2-1 테스트도 __wrapped__ 연결을 확인한다.
```
