#!/usr/bin/env python3
"""
Скрипт для запуска Flask приложения UMAY
"""

import os
import sys
import subprocess

def main():
    # Активируем виртуальное окружение
    venv_python = os.path.join(os.getcwd(), '.venv', 'bin', 'python')
    
    if not os.path.exists(venv_python):
        print("❌ Виртуальное окружение не найдено!")
        print("Убедитесь, что вы находитесь в корневой папке проекта")
        sys.exit(1)
    
    # Запускаем Flask приложение
    try:
        print("🚀 Запуск Flask приложения UMAY...")
        print("📱 Приложение будет доступно по адресу: http://localhost:5001")
        print("⏹️  Для остановки нажмите Ctrl+C")
        print("-" * 50)
        
        subprocess.run([venv_python, 'app.py'])
        
    except KeyboardInterrupt:
        print("\n🛑 Приложение остановлено")
    except Exception as e:
        print(f"❌ Ошибка при запуске: {e}")

if __name__ == "__main__":
    main() 