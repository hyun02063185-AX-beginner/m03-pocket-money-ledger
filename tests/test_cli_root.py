"""Sprint 3: CLI root/global behavior tests (--help, --data-dir, unknown command)."""

from __future__ import annotations

import unittest
from pathlib import Path

from ledger.cli import DEFAULT_DATA_DIR, build_parser, main
from tests.cli_support import CLITestMixin


class RootCLITests(CLITestMixin, unittest.TestCase):
    def test_help_exits_zero(self) -> None:
        with self.assertRaises(SystemExit) as cm:
            main(["--help"])
        self.assertEqual(cm.exception.code, 0)

    def test_subcommand_help_exits_zero(self) -> None:
        for command in [
            "add",
            "list",
            "search",
            "summary",
            "update",
            "delete",
            "budget",
            "category",
            "import",
            "export",
        ]:
            with self.subTest(command=command):
                with self.assertRaises(SystemExit) as cm:
                    main([command, "--help"])
                self.assertEqual(cm.exception.code, 0)

    def test_unknown_command_exits_two(self) -> None:
        with self.assertRaises(SystemExit) as cm:
            main(["frobnicate"])
        self.assertEqual(cm.exception.code, 2)

    def test_missing_command_exits_two(self) -> None:
        with self.assertRaises(SystemExit) as cm:
            main([])
        self.assertEqual(cm.exception.code, 2)

    def test_import_export_now_exposed(self) -> None:
        # Sprint 4: import/export are real subcommands now.
        with self.assertRaises(SystemExit) as cm:
            main(["import", "--help"])
        self.assertEqual(cm.exception.code, 0)
        with self.assertRaises(SystemExit) as cm:
            main(["export", "--help"])
        self.assertEqual(cm.exception.code, 0)

    def test_default_data_dir_is_wired(self) -> None:
        # Argparse-level only: never invoke main() without --data-dir in
        # tests, to guarantee the project's real ./data is never touched.
        args = build_parser().parse_args(["list"])
        self.assertEqual(args.data_dir, DEFAULT_DATA_DIR)
        self.assertEqual(DEFAULT_DATA_DIR, Path("data"))

    def test_custom_data_dir_is_used_and_not_created_by_reads(self) -> None:
        data_dir = self.make_data_dir()
        code, out, err = self.run_cli(["category", "list"], data_dir=data_dir)
        self.assertEqual(code, 0)
        self.assertFalse(data_dir.exists())

        code, out, err = self.run_cli(["category", "add"], inputs=["food"], data_dir=data_dir)
        self.assertEqual(code, 0)
        self.assertTrue((data_dir / "categories.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
