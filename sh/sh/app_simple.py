from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
from family_budget_simple import FamilyBudgetDB, TransactionType
from datetime import datetime
import json
import os

app = Flask(__name__)
CORS(app)

budget = FamilyBudgetDB("family_budget.db")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/balance')
def get_balance():
    balance = budget.get_balance()
    return jsonify({'balance': balance, 'formatted': f"{balance:,.2f} ₽"})

@app.route('/api/summary')
def get_summary():
    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', datetime.now().month, type=int)
    
    summary = budget.get_monthly_summary(year, month)
    stats = budget.get_statistics(year, month)
    
    return jsonify({'summary': summary, 'stats': stats})

@app.route('/api/transactions')
def get_transactions():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    category = request.args.get('category')
    trans_type = request.args.get('type')
    search = request.args.get('search')
    limit = request.args.get('limit', type=int)
    
    if start_date and end_date:
        transactions = budget.get_transactions_by_date_range(start_date, end_date)
    elif category:
        transactions = budget.get_transactions_by_category(category, limit)
    elif trans_type:
        trans_type_enum = TransactionType.INCOME if trans_type == 'income' else TransactionType.EXPENSE
        transactions = budget.get_transactions_by_type(trans_type_enum, limit)
    elif search:
        transactions = budget.search_transactions(search, limit)
    else:
        transactions = budget.get_all_transactions(limit)
    
    transactions.sort(key=lambda x: x.date, reverse=True)
    
    return jsonify({'transactions': [t.to_dict() for t in transactions], 'count': len(transactions)})

@app.route('/api/transactions', methods=['POST'])
def add_transaction():
    data = request.json
    
    try:
        amount = float(data['amount'])
        category = data['category']
        description = data['description']
        date_str = data.get('date')
        trans_type_str = data.get('type', 'expense')
        
        trans_type = TransactionType.INCOME if trans_type_str == 'income' else TransactionType.EXPENSE
        
        transaction_id = budget.add_transaction(amount, category, description, date_str, trans_type)
        
        return jsonify({'success': True, 'transaction_id': transaction_id, 'message': 'Транзакция добавлена'})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'message': 'Ошибка добавления'}), 400

@app.route('/api/transactions/<transaction_id>', methods=['DELETE'])
def delete_transaction(transaction_id):
    try:
        if budget.delete_transaction(transaction_id):
            return jsonify({'success': True, 'message': 'Транзакция удалена'})
        else:
            return jsonify({'success': False, 'message': 'Транзакция не найдена'}), 404
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'message': 'Ошибка удаления'}), 400

@app.route('/api/categories')
def get_categories():
    categories = budget.get_all_categories()
    
    income_categories = [c.to_dict() for c in categories if c.type == TransactionType.INCOME]
    expense_categories = [c.to_dict() for c in categories if c.type == TransactionType.EXPENSE]
    
    return jsonify({'income': income_categories, 'expense': expense_categories, 'all': [c.to_dict() for c in categories]})

@app.route('/api/categories', methods=['POST'])
def add_category():
    data = request.json
    
    try:
        name = data['name']
        trans_type_str = data['type']
        budget_limit = data.get('limit')
        
        trans_type = TransactionType.INCOME if trans_type_str == 'income' else TransactionType.EXPENSE
        
        budget.add_category(name, trans_type, budget_limit)
        
        return jsonify({'success': True, 'message': 'Категория добавлена'})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'message': 'Ошибка добавления категории'}), 400

@app.route('/api/alerts')
def get_alerts():
    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', datetime.now().month, type=int)
    
    alerts = budget.check_budget_limits(year, month)
    
    return jsonify({'alerts': alerts, 'count': len(alerts)})

@app.route('/api/export')
def export_data():
    try:
        filename = f"budget_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        if budget.export_to_json(filename):
            return send_from_directory('.', filename, as_attachment=True)
        else:
            return jsonify({'success': False, 'message': 'Ошибка экспорта'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'message': 'Ошибка экспорта'}), 500

@app.route('/api/backup')
def backup_data():
    try:
        filename = f"budget_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        if budget.backup_database(filename):
            return send_from_directory('.', filename, as_attachment=True)
        else:
            return jsonify({'success': False, 'message': 'Ошибка бэкапа'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'message': 'Ошибка бэкапа'}), 500

if __name__ == '__main__':
    if not os.path.exists('templates'):
        os.makedirs('templates')
    if not os.path.exists('static'):
        os.makedirs('static')
    
    app.run(debug=True, host='0.0.0.0', port=5000)
