#!/usr/bin/env python3
"""
Скрипт для тестирования SMS настроек UMAY
"""

import os
import sys

def test_sms_config():
    """Тестирует конфигурацию SMS"""
    print("🔧 Тестирование SMS конфигурации UMAY")
    print("=" * 50)
    
    # Загружаем переменные через app.py (как в реальном приложении)
    try:
        sys.path.append('.')
        from app import SMS_PROVIDER, SMS_BASE_URL, SMS_API_KEY, SMS_SENDER
        
        sms_provider = SMS_PROVIDER
        sms_base_url = SMS_BASE_URL
        sms_api_key = SMS_API_KEY
        sms_sender = SMS_SENDER
    except Exception as e:
        print(f"❌ Ошибка загрузки переменных из app.py: {e}")
        # Fallback к os.getenv
        sms_provider = os.getenv('SMS_PROVIDER', 'NOT_SET')
        sms_base_url = os.getenv('SMS_BASE_URL', 'NOT_SET')
        sms_api_key = os.getenv('SMS_API_KEY', 'NOT_SET')
        sms_sender = os.getenv('SMS_SENDER', 'UMAY')
    
    print(f"SMS_PROVIDER: {sms_provider}")
    print(f"SMS_BASE_URL: {sms_base_url}")
    print(f"SMS_API_KEY: {'*' * 10 if sms_api_key != 'NOT_SET' else 'NOT_SET'}")
    print(f"SMS_SENDER: {sms_sender}")
    print()
    
    # Анализируем проблемы
    issues = []
    
    if sms_provider == 'NOT_SET':
        issues.append("❌ SMS_PROVIDER не установлен")
    elif sms_provider != 'infobip':
        issues.append(f"⚠️  SMS_PROVIDER установлен как '{sms_provider}', рекомендуется 'infobip'")
    
    if sms_base_url == 'NOT_SET':
        issues.append("❌ SMS_BASE_URL не установлен")
    elif not sms_base_url.startswith('https://'):
        issues.append(f"⚠️  SMS_BASE_URL должен начинаться с 'https://'")
    
    if sms_api_key == 'NOT_SET':
        issues.append("❌ SMS_API_KEY не установлен")
    elif len(sms_api_key) < 10:
        issues.append("⚠️  SMS_API_KEY слишком короткий")
    
    if sms_sender == 'UMAY':
        print("ℹ️  SMS_SENDER использует значение по умолчанию 'UMAY'")
        print("   Убедитесь, что это соответствует вашему буквенному номеру от Infobip")
    
    # Выводим результаты
    if issues:
        print("🚨 Найдены проблемы:")
        for issue in issues:
            print(f"   {issue}")
        print()
        print("📋 Для исправления:")
        print("   1. Создайте файл .env в корне проекта")
        print("   2. Добавьте переменные SMS_*")
        print("   3. Перезапустите приложение")
        print()
        print("📖 Подробности в файле SMS_SETUP_INSTRUCTIONS.md")
        return False
    else:
        print("✅ Все SMS настройки корректны!")
        print("📱 SMS должен работать")
        return True

def test_sms_import():
    """Тестирует импорт SMS функций"""
    print("\n🧪 Тестирование импорта SMS функций...")
    
    try:
        # Пытаемся импортировать app
        sys.path.append('.')
        from app import send_sms_infobip, send_otp
        
        print("✅ SMS функции импортированы успешно")
        
        # Тестируем функцию отправки SMS
        print("\n📱 Тестирование функции send_sms_infobip...")
        
        # Проверяем, есть ли настройки
        from app import SMS_BASE_URL, SMS_API_KEY
        
        if SMS_BASE_URL and SMS_API_KEY:
            print("✅ SMS настройки загружены")
            print(f"   Base URL: {SMS_BASE_URL}")
            print(f"   API Key: {'*' * 10}")
        else:
            print("❌ SMS настройки не загружены")
            print("   Проверьте переменные окружения")
        
        return True
        
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def main():
    """Основная функция"""
    print("🚀 UMAY SMS Test Tool")
    print("=" * 50)
    
    # Тест 1: Конфигурация
    config_ok = test_sms_config()
    
    # Тест 2: Импорт функций
    import_ok = test_sms_import()
    
    print("\n" + "=" * 50)
    if config_ok and import_ok:
        print("🎉 Все тесты пройдены! SMS должен работать.")
    else:
        print("⚠️  Найдены проблемы. Исправьте их перед использованием SMS.")
    
    print("\n📚 Документация:")
    print("   - SMS_SETUP_INSTRUCTIONS.md - подробная инструкция")
    print("   - env_example.txt - пример переменных окружения")

if __name__ == '__main__':
    main()
