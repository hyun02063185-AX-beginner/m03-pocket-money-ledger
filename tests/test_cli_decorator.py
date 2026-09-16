"""Sprint 3: proves handle_errors is actually applied on the real CLI
path — not just unit-tested in isolation on a throwaway function."""

from __future__ import annotations

import unittest
from unittest.mock import patch

import ledger.cli as cli_module
import ledger.decorators as decorators_module
from tests.cli_support import CLITestMixin


class DecoratorApplicationTests(CLITestMixin, unittest.TestCase):
    def test_dispatch_is_wrapped_by_handle_errors(self) -> None:
        # functools.wraps() preserves __wrapped__, pointing back at the
        # undecorated function — evidence _dispatch is actually
        # decorated, not just that a decorator with this name exists
        # somewhere unused in the module.
        self.assertTrue(hasattr(cli_module._dispatch, "__wrapped__"))

    def test_real_error_path_goes_through_the_decorator(self) -> None:
        # Patch describe_error where handle_errors actually resolves it
        # from (ledger.decorators' own module globals) — not where
        # cli.py imported a copy of the name — so this only passes if
        # the live decorator body genuinely runs it.
        data_dir = self.make_data_dir()
        with patch.object(
            decorators_module, "describe_error", wraps=decorators_module.describe_error
        ) as spy:
            code, out, err = self.run_cli(["delete", "--id", "999"], data_dir=data_dir)
        self.assertEqual(code, 1)
        spy.assert_called_once()
        self.assertIn("[오류]", err)
        self.assertIn("[힌트]", err)

    def test_success_path_returns_zero_without_error_output(self) -> None:
        data_dir = self.make_data_dir()
        code, out, err = self.run_cli(["category", "list"], data_dir=data_dir)
        self.assertEqual(code, 0)
        self.assertEqual(err, "")


if __name__ == "__main__":
    unittest.main()
