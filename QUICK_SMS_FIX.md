# 🚀 Быстрое исправление SMS в UMAY

## 🚨 Проблема
SMS не работает - переменные окружения не настроены.

## ⚡ Быстрое решение (5 минут)

### 1. Создайте файл .env
```bash
# В корне проекта UMAY_stat создайте файл .env
touch .env
```

### 2. Добавьте в .env:
```bash
SMS_PROVIDER=infobip
SMS_BASE_URL=https://api.infobip.com
SMS_API_KEY=ВАШ_РЕАЛЬНЫЙ_API_КЛЮЧ_ОТ_INFOBIP
SMS_SENDER=UMAY
```

### 3. Получите API ключ от Infobip:
- Войдите в аккаунт Infobip
- API Keys → Create new key
- Скопируйте ключ в .env

### 4. Перезапустите приложение:
```bash
# Остановите текущее (Ctrl+C)
# Запустите заново:
source .venv/bin/activate
python3 run_local.py
```

### 5. Протестируйте:
- Откройте http://localhost:5001/register
- Введите номер телефона
- Нажмите "Код"
- Должно прийти SMS!

## 🔍 Проверка
```bash
python3 test_sms.py
```

## 📱 Если SMS все равно не приходит:
1. Проверьте баланс в Infobip
2. Убедитесь, что буквенный номер подтвержден
3. Проверьте логи приложения
4. Убедитесь, что номер телефона в формате +7XXXXXXXXX

## 📞 Поддержка
- Подробная инструкция: `SMS_SETUP_INSTRUCTIONS.md`
- Пример переменных: `env_example.txt`
- Тест настроек: `test_sms.py`
