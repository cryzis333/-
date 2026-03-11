import sqlite3
from flask import Flask, request, jsonify, render_template
from datetime import datetime

app = Flask(__name__)

def init_db():
    conn = sqlite3.connect('budget.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS transactions 
                 (id INTEGER PRIMARY KEY, amount REAL, type TEXT, category TEXT, description TEXT, date TEXT)''')
    conn.commit()
    conn.close()

def get_balance():
    conn = sqlite3.connect('budget.db')
    c = conn.cursor()
    c.execute('SELECT SUM(CASE WHEN type="income" THEN amount ELSE -amount END) FROM transactions')
    balance = c.fetchone()[0] or 0
    conn.close()
    return balance

def add_transaction(amount, trans_type, category, description, date):
    conn = sqlite3.connect('budget.db')
    c = conn.cursor()
    c.execute('INSERT INTO transactions (amount, type, category, description, date) VALUES (?, ?, ?, ?, ?)',
              (amount, trans_type, category, description, date))
    conn.commit()
    conn.close()

def get_transactions():
    conn = sqlite3.connect('budget.db')
    c = conn.cursor()
    c.execute('SELECT * FROM transactions ORDER BY date DESC')
    transactions = c.fetchall()
    conn.close()
    return transactions

@app.route('/')
def index():
    return render_template('index_minimal.html')

@app.route('/api/balance')
def balance():
    return jsonify({'balance': get_balance()})

@app.route('/api/add', methods=['POST'])
def add():
    data = request.json
    add_transaction(data['amount'], data['type'], data['category'], data['description'], data['date'])
    return jsonify({'success': True})

@app.route('/api/transactions')
def transactions():
    return jsonify({'transactions': get_transactions()})

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
