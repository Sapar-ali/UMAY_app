from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import pandas as pd
import io
import os
import sys
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ============================================================================
# UMAY APP - ПРОСТАЯ ВЕРСИЯ ДЛЯ RENDER И RAILWAY
# Версия: 5.1 - Поддержка Render и Railway
# ОБНОВЛЕНИЕ: Исправлена ошибка 500 - CSS классы и обработка ошибок
# ============================================================================

# Настройка логирования
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info("=== UMAY APP STARTING - SIMPLE VERSION v5.0 ===")

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')

# Создаем папку data если её нет
try:
    os.makedirs('data', exist_ok=True)
    logger.info("Data directory created/verified")
except Exception as e:
    logger.error(f"Ошибка при создании папки data: {e}")
    print(f"Ошибка при создании папки data: {e}")

# ПРОСТАЯ НАСТРОЙКА БАЗЫ ДАННЫХ - SQLITE И POSTGRESQL
# Проверяем наличие PostgreSQL URL от Render или Railway
DATABASE_URL = os.environ.get('DATABASE_URL')

# Проверяем Railway PostgreSQL переменные
if not DATABASE_URL and os.environ.get('RAILWAY'):
    # Railway автоматически предоставляет эти переменные
    pg_user = os.environ.get('PGUSER')
    pg_password = os.environ.get('POSTGRES_PASSWORD')
    pg_host = os.environ.get('RAILWAY_PRIVATE_DOMAIN')
    pg_database = os.environ.get('PGDATABASE')
    
    if all([pg_user, pg_password, pg_host, pg_database]):
        DATABASE_URL = f"postgresql://{pg_user}:{pg_password}@{pg_host}:5432/{pg_database}"
        logger.info("✅ Constructed Railway PostgreSQL URL from environment variables")

if DATABASE_URL and (DATABASE_URL.startswith('postgres://') or DATABASE_URL.startswith('postgresql://')):
    # PostgreSQL на Render или Railway - попробуем без специальных библиотек
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
    if os.environ.get('RENDER'):
        logger.info("✅ Using Render PostgreSQL database")
    elif os.environ.get('RAILWAY'):
        logger.info("✅ Using Railway PostgreSQL database")
    else:
        logger.info("✅ Using PostgreSQL database")
    logger.info(f"PostgreSQL URL: {DATABASE_URL[:50]}...")  # Показываем только начало URL
    logger.info("⚠️ Попытка подключения без psycopg2")
elif os.environ.get('RENDER'):
    # SQLite на Render (fallback)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/umay.db'
    logger.info("✅ Using Render SQLite database in /tmp")
elif os.environ.get('RAILWAY'):
    # SQLite на Railway (fallback)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/umay.db'
    logger.info("✅ Using Railway SQLite database in /tmp")
else:
    # Локально используем абсолютный путь
    current_dir = os.getcwd()
    db_path = os.path.join(current_dir, 'data', 'umay.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    logger.info("✅ Using local SQLite database with absolute path")

logger.info(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Данные о городах и медицинских учреждениях с отделениями
CITIES_DATA = {
    "Шымкент": {
        "Городской перинатальный центр": [
            "Родильное отделение",
            "Отделение Паталогии",
            "Отделение Физиологии"
        ],
        "ГКП на ПХВ Городской родильный дом": [
            "Родильное отделение",
            "Отделение Паталогии",
            "Отделение Физиологии"
        ],
        "Городская больница - 2": [
            "Родильное отделение",
            "Отделение Паталогии",
            "Отделение Физиологии"
        ],
        "Городская больница - 3": [
            "Родильное отделение",
            "Отделение Паталогии",
            "Отделение Физиологии"
        ]
    },
    "ЮКО": {
        "Скоро добавим...": ["Скоро добавим..."]
    },
    "Астана": {
        "Скоро добавим...": ["Скоро добавим..."]
    }
}

# Инициализация базы данных
with app.app_context():
    try:
        db.create_all()
        logger.info("✅ База данных успешно инициализирована")
    except Exception as e:
        logger.error(f"❌ Ошибка при инициализации базы данных: {e}")
        print(f"❌ Ошибка при инициализации базы данных: {e}")

# Модели базы данных
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    login = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    user_type = db.Column(db.String(20), default='user')  # user или midwife
    position = db.Column(db.String(50), nullable=False)
    city = db.Column(db.String(50), nullable=False)
    medical_institution = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(100), nullable=False)  # Новое поле для отделения
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# CMS Модели для контента
class News(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    short_description = db.Column(db.Text, nullable=False)
    full_content = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(500))
    category = db.Column(db.String(50), default='general')
    author = db.Column(db.String(100))
    published_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_published = db.Column(db.Boolean, default=True)
    views = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class MamaContent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)  # sport, nutrition, vitamins, body_care, baby_care, doctor_advice
    image_url = db.Column(db.String(500))
    video_url = db.Column(db.String(500))
    trimester = db.Column(db.String(20))  # 1, 2, 3, all
    difficulty_level = db.Column(db.String(20))  # easy, medium, hard
    duration = db.Column(db.String(50))  # для упражнений
    author = db.Column(db.String(100))
    is_published = db.Column(db.Boolean, default=True)
    views = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class MediaFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    original_filename = db.Column(db.String(200), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)  # image, video, document
    file_size = db.Column(db.Integer)
    uploaded_by = db.Column(db.String(100))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

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
    return db.session.get(User, int(user_id))

