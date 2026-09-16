"""Sprint 3: CLI `add` interactive flow tests."""

from __future__ import annotations

import unittest

from tests.cli_support import CLITestMixin


class AddCLITests(CLITestMixin, unittest.TestCase):
    def setUp(self) -> None:
        self.data_dir = self.make_data_dir()
        self.run_cli(["category", "add"], inputs=["food"], data_dir=self.data_dir)

    def test_valid_add_shows_created_id(self) -> None:
        code, out, err = self.run_cli(
            ["add"],
            inputs=["2026-09-16", "expense", "food", "4500", "lunch", "cafe,work"],
            data_dir=self.data_dir,
        )
        self.assertEqual(code, 0)
        self.assertIn("TX-000001", out)
        self.assertEqual(err, "")

    def test_invalid_date_then_valid_retries(self) -> None:
        code, out, err = self.run_cli(
            ["add"],
            inputs=["not-a-date", "2026-09-16", "expense", "food", "1000", "", ""],
            data_dir=self.data_dir,
        )
        self.assertEqual(code, 0)
        self.assertIn("[오류]", err)
        self.assertIn("[힌트]", err)
        self.assertIn("TX-000001", out)

    def test_invalid_amount_then_valid_retries(self) -> None:
        code, out, err = self.run_cli(
            ["add"],
            inputs=["2026-09-16", "expense", "food", "-100", "5000", "", ""],
            data_dir=self.data_dir,
        )
        self.assertEqual(code, 0)
        self.assertIn("[오류]", err)
        self.assertIn("TX-000001", out)

    def test_invalid_type_then_valid_retries(self) -> None:
        code, out, err = self.run_cli(
            ["add"],
            inputs=["2026-09-16", "spending", "expense", "food", "1000", "", ""],
            data_dir=self.data_dir,
        )
        self.assertEqual(code, 0)
        self.assertIn("[오류]", err)
        self.assertIn("TX-000001", out)

    def test_nonexistent_category_then_valid_retries(self) -> None:
        code, out, err = self.run_cli(
            ["add"],
            inputs=["2026-09-16", "expense", "nope", "food", "1000", "", ""],
            data_dir=self.data_dir,
        )
        self.assertEqual(code, 0)
        self.assertIn("[오류]", err)
        self.assertIn("TX-000001", out)

    def test_category_retries_exhausted_fails_cleanly(self) -> None:
        code, out, err = self.run_cli(
            ["add"],
            inputs=["2026-09-16", "expense", "nope1", "nope2", "nope3"],
            data_dir=self.data_dir,
        )
        self.assertEqual(code, 1)
        self.assertNotIn("Traceback", err)
        self.assertIn("[오류]", err)

    def test_optional_memo_and_tags_can_be_blank(self) -> None:
        code, out, err = self.run_cli(
            ["add"],
            inputs=["2026-09-16", "expense", "food", "1000", "", ""],
            data_dir=self.data_dir,
        )
        self.assertEqual(code, 0)
        code, out, err = self.run_cli(["list"], data_dir=self.data_dir)
        self.assertIn("TX-000001", out)

    def test_tags_are_parsed_from_comma_separated_input(self) -> None:
        self.run_cli(
            ["add"],
            inputs=["2026-09-16", "expense", "food", "1000", "", " meal, lunch ,, work "],
            data_dir=self.data_dir,
        )
        code, out, err = self.run_cli(["list"], data_dir=self.data_dir)
        self.assertIn("tags: meal,lunch,work", out)


if __name__ == "__main__":
    unittest.main()
