"""Sprint 3: CLI `search` command tests."""

from __future__ import annotations

import unittest

from tests.cli_support import CLITestMixin


class SearchCLITests(CLITestMixin, unittest.TestCase):
    def setUp(self) -> None:
        self.data_dir = self.make_data_dir()
        self.run_cli(["category", "add"], inputs=["food"], data_dir=self.data_dir)
        self.run_cli(["category", "add"], inputs=["transport"], data_dir=self.data_dir)
        self.run_cli(
            ["add"],
            inputs=["2026-09-01", "expense", "food", "1000", "lunch", "work"],
            data_dir=self.data_dir,
        )
        self.run_cli(
            ["add"],
            inputs=["2026-09-10", "income", "transport", "50000", "salary", ""],
            data_dir=self.data_dir,
        )

    def test_category_filter(self) -> None:
        code, out, err = self.run_cli(["search", "--category", "food"], data_dir=self.data_dir)
        self.assertEqual(code, 0)
        self.assertIn("TX-000001", out)
        self.assertNotIn("TX-000002", out)

    def test_type_filter(self) -> None:
        code, out, err = self.run_cli(["search", "--type", "income"], data_dir=self.data_dir)
        self.assertIn("TX-000002", out)
        self.assertNotIn("TX-000001", out)

    def test_from_to_filters(self) -> None:
        code, out, err = self.run_cli(
            ["search", "--from", "2026-09-05", "--to", "2026-09-30"], data_dir=self.data_dir
        )
        self.assertIn("TX-000002", out)
        self.assertNotIn("TX-000001", out)

    def test_query_filter_is_case_insensitive(self) -> None:
        code, out, err = self.run_cli(["search", "--q", "LUNCH"], data_dir=self.data_dir)
        self.assertIn("TX-000001", out)

    def test_tag_filter(self) -> None:
        code, out, err = self.run_cli(["search", "--tag", "work"], data_dir=self.data_dir)
        self.assertIn("TX-000001", out)
        self.assertNotIn("TX-000002", out)

    def test_combined_filters(self) -> None:
        code, out, err = self.run_cli(
            ["search", "--category", "food", "--type", "expense"], data_dir=self.data_dir
        )
        self.assertIn("TX-000001", out)

    def test_no_filters_returns_all(self) -> None:
        code, out, err = self.run_cli(["search"], data_dir=self.data_dir)
        self.assertIn("TX-000001", out)
        self.assertIn("TX-000002", out)

    def test_no_results(self) -> None:
        code, out, err = self.run_cli(
            ["search", "--category", "nonexistent"], data_dir=self.data_dir
        )
        self.assertEqual(code, 0)
        self.assertIn("[안내]", out)


if __name__ == "__main__":
    unittest.main()
