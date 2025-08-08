#!/usr/bin/env python3
"""
Скрипт для исправления схемы базы данных PostgreSQL
Исправляет ограничения полей в таблице user
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

def fix_database_schema():
    """Исправляет схему базы данных для совместимости с регистрацией"""
    
    # Получаем DATABASE_URL из переменных окружения
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        print("❌ DATABASE_URL не найден в переменных окружения")
        return False
    
    try:
        # Создаем подключение к базе данных
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            print("🔧 Исправление схемы базы данных...")
            
            # Проверяем текущую схему таблицы user
            result = conn.execute(text("""
                SELECT column_name, data_type, character_maximum_length 
                FROM information_schema.columns 
                WHERE table_name = 'user'
                ORDER BY ordinal_position;
            """))
            
            columns = result.fetchall()
            print("📊 Текущая схема таблицы user:")
            for col in columns:
                print(f"  - {col[0]}: {col[1]}{f'({col[2]})' if col[2] else ''}")
            
            # Исправляем ограничения полей
            print("\n🔧 Исправление ограничений полей...")
            
            # 1. Изменяем user_type с character(1) на varchar(10)
            try:
                conn.execute(text("ALTER TABLE \"user\" ALTER COLUMN user_type TYPE varchar(10);"))
                print("✅ user_type изменен на varchar(10)")
            except Exception as e:
                print(f"⚠️  user_type уже исправлен или ошибка: {e}")
            
            # 2. Изменяем position с varchar(50) на varchar(100)
            try:
                conn.execute(text("ALTER TABLE \"user\" ALTER COLUMN position TYPE varchar(100);"))
                print("✅ position изменен на varchar(100)")
            except Exception as e:
                print(f"⚠️  position уже исправлен или ошибка: {e}")
            
            # 3. Изменяем city с varchar(50) на varchar(100)
            try:
                conn.execute(text("ALTER TABLE \"user\" ALTER COLUMN city TYPE varchar(100);"))
                print("✅ city изменен на varchar(100)")
            except Exception as e:
                print(f"⚠️  city уже исправлен или ошибка: {e}")
            
            # 4. Изменяем medical_institution с varchar(100) на varchar(200)
            try:
                conn.execute(text("ALTER TABLE \"user\" ALTER COLUMN medical_institution TYPE varchar(200);"))
                print("✅ medical_institution изменен на varchar(200)")
            except Exception as e:
                print(f"⚠️  medical_institution уже исправлен или ошибка: {e}")
            
            # 5. Изменяем department с varchar(100) на varchar(200)
            try:
                conn.execute(text("ALTER TABLE \"user\" ALTER COLUMN department TYPE varchar(200);"))
                print("✅ department изменен на varchar(200)")
            except Exception as e:
                print(f"⚠️  department уже исправлен или ошибка: {e}")
            
            # Проверяем обновленную схему
            result = conn.execute(text("""
                SELECT column_name, data_type, character_maximum_length 
                FROM information_schema.columns 
                WHERE table_name = 'user'
                ORDER BY ordinal_position;
            """))
            
            columns = result.fetchall()
            print("\n📊 Обновленная схема таблицы user:")
            for col in columns:
                print(f"  - {col[0]}: {col[1]}{f'({col[2]})' if col[2] else ''}")
            
            conn.commit()
            print("\n✅ Схема базы данных успешно исправлена!")
            return True
            
    except SQLAlchemyError as e:
        print(f"❌ Ошибка при исправлении схемы: {e}")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False

def test_registration():
    """Тестирует регистрацию с исправленной схемой"""
    try:
        from app import app, db, User
        from werkzeug.security import generate_password_hash
        
        with app.app_context():
            # Пытаемся создать тестового пользователя
            test_user = User(
                full_name='Test User',
                login='testuser',
                password=generate_password_hash('password123'),
                user_type='user',
                position='Пользователь',
                city='Не указан',
                medical_institution='Не указано',
                department='Не указано'
            )
            
            db.session.add(test_user)
            db.session.commit()
            
            # Удаляем тестового пользователя
            db.session.delete(test_user)
            db.session.commit()
            
            print("✅ Тест регистрации прошел успешно!")
            return True
            
    except Exception as e:
        print(f"❌ Тест регистрации не прошел: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Запуск исправления схемы базы данных...")
    
    if fix_database_schema():
        print("\n🧪 Тестирование регистрации...")
        if test_registration():
            print("\n🎉 ВСЕ ИСПРАВЛЕНО! Регистрация теперь работает!")
        else:
            print("\n⚠️  Схема исправлена, но тест не прошел")
    else:
        print("\n❌ Не удалось исправить схему базы данных")
