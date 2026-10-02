"""진입점. Sprint 1 구현 대상."""

import sys

from ledger.cli import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
