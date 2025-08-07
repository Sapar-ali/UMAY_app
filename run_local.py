#!/usr/bin/env python3
"""
Скрипт для локального запуска Flask приложения UMAY
"""

from app import app

if __name__ == '__main__':
    print("🚀 Запуск UMAY Flask приложения локально...")
    print("📱 Откройте браузер и перейдите по адресу: http://localhost:5001")
    print("⏹️  Для остановки нажмите Ctrl+C")
    print("-" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5001) 