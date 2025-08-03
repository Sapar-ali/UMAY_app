// Анимации при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    // Анимация появления элементов
    const elements = document.querySelectorAll('.card, .btn, .alert');
    elements.forEach((element, index) => {
        element.style.opacity = '0';
        element.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            element.style.transition = 'all 0.6s ease';
            element.style.opacity = '1';
            element.style.transform = 'translateY(0)';
        }, index * 100);
    });

    // Проверка совпадения паролей при регистрации
    const passwordField = document.getElementById('password');
    const confirmPasswordField = document.getElementById('confirm_password');
    
    if (passwordField && confirmPasswordField) {
        function checkPasswordMatch() {
            if (passwordField.value !== confirmPasswordField.value) {
                confirmPasswordField.setCustomValidity('Пароли не совпадают');
            } else {
                confirmPasswordField.setCustomValidity('');
            }
        }
        
        passwordField.addEventListener('change', checkPasswordMatch);
        confirmPasswordField.addEventListener('keyup', checkPasswordMatch);
    }

    // Автоматическое скрытие алертов
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // Подсветка активной ссылки в навигации
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.navbar-nav .nav-link');
    
    navLinks.forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });

    // Плавная прокрутка для якорных ссылок
    const anchorLinks = document.querySelectorAll('a[href^="#"]');
    anchorLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Улучшенная валидация форм
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const requiredFields = form.querySelectorAll('[required]');
            let isValid = true;
            
            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    field.classList.add('is-invalid');
                    isValid = false;
                } else {
                    field.classList.remove('is-invalid');
                }
            });
            
            if (!isValid) {
                e.preventDefault();
                showNotification('Пожалуйста, заполните все обязательные поля', 'error');
            }
        });
    });

    // Функция для показа уведомлений
    function showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 5000);
    }

    // Обработка ошибок AJAX
    window.addEventListener('error', function(e) {
        console.error('JavaScript error:', e.error);
        showNotification('Произошла ошибка. Попробуйте обновить страницу.', 'error');
    });

    // Улучшенная таблица с сортировкой
    const tables = document.querySelectorAll('.table');
    tables.forEach(table => {
        const headers = table.querySelectorAll('th[data-sort]');
        headers.forEach(header => {
            header.style.cursor = 'pointer';
            header.addEventListener('click', function() {
                const column = this.cellIndex;
                const rows = Array.from(table.querySelectorAll('tbody tr'));
                const isAscending = this.classList.contains('sort-asc');
                
                // Удаляем классы сортировки со всех заголовков
                headers.forEach(h => h.classList.remove('sort-asc', 'sort-desc'));
                
                // Добавляем класс сортировки к текущему заголовку
                this.classList.add(isAscending ? 'sort-desc' : 'sort-asc');
                
                // Сортируем строки
                rows.sort((a, b) => {
                    const aValue = a.cells[column].textContent.trim();
                    const bValue = b.cells[column].textContent.trim();
                    
                    if (isAscending) {
                        return bValue.localeCompare(aValue);
                    } else {
                        return aValue.localeCompare(bValue);
                    }
                });
                
                // Переставляем строки в таблице
                const tbody = table.querySelector('tbody');
                rows.forEach(row => tbody.appendChild(row));
            });
        });
    });

    // Анимация загрузки для кнопок
    const buttons = document.querySelectorAll('.btn');
    buttons.forEach(button => {
        button.addEventListener('click', function() {
            if (!this.classList.contains('btn-loading')) {
                this.classList.add('btn-loading');
                this.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Загрузка...';
                
                setTimeout(() => {
                    this.classList.remove('btn-loading');
                    this.innerHTML = this.getAttribute('data-original-text') || this.innerHTML;
                }, 2000);
            }
        });
    });

    // Сохранение оригинального текста кнопок
    buttons.forEach(button => {
        button.setAttribute('data-original-text', button.innerHTML);
    });
});

// Дополнительные функции для работы с данными
window.UMAY = {
    // Форматирование даты
    formatDate: function(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('ru-RU', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    },
    
    // Валидация медицинских данных
    validateMedicalData: function(data) {
        const errors = [];
        
        if (data.age && (data.age < 12 || data.age > 60)) {
            errors.push('Возраст должен быть от 12 до 60 лет');
        }
        
        if (data.pregnancy_weeks && (data.pregnancy_weeks < 20 || data.pregnancy_weeks > 45)) {
            errors.push('Срок беременности должен быть от 20 до 45 недель');
        }
        
        if (data.child_weight && (data.child_weight < 500 || data.child_weight > 6000)) {
            errors.push('Вес ребенка должен быть от 500 до 6000 грамм');
        }
        
        return errors;
    },
    
    // Экспорт данных
    exportData: function(format) {
        // Логика экспорта данных
        console.log(`Экспорт в формате: ${format}`);
    }
}; 