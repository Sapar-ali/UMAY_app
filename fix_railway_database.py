#!/usr/bin/env python3
"""
Скрипт для исправления базы данных на Railway
Создает таблицу patient и добавляет тестовые данные
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime

def fix_railway_database():
    """Исправляет базу данных на Railway"""
    
    # Получаем DATABASE_URL из переменных окружения
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        print("❌ DATABASE_URL не найден в переменных окружения")
        return False
    
    try:
        # Создаем подключение к базе данных
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            print("🔧 Исправление базы данных Railway...")
            
            # Проверяем, существует ли таблица patient
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'patient'
                );
            """))
            
            table_exists = result.fetchone()[0]
            
            if not table_exists:
                print("📋 Создание таблицы patient...")
                
                # Создаем таблицу patient
                conn.execute(text("""
                    CREATE TABLE patient (
                        id SERIAL PRIMARY KEY,
                        date VARCHAR(20) NOT NULL,
                        patient_name VARCHAR(100) NOT NULL,
                        age INTEGER NOT NULL,
                        pregnancy_weeks INTEGER NOT NULL,
                        weight_before FLOAT NOT NULL,
                        weight_after FLOAT NOT NULL,
                        complications TEXT,
                        notes TEXT,
                        midwife VARCHAR(100) NOT NULL,
                        birth_date VARCHAR(20) NOT NULL,
                        birth_time VARCHAR(10) NOT NULL,
                        child_gender VARCHAR(10) NOT NULL,
                        child_weight INTEGER NOT NULL,
                        delivery_method VARCHAR(50) NOT NULL,
                        anesthesia VARCHAR(50) NOT NULL,
                        blood_loss INTEGER NOT NULL,
                        labor_duration FLOAT NOT NULL,
                        other_diseases TEXT,
                        gestosis VARCHAR(10) NOT NULL,
                        diabetes VARCHAR(10) NOT NULL,
                        hypertension VARCHAR(10) NOT NULL,
                        anemia VARCHAR(10) NOT NULL,
                        infections VARCHAR(10) NOT NULL,
                        placenta_pathology VARCHAR(10) NOT NULL,
                        polyhydramnios VARCHAR(10) NOT NULL,
                        oligohydramnios VARCHAR(10) NOT NULL,
                        pls VARCHAR(10) NOT NULL,
                        pts VARCHAR(10) NOT NULL,
                        eclampsia VARCHAR(10) NOT NULL,
                        gestational_hypertension VARCHAR(10) NOT NULL,
                        placenta_previa VARCHAR(10) NOT NULL,
                        shoulder_dystocia VARCHAR(10) NOT NULL,
                        third_degree_tear VARCHAR(10) NOT NULL,
                        cord_prolapse VARCHAR(10) NOT NULL,
                        postpartum_hemorrhage VARCHAR(10) NOT NULL,
                        placental_abruption VARCHAR(10) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """))
                print("✅ Таблица patient создана")
            else:
                print("✅ Таблица patient уже существует")
            
            # Проверяем, есть ли данные в таблице
            result = conn.execute(text("SELECT COUNT(*) FROM patient;"))
            count = result.fetchone()[0]
            
            if count == 0:
                print("📊 Добавление тестовых данных...")
                
                # Добавляем тестовые данные
                test_data = [
                    {
                        'date': '2024-01-15',
                        'patient_name': 'Анна Иванова',
                        'age': 28,
                        'pregnancy_weeks': 39,
                        'weight_before': 65.5,
                        'weight_after': 70.2,
                        'complications': 'Нет',
                        'notes': 'Нормальные роды',
                        'midwife': 'Доктор Петрова',
                        'birth_date': '2024-01-15',
                        'birth_time': '14:30',
                        'child_gender': 'Девочка',
                        'child_weight': 3200,
                        'delivery_method': 'Естественные роды',
                        'anesthesia': 'Эпидуральная анестезия',
                        'blood_loss': 450,
                        'labor_duration': 8.5,
                        'other_diseases': 'Нет',
                        'gestosis': 'Нет',
                        'diabetes': 'Нет',
                        'hypertension': 'Нет',
                        'anemia': 'Нет',
                        'infections': 'Нет',
                        'placenta_pathology': 'Нет',
                        'polyhydramnios': 'Нет',
                        'oligohydramnios': 'Нет',
                        'pls': 'Нет',
                        'pts': 'Нет',
                        'eclampsia': 'Нет',
                        'gestational_hypertension': 'Нет',
                        'placenta_previa': 'Нет',
                        'shoulder_dystocia': 'Нет',
                        'third_degree_tear': 'Нет',
                        'cord_prolapse': 'Нет',
                        'postpartum_hemorrhage': 'Нет',
                        'placental_abruption': 'Нет'
                    },
                    {
                        'date': '2024-02-20',
                        'patient_name': 'Мария Сидорова',
                        'age': 32,
                        'pregnancy_weeks': 38,
                        'weight_before': 68.0,
                        'weight_after': 72.5,
                        'complications': 'Гестоз',
                        'notes': 'Осложненные роды',
                        'midwife': 'Доктор Козлова',
                        'birth_date': '2024-02-20',
                        'birth_time': '16:45',
                        'child_gender': 'Мальчик',
                        'child_weight': 3500,
                        'delivery_method': 'Кесарево сечение',
                        'anesthesia': 'Общая анестезия',
                        'blood_loss': 800,
                        'labor_duration': 12.0,
                        'other_diseases': 'Нет',
                        'gestosis': 'Да',
                        'diabetes': 'Нет',
                        'hypertension': 'Да',
                        'anemia': 'Нет',
                        'infections': 'Нет',
                        'placenta_pathology': 'Нет',
                        'polyhydramnios': 'Нет',
                        'oligohydramnios': 'Нет',
                        'pls': 'Да',
                        'pts': 'Нет',
                        'eclampsia': 'Нет',
                        'gestational_hypertension': 'Нет',
                        'placenta_previa': 'Нет',
                        'shoulder_dystocia': 'Нет',
                        'third_degree_tear': 'Нет',
                        'cord_prolapse': 'Нет',
                        'postpartum_hemorrhage': 'Нет',
                        'placental_abruption': 'Нет'
                    },
                    {
                        'date': '2024-03-10',
                        'patient_name': 'Елена Петрова',
                        'age': 25,
                        'pregnancy_weeks': 40,
                        'weight_before': 62.0,
                        'weight_after': 66.8,
                        'complications': 'ПРК',
                        'notes': 'Послеродовое кровотечение',
                        'midwife': 'Доктор Иванова',
                        'birth_date': '2024-03-10',
                        'birth_time': '09:15',
                        'child_gender': 'Девочка',
                        'child_weight': 3100,
                        'delivery_method': 'Естественные роды',
                        'anesthesia': 'Без анестезии',
                        'blood_loss': 1200,
                        'labor_duration': 6.5,
                        'other_diseases': 'Нет',
                        'gestosis': 'Нет',
                        'diabetes': 'Нет',
                        'hypertension': 'Нет',
                        'anemia': 'Нет',
                        'infections': 'Нет',
                        'placenta_pathology': 'Нет',
                        'polyhydramnios': 'Нет',
                        'oligohydramnios': 'Нет',
                        'pls': 'Нет',
                        'pts': 'Нет',
                        'eclampsia': 'Нет',
                        'gestational_hypertension': 'Нет',
                        'placenta_previa': 'Нет',
                        'shoulder_dystocia': 'Нет',
                        'third_degree_tear': 'Нет',
                        'cord_prolapse': 'Нет',
                        'postpartum_hemorrhage': 'Да',
                        'placental_abruption': 'Нет'
                    }
                ]
                
                for data in test_data:
                    conn.execute(text("""
                        INSERT INTO patient (
                            date, patient_name, age, pregnancy_weeks, weight_before, weight_after,
                            complications, notes, midwife, birth_date, birth_time, child_gender,
                            child_weight, delivery_method, anesthesia, blood_loss, labor_duration,
                            other_diseases, gestosis, diabetes, hypertension, anemia, infections,
                            placenta_pathology, polyhydramnios, oligohydramnios, pls, pts, eclampsia,
                            gestational_hypertension, placenta_previa, shoulder_dystocia, third_degree_tear,
                            cord_prolapse, postpartum_hemorrhage, placental_abruption
                        ) VALUES (
                            :date, :patient_name, :age, :pregnancy_weeks, :weight_before, :weight_after,
                            :complications, :notes, :midwife, :birth_date, :birth_time, :child_gender,
                            :child_weight, :delivery_method, :anesthesia, :blood_loss, :labor_duration,
                            :other_diseases, :gestosis, :diabetes, :hypertension, :anemia, :infections,
                            :placenta_pathology, :polyhydramnios, :oligohydramnios, :pls, :pts, :eclampsia,
                            :gestational_hypertension, :placenta_previa, :shoulder_dystocia, :third_degree_tear,
                            :cord_prolapse, :postpartum_hemorrhage, :placental_abruption
                        )
                    """), data)
                
                print("✅ Тестовые данные добавлены")
            else:
                print(f"✅ В таблице уже есть {count} записей")
            
            # Проверяем финальную статистику
            result = conn.execute(text("SELECT COUNT(*) FROM patient;"))
            final_count = result.fetchone()[0]
            
            print(f"\n📊 Финальная статистика:")
            print(f"  - Всего пациентов: {final_count}")
            
            conn.commit()
            print("\n✅ База данных Railway успешно исправлена!")
            return True
            
    except SQLAlchemyError as e:
        print(f"❌ Ошибка при исправлении базы данных: {e}")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Запуск исправления базы данных Railway...")
    
    if fix_railway_database():
        print("\n🎉 БАЗА ДАННЫХ ИСПРАВЛЕНА! Аналитика теперь должна работать!")
    else:
        print("\n❌ Не удалось исправить базу данных")
