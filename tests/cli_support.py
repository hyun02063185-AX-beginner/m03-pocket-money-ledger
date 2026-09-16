"""Shared test helpers for Sprint 3 CLI tests.

Not named test_*.py on purpose so unittest discovery skips it.
"""

from __future__ import annotations

import io
import tempfile
from pathlib import Path
from unittest.mock import patch

from ledger.cli import main


class CLITestMixin:
    """Mixin (combine with unittest.TestCase). Drives ledger.cli.main()
    in-process (no subprocess) against a tempdir-backed --data-dir,
    capturing stdout/stderr and simulating input() for interactive
    commands — never touches the project's real ./data."""

    def make_data_dir(self) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)  # type: ignore[attr-defined]
        return Path(tmp.name) / "data"

    def run_cli(
        self,
        argv: list[str],
        inputs: list[str] | None = None,
        data_dir: Path | None = None,
    ) -> tuple[int, str, str]:
        if data_dir is None:
            data_dir = self.make_data_dir()
        full_argv = ["--data-dir", str(data_dir), *argv]
        buf_out, buf_err = io.StringIO(), io.StringIO()
        with patch("sys.stdout", buf_out), patch("sys.stderr", buf_err):
            if inputs is not None:
                with patch("builtins.input", side_effect=inputs):
                    code = main(full_argv)
            else:
                code = main(full_argv)
        return code, buf_out.getvalue(), buf_err.getvalue()
