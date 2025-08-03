#!/bin/bash
# Скрипт запуска для Render

# Создаем папку data если её нет
mkdir -p data

# Запускаем приложение через gunicorn
gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120 