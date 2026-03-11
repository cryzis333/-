// JavaScript функционал для веб-интерфейса семейного бюджета

let currentTransactions = [];
let categoryChart = null;

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    loadBalance();
    loadSummary();
    loadCategories();
    loadTransactions();
    loadAlerts();
    
    // Установка сегодняшней даты по умолчанию
    document.getElementById('date').value = new Date().toISOString().split('T')[0];
    
    // Обработчики событий
    document.getElementById('transaction-form').addEventListener('submit', handleTransactionSubmit);
    document.getElementById('transaction-type').addEventListener('change', updateCategories);
    document.getElementById('search').addEventListener('input', debounce(searchTransactions, 300));
}

// Загрузка баланса
async function loadBalance() {
    try {
        const response = await fetch('/api/balance');
        const data = await response.json();
        document.getElementById('balance').textContent = data.formatted;
    } catch (error) {
        console.error('Ошибка загрузки баланса:', error);
    }
}

// Загрузка сводки
async function loadSummary() {
    try {
        const response = await fetch('/api/summary');
        const data = await response.json();
        
        const summary = data.summary;
        const stats = data.stats;
        
        // Обновление основных показателей
        document.getElementById('income').textContent = formatCurrency(summary.income);
        document.getElementById('expenses').textContent = formatCurrency(summary.expenses);
        
        // Обновление статистики
        document.getElementById('avg-income').textContent = formatCurrency(stats.average_income);
        document.getElementById('avg-expense').textContent = formatCurrency(stats.average_expense);
        document.getElementById('total-transactions').textContent = stats.transaction_count.total;
        document.getElementById('income-transactions').textContent = stats.transaction_count.income;
        document.getElementById('expense-transactions').textContent = stats.transaction_count.expenses;
        
        // Обновление графика категорий
        updateCategoryChart(summary.category_breakdown);
        
    } catch (error) {
        console.error('Ошибка загрузки сводки:', error);
    }
}

// Загрузка категорий
async function loadCategories() {
    try {
        const response = await fetch('/api/categories');
        const data = await response.json();
        
        updateCategorySelects(data.all);
        updateFilterCategories(data.all);
        
    } catch (error) {
        console.error('Ошибка загрузки категорий:', error);
    }
}

// Обновление селектов категорий
function updateCategorySelects(categories) {
    const transactionSelect = document.getElementById('category');
    const filterSelect = document.getElementById('filter-category');
    
    // Очистка селектов
    transactionSelect.innerHTML = '<option value="">Выберите категорию</option>';
    filterSelect.innerHTML = '<option value="">Все категории</option>';
    
    // Добавление опций
    categories.forEach(category => {
        const option = new Option(category.name, category.name);
        transactionSelect.add(option.cloneNode(true));
        filterSelect.add(option);
    });
}

// Обновление категорий в фильтрах
function updateFilterCategories(categories) {
    const filterSelect = document.getElementById('filter-category');
    filterSelect.innerHTML = '<option value="">Все категории</option>';
    
    categories.forEach(category => {
        const option = new Option(category.name, category.name);
        filterSelect.add(option);
    });
}

// Обновление категорий в зависимости от типа транзакции
function updateCategories() {
    const type = document.getElementById('transaction-type').value;
    const categorySelect = document.getElementById('category');
    
    // Здесь можно добавить фильтрацию категорий по типу
    // Пока оставляем все категории
}

// Загрузка транзакций
async function loadTransactions() {
    try {
        const response = await fetch('/api/transactions');
        const data = await response.json();
        
        currentTransactions = data.transactions;
        displayTransactions(currentTransactions);
        document.getElementById('transactions-count').textContent = `${data.count} записей`;
        
    } catch (error) {
        console.error('Ошибка загрузки транзакций:', error);
    }
}

