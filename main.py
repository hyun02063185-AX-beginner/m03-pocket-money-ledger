"""Entry point. Sprint 1 implementation target."""

import sys

from ledger.cli import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
