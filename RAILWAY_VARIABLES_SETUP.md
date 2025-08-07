# 🔧 Настройка переменных окружения в Railway

## ✅ Автоматические переменные Railway

Railway автоматически предоставляет следующие переменные для PostgreSQL:

- `PGUSER` - имя пользователя
- `POSTGRES_PASSWORD` - пароль
- `RAILWAY_PRIVATE_DOMAIN` - хост базы данных
- `PGDATABASE` - название базы данных

## 🔧 Ручная настройка переменных

В Railway Dashboard → Variables добавьте:

### Обязательные переменные:
```
SECRET_KEY=your-very-secure-secret-key-here
FLASK_ENV=production
RAILWAY=true
```

### Для PostgreSQL (если нужно вручную):
```
DATABASE_URL=postgresql://username:password@host:5432/database
```

## 🚨 Важно!

**НЕ добавляйте вручную переменные PostgreSQL**, если Railway их уже предоставляет автоматически:

- ❌ `PGUSER`
- ❌ `POSTGRES_PASSWORD` 
- ❌ `RAILWAY_PRIVATE_DOMAIN`
- ❌ `PGDATABASE`

Эти переменные Railway создает автоматически при подключении PostgreSQL сервиса.

## 🔍 Проверка переменных

В Railway Dashboard → Variables вы должны увидеть:

### Автоматические (от Railway):
- `PGUSER`
- `POSTGRES_PASSWORD`
- `RAILWAY_PRIVATE_DOMAIN`
- `PGDATABASE`

### Ручные (добавьте сами):
- `SECRET_KEY`
- `FLASK_ENV`
- `RAILWAY`

## 🐛 Устранение проблем

### Проблема: База данных не подключается
**Решение:**
1. Убедитесь, что PostgreSQL сервис создан
2. Проверьте, что все автоматические переменные присутствуют
3. Добавьте `RAILWAY=true`

### Проблема: Приложение не запускается
**Решение:**
1. Добавьте `SECRET_KEY`
2. Добавьте `FLASK_ENV=production`
3. Добавьте `RAILWAY=true`

### Проблема: Ошибка с переменными
**Решение:**
1. НЕ добавляйте вручную переменные PostgreSQL
2. Позвольте Railway создать их автоматически
3. Перезапустите деплой: `railway up`

## 📋 Полный список переменных

### Автоматические (Railway):
```
PGUSER=postgres
POSTGRES_PASSWORD=your_password
RAILWAY_PRIVATE_DOMAIN=your_host
PGDATABASE=your_database
```

### Ручные (добавьте):
```
SECRET_KEY=your-very-secure-secret-key-here
FLASK_ENV=production
RAILWAY=true
```

## ✅ Проверка

После настройки:
1. Перезапустите деплой: `railway up`
2. Проверьте логи: `railway logs`
3. Убедитесь, что видите: "✅ Using Railway PostgreSQL database"
