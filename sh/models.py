import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


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
