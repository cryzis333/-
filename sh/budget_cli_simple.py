#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import sys
import locale
from datetime import datetime
from family_budget_db import FamilyBudgetDB, TransactionType

if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())

def format_currency(amount):
    return f"{amount:,.2f} ₽"

def print_monthly_summary(summary):
    print(f"\n=== Сводка за {summary['month']:02d}.{summary['year']} ===")
    print(f"Доходы: {format_currency(summary['income'])}")
    print(f"Расходы: {format_currency(summary['expenses'])}")
    print(f"Баланс: {format_currency(summary['balance'])}")
    
    if summary.get('category_breakdown'):
        print("\nРасходы по категориям:")
        for category, amount in summary['category_breakdown'].items():
            print(f"  {category}: {format_currency(amount)}")

def print_statistics(stats):
    print_monthly_summary(stats)
    
    print(f"\n=== ДОПОЛНИТЕЛЬНАЯ СТАТИСТИКА ===")
    print(f"Средний доход: {format_currency(stats['average_income'])}")
    print(f"Средний расход: {format_currency(stats['average_expense'])}")
    print(f"Всего транзакций: {stats['transaction_count']['total']}")
    print(f"  Доходов: {stats['transaction_count']['income']}")
    print(f"  Расходов: {stats['transaction_count']['expenses']}")
    print(f"Дней в месяце: {stats['days_in_month']}")

def print_budget_alerts(alerts):
    if alerts:
        print("\n⚠️  ПРЕДУПРЕЖДЕНИЯ О БЮДЖЕТЕ:")
        for alert in alerts:
            print(f"  Категория '{alert['category']}':")
            print(f"    Лимит: {format_currency(alert['limit'])}")
            print(f"    Потрачено: {format_currency(alert['spent'])}")
            print(f"    Превышение: {format_currency(alert['over_limit'])}")
    else:
        print("\n✅ Превышений бюджета нет")

def add_income_command(args):
    budget = FamilyBudgetDB(args.file)
    transaction_id = budget.add_transaction(amount=args.amount, category=args.category, 
                                          description=args.description, date=args.date, 
                                          transaction_type=TransactionType.INCOME)
    print(f"✅ Доход добавлен. ID: {transaction_id}")

def add_expense_command(args):
    budget = FamilyBudgetDB(args.file)
    transaction_id = budget.add_transaction(amount=args.amount, category=args.category, 
                                          description=args.description, date=args.date, 
                                          transaction_type=TransactionType.EXPENSE)
    print(f"✅ Расход добавлен. ID: {transaction_id}")

def balance_command(args):
    budget = FamilyBudgetDB(args.file)
    balance = budget.get_balance()
    print(f"\nТекущий баланс: {format_currency(balance)}")

def summary_command(args):
    budget = FamilyBudgetDB(args.file)
    summary = budget.get_monthly_summary(args.year, args.month)
    print_monthly_summary(summary)

def statistics_command(args):
    budget = FamilyBudgetDB(args.file)
    stats = budget.get_statistics(args.year, args.month)
    print_statistics(stats)

def categories_command(args):
    budget = FamilyBudgetDB(args.file)
    
    print("\n=== КАТЕГОРИИ ДОХОДОВ ===")
    income_categories = budget.get_categories_by_type(TransactionType.INCOME)
    for cat in income_categories:
        print(f"  {cat}")
    
    print("\n=== КАТЕГОРИИ РАСХОДОВ ===")
    all_categories = budget.get_all_categories()
    for cat in all_categories:
        if cat.type == TransactionType.EXPENSE:
            limit_str = f" (лимит: {format_currency(cat.budget_limit)})" if cat.budget_limit else ""
            print(f"  {cat.name}{limit_str}")

def alerts_command(args):
    budget = FamilyBudgetDB(args.file)
    alerts = budget.check_budget_limits(args.year, args.month)
    print_budget_alerts(alerts)

def transactions_command(args):
    budget = FamilyBudgetDB(args.file)
    
    if args.start_date and args.end_date:
        transactions = budget.get_transactions_by_date_range(args.start_date, args.end_date)
        print(f"\n=== Транзакции за период {args.start_date} - {args.end_date} ===")
    elif args.category:
        transactions = budget.get_transactions_by_category(args.category, args.limit)
        print(f"\n=== Транзакции по категории '{args.category}' ===")
    elif args.type:
        trans_type = TransactionType.INCOME if args.type == 'income' else TransactionType.EXPENSE
        transactions = budget.get_transactions_by_type(trans_type, args.limit)
        print(f"\n=== {'Доходы' if args.type == 'income' else 'Расходы'} ===")
    elif args.search:
        transactions = budget.search_transactions(args.search, args.limit)
        print(f"\n=== Результаты поиска по '{args.search}' ===")
    else:
        transactions = budget.get_all_transactions(args.limit)
        print("\n=== ВСЕ ТРАНЗАКЦИИ ===")
    
    transactions.sort(key=lambda x: x.date, reverse=True)
    
    for t in transactions:
        type_symbol = "➕" if t.type == TransactionType.INCOME else "➖"
        print(f"{type_symbol} {t.date} | {t.category} | {format_currency(t.amount)} | {t.description}")

