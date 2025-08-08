#!/usr/bin/env python3
"""
Скрипт для создания тестового админа
"""

from app import app, db, User
from werkzeug.security import generate_password_hash

def create_admin():
    with app.app_context():
        # Создаем базу данных
        db.create_all()
        
        # Проверяем, существует ли уже админ
        admin = User.query.filter_by(login='admin').first()
        if admin:
            print("Админ уже существует!")
            return
        
        # Создаем нового админа
        admin = User(
            full_name='Супер Админ',
            login='admin',
            password=generate_password_hash('admin123'),
            user_type='admin',
            position='Администратор',
            city='Шымкент',
            medical_institution='UMAY System',
            department='IT'
        )
        
        db.session.add(admin)
        db.session.commit()
        
        print("✅ Админ успешно создан!")
        print("Логин: admin")
        print("Пароль: admin123")
        print("URL: http://localhost:5000/admin")

if __name__ == '__main__':
    create_admin()
