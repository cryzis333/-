import sqlite3
from typing import List, Dict, Optional, Any
from datetime import datetime
import os


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
    
    def migrate_from_json(self, json_file: str) -> bool:
        if not os.path.exists(json_file):
            return False
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for name, cat_data in data.get('categories', {}).items():
                self.add_category(name, cat_data['type'], cat_data.get('budget_limit'))
            
            for trans_data in data.get('transactions', []):
                self.add_transaction(trans_data['id'], trans_data['amount'], trans_data['category'],
                                   trans_data['description'], trans_data['date'], trans_data['type'])
            
            return True
        except Exception:
            return False
    
    def export_to_json(self, json_file: str) -> bool:
        try:
            categories = self.get_categories()
            transactions = self.get_transactions()
            
            json_data = {
                'categories': {cat['name']: {'name': cat['name'], 'type': cat['type'], 
                                            'budget_limit': cat['budget_limit']} for cat in categories},
                'transactions': [{'id': trans['id'], 'amount': trans['amount'], 'category': trans['category_name'],
                                'description': trans['description'], 'date': trans['date'], 'type': trans['type']} 
                               for trans in transactions]
            }
            
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception:
            return False
    
    def backup_database(self, backup_path: str) -> bool:
        try:
            with sqlite3.connect(self.db_path) as source:
                with sqlite3.connect(backup_path) as backup:
                    source.backup(backup)
            return True
        except Exception:
            return False
