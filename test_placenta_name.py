#!/usr/bin/env python3
"""
Скрипт для тестирования нового названия "Плотное прикрепление последа"
"""

from app import app, db, Patient
from datetime import datetime

def test_placenta_name():
    """Тестируем новое название"""
    with app.app_context():
        print("🔍 Тестируем новое название 'Плотное прикрепление последа'...")
        
        # Создаем тестового пациента с новым осложнением
        test_patient = Patient(
            date=datetime.now().strftime("%Y-%m-%d %H:%M"),
            patient_name="Тестовая роженица с плотным прикреплением",
            age=29,
            pregnancy_weeks=38,
            weight_before=68.0,
            weight_after=63.0,
            complications="",
            notes="",
            midwife="Тестовая акушерка",
            birth_date="2024-01-30",
            birth_time="12:15",
            child_gender="Мальчик",
            child_weight=3400,
            delivery_method="Естественные роды",
            anesthesia="Эпидуральная анестезия",
            blood_loss=600,
            labor_duration=7.5,
            other_diseases="",
            gestosis="Нет",
            diabetes="Нет",
            hypertension="Нет",
            anemia="Нет",
            infections="Нет",
            placenta_pathology="Нет",
            polyhydramnios="Нет",
            oligohydramnios="Нет",
            pls="Нет",
            pts="Нет",
            eclampsia="Нет",
            gestational_hypertension="Нет",
            placenta_previa="Да",  # Плотное прикрепление последа
            shoulder_dystocia="Нет",
            third_degree_tear="Нет",
            cord_prolapse="Нет",
            postpartum_hemorrhage="Нет",
            placental_abruption="Нет"
        )
        
        try:
            db.session.add(test_patient)
            db.session.commit()
            print("✅ Тестовый пациент с плотным прикреплением добавлен успешно!")
            
            # Проверяем, что поле сохранилось
            saved_patient = Patient.query.filter_by(patient_name="Тестовая роженица с плотным прикреплением").first()
            if saved_patient:
                print("\n📊 Проверяем сохраненное осложнение:")
                print(f"✅ Плотное прикрепление последа: {saved_patient.placenta_previa}")
                print(f"✅ Кровопотеря: {saved_patient.blood_loss} мл")
                
                # Удаляем тестового пациента
                db.session.delete(saved_patient)
                db.session.commit()
                print("\n✅ Тестовый пациент удален")
            else:
                print("❌ Не удалось найти тестового пациента")
                
        except Exception as e:
            print(f"❌ Ошибка при тестировании: {e}")
            db.session.rollback()

if __name__ == "__main__":
    test_placenta_name()
