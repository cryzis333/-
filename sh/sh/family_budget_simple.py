import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
from database_simple import BudgetDatabase


class TransactionType(Enum):
    INCOME = "income"
    EXPENSE = "expense"


@dataclass
class Transaction:
    id: str
    amount: float
    category: str
    description: str
    date: str
    type: TransactionType
    
    def to_dict(self):
        return {'id': self.id, 'amount': self.amount, 'category': self.category, 
                'description': self.description, 'date': self.date, 'type': self.type.value}
    
    @classmethod
    def from_dict(cls, data):
        return cls(id=data['id'], amount=data['amount'], category=data['category'],
                  description=data['description'], date=data['date'], type=TransactionType(data['type']))
    
    @classmethod
    def from_db_dict(cls, data):
        return cls(id=data['id'], amount=data['amount'], category=data['category_name'],
                  description=data['description'], date=data['date'], type=TransactionType(data['type']))


@dataclass
class Category:
    name: str
    type: TransactionType
    budget_limit: Optional[float] = None
    
    def to_dict(self):
        return {'name': self.name, 'type': self.type.value, 'budget_limit': self.budget_limit}
    
    @classmethod
    def from_dict(cls, data):
        return cls(name=data['name'], type=TransactionType(data['type']), budget_limit=data.get('budget_limit'))
    
    @classmethod
    def from_db_dict(cls, data):
        return cls(name=data['name'], type=TransactionType(data['type']), budget_limit=data.get('budget_limit'))


class FamilyBudgetDB:
    def __init__(self, db_path: str = "family_budget.db"):
        self.db = BudgetDatabase(db_path)
        self._init_default_categories()
    
    def _init_default_categories(self):
        default_categories = [
            Category("Зарплата", TransactionType.INCOME),
            Category("Продукты", TransactionType.EXPENSE, 15000),
            Category("Коммунальные платежи", TransactionType.EXPENSE, 5000),
            Category("Транспорт", TransactionType.EXPENSE, 3000),
            Category("Развлечения", TransactionType.EXPENSE, 5000),
            Category("Здоровье", TransactionType.EXPENSE, 3000),
            Category("Одежда", TransactionType.EXPENSE, 4000),
            Category("Прочее", TransactionType.EXPENSE, 2000),
        ]
        
        for category in default_categories:
            existing = self.db.get_category_by_name(category.name)
            if not existing:
                self.db.add_category(category.name, category.type.value, category.budget_limit)
    
    def add_transaction(self, amount: float, category: str, description: str, 
                       date: str = None, transaction_type: TransactionType = TransactionType.EXPENSE) -> str:
        if date is None:
            date = datetime.date.today().isoformat()
        
        transaction_id = f"{datetime.datetime.now().timestamp()}"
        self.db.add_transaction(transaction_id, amount, category, description, date, transaction_type.value)
        return transaction_id
    
    def add_category(self, name: str, transaction_type: TransactionType, budget_limit: float = None):
        self.db.add_category(name, transaction_type.value, budget_limit)
    
    def get_balance(self) -> float:
        return self.db.get_balance()
    
    def get_monthly_summary(self, year: int = None, month: int = None) -> Dict:
        if year is None:
            year = datetime.date.today().year
        if month is None:
            month = datetime.date.today().month
        
        return self.db.get_monthly_summary(year, month)
    
    def get_category_spending(self, category: str, year: int = None, month: int = None) -> float:
        if year is None:
            year = datetime.date.today().year
        if month is None:
            month = datetime.date.today().month
        
        return self.db.get_category_spending(category, year, month)
    
    def check_budget_limits(self, year: int = None, month: int = None) -> List[Dict]:
        if year is None:
            year = datetime.date.today().year
        if month is None:
            month = datetime.date.today().month
        
        alerts = []
        db_alerts = self.db.get_budget_alerts(year, month)
        
        for alert in db_alerts:
            alerts.append({'category': alert['name'], 'limit': alert['budget_limit'],
                          'spent': alert['spent'], 'over_limit': alert['over_limit']})
        
        return alerts
    
    def get_transactions_by_date_range(self, start_date: str, end_date: str) -> List[Transaction]:
        db_transactions = self.db.get_transactions(start_date=start_date, end_date=end_date)
        return [Transaction.from_db_dict(t) for t in db_transactions]
    
    def get_all_transactions(self, limit: int = None) -> List[Transaction]:
        db_transactions = self.db.get_transactions(limit=limit)
        return [Transaction.from_db_dict(t) for t in db_transactions]
    
    def delete_transaction(self, transaction_id: str) -> bool:
        return self.db.delete_transaction(transaction_id)
    
    def get_categories_by_type(self, transaction_type: TransactionType) -> List[str]:
        categories = self.db.get_categories(transaction_type.value)
        return [cat['name'] for cat in categories]
    
    def get_all_categories(self) -> List[Category]:
        db_categories = self.db.get_categories()
        return [Category.from_db_dict(cat) for cat in db_categories]
    
    def migrate_from_json(self, json_file: str) -> bool:
        return self.db.migrate_from_json(json_file)
    
    def export_to_json(self, json_file: str) -> bool:
        return self.db.export_to_json(json_file)
    
    def backup_database(self, backup_path: str) -> bool:
        return self.db.backup_database(backup_path)
    
    def get_transactions_by_category(self, category: str, limit: int = None) -> List[Transaction]:
        db_transactions = self.db.get_transactions(category_name=category, limit=limit)
        return [Transaction.from_db_dict(t) for t in db_transactions]
    
    def get_transactions_by_type(self, transaction_type: TransactionType, limit: int = None) -> List[Transaction]:
        db_transactions = self.db.get_transactions(transaction_type=transaction_type.value, limit=limit)
        return [Transaction.from_db_dict(t) for t in db_transactions]
    
    def search_transactions(self, description: str, limit: int = None) -> List[Transaction]:
        with self.db:
            import sqlite3
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''SELECT t.*, c.name as category_name FROM transactions t
                               JOIN categories c ON t.category_id = c.id
                               WHERE t.description LIKE ? ORDER BY t.date DESC LIMIT ?''', 
                             (f'%{description}%', limit if limit else -1))
                
                columns = [desc[0] for desc in cursor.description]
                db_transactions = [dict(zip(columns, row)) for row in cursor.fetchall()]
                return [Transaction.from_db_dict(t) for t in db_transactions]
    
    def get_statistics(self, year: int = None, month: int = None) -> Dict:
        if year is None:
            year = datetime.date.today().year
        if month is None:
            month = datetime.date.today().month
        
        summary = self.get_monthly_summary(year, month)
        
        all_transactions = self.get_transactions_by_date_range(f"{year}-{month:02d}-01", f"{year}-{month:02d}-31")
        
        income_transactions = [t for t in all_transactions if t.type == TransactionType.INCOME]
        expense_transactions = [t for t in all_transactions if t.type == TransactionType.EXPENSE]
        
        avg_income = sum(t.amount for t in income_transactions) / len(income_transactions) if income_transactions else 0
        avg_expense = sum(t.amount for t in expense_transactions) / len(expense_transactions) if expense_transactions else 0
        
        transaction_count = {'total': len(all_transactions), 'income': len(income_transactions), 'expenses': len(expense_transactions)}
        
        return {**summary, 'average_income': avg_income, 'average_expense': avg_expense,
                'transaction_count': transaction_count, 'days_in_month': (datetime.date(year, month % 12 + 1, 1) - datetime.date(year, month, 1)).days}
