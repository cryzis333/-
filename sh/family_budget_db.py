import sqlite3
from typing import List, Dict, Optional, Any
from datetime import datetime
import os
import json
from dataclasses import dataclass


class TransactionType:
    INCOME = "income"
    EXPENSE = "expense"


@dataclass
class Transaction:
    id: str
    amount: float
    category: str
    description: str
    date: str
    type: str
    
    @classmethod
    def from_db_dict(cls, data):
        return cls(id=data['id'], amount=data['amount'], category=data['category_name'],
                  description=data['description'], date=data['date'], type=data['type'])


@dataclass
class Category:
    name: str
    type: str
    budget_limit: Optional[float] = None


class BudgetDatabase:
    def __init__(self, db_path: str = "family_budget.db"):
        self.db_path = db_path
    
    def init_database(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    type TEXT NOT NULL CHECK (type IN ('income', 'expense')),
                    budget_limit REAL DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id TEXT PRIMARY KEY,
                    amount REAL NOT NULL,
                    category_id INTEGER NOT NULL,
                    description TEXT NOT NULL,
                    date TEXT NOT NULL,
                    type TEXT NOT NULL CHECK (type IN ('income', 'expense')),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (category_id) REFERENCES categories (id)
                )
            ''')
            
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(type)')
            
            conn.commit()
    
    def add_category(self, name: str, category_type: str, budget_limit: Optional[float] = None) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT OR REPLACE INTO categories (name, type, budget_limit) VALUES (?, ?, ?)', 
                         (name, category_type, budget_limit))
            conn.commit()
            return cursor.lastrowid
    
    def get_categories(self, category_type: Optional[str] = None) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if category_type:
                cursor.execute('SELECT * FROM categories WHERE type = ? ORDER BY name', (category_type,))
            else:
                cursor.execute('SELECT * FROM categories ORDER BY name')
            
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def get_category_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM categories WHERE name = ?', (name,))
            row = cursor.fetchone()
            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
            return None
    
    def add_transaction(self, transaction_id: str, amount: float, category_name: str, 
                       description: str, date: str, transaction_type: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            category = self.get_category_by_name(category_name)
            if not category:
                category_id = self.add_category(category_name, transaction_type)
            else:
                category_id = category['id']
            
            cursor.execute('INSERT OR REPLACE INTO transactions (id, amount, category_id, description, date, type) VALUES (?, ?, ?, ?, ?, ?)', 
                         (transaction_id, amount, category_id, description, date, transaction_type))
            
            conn.commit()
            return True
    
    def get_transactions(self, start_date: Optional[str] = None, end_date: Optional[str] = None,
                        category_name: Optional[str] = None, transaction_type: Optional[str] = None,
                        limit: Optional[int] = None) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            query = '''SELECT t.*, c.name as category_name FROM transactions t
                      JOIN categories c ON t.category_id = c.id WHERE 1=1'''
            params = []
            
            if start_date:
                query += ' AND t.date >= ?'
                params.append(start_date)
            
            if end_date:
                query += ' AND t.date <= ?'
                params.append(end_date)
            
            if category_name:
                query += ' AND c.name = ?'
                params.append(category_name)
            
            if transaction_type:
                query += ' AND t.type = ?'
                params.append(transaction_type)
            
            query += ' ORDER BY t.date DESC, t.created_at DESC'
            
            if limit:
                query += ' LIMIT ?'
                params.append(limit)
            
            cursor.execute(query, params)
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def get_monthly_summary(self, year: int, month: int) -> Dict[str, Any]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''SELECT type, SUM(amount) as total FROM transactions 
                           WHERE strftime('%Y', date) = ? AND strftime('%m', date) = ? GROUP BY type''', 
                         (f"{year:04d}", f"{month:02d}"))
            
            results = dict(cursor.fetchall())
            income = results.get('income', 0)
            expenses = results.get('expense', 0)
            
            cursor.execute('''SELECT c.name, SUM(t.amount) as total FROM transactions t
                           JOIN categories c ON t.category_id = c.id
                           WHERE t.type = 'expense' AND strftime('%Y', t.date) = ? AND strftime('%m', t.date) = ?
                           GROUP BY c.name ORDER BY total DESC''', 
                         (f"{year:04d}", f"{month:02d}"))
            
            category_breakdown = dict(cursor.fetchall())
            
            return {
                'year': year, 'month': month, 'income': income, 'expenses': expenses,
                'balance': income - expenses, 'category_breakdown': category_breakdown
            }
    
    def get_category_spending(self, category_name: str, year: int, month: int) -> float:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''SELECT SUM(t.amount) FROM transactions t
                           JOIN categories c ON t.category_id = c.id
                           WHERE c.name = ? AND t.type = 'expense'
                           AND strftime('%Y', t.date) = ? AND strftime('%m', t.date) = ?''', 
                         (category_name, f"{year:04d}", f"{month:02d}"))
            
            result = cursor.fetchone()
            return result[0] if result[0] else 0
    
    def get_balance(self) -> float:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''SELECT SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) -
                           SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) as balance FROM transactions''')
            
            result = cursor.fetchone()
            return result[0] if result[0] else 0
    
    def delete_transaction(self, transaction_id: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM transactions WHERE id = ?', (transaction_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def get_budget_alerts(self, year: int, month: int) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''SELECT c.name, c.budget_limit, COALESCE(SUM(t.amount), 0) as spent
                           FROM categories c LEFT JOIN transactions t ON c.id = t.category_id
                           AND t.type = 'expense' AND strftime('%Y', t.date) = ? AND strftime('%m', t.date) = ?
                           WHERE c.type = 'expense' AND c.budget_limit IS NOT NULL
                           GROUP BY c.id, c.name, c.budget_limit HAVING spent > c.budget_limit''', 
                         (f"{year:04d}", f"{month:02d}"))
            
            columns = [desc[0] for desc in cursor.description]
            alerts = []
            for row in cursor.fetchall():
                alert = dict(zip(columns, row))
                alert['over_limit'] = alert['spent'] - alert['budget_limit']
                alerts.append(alert)
            
            return alerts


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
