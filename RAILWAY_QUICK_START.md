# 🚀 Быстрый деплой UMAY на Railway

## Шаг 1: Установка Railway CLI
```bash
npm install -g @railway/cli
```

## Шаг 2: Авторизация
```bash
railway login
```

## Шаг 3: Инициализация проекта
```bash
railway init
```

## Шаг 4: Подключение к проекту
```bash
railway link
```

## Шаг 5: Создание базы данных (опционально)
```bash
railway add
```
Выберите PostgreSQL

## Шаг 6: Деплой
```bash
railway up
```

## Шаг 7: Открытие приложения
```bash
railway open
```

## Переменные окружения

В Railway Dashboard добавьте:

### Обязательные:
```
SECRET_KEY=your-very-secure-secret-key-here
FLASK_ENV=production
```

### Для PostgreSQL (если создали):
```
DATABASE_URL=postgresql://username:password@host:port/database
```

## Полезные команды

```bash
# Просмотр логов
railway logs

# Статус деплоя
railway status

# Перезапуск
railway restart

# Обновление после изменений
railway up
```

## Возможные проблемы

1. **Ошибка с портом**: Приложение настроено на `$PORT`
2. **Ошибка с базой данных**: Проверьте `DATABASE_URL`
3. **Ошибка с зависимостями**: Все в `requirements.txt`

## Поддержка

- Логи: `railway logs`
- Документация: `RAILWAY_DEPLOYMENT.md`
- Тест: `python test_railway.py`
