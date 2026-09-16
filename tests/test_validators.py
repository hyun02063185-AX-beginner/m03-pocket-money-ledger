"""Sprint 2: unit tests for ledger.validators (implemented for the
first time this sprint)."""

from __future__ import annotations

import datetime
import unittest

from ledger.errors import (
    InvalidAmountError,
    InvalidDateError,
    InvalidMonthError,
    InvalidTransactionTypeError,
    ValidationError,
)
from ledger.validators import (
    validate_amount,
    validate_category_name,
    validate_date,
    validate_month,
    validate_transaction_type,
)


class ValidateDateTests(unittest.TestCase):
    def test_valid(self) -> None:
        self.assertEqual(validate_date("2026-09-16"), datetime.date(2026, 9, 16))

    def test_wrong_separator_rejected(self) -> None:
        with self.assertRaises(InvalidDateError):
            validate_date("2026/09/16")

    def test_nonexistent_calendar_date_rejected(self) -> None:
        with self.assertRaises(InvalidDateError):
            validate_date("2026-02-30")

    def test_non_string_rejected(self) -> None:
        with self.assertRaises(InvalidDateError):
            validate_date(20260916)  # type: ignore[arg-type]


class ValidateMonthTests(unittest.TestCase):
    def test_valid(self) -> None:
        self.assertEqual(validate_month("2026-09"), "2026-09")

    def test_unpadded_month_rejected(self) -> None:
        with self.assertRaises(InvalidMonthError):
            validate_month("2026-9")

    def test_month_out_of_range_rejected(self) -> None:
        with self.assertRaises(InvalidMonthError):
            validate_month("2026-13")
        with self.assertRaises(InvalidMonthError):
            validate_month("2026-00")

    def test_full_date_rejected(self) -> None:
        with self.assertRaises(InvalidMonthError):
            validate_month("2026-09-16")


class ValidateAmountTests(unittest.TestCase):
    def test_valid_int(self) -> None:
        self.assertEqual(validate_amount(1000), 1000)

    def test_valid_numeric_string(self) -> None:
        self.assertEqual(validate_amount("1000"), 1000)

    def test_zero_rejected(self) -> None:
        with self.assertRaises(InvalidAmountError):
            validate_amount(0)

    def test_negative_rejected(self) -> None:
        with self.assertRaises(InvalidAmountError):
            validate_amount(-1)

    def test_non_numeric_string_rejected(self) -> None:
        with self.assertRaises(InvalidAmountError):
            validate_amount("abc")

    def test_bool_rejected(self) -> None:
        with self.assertRaises(InvalidAmountError):
            validate_amount(True)


class ValidateTransactionTypeTests(unittest.TestCase):
    def test_income_and_expense_accepted(self) -> None:
        self.assertEqual(validate_transaction_type("income"), "income")
        self.assertEqual(validate_transaction_type("expense"), "expense")

    def test_other_values_rejected(self) -> None:
        with self.assertRaises(InvalidTransactionTypeError):
            validate_transaction_type("Income")
        with self.assertRaises(InvalidTransactionTypeError):
            validate_transaction_type("spending")


class ValidateCategoryNameTests(unittest.TestCase):
    def test_valid_name(self) -> None:
        self.assertEqual(validate_category_name("food"), "food")

    def test_strips_whitespace(self) -> None:
        self.assertEqual(validate_category_name("  food  "), "food")

    def test_empty_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            validate_category_name("   ")


if __name__ == "__main__":
    unittest.main()
