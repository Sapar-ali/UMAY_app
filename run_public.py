import streamlit as st
import subprocess
import time
import requests
from pyngrok import ngrok
import os

def main():
    print("🚀 Запуск UMAY с публичной ссылкой...")
    
    # Запуск Streamlit в фоне
    print("📱 Запуск Streamlit...")
    streamlit_process = subprocess.Popen([
        "streamlit", "run", "app.py", 
        "--server.port", "8501",
        "--server.headless", "true"
    ])
    
    # Ждем немного для запуска
    time.sleep(5)
    
    # Создание публичной ссылки
    print("🌐 Создание публичной ссылки...")
    try:
        public_url = ngrok.connect(8501)
        print(f"\n🎉 ГОТОВО! Публичная ссылка: {public_url}")
        print(f"📧 Отправь эту ссылку сестре: {public_url}")
        print("\n⚠️  Приложение будет доступно пока этот терминал открыт")
        print("🛑 Для остановки нажми Ctrl+C")
        
        # Держим процесс активным
        try:
            streamlit_process.wait()
        except KeyboardInterrupt:
            print("\n🛑 Остановка приложения...")
            streamlit_process.terminate()
            ngrok.kill()
            print("✅ Приложение остановлено")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        streamlit_process.terminate()

if __name__ == "__main__":
    main() 