// Отображение транзакций
function displayTransactions(transactions) {
    const tbody = document.getElementById('transactions-table');
    
    if (transactions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center">Нет транзакций</td></tr>';
        return;
    }
    
    tbody.innerHTML = transactions.map(transaction => `
        <tr class="transaction-row">
            <td>${formatDate(transaction.date)}</td>
            <td>
                <span class="transaction-type-badge badge bg-${transaction.type === 'income' ? 'success' : 'danger'}">
                    ${transaction.type === 'income' ? '➕ Доход' : '➖ Расход'}
                </span>
            </td>
            <td>
                <span class="category-badge">${transaction.category}</span>
            </td>
            <td class="amount-display transaction-${transaction.type}">
                ${transaction.type === 'income' ? '+' : '-'}${formatCurrency(transaction.amount)}
            </td>
            <td>${transaction.description}</td>
            <td>
                <button class="btn btn-sm btn-outline-danger" onclick="deleteTransaction('${transaction.id}')">
                    <i class="bi bi-trash"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

// Обработка формы транзакции
async function handleTransactionSubmit(event) {
    event.preventDefault();
    
    const formData = {
        amount: parseFloat(document.getElementById('amount').value),
        category: document.getElementById('category').value,
        description: document.getElementById('description').value,
        date: document.getElementById('date').value,
        type: document.getElementById('transaction-type').value
    };
    
    try {
        const response = await fetch('/api/transactions', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showAlert('success', 'Транзакция успешно добавлена');
            clearForm();
            loadBalance();
            loadSummary();
            loadTransactions();
            loadAlerts();
        } else {
            showAlert('danger', result.message);
        }
        
    } catch (error) {
        console.error('Ошибка добавления транзакции:', error);
        showAlert('danger', 'Ошибка при добавлении транзакции');
    }
}

// Удаление транзакции
async function deleteTransaction(transactionId) {
    if (!confirm('Вы уверены, что хотите удалить эту транзакцию?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/transactions/${transactionId}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.success) {
            showAlert('success', 'Транзакция успешно удалена');
            loadBalance();
            loadSummary();
            loadTransactions();
            loadAlerts();
        } else {
            showAlert('danger', result.message);
        }
        
    } catch (error) {
        console.error('Ошибка удаления транзакции:', error);
        showAlert('danger', 'Ошибка при удалении транзакции');
    }
}

// Загрузка предупреждений
async function loadAlerts() {
    try {
        const response = await fetch('/api/alerts');
        const data = await response.json();
        
        displayAlerts(data.alerts);
        
    } catch (error) {
        console.error('Ошибка загрузки предупреждений:', error);
    }
}

// Отображение предупреждений
function displayAlerts(alerts) {
    const container = document.getElementById('alerts-container');
    
    if (alerts.length === 0) {
        container.innerHTML = '';
        return;
    }
    
    container.innerHTML = `
        <div class="alert alert-warning" role="alert">
            <h5 class="alert-heading">
                <i class="bi bi-exclamation-triangle"></i> Предупреждения о бюджете
            </h5>
            ${alerts.map(alert => `
                <div class="mb-2">
                    <strong>${alert.category}:</strong> 
                    потрачено ${formatCurrency(alert.spent)} из ${formatCurrency(alert.limit)}
                    (превышение на ${formatCurrency(alert.over_limit)})
                </div>
            `).join('')}
        </div>
    `;
}

// Поиск транзакций
async function searchTransactions() {
    const searchTerm = document.getElementById('search').value;
    
    if (!searchTerm) {
        displayTransactions(currentTransactions);
        return;
    }
    
    try {
        const response = await fetch(`/api/transactions?search=${encodeURIComponent(searchTerm)}`);
        const data = await response.json();
        
        displayTransactions(data.transactions);
        
    } catch (error) {
        console.error('Ошибка поиска:', error);
    }
}

// Применение фильтров
async function applyFilters() {
    const params = new URLSearchParams();
    
    const type = document.getElementById('filter-type').value;
    const category = document.getElementById('filter-category').value;
    const startDate = document.getElementById('start-date').value;
    const endDate = document.getElementById('end-date').value;
    
    if (type) params.append('type', type);
    if (category) params.append('category', category);
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    
    try {
        const response = await fetch(`/api/transactions?${params}`);
        const data = await response.json();
        
        displayTransactions(data.transactions);
        
    } catch (error) {
        console.error('Ошибка применения фильтров:', error);
    }
}

// Добавление категории
async function addCategory() {
    const formData = {
        name: document.getElementById('category-name').value,
        type: document.getElementById('category-type').value,
        limit: parseFloat(document.getElementById('category-limit').value) || null
    };
    
    try {
        const response = await fetch('/api/categories', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showAlert('success', 'Категория успешно добавлена');
            const modal = bootstrap.Modal.getInstance(document.getElementById('categoryModal'));
            modal.hide();
            document.getElementById('category-form').reset();
            loadCategories();
        } else {
            showAlert('danger', result.message);
        }
        
    } catch (error) {
        console.error('Ошибка добавления категории:', error);
        showAlert('danger', 'Ошибка при добавлении категории');
    }
}

// Экспорт данных
function exportData() {
    window.open('/api/export', '_blank');
}

// Резервное копирование
function backupData() {
    window.open('/api/backup', '_blank');
}

// Очистка формы
function clearForm() {
    document.getElementById('transaction-form').reset();
    document.getElementById('date').value = new Date().toISOString().split('T')[0];
}

// Показ уведомления
function showAlert(type, message) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.querySelector('.container').insertBefore(alertDiv, document.querySelector('.container').firstChild);
    
    // Автоматическое скрытие через 5 секунд
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

// Обновление графика категорий
function updateCategoryChart(categoryData) {
    const ctx = document.getElementById('category-chart').getContext('2d');
    
    if (categoryChart) {
        categoryChart.destroy();
    }
    
    const labels = Object.keys(categoryData);
    const data = Object.values(categoryData);
    
    categoryChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: [
                    '#FF6384',
                    '#36A2EB',
                    '#FFCE56',
                    '#4BC0C0',
                    '#9966FF',
                    '#FF9F40',
                    '#FF6384',
                    '#C9CBCF'
                ],
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 15,
                        font: {
                            size: 12
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = formatCurrency(context.raw);
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((context.raw / total) * 100).toFixed(1);
                            return `${label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

// Вспомогательные функции
function formatCurrency(amount) {
    return new Intl.NumberFormat('ru-RU', {
        style: 'currency',
        currency: 'RUB',
        minimumFractionDigits: 2
    }).format(amount);
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('ru-RU', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
    });
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Горячие клавиши
document.addEventListener('keydown', function(event) {
    // Ctrl+N - новая транзакция
    if (event.ctrlKey && event.key === 'n') {
        event.preventDefault();
        document.getElementById('amount').focus();
    }
    
    // Ctrl+S - поиск
    if (event.ctrlKey && event.key === 'f') {
        event.preventDefault();
        document.getElementById('search').focus();
    }
    
    // Escape - очистка формы
    if (event.key === 'Escape') {
        clearForm();
    }
});