def add_category_command(args):
    budget = FamilyBudgetDB(args.file)
    transaction_type = TransactionType.INCOME if args.type == 'income' else TransactionType.EXPENSE
    budget.add_category(args.name, transaction_type, args.limit)
    print(f"✅ Категория '{args.name}' добавлена")

def delete_transaction_command(args):
    budget = FamilyBudgetDB(args.file)
    if budget.delete_transaction(args.id):
        print(f"✅ Транзакция {args.id} удалена")
    else:
        print(f"❌ Транзакция {args.id} не найдена")

def migrate_command(args):
    budget = FamilyBudgetDB(args.file)
    if budget.migrate_from_json(args.json_file):
        print(f"✅ Данные мигрированы из {args.json_file}")
    else:
        print(f"❌ Ошибка миграции из {args.json_file}")

def export_command(args):
    budget = FamilyBudgetDB(args.file)
    if budget.export_to_json(args.json_file):
        print(f"✅ Данные экспортированы в {args.json_file}")
    else:
        print(f"❌ Ошибка экспорта в {args.json_file}")

def backup_command(args):
    budget = FamilyBudgetDB(args.file)
    if budget.backup_database(args.backup_file):
        print(f"✅ Резервная копия создана: {args.backup_file}")
    else:
        print(f"❌ Ошибка создания резервной копии")

def main():
    parser = argparse.ArgumentParser(description="Управление семейным бюджетом")
    parser.add_argument('--file', default='family_budget.db', help='Файл базы данных')
    
    subparsers = parser.add_subparsers(dest='command', help='Команды')
    
    income_parser = subparsers.add_parser('income', help='Добавить доход')
    income_parser.add_argument('amount', type=float, help='Сумма')
    income_parser.add_argument('category', help='Категория')
    income_parser.add_argument('description', help='Описание')
    income_parser.add_argument('--date', help='Дата (YYYY-MM-DD)')
    income_parser.set_defaults(func=add_income_command)
    
    expense_parser = subparsers.add_parser('expense', help='Добавить расход')
    expense_parser.add_argument('amount', type=float, help='Сумма')
    expense_parser.add_argument('category', help='Категория')
    expense_parser.add_argument('description', help='Описание')
    expense_parser.add_argument('--date', help='Дата (YYYY-MM-DD)')
    expense_parser.set_defaults(func=add_expense_command)
    
    balance_parser = subparsers.add_parser('balance', help='Показать баланс')
    balance_parser.set_defaults(func=balance_command)
    
    summary_parser = subparsers.add_parser('summary', help='Показать сводку')
    summary_parser.add_argument('--year', type=int, help='Год')
    summary_parser.add_argument('--month', type=int, help='Месяц')
    summary_parser.set_defaults(func=summary_command)
    
    stats_parser = subparsers.add_parser('stats', help='Показать статистику')
    stats_parser.add_argument('--year', type=int, help='Год')
    stats_parser.add_argument('--month', type=int, help='Месяц')
    stats_parser.set_defaults(func=statistics_command)
    
    categories_parser = subparsers.add_parser('categories', help='Показать категории')
    categories_parser.set_defaults(func=categories_command)
    
    alerts_parser = subparsers.add_parser('alerts', help='Проверить бюджет')
    alerts_parser.add_argument('--year', type=int, help='Год')
    alerts_parser.add_argument('--month', type=int, help='Месяц')
    alerts_parser.set_defaults(func=alerts_command)
    
    transactions_parser = subparsers.add_parser('transactions', help='Показать транзакции')
    transactions_parser.add_argument('--start-date', help='Начальная дата')
    transactions_parser.add_argument('--end-date', help='Конечная дата')
    transactions_parser.add_argument('--category', help='Категория')
    transactions_parser.add_argument('--type', choices=['income', 'expense'], help='Тип')
    transactions_parser.add_argument('--search', help='Поиск')
    transactions_parser.add_argument('--limit', type=int, help='Лимит')
    transactions_parser.set_defaults(func=transactions_command)
    
    add_category_parser = subparsers.add_parser('add-category', help='Добавить категорию')
    add_category_parser.add_argument('name', help='Название')
    add_category_parser.add_argument('type', choices=['income', 'expense'], help='Тип')
    add_category_parser.add_argument('--limit', type=float, help='Лимит')
    add_category_parser.set_defaults(func=add_category_command)
    
    delete_parser = subparsers.add_parser('delete', help='Удалить транзакцию')
    delete_parser.add_argument('id', help='ID транзакции')
    delete_parser.set_defaults(func=delete_transaction_command)
    
    migrate_parser = subparsers.add_parser('migrate', help='Мигрировать из JSON')
    migrate_parser.add_argument('json_file', help='JSON файл')
    migrate_parser.set_defaults(func=migrate_command)
    
    export_parser = subparsers.add_parser('export', help='Экспортировать в JSON')
    export_parser.add_argument('json_file', help='JSON файл')
    export_parser.set_defaults(func=export_command)
    
    backup_parser = subparsers.add_parser('backup', help='Создать бэкап')
    backup_parser.add_argument('backup_file', help='Файл бэкапа')
    backup_parser.set_defaults(func=backup_command)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        args.func(args)
    except Exception as e:
        print(f"❌ Ошибка: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
