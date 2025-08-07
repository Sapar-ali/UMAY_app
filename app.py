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

# ============================================================================
# UMAY APP - ПРОСТАЯ ВЕРСИЯ ДЛЯ RENDER И RAILWAY
# Версия: 5.1 - Поддержка Render и Railway
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

# Данные о городах и медицинских учреждениях
CITIES_DATA = {
    "Шымкент": [
        "Городской перинатальный центр",
        "ГКП на ПХВ Городской родильный дом",
        "Городская больница - 2",
        "Городская больница - 3"
    ],
    "ЮКО": [
        "Скоро добавим..."
    ],
    "Астана": [
        "Скоро добавим..."
    ]
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
                medical_institution='UMAY System'
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
        return jsonify(CITIES_DATA[city])
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
        full_name = request.form['full_name']
        login = request.form['login']
        password = request.form['password']
        
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
                medical_institution='Не указано'
            )
        else:
            # Полная регистрация для акушерок
            position = request.form['position']
            city = request.form['city']
            medical_institution = request.form['medical_institution']
            
            new_user = User(
                full_name=full_name,
                login=login,
                password=hashed_password,
                user_type='midwife',
                position=position,
                city=city,
                medical_institution=medical_institution
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
            logger.error(f"Ошибка при регистрации: {e}")
            flash('Ошибка при регистрации. Попробуйте еще раз.', 'error')
    
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
    # Получаем статистику
    total_patients = Patient.query.count()
    boys_count = Patient.query.filter_by(child_gender='Мальчик').count()
    girls_count = Patient.query.filter_by(child_gender='Девочка').count()
    
    # Дополнительная статистика
    if total_patients > 0:
        avg_age = db.session.query(db.func.avg(Patient.age)).scalar() or 0
        avg_weight = db.session.query(db.func.avg(Patient.child_weight)).scalar() or 0
        children_percentage = ((boys_count + girls_count) / total_patients) * 100
    else:
        avg_age = avg_weight = children_percentage = 0
    
    # Статистика по учреждениям
    institution_stats = db.session.query(
        Patient.midwife,
        db.func.count(Patient.id).label('count')
    ).group_by(Patient.midwife).all()
    
    # Получаем последние пациентов для таблицы
    patients = Patient.query.order_by(Patient.created_at.desc()).limit(10).all()
    
    return render_template('dashboard.html', 
                         total_patients=total_patients,
                         boys=boys_count,
                         girls=girls_count,
                         avg_age=round(avg_age, 1),
                         avg_child_weight=round(avg_weight, 1),
                         institution_stats=institution_stats,
                         patients=patients)

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
    if not (current_user.user_type == 'midwife' or current_user.login == 'Joker'):
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
    if not (current_user.user_type == 'midwife' or current_user.login == 'Joker'):
        flash('Доступ запрещен.', 'error')
        return redirect(url_for('dashboard'))
    
    news = News.query.order_by(News.created_at.desc()).all()
    return render_template('admin/news.html', news=news)

@app.route('/admin/news/add', methods=['GET', 'POST'])
@login_required
def admin_news_add():
    """Добавление новости"""
    if not (current_user.user_type == 'midwife' or current_user.login == 'Joker'):
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
    if not (current_user.user_type == 'midwife' or current_user.login == 'Joker'):
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
    if not (current_user.user_type == 'midwife' or current_user.login == 'Joker'):
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
    """Управление контентом для беременных"""
    if not (current_user.user_type == 'midwife' or current_user.login == 'Joker'):
        flash('Доступ запрещен.', 'error')
        return redirect(url_for('dashboard'))
    
    content = MamaContent.query.order_by(MamaContent.created_at.desc()).all()
    return render_template('admin/mama_content.html', content=content)

@app.route('/admin/mama-content/add', methods=['GET', 'POST'])
@login_required
def admin_mama_content_add():
    """Добавление контента для беременных"""
    if not (current_user.user_type == 'midwife' or current_user.login == 'Joker'):
        flash('Доступ запрещен.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        category = request.form.get('category')
        image_url = request.form.get('image_url')
        video_url = request.form.get('video_url')
        trimester = request.form.get('trimester')
        difficulty_level = request.form.get('difficulty_level')
        duration = request.form.get('duration')
        
        mama_content = MamaContent(
            title=title,
            content=content,
            category=category,
            image_url=image_url,
            video_url=video_url,
            trimester=trimester,
            difficulty_level=difficulty_level,
            duration=duration,
            author=current_user.full_name
        )
        
        db.session.add(mama_content)
        db.session.commit()
        
        flash('Контент успешно добавлен!', 'success')
        return redirect(url_for('admin_mama_content'))
    
    return render_template('admin/mama_content_form.html')

@app.route('/admin/media')
@login_required
def admin_media():
    """Управление медиафайлами"""
    if not (current_user.user_type == 'midwife' or current_user.login == 'Joker'):
        flash('Доступ запрещен.', 'error')
        return redirect(url_for('dashboard'))
    
    media = MediaFile.query.order_by(MediaFile.uploaded_at.desc()).all()
    return render_template('admin/media.html', media=media)

@app.route('/admin/media/upload', methods=['POST'])
@login_required
def admin_media_upload():
    """Загрузка медиафайлов"""
    if not (current_user.user_type == 'midwife' or current_user.login == 'Joker'):
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
    # Получаем все пациентов
    patients = Patient.query.all()
    
    # Создаем данные для экспорта
    data = []
    for patient in patients:
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
    # Для прямого запуска app.py (не рекомендуется)
    # Используйте run_local.py для локального запуска
    print("⚠️  Для запуска используйте: python run_local.py")
    print("📱 Или: python run_public.py для публичной ссылки")
    sys.exit(1)

# Обработчик ошибок для отладки
@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal Server Error: {error}")
    return "Internal Server Error", 500

@app.errorhandler(404)
def not_found_error(error):
    logger.error(f"Not Found Error: {error}")
    return "Not Found", 404 