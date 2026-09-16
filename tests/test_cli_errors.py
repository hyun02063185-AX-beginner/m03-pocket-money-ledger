"""Sprint 3: CLI error-handling/exit-code tests — no raw traceback for
expected errors, application errors -> exit 1, argparse misuse -> exit 2."""

from __future__ import annotations

import unittest

from tests.cli_support import CLITestMixin


class CLIErrorHandlingTests(CLITestMixin, unittest.TestCase):
    def setUp(self) -> None:
        self.data_dir = self.make_data_dir()
        self.run_cli(["category", "add"], inputs=["food"], data_dir=self.data_dir)

    def _assert_no_traceback(self, err: str) -> None:
        self.assertNotIn("Traceback", err)

    def test_invalid_date_no_traceback(self) -> None:
        code, out, err = self.run_cli(
            ["update", "--id", "999", "--date", "not-a-date"], data_dir=self.data_dir
        )
        self.assertEqual(code, 1)
        self._assert_no_traceback(err)

    def test_invalid_amount_no_traceback(self) -> None:
        code, out, err = self.run_cli(
            ["budget", "set", "--month", "2026-09", "--amount", "-1"], data_dir=self.data_dir
        )
        self.assertEqual(code, 1)
        self._assert_no_traceback(err)

    def test_invalid_type_no_traceback(self) -> None:
        code, out, err = self.run_cli(["search", "--type", "spending"], data_dir=self.data_dir)
        self.assertEqual(code, 1)
        self._assert_no_traceback(err)

    def test_unknown_category_retries_exhausted_no_traceback(self) -> None:
        code, out, err = self.run_cli(
            ["add"],
            inputs=["2026-09-01", "expense", "nope1", "nope2", "nope3"],
            data_dir=self.data_dir,
        )
        self.assertEqual(code, 1)
        self._assert_no_traceback(err)

    def test_missing_transaction_no_traceback(self) -> None:
        code, out, err = self.run_cli(["delete", "--id", "42"], data_dir=self.data_dir)
        self.assertEqual(code, 1)
        self._assert_no_traceback(err)

    def test_remove_used_category_no_traceback(self) -> None:
        self.run_cli(
            ["add"], inputs=["2026-09-01", "expense", "food", "1000", "", ""], data_dir=self.data_dir
        )
        code, out, err = self.run_cli(
            ["category", "remove"], inputs=["food"], data_dir=self.data_dir
        )
        self.assertEqual(code, 1)
        self._assert_no_traceback(err)

    def test_update_only_id_no_traceback(self) -> None:
        self.run_cli(
            ["add"], inputs=["2026-09-01", "expense", "food", "1000", "", ""], data_dir=self.data_dir
        )
        code, out, err = self.run_cli(["update", "--id", "1"], data_dir=self.data_dir)
        self.assertEqual(code, 1)
        self._assert_no_traceback(err)

    def test_application_errors_return_one(self) -> None:
        code, out, err = self.run_cli(["delete", "--id", "999"], data_dir=self.data_dir)
        self.assertEqual(code, 1)

    def test_argparse_misuse_returns_two(self) -> None:
        with self.assertRaises(SystemExit) as cm:
            self.run_cli(["update"], data_dir=self.data_dir)  # missing required --id
        self.assertEqual(cm.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
