#!/usr/bin/env python3
"""
Скрипт для тестирования приложения перед деплоем на Railway
"""

import os
import sys
from app import app, db

def test_app():
    """Тестирование основных компонентов приложения"""
    print("🧪 Тестирование приложения UMAY...")
    
    # Проверка переменных окружения
    print("\n1. Проверка переменных окружения:")
    secret_key = os.environ.get('SECRET_KEY', 'default-key')
    print(f"   ✅ SECRET_KEY: {'*' * len(secret_key)}")
    
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        print(f"   ✅ DATABASE_URL: {database_url[:30]}...")
    else:
        print("   ⚠️  DATABASE_URL не установлен")
    
    # Проверка базы данных
    print("\n2. Проверка базы данных:")
    try:
        with app.app_context():
            db.create_all()
            print("   ✅ База данных инициализирована успешно")
    except Exception as e:
        print(f"   ❌ Ошибка базы данных: {e}")
        return False
    
    # Проверка шаблонов
    print("\n3. Проверка шаблонов:")
    required_templates = [
        'base.html',
        'index.html',
        'login.html',
        'register.html',
        'dashboard.html',
        'news/list.html',
        'news/detail.html',
        'mama/content.html'
    ]
    
    for template in required_templates:
        try:
            app.jinja_env.get_template(template)
            print(f"   ✅ {template}")
        except Exception as e:
            print(f"   ❌ {template}: {e}")
            return False
    
    # Проверка статических файлов
    print("\n4. Проверка статических файлов:")
    static_dirs = ['static/css', 'static/js', 'static/assets']
    for static_dir in static_dirs:
        if os.path.exists(static_dir):
            print(f"   ✅ {static_dir}")
        else:
            print(f"   ⚠️  {static_dir} не найден")
    
    print("\n✅ Тестирование завершено успешно!")
    return True

def main():
    """Основная функция"""
    print("=" * 50)
    print("🚀 UMAY Railway Deployment Test")
    print("=" * 50)
    
    if test_app():
        print("\n🎉 Приложение готово к деплою на Railway!")
        print("\nСледующие шаги:")
        print("1. Установите Railway CLI: npm install -g @railway/cli")
        print("2. Авторизуйтесь: railway login")
        print("3. Инициализируйте проект: railway init")
        print("4. Подключитесь к проекту: railway link")
        print("5. Деплойте: railway up")
        print("\nПодробная инструкция в файле RAILWAY_DEPLOYMENT.md")
    else:
        print("\n❌ Обнаружены проблемы. Исправьте их перед деплоем.")
        sys.exit(1)

if __name__ == '__main__':
    main()
