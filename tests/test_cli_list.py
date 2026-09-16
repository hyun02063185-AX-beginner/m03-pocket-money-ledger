"""Sprint 3: CLI `list` command tests."""

from __future__ import annotations

import unittest

from tests.cli_support import CLITestMixin


class ListCLITests(CLITestMixin, unittest.TestCase):
    def setUp(self) -> None:
        self.data_dir = self.make_data_dir()
        self.run_cli(["category", "add"], inputs=["food"], data_dir=self.data_dir)

    def _add(self, amount: str) -> None:
        self.run_cli(
            ["add"],
            inputs=["2026-09-01", "expense", "food", amount, "", ""],
            data_dir=self.data_dir,
        )

    def test_empty(self) -> None:
        code, out, err = self.run_cli(["list"], data_dir=self.data_dir)
        self.assertEqual(code, 0)
        self.assertIn("[안내]", out)

    def test_default_limit(self) -> None:
        for i in range(1, 15):
            self._add(str(i * 100))
        code, out, err = self.run_cli(["list"], data_dir=self.data_dir)
        self.assertEqual(code, 0)
        self.assertEqual(out.count("TX-"), 10)  # DEFAULT_LIST_LIMIT

    def test_explicit_limit(self) -> None:
        for i in range(1, 6):
            self._add(str(i * 100))
        code, out, err = self.run_cli(["list", "--limit", "2"], data_dir=self.data_dir)
        self.assertEqual(code, 0)
        self.assertEqual(out.count("TX-"), 2)

    def test_newest_first(self) -> None:
        self._add("100")
        self._add("200")
        code, out, err = self.run_cli(["list"], data_dir=self.data_dir)
        self.assertLess(out.index("TX-000002"), out.index("TX-000001"))


if __name__ == "__main__":
    unittest.main()
