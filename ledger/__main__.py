"""Canonical entry point: `python -m ledger <command>`.

See docs/m03-architecture-design.md section 2 for why the package is
named `ledger` rather than the officially-suggested `budget_app`.
"""

import sys

from ledger.cli import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