# Создание таблиц при запуске
with app.app_context():
    try:
        logger.info("🔄 Создание таблиц базы данных...")
        logger.info(f"Текущая директория: {os.getcwd()}")
        logger.info(f"Путь к базе данных: {app.config['SQLALCHEMY_DATABASE_URI']}")
        db.create_all()
        logger.info("✅ Таблицы успешно созданы")
        
        # Проверяем и добавляем колонку department если её нет
        try:
            logger.info("🔄 Проверка колонки department...")
            # Проверяем существование колонки department
            result = db.engine.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'user' AND column_name = 'department'
            """).fetchone()
            
            if not result:
                logger.info("🔄 Добавление колонки department...")
                # Добавляем колонку department с правильным синтаксисом
                db.engine.execute('ALTER TABLE "user" ADD COLUMN department VARCHAR(100) DEFAULT \'Не указано\'')
                logger.info("✅ Колонка department добавлена")
                
                # Обновляем существующие записи
                db.engine.execute('UPDATE "user" SET department = \'Не указано\' WHERE department IS NULL')
                logger.info("✅ Существующие записи обновлены")
            else:
                logger.info("✅ Колонка department уже существует")
        except Exception as e:
            logger.error(f"❌ Ошибка при работе с колонкой department: {e}")
            # Если не удалось добавить колонку, продолжаем работу
            pass
        
        # Создание супер-админа если его нет
        admin_user = User.query.filter_by(login='Joker').first()
        if not admin_user:
            admin_user = User(
                full_name='Супер Администратор',
                login='Joker',
                password=generate_password_hash('19341934'),
                user_type='midwife',
                position='Главный администратор',
                city='Алматы',
                medical_institution='UMAY System',
                department='Системное отделение'
            )
            db.session.add(admin_user)
            db.session.commit()
            logger.info("✅ Супер-админ создан: login=Joker, password=19341934")
    except Exception as e:
        logger.error(f"❌ Ошибка при создании таблиц: {e}")
        print(f"❌ Ошибка при создании таблиц: {e}")
        import traceback
        traceback.print_exc()

# Маршруты
@app.route('/')
def index():
    # Получаем последние 6 опубликованных новостей
    latest_news = News.query.filter_by(is_published=True).order_by(News.published_at.desc()).limit(6).all()
    return render_template('index.html', news=latest_news)

@app.route('/api/cities')
def get_cities():
    """API для получения списка городов"""
    return jsonify(list(CITIES_DATA.keys()))

@app.route('/api/institutions/<city>')
def get_institutions(city):
    """API для получения списка учреждений по городу"""
    if city in CITIES_DATA:
        return jsonify(list(CITIES_DATA[city].keys()))
    return jsonify([])

@app.route('/api/departments/<city>/<institution>')
def get_departments(city, institution):
    """API для получения списка отделений по городу и учреждению"""
    if city in CITIES_DATA and institution in CITIES_DATA[city]:
        return jsonify(CITIES_DATA[city][institution])
    return jsonify([])

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login = request.form['login']
        password = request.form['password']
        
        user = User.query.filter_by(login=login).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Успешный вход!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Неверный логин или пароль!', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user_type = request.form.get('user_type', 'midwife')
        full_name = request.form.get('full_name', '').strip()
        login = request.form.get('login', '').strip()
        password = request.form.get('password', '')
        
        # Валидация данных
        if not full_name:
            flash('Имя обязательно для заполнения!', 'error')
            return render_template('register.html')
        
        if not login:
            flash('Логин обязателен для заполнения!', 'error')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('Пароль должен содержать минимум 6 символов!', 'error')
            return render_template('register.html')
        
        # Проверяем подтверждение пароля
        confirm_password = request.form.get('confirm_password', '')
        if password != confirm_password:
            flash('Пароли не совпадают!', 'error')
            return render_template('register.html')
        
        # Проверяем, существует ли пользователь
        existing_user = User.query.filter_by(login=login).first()
        if existing_user:
            flash('Пользователь с таким логином уже существует!', 'error')
            return render_template('register.html')
        
        # Создаем нового пользователя
        hashed_password = generate_password_hash(password)
        
        if user_type == 'user':
            # Упрощенная регистрация для обычных пользователей
            new_user = User(
                full_name=full_name,
                login=login,
                password=hashed_password,
                user_type='user',
                position='Пользователь',
                city='Не указан',
                medical_institution='Не указано',
                department='Не указано'
            )
        else:
            # Полная регистрация для акушерок
            position = request.form['position']
            city = request.form['city']
            medical_institution = request.form['medical_institution']
            department = request.form.get('department', 'Не указано')
            
            new_user = User(
                full_name=full_name,
                login=login,
                password=hashed_password,
                user_type='midwife',
                position=position,
                city=city,
                medical_institution=medical_institution,
                department=department
            )
        
        try:
            db.session.add(new_user)
            db.session.commit()
            
            if user_type == 'user':
                flash('Регистрация успешна! Добро пожаловать в UMAY Mama!', 'success')
            else:
                flash('Регистрация успешна! Теперь вы можете войти в UMAY Pro.', 'success')
            
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка при регистрации пользователя {login}: {e}")
            flash(f'Ошибка при регистрации: {str(e)}. Попробуйте еще раз.', 'error')
            return render_template('register.html')
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы!', 'success')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    logger.info(f"Dashboard accessed by user: {current_user.full_name} (login: {current_user.login})")
    try:
        # Получаем статистику
        patients = Patient.query.all()
        total_patients = len(patients)
        
        # Статистика по полу
        male_count = sum(1 for p in patients if p.child_gender == 'Мальчик')
        female_count = sum(1 for p in patients if p.child_gender == 'Девочка')
        
        # Статистика по способам родоразрешения
        natural_births = sum(1 for p in patients if p.delivery_method == 'Естественные роды')
        cesarean_count = sum(1 for p in patients if p.delivery_method == 'Кесарево сечение')
        
        # Статистика за этот месяц
        from datetime import datetime
        current_month = datetime.now().month
        current_year = datetime.now().year
        this_month = 0
        
        for patient in patients:
            try:
                birth_date = datetime.strptime(patient.birth_date, '%Y-%m-%d')
                if birth_date.month == current_month and birth_date.year == current_year:
                    this_month += 1
            except:
                continue
        
        # Получаем последние 10 пациентов
        recent_patients = Patient.query.order_by(Patient.id.desc()).limit(10).all()
        
        return render_template('dashboard.html',
                             total_patients=total_patients,
                             male_count=male_count, female_count=female_count,
                             natural_births=natural_births,
                             cesarean_count=cesarean_count,
                             this_month=this_month,
                             patients=recent_patients)
    except Exception as e:
        logger.error(f"Error in dashboard: {e}")
        flash('Ошибка при загрузке панели управления', 'error')
        return redirect(url_for('index'))

@app.route('/add_patient', methods=['GET', 'POST'])
@login_required
def add_patient():
    if request.method == 'POST':
        try:
            # Обработка чекбоксов - если не отмечен, то "Нет"
            gestosis = "Да" if 'gestosis' in request.form else "Нет"
            diabetes = "Да" if 'diabetes' in request.form else "Нет"
            hypertension = "Да" if 'hypertension' in request.form else "Нет"
            anemia = "Да" if 'anemia' in request.form else "Нет"
            infections = "Да" if 'infections' in request.form else "Нет"
            placenta_pathology = "Да" if 'placenta_pathology' in request.form else "Нет"
            polyhydramnios = "Да" if 'polyhydramnios' in request.form else "Нет"
            oligohydramnios = "Да" if 'oligohydramnios' in request.form else "Нет"
            
            # Валидация обязательных полей
            if not request.form['patient_name'] or request.form['patient_name'].strip() == "":
                flash('ФИО роженицы обязательно для заполнения', 'error')
                return render_template('add_patient.html')
            
            if not request.form['child_gender'] or request.form['child_gender'] == "":
                flash('Необходимо выбрать пол ребенка', 'error')
                return render_template('add_patient.html')
            
            if not request.form['delivery_method'] or request.form['delivery_method'] == "":
                flash('Необходимо выбрать способ родоразрешения', 'error')
                return render_template('add_patient.html')
            
            if not request.form['anesthesia'] or request.form['anesthesia'] == "":
                flash('Необходимо выбрать тип анестезии', 'error')
                return render_template('add_patient.html')
            
            new_patient = Patient(
                date=datetime.now().strftime("%Y-%m-%d %H:%M"),
                patient_name=request.form['patient_name'].strip(),
                age=int(request.form['age']),
                pregnancy_weeks=int(request.form['pregnancy_weeks']),
                weight_before=float(request.form['weight_before']),
                weight_after=float(request.form['weight_after']),
                complications=request.form['complications'] or "",
                notes=request.form['notes'] or "",
                midwife=current_user.full_name,
                birth_date=request.form['birth_date'],
                birth_time=request.form['birth_time'],
                child_gender=request.form['child_gender'],
                child_weight=int(request.form['child_weight']),
                delivery_method=request.form['delivery_method'],
                anesthesia=request.form['anesthesia'],
                blood_loss=int(request.form['blood_loss']),
                labor_duration=float(request.form['labor_duration']),
                other_diseases=request.form['other_diseases'] or "",
                gestosis=gestosis,
                diabetes=diabetes,
                hypertension=hypertension,
                anemia=anemia,
                infections=infections,
                placenta_pathology=placenta_pathology,
                polyhydramnios=polyhydramnios,
                oligohydramnios=oligohydramnios
            )
            
            db.session.add(new_patient)
            db.session.commit()
            flash('Пациент успешно добавлен!', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка при добавлении пациента: {e}")
            flash('Ошибка при добавлении пациента. Проверьте данные.', 'error')
    
    return render_template('add_patient.html')

@app.route('/edit_patient/<int:patient_id>', methods=['GET', 'POST'])
@login_required
def edit_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    
    # Проверяем права доступа
    # Супер-админ может редактировать все записи
    # Акушерки могут редактировать только свои записи
    if current_user.login != 'Joker' and patient.midwife != current_user.full_name:
        flash('У вас нет прав для редактирования этой записи', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        try:
            # Обработка чекбоксов - если не отмечен, то "Нет"
            gestosis = "Да" if 'gestosis' in request.form else "Нет"
            diabetes = "Да" if 'diabetes' in request.form else "Нет"
            hypertension = "Да" if 'hypertension' in request.form else "Нет"
            anemia = "Да" if 'anemia' in request.form else "Нет"
            infections = "Да" if 'infections' in request.form else "Нет"
            placenta_pathology = "Да" if 'placenta_pathology' in request.form else "Нет"
            polyhydramnios = "Да" if 'polyhydramnios' in request.form else "Нет"
            oligohydramnios = "Да" if 'oligohydramnios' in request.form else "Нет"
            
            # Валидация обязательных полей
            if not request.form['patient_name'] or request.form['patient_name'].strip() == "":
                flash('ФИО роженицы обязательно для заполнения', 'error')
                return render_template('edit_patient.html', patient=patient)
            
            if not request.form['child_gender'] or request.form['child_gender'] == "":
                flash('Необходимо выбрать пол ребенка', 'error')
                return render_template('edit_patient.html', patient=patient)
            
            if not request.form['delivery_method'] or request.form['delivery_method'] == "":
                flash('Необходимо выбрать способ родоразрешения', 'error')
                return render_template('edit_patient.html', patient=patient)
            
            if not request.form['anesthesia'] or request.form['anesthesia'] == "":
                flash('Необходимо выбрать тип анестезии', 'error')
                return render_template('edit_patient.html', patient=patient)
            
            # Обновляем данные пациента
            patient.patient_name = request.form['patient_name'].strip()
            patient.age = int(request.form['age'])
            patient.pregnancy_weeks = int(request.form['pregnancy_weeks'])
            patient.weight_before = float(request.form['weight_before'])
            patient.weight_after = float(request.form['weight_after'])
            patient.complications = request.form['complications'] or ""
            patient.notes = request.form['notes'] or ""
            patient.birth_date = request.form['birth_date']
            patient.birth_time = request.form['birth_time']
            patient.child_gender = request.form['child_gender']
            patient.child_weight = int(request.form['child_weight'])
            patient.delivery_method = request.form['delivery_method']
            patient.anesthesia = request.form['anesthesia']
            patient.blood_loss = int(request.form['blood_loss'])
            patient.labor_duration = float(request.form['labor_duration'])
            patient.other_diseases = request.form['other_diseases'] or ""
            patient.gestosis = gestosis
            patient.diabetes = diabetes
            patient.hypertension = hypertension
            patient.anemia = anemia
            patient.infections = infections
            patient.placenta_pathology = placenta_pathology
            patient.polyhydramnios = polyhydramnios
            patient.oligohydramnios = oligohydramnios
            
            db.session.commit()
            flash('Данные пациента успешно обновлены!', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка при обновлении пациента: {e}")
            flash('Ошибка при обновлении данных пациента. Проверьте данные.', 'error')
    
    return render_template('edit_patient.html', patient=patient)

@app.route('/delete_patient/<int:patient_id>', methods=['POST'])
@login_required
def delete_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    
    # Проверяем права доступа
    # Супер-админ может удалять все записи
    # Акушерки могут удалять только свои записи
    if current_user.login != 'Joker' and patient.midwife != current_user.full_name:
        flash('У вас нет прав для удаления этой записи', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        db.session.delete(patient)
        db.session.commit()
        flash('Запись пациента успешно удалена!', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Ошибка при удалении пациента: {e}")
        flash('Ошибка при удалении записи пациента.', 'error')
    
    return redirect(url_for('dashboard'))

@app.route('/search')
@login_required
def search():
    # Получаем параметры поиска
    search_query = request.args.get('search', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    selected_midwives = request.args.getlist('midwives')
    selected_methods = request.args.getlist('delivery_methods')
    selected_genders = request.args.getlist('genders')
    age_min = request.args.get('age_min', '')
    age_max = request.args.get('age_max', '')
    weight_min = request.args.get('weight_min', '')
    weight_max = request.args.get('weight_max', '')
    
    # Базовый запрос
    query = Patient.query
    
    # Применяем фильтры
    if search_query:
        query = query.filter(Patient.patient_name.contains(search_query))
    if date_from:
        query = query.filter(Patient.birth_date >= date_from)
    if date_to:
        query = query.filter(Patient.birth_date <= date_to)
    if selected_midwives:
        query = query.filter(Patient.midwife.in_(selected_midwives))
    if selected_methods:
        query = query.filter(Patient.delivery_method.in_(selected_methods))
    if selected_genders:
        query = query.filter(Patient.child_gender.in_(selected_genders))
    if age_min:
        query = query.filter(Patient.age >= int(age_min))
    if age_max:
        query = query.filter(Patient.age <= int(age_max))
    if weight_min:
        query = query.filter(Patient.child_weight >= int(weight_min))
    if weight_max:
        query = query.filter(Patient.child_weight <= int(weight_max))
    
    patients = query.all()
    
    # Получаем уникальные значения для фильтров
    midwives = db.session.query(Patient.midwife).distinct().all()
    delivery_methods = db.session.query(Patient.delivery_method).distinct().all()
    genders = db.session.query(Patient.child_gender).distinct().all()
    
    return render_template('search.html', 
                         patients=patients,
                         midwives=[m[0] for m in midwives],
                         delivery_methods=[d[0] for d in delivery_methods],
                         genders=[g[0] for g in genders])

@app.route('/profile')
@login_required
def profile():
    # Получаем статистику для текущего пользователя
    total_patients = Patient.query.filter_by(midwife=current_user.full_name).count()
    
    # Дополнительная статистика
    if total_patients > 0:
        avg_age = db.session.query(db.func.avg(Patient.age)).filter_by(midwife=current_user.full_name).scalar() or 0
        avg_weight = db.session.query(db.func.avg(Patient.child_weight)).filter_by(midwife=current_user.full_name).scalar() or 0
    else:
        avg_age = avg_weight = 0
    
    # Получаем последние пациентов текущего пользователя
    recent_patients = Patient.query.filter_by(midwife=current_user.full_name).order_by(Patient.created_at.desc()).limit(5).all()
    
    return render_template('profile.html', 
                         total_patients=total_patients,
                         avg_age=round(avg_age, 1),
                         avg_child_weight=round(avg_weight, 1),
                         recent_patients=recent_patients)

# ============================================================================
# CMS АДМИН-ПАНЕЛЬ МАРШРУТЫ
# ============================================================================

@app.route('/admin')
@login_required
def admin_panel():
    """Главная страница админ-панели"""
    if current_user.user_type != 'admin' and current_user.login != 'Joker':
        flash('Доступ запрещен. Требуются права администратора.', 'error')
        return redirect(url_for('dashboard'))
    
    # Статистика
    news_count = News.query.count()
    mama_content_count = MamaContent.query.count()
    media_count = MediaFile.query.count()
    patients_count = Patient.query.count()
    
    return render_template('admin/dashboard.html', 
                         news_count=news_count,
                         mama_content_count=mama_content_count,
                         media_count=media_count,
                         patients_count=patients_count)

@app.route('/admin/news')
@login_required
def admin_news():
    """Управление новостями"""
    if current_user.user_type != 'admin' and current_user.login != 'Joker':
        flash('Доступ запрещен.', 'error')
        return redirect(url_for('dashboard'))
    
    news = News.query.order_by(News.created_at.desc()).all()
    return render_template('admin/news.html', news=news)

@app.route('/admin/news/add', methods=['GET', 'POST'])
@login_required
def admin_news_add():
    """Добавление новости"""
    if current_user.user_type != 'admin' and current_user.login != 'Joker':
        flash('Доступ запрещен.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        short_description = request.form.get('short_description')
        full_content = request.form.get('full_content')
        category = request.form.get('category', 'general')
        image_url = request.form.get('image_url')
        
        news = News(
            title=title,
            short_description=short_description,
            full_content=full_content,
            category=category,
            image_url=image_url,
            author=current_user.full_name
        )
        
        db.session.add(news)
        db.session.commit()
        
        flash('Новость успешно добавлена!', 'success')
        return redirect(url_for('admin_news'))
    
    return render_template('admin/news_form.html')

@app.route('/admin/news/edit/<int:news_id>', methods=['GET', 'POST'])
@login_required
def admin_news_edit(news_id):
    """Редактирование новости"""
    if current_user.user_type != 'admin' and current_user.login != 'Joker':
        flash('Доступ запрещен.', 'error')
        return redirect(url_for('dashboard'))
    
    news = News.query.get_or_404(news_id)
    
    if request.method == 'POST':
        news.title = request.form.get('title')
        news.short_description = request.form.get('short_description')
        news.full_content = request.form.get('full_content')
        news.category = request.form.get('category', 'general')
        news.image_url = request.form.get('image_url')
        news.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        flash('Новость успешно обновлена!', 'success')
        return redirect(url_for('admin_news'))
    
    return render_template('admin/news_form.html', news=news)

@app.route('/admin/news/delete/<int:news_id>', methods=['POST'])
@login_required
def admin_news_delete(news_id):
    """Удаление новости"""
    if current_user.user_type != 'admin' and current_user.login != 'Joker':
        return jsonify({'error': 'Доступ запрещен.'}), 403
    
    news = News.query.get_or_404(news_id)
    
    try:
        db.session.delete(news)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Новость успешно удалена!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Ошибка при удалении новости.'}), 500

@app.route('/admin/mama-content')
@login_required
def admin_mama_content():
    """Админ панель для управления контентом Умай Мама"""
    if current_user.user_type != 'admin' and current_user.login != 'Joker':
        flash('Доступ запрещен', 'error')
        return redirect(url_for('dashboard'))
    
    # Получаем статистику
    total_content = MamaContent.query.count()
    published_content = MamaContent.query.filter_by(is_published=True).count()
    pending_content = MamaContent.query.filter_by(is_published=False).count()
    
    # Популярные категории
    categories_stats = db.session.query(
        MamaContent.category,
        db.func.count(MamaContent.id).label('count')
    ).group_by(MamaContent.category).all()
    
    # Последние статьи
    recent_content = MamaContent.query.order_by(MamaContent.created_at.desc()).limit(5).all()
    
    # Преобразуем статистику категорий в словарь
    categories_dict = {stat.category: stat.count for stat in categories_stats}
    
    # Создаем объект статистики
    stats = {
        'total': total_content,
        'published': published_content,
        'pending': pending_content,
        'categories': categories_dict
    }
    
    return render_template('admin/mama_content_dashboard.html',
                         stats=stats,
                         recent_content=recent_content)

@app.route('/admin/mama-content/add', methods=['GET', 'POST'])
@login_required
def admin_mama_content_add():
    """Добавление нового контента"""
    if current_user.user_type != 'admin' and current_user.login != 'Joker':
        flash('Доступ запрещен', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        category = request.form.get('category')
        trimester = request.form.get('trimester')
        difficulty_level = request.form.get('difficulty_level')
        duration = request.form.get('duration')
        image_url = request.form.get('image_url')
        video_url = request.form.get('video_url')
        author = request.form.get('author', current_user.full_name)
        
        new_content = MamaContent(
            title=title,
            content=content,
            category=category,
            trimester=trimester,
            difficulty_level=difficulty_level,
            duration=duration,
            image_url=image_url,
            video_url=video_url,
            author=author,
            is_published=True
        )
        
        db.session.add(new_content)
        db.session.commit()
        
        flash('Контент успешно добавлен!', 'success')
        return redirect(url_for('admin_mama_content'))
    
    categories = {
        'sport': 'Спорт',
        'nutrition': 'Питание',
        'vitamins': 'Витамины',
        'body_care': 'Уход за телом',
        'baby_care': 'Уход за новорождённым',
        'doctor_advice': 'Советы врачей'
    }
    
    return render_template('admin/mama_content_add.html', categories=categories)

@app.route('/admin/mama-content/edit/<int:content_id>', methods=['GET', 'POST'])
@login_required
def admin_mama_content_edit(content_id):
    """Редактирование контента"""
    if current_user.user_type != 'admin' and current_user.login != 'Joker':
        flash('Доступ запрещен', 'error')
        return redirect(url_for('dashboard'))
    
    content = MamaContent.query.get_or_404(content_id)
    
    if request.method == 'POST':
        content.title = request.form.get('title')
        content.content = request.form.get('content')
        content.category = request.form.get('category')
        content.trimester = request.form.get('trimester')
        content.difficulty_level = request.form.get('difficulty_level')
        content.duration = request.form.get('duration')
        content.image_url = request.form.get('image_url')
        content.video_url = request.form.get('video_url')
        content.is_published = request.form.get('is_published') == 'on'
        
        db.session.commit()
        flash('Контент успешно обновлен!', 'success')
        return redirect(url_for('admin_mama_content'))
    
    categories = {
        'sport': 'Спорт',
        'nutrition': 'Питание',
        'vitamins': 'Витамины',
        'body_care': 'Уход за телом',
        'baby_care': 'Уход за новорождённым',
        'doctor_advice': 'Советы врачей'
    }
    
    return render_template('admin/mama_content_edit.html', content=content, categories=categories)

@app.route('/admin/mama-content/delete/<int:content_id>', methods=['POST'])
@login_required
def admin_mama_content_delete(content_id):
    """Удаление контента"""
    if current_user.user_type != 'admin' and current_user.login != 'Joker':
        flash('Доступ запрещен', 'error')
        return redirect(url_for('dashboard'))
    
    content = MamaContent.query.get_or_404(content_id)
    db.session.delete(content)
    db.session.commit()
    
    flash('Контент успешно удален!', 'success')
    return redirect(url_for('admin_mama_content'))

@app.route('/admin/mama-content/moderate')
@login_required
def admin_mama_content_moderate():
    """Модерация контента"""
    if current_user.user_type != 'admin' and current_user.login != 'Joker':
        flash('Доступ запрещен', 'error')
        return redirect(url_for('dashboard'))
    
    # Получаем статьи для модерации (неопубликованные)
    pending_content = MamaContent.query.filter_by(is_published=False).order_by(MamaContent.created_at.desc()).all()
    
    # Дополнительная статистика для шаблона
    total_content = MamaContent.query.count()
    published_content = MamaContent.query.filter_by(is_published=True).count()
    categories_count = db.session.query(MamaContent.category).distinct().count()
    
    return render_template('admin/mama_content_moderate.html', 
                         pending_content=pending_content,
                         total_content=total_content,
                         published_content=published_content,
                         categories_count=categories_count)

@app.route('/admin/mama-content/approve/<int:content_id>', methods=['POST'])
@login_required
def admin_mama_content_approve(content_id):
    """Одобрение контента"""
    if current_user.user_type != 'admin' and current_user.login != 'Joker':
        flash('Доступ запрещен', 'error')
        return redirect(url_for('dashboard'))
    
    content = MamaContent.query.get_or_404(content_id)
    content.is_published = True
    db.session.commit()
    
    flash('Контент одобрен и опубликован!', 'success')
    return redirect(url_for('admin_mama_content_moderate'))

@app.route('/admin/mama-content/reject/<int:content_id>', methods=['POST'])
@login_required
def admin_mama_content_reject(content_id):
    """Отклонение контента"""
    if current_user.user_type != 'admin' and current_user.login != 'Joker':
        flash('Доступ запрещен', 'error')
        return redirect(url_for('dashboard'))
    
    content = MamaContent.query.get_or_404(content_id)
    db.session.delete(content)
    db.session.commit()
    
    flash('Контент отклонен и удален!', 'success')
    return redirect(url_for('admin_mama_content_moderate'))

@app.route('/admin/mama-content/generate', methods=['GET', 'POST'])
@login_required
def admin_mama_content_generate():
    """ИИ-генерация контента"""
    if current_user.user_type != 'admin' and current_user.login != 'Joker':
        flash('Доступ запрещен', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        category = request.form.get('category')
        trimester = request.form.get('trimester')
        count = int(request.form.get('count', 1))
        
        # Генерируем контент с помощью ИИ
        generated_content = generate_ai_content(category, trimester, count)
        
        flash(f'Сгенерировано {len(generated_content)} статей!', 'success')
        return redirect(url_for('admin_mama_content'))
    
    categories = {
        'sport': 'Спорт',
        'nutrition': 'Питание',
        'vitamins': 'Витамины',
        'body_care': 'Уход за телом',
        'baby_care': 'Уход за новорождённым',
        'doctor_advice': 'Советы врачей'
    }
    
    return render_template('admin/mama_content_generate.html', categories=categories)

@app.route('/admin/mama-content/analytics')
@login_required
def admin_mama_content_analytics():
    """Аналитика контента"""
    if current_user.user_type != 'admin' and current_user.login != 'Joker':
        flash('Доступ запрещен', 'error')
        return redirect(url_for('dashboard'))
    
    # Статистика по категориям
    category_stats = db.session.query(
        MamaContent.category,
        db.func.count(MamaContent.id).label('count'),
        db.func.avg(MamaContent.views).label('avg_views')
    ).group_by(MamaContent.category).all()
    
    # Статистика по триместрам
    trimester_stats = db.session.query(
        MamaContent.trimester,
        db.func.count(MamaContent.id).label('count')
    ).filter(MamaContent.trimester.isnot(None)).group_by(MamaContent.trimester).all()
    
    # Популярные статьи
    popular_content = MamaContent.query.order_by(MamaContent.views.desc()).limit(10).all()
    
    # Статистика по времени
    recent_stats = db.session.query(
        db.func.date(MamaContent.created_at).label('date'),
        db.func.count(MamaContent.id).label('count')
    ).group_by(db.func.date(MamaContent.created_at)).order_by(db.func.date(MamaContent.created_at).desc()).limit(30).all()
    
    return render_template('admin/mama_content_analytics.html',
                         category_stats=category_stats,
                         trimester_stats=trimester_stats,
                         popular_content=popular_content,
                         recent_stats=recent_stats)

def generate_ai_content(category, trimester, count):
    """ИИ-генерация контента"""
    # Базовые шаблоны для генерации
    templates = {
        'sport': {
            'titles': [
                'Упражнения для беременных в {trimester} триместре',
                'Безопасная гимнастика для будущих мам',
                'Йога для беременных: {trimester} триместр',
                'Дыхательные упражнения для родов',
                'Пилатес для беременных'
            ],
            'content': [
                'В {trimester} триместре беременности важно поддерживать физическую активность. Эти упражнения помогут укрепить мышцы и подготовиться к родам.',
                'Регулярные занятия спортом во время беременности улучшают кровообращение и общее самочувствие.',
                'Перед началом любых упражнений обязательно проконсультируйтесь с врачом.'
            ]
        },
        'nutrition': {
            'titles': [
                'Правильное питание в {trimester} триместре',
                'Витамины и минералы для беременных',
                'Рецепты здорового питания для будущих мам',
                'Продукты, которые нужно исключить',
                'Питьевой режим во время беременности'
            ],
            'content': [
                'В {trimester} триместре особенно важно следить за питанием. Рацион должен быть сбалансированным и богатым витаминами.',
                'Включите в меню больше овощей, фруктов, белковых продуктов и полезных жиров.',
                'Избегайте сырых продуктов, непастеризованного молока и избытка кофеина.'
            ]
        },
        'vitamins': {
            'titles': [
                'Витамины для {trimester} триместра',
                'Фолиевая кислота: зачем она нужна',
                'Витамин D во время беременности',
                'Железо и анемия беременных',
                'Омега-3 для развития мозга малыша'
            ],
            'content': [
                'В {trimester} триместре потребность в витаминах меняется. Важно принимать назначенные врачом препараты.',
                'Фолиевая кислота особенно важна в первом триместре для профилактики пороков развития.',
                'Не принимайте витамины без назначения врача - это может быть опасно.'
            ]
        },
        'body_care': {
            'titles': [
                'Уход за кожей во время беременности',
                'Профилактика растяжек в {trimester} триместре',
                'Уход за волосами и ногтями',
                'Гигиена беременных',
                'Косметика для будущих мам'
            ],
            'content': [
                'Во время беременности кожа требует особого ухода. Используйте увлажняющие кремы и избегайте агрессивных средств.',
                'Для профилактики растяжек регулярно увлажняйте кожу специальными средствами.',
                'Выбирайте косметику без вредных химических веществ.'
            ]
        },
        'baby_care': {
            'titles': [
                'Подготовка к рождению малыша',
                'Что нужно купить для новорождённого',
                'Уход за пуповиной',
                'Кормление новорождённого',
                'Сон новорождённого'
            ],
            'content': [
                'Заблаговременно подготовьте все необходимое для малыша. Составьте список покупок.',
                'Изучите основы ухода за новорождённым: кормление, сон, гигиена.',
                'Не стесняйтесь обращаться за помощью к педиатру и опытным мамам.'
            ]
        },
        'doctor_advice': {
            'titles': [
                'Советы врача: {trimester} триместр',
                'Когда обращаться к врачу',
                'Тревожные симптомы беременности',
                'Подготовка к родам',
                'Послеродовой период'
            ],
            'content': [
                'В {trimester} триместре важно регулярно посещать врача и сдавать анализы.',
                'При любых тревожных симптомах немедленно обращайтесь к врачу.',
                'Задавайте врачу все интересующие вопросы - это нормально и необходимо.'
            ]
        }
    }
    
    trimester_names = {
        '1': 'первом',
        '2': 'втором', 
        '3': 'третьем',
        'all': 'любом'
    }
    
    generated = []
    
    for i in range(count):
        template = templates.get(category, templates['doctor_advice'])
        title = template['titles'][i % len(template['titles'])].format(
            trimester=trimester_names.get(trimester, 'любом')
        )
        content = template['content'][i % len(template['content'])].format(
            trimester=trimester_names.get(trimester, 'любом')
        )
        
        new_content = MamaContent(
            title=title,
            content=content,
            category=category,
            trimester=trimester,
            difficulty_level='medium',
            author='ИИ-Помощник',
            is_published=False  # Требует модерации
        )
        
        db.session.add(new_content)
        generated.append(new_content)
    
    db.session.commit()
    return generated

@app.route('/admin/media')
@login_required
def admin_media():
    """Управление медиафайлами"""
    if current_user.user_type != 'admin' and current_user.login != 'Joker':
        flash('Доступ запрещен.', 'error')
        return redirect(url_for('dashboard'))
    
    media = MediaFile.query.order_by(MediaFile.uploaded_at.desc()).all()
    return render_template('admin/media.html', media=media)

@app.route('/admin/media/upload', methods=['POST'])
@login_required
def admin_media_upload():
    """Загрузка медиафайлов"""
    if current_user.user_type != 'admin' and current_user.login != 'Joker':
        return jsonify({'error': 'Доступ запрещен.'}), 403
    
    if 'file' not in request.files:
        return jsonify({'error': 'Файл не выбран'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Файл не выбран'}), 400
    
    if file:
        # Создаем папку для медиафайлов
        os.makedirs('static/uploads', exist_ok=True)
        
        # Генерируем уникальное имя файла
        import uuid
        filename = str(uuid.uuid4()) + '.' + file.filename.rsplit('.', 1)[1].lower()
        file_path = os.path.join('static/uploads', filename)
        
        # Сохраняем файл
        file.save(file_path)
        
        # Определяем тип файла
        file_type = 'image' if file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')) else 'document'
        if file.filename.lower().endswith(('.mp4', '.avi', '.mov', '.wmv')):
            file_type = 'video'
        
        # Сохраняем в базу данных
        media_file = MediaFile(
            filename=filename,
            original_filename=file.filename,
            file_path=file_path,
            file_type=file_type,
            file_size=os.path.getsize(file_path),
            uploaded_by=current_user.full_name
        )
        
        db.session.add(media_file)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'filename': filename,
            'url': url_for('static', filename=f'uploads/{filename}')
        })
    
    return jsonify({'error': 'Ошибка загрузки файла'}), 500

# ============================================================================
# ПУБЛИЧНЫЕ МАРШРУТЫ ДЛЯ КОНТЕНТА
# ============================================================================

@app.route('/news')
def news_list():
    """Список новостей"""
    news = News.query.filter_by(is_published=True).order_by(News.published_at.desc()).all()
    return render_template('news/list.html', news=news)

@app.route('/news/<int:news_id>')
def news_detail(news_id):
    """Детальная страница новости"""
    news = News.query.get_or_404(news_id)
    if news.is_published:
        news.views += 1
        db.session.commit()
    return render_template('news/detail.html', news=news)

@app.route('/mama')
def mama_content():
    """Контент для беременных"""
    categories = {
        'sport': 'Спорт',
        'nutrition': 'Питание', 
        'vitamins': 'Витамины',
        'body_care': 'Уход за телом',
        'baby_care': 'Уход за новорождённым',
        'doctor_advice': 'Советы врачей'
    }
    
    selected_category = request.args.get('category', 'sport')
    content = MamaContent.query.filter_by(
        category=selected_category, 
        is_published=True
    ).order_by(MamaContent.created_at.desc()).all()
    
    return render_template('mama/content.html', 
                         content=content, 
                         categories=categories,
                         selected_category=selected_category)

@app.route('/export_csv')
@login_required
def export_csv():
    # Получаем параметры фильтрации
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    user_only = request.args.get('user_only', 'false').lower() == 'true'
    
    # Базовый запрос
    query = Patient.query
    
    # Применяем фильтры по датам
    if start_date:
        query = query.filter(Patient.birth_date >= start_date)
    if end_date:
        query = query.filter(Patient.birth_date <= end_date)
    
    # Если запрошен экспорт только для текущего пользователя
    if user_only:
        query = query.filter(Patient.midwife == current_user.full_name)
    
    # Получаем отфильтрованных пациентов
    patients = query.all()
    
    if not patients:
        flash('Нет данных для экспорта в указанном периоде', 'error')
        return redirect(url_for('dashboard'))
    
    # Создаем данные для экспорта
    data = []
    for patient in patients:
        # Находим информацию об акушерке
        midwife_info = User.query.filter_by(full_name=patient.midwife).first()
        midwife_position = midwife_info.position if midwife_info else "Не указано"
        midwife_department = getattr(midwife_info, 'department', 'Не указано') if midwife_info else "Не указано"
        midwife_institution = midwife_info.medical_institution if midwife_info else "Не указано"
        
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
            'Должность акушерки': midwife_position,
            'Учреждение акушерки': midwife_institution,
            'Отделение акушерки': midwife_department,
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
    
    # Формируем имя файла с периодом
    period_suffix = ""
    if start_date and end_date:
        period_suffix = f"_{start_date}_to_{end_date}"
    elif start_date:
        period_suffix = f"_from_{start_date}"
    elif end_date:
        period_suffix = f"_until_{end_date}"
    
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'umay_patients{period_suffix}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    )

@app.route('/analytics')
@login_required
def analytics():
    """Улучшенная аналитика с графиками"""
    try:
        # Получаем все пациентов
        patients = Patient.query.all()
        
        if not patients:
            return render_template('analytics.html', 
                                total_patients=0,
                                male_count=0, female_count=0, avg_age=0,
                                delivery_methods={}, complications={}, anesthesia_types={},
                                avg_child_weight=0, avg_pregnancy_weeks=0, avg_blood_loss=0, avg_labor_duration=0,
                                monthly_trends={})
        
        # Основная статистика
        total_patients = len(patients)
        male_count = sum(1 for p in patients if p.child_gender == 'Мальчик')
        female_count = sum(1 for p in patients if p.child_gender == 'Девочка')
        avg_age = sum(p.age for p in patients) / total_patients if total_patients > 0 else 0
        
        # Способы родоразрешения
        delivery_methods = {}
        for patient in patients:
            method = patient.delivery_method or 'Не указан'
            delivery_methods[method] = delivery_methods.get(method, 0) + 1
        
        # Осложнения
        complications = {}
        for patient in patients:
            if patient.gestosis == 'Да':
                complications['Гестоз'] = complications.get('Гестоз', 0) + 1
            if patient.diabetes == 'Да':
                complications['Сахарный диабет'] = complications.get('Сахарный диабет', 0) + 1
            if patient.hypertension == 'Да':
                complications['Гипертония'] = complications.get('Гипертония', 0) + 1
            if patient.anemia == 'Да':
                complications['Анемия'] = complications.get('Анемия', 0) + 1
            if patient.infections == 'Да':
                complications['Инфекции'] = complications.get('Инфекции', 0) + 1
        
        # Типы анестезии
        anesthesia_types = {}
        for patient in patients:
            anesthesia = patient.anesthesia or 'Не указан'
            anesthesia_types[anesthesia] = anesthesia_types.get(anesthesia, 0) + 1
        
        # Средние показатели
        avg_child_weight = sum(p.child_weight for p in patients) / total_patients if total_patients > 0 else 0
        avg_pregnancy_weeks = sum(p.pregnancy_weeks for p in patients) / total_patients if total_patients > 0 else 0
        avg_blood_loss = sum(p.blood_loss for p in patients) / total_patients if total_patients > 0 else 0
        avg_labor_duration = sum(p.labor_duration for p in patients) / total_patients if total_patients > 0 else 0
        
        # Месячные тренды
        monthly_trends = {}
        for patient in patients:
            try:
                birth_date = datetime.strptime(patient.birth_date, '%Y-%m-%d')
                month_key = birth_date.strftime('%B %Y')
                monthly_trends[month_key] = monthly_trends.get(month_key, 0) + 1
            except:
                continue
        
        return render_template('analytics.html',
                            total_patients=total_patients,
                            male_count=male_count, female_count=female_count, avg_age=round(avg_age, 1),
                            delivery_methods=delivery_methods, complications=complications, 
                            anesthesia_types=anesthesia_types,
                            avg_child_weight=round(avg_child_weight, 0),
                            avg_pregnancy_weeks=round(avg_pregnancy_weeks, 1),
                            avg_blood_loss=round(avg_blood_loss, 0),
                            avg_labor_duration=round(avg_labor_duration, 1),
                            monthly_trends=monthly_trends)
    
    except Exception as e:
        logger.error(f"Ошибка при загрузке аналитики: {e}")
        flash('Ошибка при загрузке аналитики', 'error')
        return redirect(url_for('dashboard'))

@app.route('/export_pdf')
@login_required
def export_pdf():
    """Экспорт данных в красивый PDF отчет"""
    try:
        # Получаем параметры фильтрации
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        user_only = request.args.get('user_only', 'false').lower() == 'true'
        
        # Базовый запрос
        query = Patient.query
        
        # Применяем фильтры по датам
        if start_date:
            query = query.filter(Patient.birth_date >= start_date)
        if end_date:
            query = query.filter(Patient.birth_date <= end_date)
        
        # Если запрошен экспорт только для текущего пользователя
        if user_only:
            query = query.filter(Patient.midwife == current_user.full_name)
        
        # Получаем отфильтрованных пациентов
        patients = query.all()
        
        if not patients:
            flash('Нет данных для экспорта в указанном периоде', 'error')
            return redirect(url_for('dashboard'))
        
        # Создаем PDF в памяти
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        story = []
        
        # Стили - используем только встроенные шрифты ReportLab
        styles = getSampleStyleSheet()
        # Регистрируем надежный шрифт с поддержкой кириллицы
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        try:
            pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
            font_name = 'STSong-Light'
        except:
            try:
                # Fallback на другой шрифт с поддержкой кириллицы
                pdfmetrics.registerFont(UnicodeCIDFont('HeiseiMin-W3'))
                font_name = 'HeiseiMin-W3'
            except:
                # Последний fallback на стандартный шрифт
                font_name = 'Helvetica'
                logger.warning("⚠️ Используем стандартный шрифт Helvetica")
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=1,  # Центрирование
            textColor=colors.HexColor('#1e40af'),  # Синий цвет
            fontName=font_name  # Используем наш шрифт
        )
        
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Heading2'],
            fontSize=16,
            spaceAfter=20,
            textColor=colors.HexColor('#374151'),  # Серый цвет
            fontName=font_name  # Используем наш шрифт
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=6,
            fontName=font_name  # Используем наш шрифт
        )
        
        # Заголовок
        story.append(Paragraph("🏥 UMAY - Медицинский отчет", title_style))
        story.append(Paragraph(f"Дата создания: {datetime.now().strftime('%d.%m.%Y %H:%M')}", normal_style))
        story.append(Paragraph(f"Всего пациентов: {len(patients)}", normal_style))
        story.append(Spacer(1, 20))
        
        # Статистика
        story.append(Paragraph("📊 Общая статистика", subtitle_style))
        
        # Подсчет статистики
        total_patients = len(patients)
        avg_age = sum(p.age for p in patients) / total_patients
        avg_pregnancy_weeks = sum(p.pregnancy_weeks for p in patients) / total_patients
        avg_child_weight = sum(p.child_weight for p in patients) / total_patients
        
        # Подсчет осложнений
        gestosis_count = sum(1 for p in patients if p.gestosis == 'Да')
        diabetes_count = sum(1 for p in patients if p.diabetes == 'Да')
        hypertension_count = sum(1 for p in patients if p.hypertension == 'Да')
        anemia_count = sum(1 for p in patients if p.anemia == 'Да')
        
        # Подсчет способов родоразрешения
        natural_births = sum(1 for p in patients if p.delivery_method == 'Естественные роды')
        cesarean_count = sum(1 for p in patients if p.delivery_method == 'Кесарево сечение')
        
        # Создаем таблицу статистики
        stats_data = [
            ['Показатель', 'Значение'],
            ['Общее количество пациентов', str(total_patients)],
            ['Средний возраст', f'{avg_age:.1f} лет'],
            ['Средний срок беременности', f'{avg_pregnancy_weeks:.1f} недель'],
            ['Средний вес ребенка', f'{avg_child_weight:.0f} г'],
            ['Естественные роды', f'{natural_births} ({natural_births/total_patients*100:.1f}%)'],
            ['Кесарево сечение', f'{cesarean_count} ({cesarean_count/total_patients*100:.1f}%)'],
            ['Гестоз', f'{gestosis_count} ({gestosis_count/total_patients*100:.1f}%)'],
            ['Сахарный диабет', f'{diabetes_count} ({diabetes_count/total_patients*100:.1f}%)'],
            ['Гипертония', f'{hypertension_count} ({hypertension_count/total_patients*100:.1f}%)'],
            ['Анемия', f'{anemia_count} ({anemia_count/total_patients*100:.1f}%)']
        ]
        
        stats_table = Table(stats_data)
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), font_name),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8fafc')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
            ('FONTNAME', (0, 1), (-1, -1), font_name),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f1f5f9')])
        ]))
        
        story.append(stats_table)
        story.append(Spacer(1, 30))
        
        # Детальная информация о пациентах
        story.append(Paragraph("👥 Детальная информация о пациентах", subtitle_style))
        
        # Создаем таблицу пациентов
        patient_data = [['ФИО', 'Возраст', 'Срок', 'Вес ребенка', 'Пол', 'Способ родов', 'Акушерка', 'Должность', 'Отделение']]
        
        for patient in patients:
            # Находим информацию об акушерке
            midwife_info = User.query.filter_by(full_name=patient.midwife).first()
            midwife_position = midwife_info.position if midwife_info else "Не указано"
            midwife_department = getattr(midwife_info, 'department', 'Не указано') if midwife_info else "Не указано"
            
            patient_data.append([
                patient.patient_name,
                str(patient.age),
                f'{patient.pregnancy_weeks} нед',
                f'{patient.child_weight} г',
                patient.child_gender,
                patient.delivery_method,
                patient.midwife,
                midwife_position,
                midwife_department
            ])
        
        patient_table = Table(patient_data)
        patient_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#10b981')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), font_name),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f0fdf4')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#bbf7d0')),
            ('FONTNAME', (0, 1), (-1, -1), font_name),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0fdf4')])
        ]))
        
        story.append(patient_table)
        story.append(Spacer(1, 30))
        
        # Осложнения и примечания
        story.append(Paragraph("⚠️ Осложнения и примечания", subtitle_style))
        
        complications_data = []
        for patient in patients:
            if patient.complications or patient.notes:
                complications_data.append([
                    patient.patient_name,
                    patient.complications or 'Нет',
                    patient.notes or 'Нет'
                ])
        
        if complications_data:
            complications_table = Table([['Пациент', 'Осложнения', 'Примечания']] + complications_data)
            complications_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f59e0b')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                                        ('FONTNAME', (0, 0), (-1, 0), font_name),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#fef3c7')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#fde68a')),
            ('FONTNAME', (0, 1), (-1, -1), font_name),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fef3c7')])
            ]))
            story.append(complications_table)
        else:
            story.append(Paragraph("Осложнений не зарегистрировано", normal_style))
        
        story.append(Spacer(1, 30))
        
        # Подпись
        story.append(Paragraph("Отчет сгенерирован системой UMAY", normal_style))
        story.append(Paragraph("© 2024 UMAY - Медицинская информационная система", normal_style))
        
        # Создаем PDF
        doc.build(story)
        buffer.seek(0)
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'umay_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        )
        
    except Exception as e:
        logger.error(f"Ошибка при создании PDF: {e}")
        flash('Ошибка при создании PDF отчета', 'error')
        return redirect(url_for('dashboard'))

# Тестовый маршрут для проверки
@app.route('/test')
def test():
    return "Приложение работает! Пользователь Joker существует и может войти."

if __name__ == '__main__':
    # Для прямого запуска app.py (не рекомендуется)
    # Используйте run_local.py для локального запуска
    print("⚠️  Для запуска используйте: python run_local.py")
    print("📱 Или: python run_public.py для публичной ссылки")
    sys.exit(1)

# Обработчик ошибок для отладки
@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal Server Error: {error}")
    return render_template('error.html', error_code=500, error_message="Внутренняя ошибка сервера"), 500

@app.errorhandler(404)
def not_found_error(error):
    logger.error(f"Not Found Error: {error}")
    return render_template('error.html', error_code=404, error_message="Страница не найдена"), 404 