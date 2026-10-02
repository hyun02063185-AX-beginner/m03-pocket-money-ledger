"""공식 진입점: `python -m ledger <command>`.

패키지 이름이 공식적으로 제안된 `budget_app` 대신 `ledger`로 지어진
이유는 docs/m03-architecture-design.md의 2번 섹션을 참고하라.
"""

import sys

from ledger.cli import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
