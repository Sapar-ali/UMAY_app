#!/usr/bin/env python3
"""
Скрипт для запуска Flask приложения UMAY с публичной ссылкой
"""

import os
import sys
import subprocess
import time
import signal
import threading

def main():
    print("🚀 UMAY - Запуск с публичной ссылкой")
    print("=" * 50)
    
    # Проверяем, что ngrok установлен
    try:
        subprocess.run(['ngrok', 'version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ ngrok не найден! Установите его:")
        print("brew install ngrok")
        sys.exit(1)
    
    # Активируем виртуальное окружение
    venv_python = os.path.join(os.getcwd(), '.venv', 'bin', 'python')
    
    if not os.path.exists(venv_python):
        print("❌ Виртуальное окружение не найдено!")
        print("Убедитесь, что вы находитесь в корневой папке проекта")
        sys.exit(1)
    
    # Запускаем Flask приложение в фоне
    print("📱 Запуск Flask приложения...")
    flask_process = subprocess.Popen([venv_python, 'app.py'])
    
    # Ждем немного, чтобы приложение запустилось
    time.sleep(5)
    
    # Запускаем ngrok
    print("🌐 Создание публичной ссылки через ngrok...")
    ngrok_process = subprocess.Popen([
        'ngrok', 'http', '5001', '--log=stdout'
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    # Ждем, пока ngrok запустится и покажет URL
    time.sleep(3)
    
    print("\n✅ Приложение запущено!")
    print("📱 Локальный адрес: http://localhost:5001")
    print("🌐 Публичная ссылка будет показана ниже:")
    print("=" * 50)
    
    try:
        # Читаем вывод ngrok для получения публичного URL
        while True:
            line = ngrok_process.stdout.readline()
            if line:
                print(line.strip())
                if "url=" in line and "https://" in line:
                    # Извлекаем URL из строки
                    url_start = line.find("https://")
                    if url_start != -1:
                        url_end = line.find(" ", url_start)
                        if url_end == -1:
                            url_end = len(line)
                        public_url = line[url_start:url_end].strip()
                        print(f"\n🎉 Публичная ссылка: {public_url}")
                        print("📋 Скопируйте эту ссылку и отправьте сестре!")
                        break
    except KeyboardInterrupt:
        print("\n🛑 Остановка приложения...")
    finally:
        # Останавливаем процессы
        flask_process.terminate()
        ngrok_process.terminate()
        print("✅ Приложение остановлено")

if __name__ == "__main__":
    main() 