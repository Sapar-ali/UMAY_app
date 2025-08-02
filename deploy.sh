#!/bin/bash

echo "🚀 Запуск UMAY для демонстрации сестре..."

# Активация виртуального окружения
source venv/bin/activate

# Установка ngrok если нужно
pip install pyngrok

# Запуск Streamlit в фоне
echo "📱 Запуск Streamlit..."
streamlit run app.py --server.port 8501 --server.headless true &
STREAMLIT_PID=$!

# Ждем запуска
sleep 5

# Создание публичной ссылки
echo "🌐 Создание публичной ссылки..."
python -c "
from pyngrok import ngrok
import time

try:
    public_url = ngrok.connect(8501)
    print(f'\n🎉 ГОТОВО! Публичная ссылка: {public_url}')
    print(f'📧 Отправь эту ссылку сестре: {public_url}')
    print('\n⚠️  Приложение будет доступно пока этот терминал открыт')
    print('🛑 Для остановки нажми Ctrl+C')
    
    # Держим процесс активным
    while True:
        time.sleep(1)
        
except KeyboardInterrupt:
    print('\n🛑 Остановка приложения...')
    ngrok.kill()
    print('✅ Приложение остановлено')
except Exception as e:
    print(f'❌ Ошибка: {e}')
"

# Остановка Streamlit
kill $STREAMLIT_PID 