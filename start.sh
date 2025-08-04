#!/bin/bash
# Скрипт запуска для Render

echo "Starting UMAY application..."

# Создаем папку data если её нет
mkdir -p data
echo "Data directory created/verified"

# Проверяем что файлы на месте
ls -la
echo "Current directory contents:"
ls -la

# Проверяем что app.py существует
if [ -f "app.py" ]; then
    echo "app.py found"
else
    echo "ERROR: app.py not found!"
    exit 1
fi

# Запускаем приложение через gunicorn
echo "Starting gunicorn..."
gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120 