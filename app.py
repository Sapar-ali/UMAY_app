from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import pandas as pd
import io
import os
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////Users/sapargali/Desktop/UMAY_stat/data/umay.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Модели базы данных
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    login = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    position = db.Column(db.String(50), nullable=False)
    medical_institution = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(20), nullable=False)
    patient_name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    pregnancy_weeks = db.Column(db.Integer, nullable=False)
    weight_before = db.Column(db.Float, nullable=False)
    weight_after = db.Column(db.Float, nullable=False)
    complications = db.Column(db.Text)
    notes = db.Column(db.Text)
    midwife = db.Column(db.String(100), nullable=False)
    birth_date = db.Column(db.String(20), nullable=False)
    birth_time = db.Column(db.String(10), nullable=False)
    child_gender = db.Column(db.String(10), nullable=False)
    child_weight = db.Column(db.Integer, nullable=False)
    delivery_method = db.Column(db.String(50), nullable=False)
    anesthesia = db.Column(db.String(50), nullable=False)
    blood_loss = db.Column(db.Integer, nullable=False)
    labor_duration = db.Column(db.Float, nullable=False)
    other_diseases = db.Column(db.Text)
    gestosis = db.Column(db.String(10), nullable=False)
    diabetes = db.Column(db.String(10), nullable=False)
    hypertension = db.Column(db.String(10), nullable=False)
    anemia = db.Column(db.String(10), nullable=False)
    infections = db.Column(db.String(10), nullable=False)
    placenta_pathology = db.Column(db.String(10), nullable=False)
    polyhydramnios = db.Column(db.String(10), nullable=False)
    oligohydramnios = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Маршруты
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login = request.form.get('login')
        password = request.form.get('password')
        
        user = User.query.filter_by(login=login).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Успешный вход в систему!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Неверный логин или пароль!', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        login = request.form.get('login')
        password = request.form.get('password')
        position = request.form.get('position')
        medical_institution = request.form.get('medical_institution')
        
        if User.query.filter_by(login=login).first():
            flash('Этот логин уже занят!', 'error')
            return render_template('register.html')
        
        hashed_password = generate_password_hash(password)
        new_user = User(
            full_name=full_name,
            login=login,
            password=hashed_password,
            position=position,
            medical_institution=medical_institution
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Регистрация успешно завершена!', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы!', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    patients = Patient.query.all()
    total_patients = len(patients)
    natural_births = len([p for p in patients if p.delivery_method == 'Естественные роды'])
    c_sections = len([p for p in patients if p.delivery_method == 'Кесарево сечение'])
    
    # Статистика по полу детей
    boys = len([p for p in patients if p.child_gender == 'Мальчик'])
    girls = len([p for p in patients if p.child_gender == 'Девочка'])
    
    # Средние показатели
    avg_age = sum(p.age for p in patients) / len(patients) if patients else 0
    avg_child_weight = sum(p.child_weight for p in patients) / len(patients) if patients else 0
    
    # Получаем последние 10 пациентов для отображения в таблице
    recent_patients = Patient.query.order_by(Patient.created_at.desc()).limit(10).all()
    
    return render_template('dashboard.html',
                         total_patients=total_patients,
                         natural_births=natural_births,
                         c_sections=c_sections,
                         boys=boys,
                         girls=girls,
                         avg_age=avg_age,
                         avg_child_weight=avg_child_weight,
                         patients=recent_patients)

@app.route('/add_patient', methods=['GET', 'POST'])
@login_required
def add_patient():
    if request.method == 'POST':
        patient_data = {
            'date': datetime.now().strftime("%Y-%m-%d %H:%M"),
            'patient_name': request.form.get('patient_name'),
            'age': int(request.form.get('age')),
            'pregnancy_weeks': int(request.form.get('pregnancy_weeks')),
            'weight_before': float(request.form.get('weight_before')),
            'weight_after': float(request.form.get('weight_after')),
            'complications': request.form.get('complications'),
            'notes': request.form.get('notes'),
            'midwife': current_user.full_name,
            'birth_date': request.form.get('birth_date'),
            'birth_time': request.form.get('birth_time'),
            'child_gender': request.form.get('child_gender'),
            'child_weight': int(request.form.get('child_weight')),
            'delivery_method': request.form.get('delivery_method'),
            'anesthesia': request.form.get('anesthesia'),
            'blood_loss': int(request.form.get('blood_loss')),
            'labor_duration': float(request.form.get('labor_duration')),
            'other_diseases': request.form.get('other_diseases'),
            'gestosis': 'Да' if request.form.get('gestosis') else 'Нет',
            'diabetes': 'Да' if request.form.get('diabetes') else 'Нет',
            'hypertension': 'Да' if request.form.get('hypertension') else 'Нет',
            'anemia': 'Да' if request.form.get('anemia') else 'Нет',
            'infections': 'Да' if request.form.get('infections') else 'Нет',
            'placenta_pathology': 'Да' if request.form.get('placenta_pathology') else 'Нет',
            'polyhydramnios': 'Да' if request.form.get('polyhydramnios') else 'Нет',
            'oligohydramnios': 'Да' if request.form.get('oligohydramnios') else 'Нет'
        }
        
        new_patient = Patient(**patient_data)
        db.session.add(new_patient)
        db.session.commit()
        
        flash('Данные роженицы успешно сохранены!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('add_patient.html')

@app.route('/search')
@login_required
def search():
    patients = Patient.query.all()
    
    # Применение фильтров
    filtered_patients = patients
    
    # Поиск по ФИО
    search_term = request.args.get('search', '').strip()
    if search_term:
        filtered_patients = [p for p in filtered_patients if search_term.lower() in p.patient_name.lower()]
    
    # Фильтр по датам
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    if date_from:
        filtered_patients = [p for p in filtered_patients if p.birth_date >= date_from]
    if date_to:
        filtered_patients = [p for p in filtered_patients if p.birth_date <= date_to]
    
    # Фильтр по акушеркам
    selected_midwives = request.args.getlist('midwives')
    if selected_midwives:
        filtered_patients = [p for p in filtered_patients if p.midwife in selected_midwives]
    
    # Фильтр по способу родоразрешения
    selected_methods = request.args.getlist('delivery_methods')
    if selected_methods:
        filtered_patients = [p for p in filtered_patients if p.delivery_method in selected_methods]
    
    # Фильтр по полу ребенка
    selected_genders = request.args.getlist('genders')
    if selected_genders:
        filtered_patients = [p for p in filtered_patients if p.child_gender in selected_genders]
    
    # Фильтр по возрасту
    age_min = request.args.get('age_min', '')
    age_max = request.args.get('age_max', '')
    if age_min:
        filtered_patients = [p for p in filtered_patients if p.age >= int(age_min)]
    if age_max:
        filtered_patients = [p for p in filtered_patients if p.age <= int(age_max)]
    
    # Фильтр по весу ребенка
    weight_min = request.args.get('weight_min', '')
    weight_max = request.args.get('weight_max', '')
    if weight_min:
        filtered_patients = [p for p in filtered_patients if p.child_weight >= int(weight_min)]
    if weight_max:
        filtered_patients = [p for p in filtered_patients if p.child_weight <= int(weight_max)]
    
    return render_template('search.html', patients=patients, filtered_patients=filtered_patients)

@app.route('/export_csv')
@login_required
def export_csv():
    patients = Patient.query.all()
    
    # Применение тех же фильтров, что и в поиске
    filtered_patients = patients
    
    # Поиск по ФИО
    search_term = request.args.get('search', '').strip()
    if search_term:
        filtered_patients = [p for p in filtered_patients if search_term.lower() in p.patient_name.lower()]
    
    # Фильтр по датам
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    if date_from:
        filtered_patients = [p for p in filtered_patients if p.birth_date >= date_from]
    if date_to:
        filtered_patients = [p for p in filtered_patients if p.birth_date <= date_to]
    
    # Фильтр по акушеркам
    selected_midwives = request.args.getlist('midwives')
    if selected_midwives:
        filtered_patients = [p for p in filtered_patients if p.midwife in selected_midwives]
    
    # Фильтр по способу родоразрешения
    selected_methods = request.args.getlist('delivery_methods')
    if selected_methods:
        filtered_patients = [p for p in filtered_patients if p.delivery_method in selected_methods]
    
    # Фильтр по полу ребенка
    selected_genders = request.args.getlist('genders')
    if selected_genders:
        filtered_patients = [p for p in filtered_patients if p.child_gender in selected_genders]
    
    # Фильтр по возрасту
    age_min = request.args.get('age_min', '')
    age_max = request.args.get('age_max', '')
    if age_min:
        filtered_patients = [p for p in filtered_patients if p.age >= int(age_min)]
    if age_max:
        filtered_patients = [p for p in filtered_patients if p.age <= int(age_max)]
    
    # Фильтр по весу ребенка
    weight_min = request.args.get('weight_min', '')
    weight_max = request.args.get('weight_max', '')
    if weight_min:
        filtered_patients = [p for p in filtered_patients if p.child_weight >= int(weight_min)]
    if weight_max:
        filtered_patients = [p for p in filtered_patients if p.child_weight <= int(weight_max)]
    
    data = []
    for patient in filtered_patients:
        data.append({
            'Дата': patient.date,
            'ФИО роженицы': patient.patient_name,
            'Возраст': patient.age,
            'Срок беременности': patient.pregnancy_weeks,
            'Вес до родов': patient.weight_before,
            'Вес после родов': patient.weight_after,
            'Осложнения': patient.complications,
            'Примечания': patient.notes,
            'Акушерка': patient.midwife,
            'Дата родов': patient.birth_date,
            'Время родов': patient.birth_time,
            'Пол ребенка': patient.child_gender,
            'Вес ребенка': patient.child_weight,
            'Способ родоразрешения': patient.delivery_method,
            'Анестезия': patient.anesthesia,
            'Кровопотеря': patient.blood_loss,
            'Продолжительность родов': patient.labor_duration,
            'Сопутствующие заболевания': patient.other_diseases,
            'Гестоз': patient.gestosis,
            'Сахарный диабет': patient.diabetes,
            'Гипертония': patient.hypertension,
            'Анемия': patient.anemia,
            'Инфекции': patient.infections,
            'Патология плаценты': patient.placenta_pathology,
            'Многоводие': patient.polyhydramnios,
            'Маловодие': patient.oligohydramnios
        })
    
    df = pd.DataFrame(data)
    output = io.StringIO()
    df.to_csv(output, index=False, encoding='utf-8-sig')
    output.seek(0)
    
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'umay_report_{datetime.now().strftime("%Y%m%d_%H%M")}.csv'
    )

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5001) 