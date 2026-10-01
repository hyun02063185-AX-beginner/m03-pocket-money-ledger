# Decorator 문법과 M03의 오류 처리

이 문서는 M03 코드를 읽는 데 필요한 decorator의 최소 개념과 `@dataclass`,
`@handle_errors`의 차이를 설명한다.

## 1. 문법

```python
@handle_errors
def _dispatch(args: argparse.Namespace) -> None:
    ...
```

위 코드는 개념적으로 다음과 같다.

```python
def _dispatch(args):
    ...

_dispatch = handle_errors(_dispatch)
```

Decorator는 함수나 class를 받아 기능을 더한 결과로 바꾸는 문법이다. `@...`는 Python
문법이고, `handle_errors`는 M03가 만든 decorator 함수다.

## 2. M03에서 왜 필요한가

모든 CLI 명령에서 같은 `try/except LedgerError`와 오류 메시지 출력을 반복하면 코드가
흩어진다. M03는 명령을 고르는 `_dispatch()` 하나에 decorator를 붙여 공통 오류 처리를
집중한다.

## 3. 실제 `@handle_errors` 흐름

```python
# ledger/decorators.py
def handle_errors(func):
    @wraps(func)
    def wrapper(*args, **kwargs) -> int:
        try:
            func(*args, **kwargs)
        except LedgerError as exc:
            message, hint = describe_error(exc)
            print(..., file=sys.stderr)
            return 1
        return 0
    return wrapper
```

```text
main() → _dispatch(args)
↓ 실제로는 wrapper 실행
원래 _dispatch가 cmd_add/cmd_list/... 호출
↓ LedgerError 발생 시
describe_error() → 오류·힌트 출력 → 1 반환
```

`LedgerError`가 아닌 `KeyError` 같은 프로그래밍 오류는 일부러 잡지 않고 드러난다.

## 4. `@dataclass`와의 차이

```python
@dataclass
class Transaction:
    ...
```

둘 다 decorator 문법이지만 적용 대상과 목적이 다르다.

- `@dataclass`: Python 제공. class 필드에서 생성 방식 등을 만들어 준다.
- `@handle_errors`: M03 제공. CLI 함수 실행을 감싸 오류를 처리한다.
- `@wraps(func)`: Python 제공. wrapper가 원래 함수 정보를 유지하게 한다.

## 5. 만들어지는 객체·구조

`handle_errors`는 원래 함수 `func`를 감싼 새 함수 `wrapper`를 반환한다. 그래서 코드에서
`_dispatch`라는 이름으로 호출해도 wrapper가 먼저 실행된다. `wraps` 덕분에 원래 함수의
이름·문서·`__wrapped__` 연결을 유지한다.

## 6. M03 코드와 연결

`ledger/cli.py`의 `_dispatch()` 위에 `@handle_errors`가 있고,
`ledger/decorators.py`에 `handle_errors()`, `describe_error()`, `@wraps(func)`가 있다.
모델 class들의 `@dataclass`는 `ledger/models.py`에 있다.

## 외워둘 5줄

```text
@decorator는 정의한 함수·class를 decorator의 결과로 바꾼다.
@handle_errors는 M03 CLI의 공통 오류 처리 wrapper를 만든다.
wrapper는 원래 함수를 호출하고 LedgerError만 사용자 메시지로 바꾼다.
@dataclass는 class를 위한 Python 제공 decorator다.
@wraps는 wrapper가 원래 함수 정보를 유지하게 한다.
```
