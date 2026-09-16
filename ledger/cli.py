"""argparse + interactive CLI — the real Sprint 3 implementation.

Translates argv/interactive input() <-> LedgerService calls, and
formats output (including id -> "TX-000012" display, section 8). No
business logic lives here — every validation and calculation call
goes through ledger.validators or LedgerService; this module only
decides *when* to call them and how to show the result or error
(docs/m03-architecture-design.md section 43). The one narrow exception
is `update`'s "at least one field supplied" check (section 15/28):
that is post-parse argument-shape validation, not a business rule.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ledger.decorators import describe_error, handle_errors
from ledger.errors import CategoryNotFoundError, LedgerError, ValidationError
from ledger.models import SearchCriteria, Transaction
from ledger.repository import BudgetRepository, CategoryRepository, TransactionRepository
from ledger.services import LedgerService
from ledger.validators import (
    parse_tags,
    validate_amount,
    validate_date,
    validate_transaction_type,
)

DEFAULT_DATA_DIR = Path("data")
DEFAULT_LIST_LIMIT = 10
DEFAULT_SUMMARY_TOP = 3
_PROMPT_ATTEMPTS = 3


# -- argument parsing --------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ledger",
        description="Personal pocket money ledger (income/expense tracker).",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help=f"persistent data directory (default: {DEFAULT_DATA_DIR})",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # add: no options besides --help — primarily interactive (section 9).
    subparsers.add_parser("add", help="add a transaction via interactive prompts")

    p_list = subparsers.add_parser("list", help="list recent transactions, newest first")
    p_list.add_argument("--limit", type=int, default=DEFAULT_LIST_LIMIT)

    p_search = subparsers.add_parser("search", help="search transactions")
    p_search.add_argument("--from", dest="from_date")
    p_search.add_argument("--to", dest="to_date")
    p_search.add_argument("--category")
    p_search.add_argument("--type", dest="transaction_type")
    p_search.add_argument("--q", dest="query")
    p_search.add_argument("--tag")

    p_summary = subparsers.add_parser("summary", help="monthly summary with budget status")
    p_summary.add_argument("--month", required=True)
    p_summary.add_argument("--top", type=int, default=DEFAULT_SUMMARY_TOP)

    p_budget = subparsers.add_parser("budget", help="manage the monthly total budget")
    budget_sub = p_budget.add_subparsers(dest="budget_command", required=True)
    p_budget_set = budget_sub.add_parser("set", help="set this month's total budget")
    p_budget_set.add_argument("--month", required=True)
    p_budget_set.add_argument("--amount", type=int, required=True)

    p_category = subparsers.add_parser("category", help="manage categories")
    category_sub = p_category.add_subparsers(dest="category_command", required=True)
    category_sub.add_parser("list", help="list registered categories")
    category_sub.add_parser("add", help="register a new category (prompts for the name)")
    category_sub.add_parser("remove", help="remove a category (prompts for the name)")

    p_update = subparsers.add_parser("update", help="update fields of an existing transaction")
    p_update.add_argument("--id", type=int, required=True)
    p_update.add_argument("--date")
    p_update.add_argument("--type", dest="transaction_type")
    p_update.add_argument("--category")
    p_update.add_argument("--amount", type=int)
    p_update.add_argument("--memo")
    p_update.add_argument("--tags")

    p_delete = subparsers.add_parser("delete", help="delete a transaction")
    p_delete.add_argument("--id", type=int, required=True)

    p_import = subparsers.add_parser("import", help="import transactions from a CSV file")
    # "from" is a Python keyword, so it can't be the attribute name
    # argparse would otherwise infer from "--from" — dest="source" sidesteps that.
    p_import.add_argument("--from", dest="source", type=Path, required=True)

    p_export = subparsers.add_parser("export", help="export transactions to a CSV file")
    p_export.add_argument("--out", type=Path, required=True)
    p_export.add_argument("--month")
    p_export.add_argument("--from", dest="from_date")
    p_export.add_argument("--to", dest="to_date")

    return parser


# -- small formatting/parsing helpers, shared by add/update -------------------------


def format_transaction_id(transaction_id: int) -> str:
    """Display-only formatting — never stored, never passed back into
    LedgerService/repository code (docs/m03-architecture-design.md
    section 10)."""
    return f"TX-{transaction_id:06d}"


def format_transaction_line(transaction: Transaction) -> str:
    line = (
        f"{format_transaction_id(transaction.id)} | {transaction.date.isoformat()} | "
        f"{transaction.type} | {transaction.category} | {transaction.amount} | {transaction.memo}"
    )
    if transaction.tags:
        line += f" | tags: {','.join(transaction.tags)}"
    return line


def _print_error(exc: LedgerError) -> None:
    message, hint = describe_error(exc)
    print(f"[오류] {message}", file=sys.stderr)
    print(f"[힌트] {hint}", file=sys.stderr)


# -- interactive prompts (used by `add`) ---------------------------------------------


def _prompt_date(attempts: int = _PROMPT_ATTEMPTS) -> str:
    for _ in range(attempts):
        raw = input("날짜 (YYYY-MM-DD): ").strip()
        try:
            validate_date(raw)
        except LedgerError as exc:
            _print_error(exc)
            continue
        return raw
    raise ValidationError("날짜를 여러 번 잘못 입력하여 등록을 중단합니다.")


def _prompt_type(attempts: int = _PROMPT_ATTEMPTS) -> str:
    for _ in range(attempts):
        raw = input("타입 (income/expense): ").strip()
        try:
            return validate_transaction_type(raw)
        except LedgerError as exc:
            _print_error(exc)
    raise ValidationError("타입을 여러 번 잘못 입력하여 등록을 중단합니다.")


def _prompt_amount(attempts: int = _PROMPT_ATTEMPTS) -> int:
    for _ in range(attempts):
        raw = input("금액: ").strip()
        try:
            return validate_amount(raw)
        except LedgerError as exc:
            _print_error(exc)
    raise ValidationError("금액을 여러 번 잘못 입력하여 등록을 중단합니다.")


def _prompt_category(service: LedgerService, attempts: int = _PROMPT_ATTEMPTS) -> str:
    for _ in range(attempts):
        raw = input("카테고리: ").strip()
        if service.categories.exists(raw):
            return raw
        _print_error(CategoryNotFoundError(f"category {raw!r} not found"))
    raise CategoryNotFoundError("카테고리를 여러 번 잘못 입력하여 등록을 중단합니다.")


def _prompt_memo() -> str:
    return input("메모 (선택, Enter로 건너뛰기): ").strip()


def _prompt_tags() -> list[str]:
    return parse_tags(input("태그 (쉼표로 구분, 선택): "))


# -- command handlers ------------------------------------------------------------------


def cmd_add(args: argparse.Namespace, service: LedgerService) -> None:
    date = _prompt_date()
    type_ = _prompt_type()
    category = _prompt_category(service)
    amount = _prompt_amount()
    memo = _prompt_memo()
    tags = _prompt_tags()
    transaction = service.add_transaction(type_, date, category, amount, memo, tags)
    print(f"[저장 완료] id={format_transaction_id(transaction.id)}")


def cmd_list(args: argparse.Namespace, service: LedgerService) -> None:
    transactions = service.list_transactions(args.limit)
    if not transactions:
        print("[안내] 거래 내역이 없습니다.")
        return
    for transaction in transactions:
        print(format_transaction_line(transaction))


def cmd_search(args: argparse.Namespace, service: LedgerService) -> None:
    criteria = SearchCriteria(
        from_date=validate_date(args.from_date) if args.from_date else None,
        to_date=validate_date(args.to_date) if args.to_date else None,
        transaction_type=validate_transaction_type(args.transaction_type)
        if args.transaction_type
        else None,
        category=args.category,
        query=args.query,
        tag=args.tag,
    )
    results = service.search(criteria)
    if not results:
        print("[안내] 조건에 맞는 거래가 없습니다.")
        return
    for transaction in results:
        print(format_transaction_line(transaction))


def cmd_summary(args: argparse.Namespace, service: LedgerService) -> None:
    summary = service.monthly_summary(args.month, args.top)
    print(f"[{summary.month} 요약]")
    if not summary.has_transactions:
        print("데이터 없음")
        return
    print(f"총 수입: {summary.total_income}")
    print(f"총 지출: {summary.total_expense}")
    print(f"잔액: {summary.balance}")
    if summary.top_categories:
        print(f"카테고리별 지출 TOP {args.top}:")
        for category, amount in summary.top_categories:
            print(f"  {category}: {amount}")
    if summary.budget_amount is not None:
        print(f"예산: {summary.budget_amount}")
        print(f"사용률: {summary.budget_usage_percent:.1f}%")
        if summary.budget_exceeded:
            over = summary.total_expense - summary.budget_amount
            print(f"[경고] 이번 달 예산을 {over}원 초과했습니다.")
        else:
            print("예산 초과: 아니오")


def cmd_budget_set(args: argparse.Namespace, service: LedgerService) -> None:
    budget = service.set_budget(args.month, args.amount)
    print(f"[저장 완료] {budget.month} 예산 {budget.amount}원")


def cmd_category_add(args: argparse.Namespace, service: LedgerService) -> None:
    name = input("카테고리명: ").strip()
    service.add_category(name)
    print(f"[저장 완료] 카테고리 '{name}' 등록")


def cmd_category_list(args: argparse.Namespace, service: LedgerService) -> None:
    categories = service.list_categories()
    if not categories:
        print("[안내] 등록된 카테고리가 없습니다.")
        return
    for category in categories:
        print(category)


def cmd_category_remove(args: argparse.Namespace, service: LedgerService) -> None:
    name = input("삭제할 카테고리명: ").strip()
    service.remove_category(name)
    print(f"[삭제 완료] 카테고리 '{name}' 삭제")


def cmd_update(args: argparse.Namespace, service: LedgerService) -> None:
    supplied = {
        key: value
        for key, value in {
            "date": args.date,
            "transaction_type": args.transaction_type,
            "category": args.category,
            "amount": args.amount,
            "memo": args.memo,
            "tags": args.tags,
        }.items()
        if value is not None
    }
    if not supplied:
        raise ValidationError("변경할 필드를 최소 1개 이상 지정해야 합니다 (--date/--type/--category/--amount/--memo/--tags).")
    if "tags" in supplied:
        supplied["tags"] = parse_tags(supplied["tags"])
    updated = service.update_transaction(args.id, **supplied)
    print(f"[수정 완료] id={format_transaction_id(updated.id)}")


def cmd_delete(args: argparse.Namespace, service: LedgerService) -> None:
    service.delete_transaction(args.id)
    print(f"[삭제 완료] id={format_transaction_id(args.id)}")


def cmd_import(args: argparse.Namespace, service: LedgerService) -> None:
    result = service.import_csv(args.source)
    for row_number, exc in result.errors:
        message, hint = describe_error(exc)
        print(f"[건너뜀] row={row_number}: {message}")
    print(f"[완료] imported={result.imported}, skipped={result.skipped}")


def cmd_export(args: argparse.Namespace, service: LedgerService) -> None:
    count = service.export_csv(
        args.out, month=args.month, from_date=args.from_date, to_date=args.to_date
    )
    print(f"[완료] {args.out} ({count} records)")


# -- composition + dispatch --------------------------------------------------------------


def _build_service(data_dir: Path) -> LedgerService:
    return LedgerService(
        TransactionRepository(data_dir),
        CategoryRepository(data_dir),
        BudgetRepository(data_dir),
    )


@handle_errors
def _dispatch(args: argparse.Namespace) -> None:
    """The single point handle_errors is applied to — every command
    handler's LedgerError propagates up to here uncaught, gets turned
    into "[오류]/[힌트]" + exit code 1 in one place, instead of each
    handler repeating its own try/except (docs/m03-architecture-design.md
    section 41)."""
    service = _build_service(args.data_dir)
    if args.command == "add":
        cmd_add(args, service)
    elif args.command == "list":
        cmd_list(args, service)
    elif args.command == "search":
        cmd_search(args, service)
    elif args.command == "summary":
        cmd_summary(args, service)
    elif args.command == "budget":
        if args.budget_command == "set":
            cmd_budget_set(args, service)
    elif args.command == "category":
        if args.category_command == "add":
            cmd_category_add(args, service)
        elif args.category_command == "list":
            cmd_category_list(args, service)
        elif args.category_command == "remove":
            cmd_category_remove(args, service)
    elif args.command == "update":
        cmd_update(args, service)
    elif args.command == "delete":
        cmd_delete(args, service)
    elif args.command == "import":
        cmd_import(args, service)
    elif args.command == "export":
        cmd_export(args, service)


def main(argv: list[str] | None = None) -> int:
    """Returns an exit code (0 success, 1 application error) rather
    than calling sys.exit() itself, so it stays directly testable:
    `main([...])` can be called in-process and its return value
    asserted on. argparse's own usage-error/--help paths still raise
    SystemExit(2)/SystemExit(0) as normal — main() does not intercept
    those (docs/m03-architecture-design.md section 45)."""
    parser = build_parser()
    args = parser.parse_args(argv)
    return _dispatch(args)
