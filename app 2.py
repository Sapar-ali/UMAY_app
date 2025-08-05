import streamlit as st
import pandas as pd
import os
import sqlite3
from datetime import datetime, time, timedelta
import io
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors

# Настройка страницы
st.set_page_config(
    page_title="UMAY - Система отчетов для акушерок",
    page_icon="👶",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Функции для работы с базой данных
def init_database():
    """Инициализация базы данных"""
    # Создаем папку data, если её нет
    os.makedirs('data', exist_ok=True)
    
    conn = sqlite3.connect('data/umay.db')
    cursor = conn.cursor()
    
    # Создание таблицы пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            login TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            position TEXT NOT NULL,
            city TEXT NOT NULL,
            medical_institution TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Создание таблицы рожениц
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            patient_name TEXT NOT NULL,
            age INTEGER NOT NULL,
            pregnancy_weeks INTEGER NOT NULL,
            weight_before REAL NOT NULL,
            weight_after REAL NOT NULL,
            complications TEXT,
            notes TEXT,
            midwife TEXT NOT NULL,
            birth_date TEXT NOT NULL,
            birth_time TEXT NOT NULL,
            child_gender TEXT NOT NULL,
            child_weight INTEGER NOT NULL,
            delivery_method TEXT NOT NULL,
            anesthesia TEXT NOT NULL,
            blood_loss INTEGER NOT NULL,
            labor_duration REAL NOT NULL,
            other_diseases TEXT,
            gestosis TEXT NOT NULL,
            diabetes TEXT NOT NULL,
            hypertension TEXT NOT NULL,
            anemia TEXT NOT NULL,
            infections TEXT NOT NULL,
            placenta_pathology TEXT NOT NULL,
            polyhydramnios TEXT NOT NULL,
            oligohydramnios TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def save_user_to_db(user_data):
    """Сохранение пользователя в базу данных"""
    conn = sqlite3.connect('data/umay.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO users (full_name, login, password, position, city, medical_institution)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        user_data['ФИО'],
        user_data['Логин'],
        user_data['Пароль'],
        user_data['Должность'],
        user_data.get('Город', ''),
        user_data['Медицинское учреждение']
    ))
    
    conn.commit()
    conn.close()

def check_user_login_db(login, password):
    """Проверка логина пользователя в базе данных"""
    conn = sqlite3.connect('data/umay.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT full_name FROM users WHERE login = ? AND password = ?
    ''', (login.strip(), password.strip()))
    
    result = cursor.fetchone()
    conn.close()
    
    return result[0] if result else None

def save_patient_to_db(patient_data):
    """Сохранение данных роженицы в базу данных"""
    conn = None
    try:
        # Проверяем, что все обязательные поля заполнены
        required_fields = ['ФИО роженицы', 'Возраст', 'Срок беременности', 'Вес до родов', 
                         'Вес после родов', 'Дата родов', 'Время родов', 'Пол ребенка', 
                         'Вес ребенка', 'Способ родоразрешения', 'Анестезия', 'Кровопотеря', 
                         'Продолжительность родов', 'Акушерка']
        
        for field in required_fields:
            if field not in patient_data or patient_data[field] is None or patient_data[field] == "":
                return False, f"Поле '{field}' обязательно для заполнения"
        
        conn = sqlite3.connect('data/umay.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO patients (
                date, patient_name, age, pregnancy_weeks, weight_before, weight_after,
                complications, notes, midwife, birth_date, birth_time, child_gender,
                child_weight, delivery_method, anesthesia, blood_loss, labor_duration,
                other_diseases, gestosis, diabetes, hypertension, anemia, infections,
                placenta_pathology, polyhydramnios, oligohydramnios
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            patient_data['Дата'],
            patient_data['ФИО роженицы'],
            patient_data['Возраст'],
            patient_data['Срок беременности'],
            patient_data['Вес до родов'],
            patient_data['Вес после родов'],
            patient_data['Осложнения'],
            patient_data['Примечания'],
            patient_data['Акушерка'],
            patient_data['Дата родов'],
            patient_data['Время родов'],
            patient_data['Пол ребенка'],
            patient_data['Вес ребенка'],
            patient_data['Способ родоразрешения'],
            patient_data['Анестезия'],
            patient_data['Кровопотеря'],
            patient_data['Продолжительность родов'],
            patient_data['Сопутствующие заболевания'],
            patient_data['Гестоз'],
            patient_data['Сахарный диабет'],
            patient_data['Гипертония'],
            patient_data['Анемия'],
            patient_data['Инфекции'],
            patient_data['Патология плаценты'],
            patient_data['Многоводие'],
            patient_data['Маловодие']
        ))
        
        conn.commit()
        conn.close()
        return True, "Данные успешно сохранены"
    except Exception as e:
        if conn:
            conn.close()
        return False, f"Ошибка при сохранении: {str(e)}"

def load_patients_from_db():
    """Загрузка данных рожениц из базы данных"""
    conn = sqlite3.connect('data/umay.db')
    
    query = '''
        SELECT 
            date as 'Дата',
            patient_name as 'ФИО роженицы',
            age as 'Возраст',
            pregnancy_weeks as 'Срок беременности',
            weight_before as 'Вес до родов',
            weight_after as 'Вес после родов',
            complications as 'Осложнения',
            notes as 'Примечания',
            midwife as 'Акушерка',
            birth_date as 'Дата родов',
            birth_time as 'Время родов',
            child_gender as 'Пол ребенка',
            child_weight as 'Вес ребенка',
            delivery_method as 'Способ родоразрешения',
            anesthesia as 'Анестезия',
            blood_loss as 'Кровопотеря',
            labor_duration as 'Продолжительность родов',
            other_diseases as 'Сопутствующие заболевания',
            gestosis as 'Гестоз',
            diabetes as 'Сахарный диабет',
            hypertension as 'Гипертония',
            anemia as 'Анемия',
            infections as 'Инфекции',
            placenta_pathology as 'Патология плаценты',
            polyhydramnios as 'Многоводие',
            oligohydramnios as 'Маловодие'
        FROM patients
        ORDER BY created_at DESC
    '''
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

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

# Инициализация базы данных при запуске
init_database()

# Загрузка кастомных стилей
def load_css():
    with open('styles/custom.css') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

load_css()

# Инициализация сессии
if 'current_user' not in st.session_state:
    st.session_state.current_user = None

# Функции для работы с данными
def load_registrations():
    if os.path.exists('data/registrations.csv'):
        return pd.read_csv('data/registrations.csv')
    else:
        return pd.DataFrame(columns=['ФИО', 'Должность', 'Медицинское учреждение', 'Логин', 'Пароль'])

def load_users():
    """Загрузка пользователей из базы данных"""
    conn = sqlite3.connect('data/umay.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT full_name, login, password, position, medical_institution FROM users')
    results = cursor.fetchall()
    conn.close()
    
    if results:
        df = pd.DataFrame(results, columns=['ФИО', 'Логин', 'Пароль', 'Должность', 'Медицинское учреждение'])
        return df
    else:
        return pd.DataFrame(columns=['ФИО', 'Логин', 'Пароль', 'Должность', 'Медицинское учреждение'])

def save_user(user_data):
    # Создаем папку data, если её нет
    os.makedirs('data', exist_ok=True)
    save_user_to_db(user_data)

def check_user_login(login, password):
    return check_user_login_db(login, password)

def save_registration(data):
    # Создаем папку data, если её нет
    os.makedirs('data', exist_ok=True)
    df = load_registrations()
    new_row = pd.DataFrame([data], columns=['ФИО', 'Должность', 'Медицинское учреждение'])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv('data/registrations.csv', index=False)

def load_patients_data():
    return load_patients_from_db()

def save_patient_data(data):
    # Создаем папку data, если её нет
    os.makedirs('data', exist_ok=True)
    return save_patient_to_db(data)

# Функция фильтрации данных
def filter_patients_data(df, search_term, date_from, date_to, selected_midwives, 
                        selected_delivery_methods, selected_genders, age_range, 
                        weight_range, blood_loss_range):
    filtered_df = df.copy()
    
    # Поиск по ФИО роженицы
    if search_term:
        filtered_df = filtered_df[filtered_df['ФИО роженицы'].str.contains(search_term, case=False, na=False)]
    
    # Фильтр по датам
    if date_from and date_to:
        filtered_df = filtered_df[
            (filtered_df['Дата родов'] >= date_from.strftime("%Y-%m-%d")) &
            (filtered_df['Дата родов'] <= date_to.strftime("%Y-%m-%d"))
        ]
    
    # Фильтр по акушеркам
    if selected_midwives:
        filtered_df = filtered_df[filtered_df['Акушерка'].isin(selected_midwives)]
    
    # Фильтр по способу родоразрешения
    if selected_delivery_methods:
        filtered_df = filtered_df[filtered_df['Способ родоразрешения'].isin(selected_delivery_methods)]
    
    # Фильтр по полу ребенка
    if selected_genders:
        filtered_df = filtered_df[filtered_df['Пол ребенка'].isin(selected_genders)]
    
    # Фильтр по возрасту
    if age_range:
        filtered_df = filtered_df[
            (filtered_df['Возраст'] >= age_range[0]) &
            (filtered_df['Возраст'] <= age_range[1])
        ]
    
    # Фильтр по весу ребенка
    if weight_range:
        filtered_df = filtered_df[
            (filtered_df['Вес ребенка'] >= weight_range[0]) &
            (filtered_df['Вес ребенка'] <= weight_range[1])
        ]
    
    # Фильтр по кровопотере
    if blood_loss_range:
        filtered_df = filtered_df[
            (filtered_df['Кровопотеря'] >= blood_loss_range[0]) &
            (filtered_df['Кровопотеря'] <= blood_loss_range[1])
        ]
    
    return filtered_df

# Функции экспорта
def export_to_excel(df, filename):
    """Экспорт данных в Excel файл"""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Данные', index=False)
    output.seek(0)
    return output

def create_pdf_report(df, title, filename):
    """Создание PDF отчета"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    
    # Стили
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        alignment=1  # Центрирование
    )
    
    # Заголовок
    elements.append(Paragraph(title, title_style))
    elements.append(Spacer(1, 20))
    
    # Создание таблицы
    if not df.empty:
        # Подготовка данных для таблицы
        data = [df.columns.tolist()] + df.values.tolist()
        
        # Создание таблицы
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(table)
    
    # Сборка документа
    doc.build(elements)
    buffer.seek(0)
    return buffer

def export_patients_report(df, current_user):
    """Экспорт отчета по роженицам"""
    if df.empty:
        return None
    
    # Создание отчета
    report_data = df.copy()
    report_data['Дата создания отчета'] = datetime.now().strftime('%Y-%m-%d %H:%M')
    report_data['Акушерка'] = current_user
    
    # Статистика
    total_patients = len(df)
    avg_age = df['Возраст'].mean()
    natural_births = len(df[df['Способ родоразрешения'] == 'Естественные роды'])
    cesarean = len(df[df['Способ родоразрешения'] == 'Кесарево сечение'])
    
    # Создание PDF
    title = f"Отчет по роженицам\nСоздан: {datetime.now().strftime('%d.%m.%Y %H:%M')}\nАкушерка: {current_user}"
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=14,
        spaceAfter=20,
        alignment=1
    )
    
    # Заголовок
    elements.append(Paragraph(title, title_style))
    elements.append(Spacer(1, 20))
    
    # Статистика
    stats_text = f"""
    <b>Статистика:</b><br/>
    • Всего рожениц: {total_patients}<br/>
    • Средний возраст: {avg_age:.1f} лет<br/>
    • Естественные роды: {natural_births}<br/>
    • Кесарево сечение: {cesarean}<br/>
    """
    elements.append(Paragraph(stats_text, styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # Таблица данных
    if not df.empty:
        # Ограничиваем количество колонок для PDF
        important_cols = ['ФИО роженицы', 'Возраст', 'Дата родов', 'Пол ребенка', 'Вес ребенка', 'Способ родоразрешения']
        df_display = df[important_cols].head(20)  # Первые 20 записей
        
        data = [df_display.columns.tolist()] + df_display.values.tolist()
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
        ]))
        elements.append(table)
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

# Главная навигация
st.title("👶 UMAY - Система отчетов для акушерок")
st.markdown("---")

# Боковая панель для навигации
with st.sidebar:
    st.header("📋 Навигация")
    page = st.radio(
        "Выберите страницу:",
        ["🔐 Вход/Регистрация", "📝 Ввод данных роженицы", "🔍 Поиск и фильтрация", "📊 Просмотр отчетов", "📈 Дашборд"]
    )
    
    # Информация о текущем пользователе
    if st.session_state.current_user:
        st.markdown("---")
        st.success(f"👤 Текущий пользователь: {st.session_state.current_user}")
        if st.button("🚪 Выйти", type="secondary"):
            st.session_state.current_user = None
            st.rerun()

# Страница входа/регистрации
if page == "🔐 Вход/Регистрация":
    st.header("🔐 Вход и регистрация")
    
    tab1, tab2 = st.tabs(["🔐 Войти", "📝 Зарегистрироваться"])
    
    with tab1:
        st.subheader("🔐 Вход в систему")
        with st.form("login_form"):
            login = st.text_input("Логин", placeholder="Введите ваш логин")
            password = st.text_input("Пароль", type="password", placeholder="Введите ваш пароль")
            
            login_submitted = st.form_submit_button("Войти", type="primary")
            
            if login_submitted:
                if login and password:
                    user_name = check_user_login(login, password)
                    if user_name:
                        st.session_state.current_user = user_name
                        st.success(f"✅ Добро пожаловать, {user_name}!")
                        st.rerun()
                    else:
                        st.error("❌ Неверный логин или пароль!")
                else:
                    st.error("❌ Пожалуйста, заполните все поля!")
    
    with tab2:
        st.subheader("📝 Регистрация нового пользователя")
        with st.form("registration_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                full_name = st.text_input("ФИО", placeholder="Введите ваше полное имя")
                position = st.selectbox(
                    "Должность",
                    ["Акушерка", "Старшая акушерка", "Заведующая отделением", "Врач-акушер-гинеколог"]
                )
                user_login = st.text_input("Логин", placeholder="Придумайте логин")
            
            with col2:
                # Выбор города
                city = st.selectbox("Город", ["Выберите город"] + list(CITIES_DATA.keys()))
                
                # Выбор учреждения в зависимости от города
                if city and city != "Выберите город":
                    institutions = CITIES_DATA[city]
                    medical_institution = st.selectbox("Медицинское учреждение", ["Выберите учреждение"] + institutions)
                else:
                    medical_institution = "Выберите учреждение"
                
                user_password = st.text_input("Пароль", type="password", placeholder="Придумайте пароль")
                confirm_password = st.text_input("Подтвердите пароль", type="password", placeholder="Повторите пароль")
            
            submitted = st.form_submit_button("Зарегистрироваться", type="primary")
            
            if submitted:
                if full_name and city and city != "Выберите город" and medical_institution and medical_institution != "Выберите учреждение" and user_login and user_password:
                    if user_password == confirm_password:
                        # Проверяем, не занят ли логин
                        users_df = load_users()
                        if not users_df.empty and user_login in users_df['Логин'].values:
                            st.error("❌ Этот логин уже занят! Выберите другой.")
                        else:
                            user_data = {
                                'ФИО': full_name,
                                'Логин': user_login,
                                'Пароль': user_password,
                                'Должность': position,
                                'Город': city,
                                'Медицинское учреждение': medical_institution
                            }
                            save_user(user_data)
                            st.success("✅ Регистрация успешно завершена! Теперь вы можете войти в систему.")
                    else:
                        st.error("❌ Пароли не совпадают!")
                else:
                    st.error("❌ Пожалуйста, заполните все обязательные поля!")

# Страница ввода данных роженицы
elif page == "📝 Ввод данных роженицы":
    st.header("📝 Ввод данных роженицы")
    
    # Проверка регистрации
    if st.session_state.current_user is None:
        st.warning("⚠️ Пожалуйста, сначала зарегистрируйтесь!")
        st.stop()
    
    with st.form("patient_data_form"):
        # Основная информация
        st.subheader("👤 Основная информация")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            patient_name = st.text_input("ФИО роженицы", placeholder="Введите ФИО роженицы")
            age = st.number_input("Возраст", min_value=14, max_value=60, value=25)
        
        with col2:
            pregnancy_weeks = st.number_input("Срок беременности (недель)", min_value=20, max_value=42, value=38)
            weight_before = st.number_input("Вес до родов (кг)", min_value=40.0, max_value=150.0, value=70.0, step=0.1)
        
        with col3:
            weight_after = st.number_input("Вес после родов (кг)", min_value=40.0, max_value=150.0, value=65.0, step=0.1)
        
        # Сопутствующие заболевания
        st.subheader("🏥 Сопутствующие заболевания во время беременности")
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Основные заболевания:**")
            gestosis = st.checkbox("Гестоз")
            diabetes = st.checkbox("Сахарный диабет")
            hypertension = st.checkbox("Гипертония")
            anemia = st.checkbox("Анемия")
        
        with col2:
            st.write("**Дополнительные патологии:**")
            infections = st.checkbox("Инфекции")
            placenta_pathology = st.checkbox("Патология плаценты")
            polyhydramnios = st.checkbox("Многоводие")
            oligohydramnios = st.checkbox("Маловодие")
        
        # Дополнительные заболевания
        other_diseases = st.text_area("Другие сопутствующие заболевания", 
                                    placeholder="Укажите другие заболевания, если были...")
        
        # Информация о родах
        st.subheader("👶 Информация о родах")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            birth_date = st.date_input("Дата родов", value=datetime.now().date())
            birth_time = st.time_input("Время родов", value=time(12, 0))
            child_gender = st.selectbox("Пол ребенка", ["Мальчик", "Девочка"])
        
        with col2:
            child_weight = st.number_input("Вес ребенка (г)", min_value=500, max_value=6000, value=3500, step=50)
            delivery_method = st.selectbox(
                "Способ родоразрешения",
                ["Естественные роды", "Кесарево сечение", "Вакуум-экстракция", "Акушерские щипцы"]
            )
        
        with col3:
            anesthesia = st.selectbox(
                "Анестезия",
                ["Нет", "Эпидуральная", "Спинальная", "Общая", "Местная"]
            )
            blood_loss = st.number_input("Кровопотеря (мл)", min_value=0, max_value=2000, value=300, step=50)
        
        # Дополнительная информация
        st.subheader("📋 Дополнительная информация")
        col1, col2 = st.columns(2)
        
        with col1:
            labor_duration = st.number_input("Продолжительность родов (часов)", min_value=0.5, max_value=24.0, value=8.0, step=0.5)
            complications = st.text_area("Осложнения в родах", placeholder="Опишите осложнения во время родов, если были")
        
        with col2:
            notes = st.text_area("Примечания", placeholder="Дополнительные заметки")
        
        submitted = st.form_submit_button("Сохранить данные", type="primary")
        
        if submitted:
            # Валидация обязательных полей
            errors = []
            
            if not patient_name or patient_name.strip() == "":
                errors.append("ФИО роженицы обязательно для заполнения")
            
            if not child_gender or child_gender == "Выберите пол":
                errors.append("Необходимо выбрать пол ребенка")
            
            if not delivery_method or delivery_method == "Выберите способ":
                errors.append("Необходимо выбрать способ родоразрешения")
            
            if not anesthesia or anesthesia == "Выберите тип анестезии":
                errors.append("Необходимо выбрать тип анестезии")
            
            if errors:
                st.error("❌ Ошибка при добавлении пациента. Проверьте данные:")
                for error in errors:
                    st.error(f"• {error}")
            else:
                patient_data = {
                    'Дата': datetime.now().strftime("%Y-%m-%d %H:%M"),
                    'ФИО роженицы': patient_name.strip(),
                    'Возраст': age,
                    'Срок беременности': pregnancy_weeks,
                    'Вес до родов': weight_before,
                    'Вес после родов': weight_after,
                    'Осложнения': complications or "",
                    'Примечания': notes or "",
                    'Акушерка': st.session_state.current_user,
                    'Дата родов': birth_date.strftime("%Y-%m-%d"),
                    'Время родов': birth_time.strftime("%H:%M"),
                    'Пол ребенка': child_gender,
                    'Вес ребенка': child_weight,
                    'Способ родоразрешения': delivery_method,
                    'Анестезия': anesthesia,
                    'Кровопотеря': blood_loss,
                    'Продолжительность родов': labor_duration,
                    'Сопутствующие заболевания': other_diseases or "",
                    'Гестоз': "Да" if gestosis else "Нет",
                    'Сахарный диабет': "Да" if diabetes else "Нет",
                    'Гипертония': "Да" if hypertension else "Нет",
                    'Анемия': "Да" if anemia else "Нет",
                    'Инфекции': "Да" if infections else "Нет",
                    'Патология плаценты': "Да" if placenta_pathology else "Нет",
                    'Многоводие': "Да" if polyhydramnios else "Нет",
                    'Маловодие': "Да" if oligohydramnios else "Нет"
                }
                success, message = save_patient_data(patient_data)
                if success:
                    st.success(f"✅ {message}")
                else:
                    st.error(f"❌ {message}")

# Страница поиска и фильтрации
elif page == "🔍 Поиск и фильтрация":
    st.header("🔍 Поиск и фильтрация")
    
    patients_df = load_patients_data()
    
    if patients_df.empty:
        st.info("📝 Пока нет данных для поиска")
    else:
        # Панель фильтров
        st.subheader("🔍 Фильтры")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Поиск по ФИО
            search_term = st.text_input("🔍 Поиск по ФИО роженицы", placeholder="Введите имя...")
            
            # Фильтр по датам
            st.write("📅 Период родов:")
            date_from = st.date_input("От", value=datetime.now().date() - timedelta(days=30))
            date_to = st.date_input("До", value=datetime.now().date())
            
            # Фильтр по акушеркам
            midwives = patients_df['Акушерка'].unique().tolist()
            selected_midwives = st.multiselect("👩‍⚕️ Акушерки", midwives, default=midwives)
        
        with col2:
            # Фильтр по способу родоразрешения
            delivery_methods = patients_df['Способ родоразрешения'].unique().tolist()
            selected_delivery_methods = st.multiselect("🏥 Способ родоразрешения", delivery_methods, default=delivery_methods)
            
            # Фильтр по полу ребенка
            genders = patients_df['Пол ребенка'].unique().tolist()
            selected_genders = st.multiselect("👶 Пол ребенка", genders, default=genders)
            
            # Фильтр по возрасту
            age_range = st.slider("👤 Возраст роженицы", 
                                 min_value=int(patients_df['Возраст'].min()), 
                                 max_value=int(patients_df['Возраст'].max()),
                                 value=(int(patients_df['Возраст'].min()), int(patients_df['Возраст'].max())))
        
        # Дополнительные фильтры
        col1, col2 = st.columns(2)
        
        with col1:
            # Фильтр по весу ребенка
            weight_range = st.slider("⚖️ Вес ребенка (г)", 
                                   min_value=int(patients_df['Вес ребенка'].min()), 
                                   max_value=int(patients_df['Вес ребенка'].max()),
                                   value=(int(patients_df['Вес ребенка'].min()), int(patients_df['Вес ребенка'].max())))
        
        with col2:
            # Фильтр по кровопотере
            blood_loss_range = st.slider("🩸 Кровопотеря (мл)", 
                                       min_value=int(patients_df['Кровопотеря'].min()), 
                                       max_value=int(patients_df['Кровопотеря'].max()),
                                       value=(int(patients_df['Кровопотеря'].min()), int(patients_df['Кровопотеря'].max())))
        
        # Применение фильтров
        filtered_df = filter_patients_data(patients_df, search_term, date_from, date_to, 
                                         selected_midwives, selected_delivery_methods, 
                                         selected_genders, age_range, weight_range, blood_loss_range)
        
        # Результаты поиска
        st.subheader(f"📋 Результаты поиска ({len(filtered_df)} записей)")
        
        if not filtered_df.empty:
            # Кнопки для экспорта
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("📄 Экспорт в CSV", type="secondary"):
                    csv = filtered_df.to_csv(index=False)
                    st.download_button(
                        label="💾 Скачать CSV",
                        data=csv,
                        file_name=f"umay_report_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                        mime="text/csv"
                    )
            
            with col2:
                if st.button("🔄 Сбросить фильтры", type="secondary"):
                    st.rerun()
            
            # Отображение данных
            st.dataframe(filtered_df, use_container_width=True)
            
            # Экспорт отфильтрованных данных
            if len(filtered_df) > 0:
                st.subheader("📤 Экспорт отфильтрованных данных")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("📊 Экспорт в Excel", key="excel_filtered"):
                        excel_data = export_to_excel(filtered_df, f"umay_filtered_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx")
                        st.download_button(
                            label="💾 Скачать Excel",
                            data=excel_data.getvalue(),
                            file_name=f"umay_filtered_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                
                with col2:
                    if st.button("📄 Создать PDF отчет", key="pdf_filtered"):
                        pdf_data = export_patients_report(filtered_df, st.session_state.current_user)
                        if pdf_data:
                            st.download_button(
                                label="💾 Скачать PDF",
                                data=pdf_data.getvalue(),
                                file_name=f"umay_filtered_report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                                mime="application/pdf"
                            )
                
                with col3:
                    if st.button("📋 Экспорт в CSV", key="csv_filtered"):
                        csv_data = filtered_df.to_csv(index=False)
                        st.download_button(
                            label="💾 Скачать CSV",
                            data=csv_data,
                            file_name=f"umay_filtered_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                            mime="text/csv"
                        )
            
            # Быстрая статистика
            if len(filtered_df) > 0:
                st.subheader("📊 Быстрая статистика")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Найдено записей", len(filtered_df))
                
                with col2:
                    avg_age = filtered_df['Возраст'].mean()
                    st.metric("Средний возраст", f"{avg_age:.1f} лет")
                
                with col3:
                    avg_weight = filtered_df['Вес ребенка'].mean()
                    st.metric("Средний вес ребенка", f"{avg_weight:.0f} г")
                
                with col4:
                    natural_births = len(filtered_df[filtered_df['Способ родоразрешения'] == 'Естественные роды'])
                    st.metric("Естественные роды", natural_births)
        else:
            st.warning("🔍 По вашему запросу ничего не найдено")

# Страница просмотра отчетов
elif page == "📊 Просмотр отчетов":
    st.header("📊 Просмотр отчетов")
    
    tab1, tab2 = st.tabs(["📋 Зарегистрированные акушерки", "👶 Данные рожениц"])
    
    with tab1:
        st.subheader("📋 Зарегистрированные акушерки")
        registrations_df = load_registrations()
        if not registrations_df.empty:
            st.dataframe(registrations_df, use_container_width=True)
        else:
            st.info("📝 Пока нет зарегистрированных акушерок")
    
    with tab2:
        st.subheader("👶 Данные рожениц")
        patients_df = load_patients_data()
        if not patients_df.empty:
            st.dataframe(patients_df, use_container_width=True)
            
            # Кнопки экспорта
            st.subheader("📤 Экспорт данных")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("📊 Экспорт в Excel", type="secondary"):
                    excel_data = export_to_excel(patients_df, f"umay_patients_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx")
                    st.download_button(
                        label="💾 Скачать Excel",
                        data=excel_data.getvalue(),
                        file_name=f"umay_patients_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            
            with col2:
                if st.button("📄 Создать PDF отчет", type="secondary"):
                    pdf_data = export_patients_report(patients_df, st.session_state.current_user)
                    if pdf_data:
                        st.download_button(
                            label="💾 Скачать PDF",
                            data=pdf_data.getvalue(),
                            file_name=f"umay_report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                            mime="application/pdf"
                        )
            
            with col3:
                if st.button("📋 Экспорт в CSV", type="secondary"):
                    csv_data = patients_df.to_csv(index=False)
                    st.download_button(
                        label="💾 Скачать CSV",
                        data=csv_data,
                        file_name=f"umay_patients_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                        mime="text/csv"
                    )
            
            # Статистика
            st.subheader("📈 Статистика")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Всего рожениц", len(patients_df))
            
            with col2:
                avg_age = patients_df['Возраст'].mean()
                st.metric("Средний возраст", f"{avg_age:.1f} лет")
            
            with col3:
                avg_weight_loss = (patients_df['Вес до родов'] - patients_df['Вес после родов']).mean()
                st.metric("Средняя потеря веса", f"{avg_weight_loss:.1f} кг")
            
            with col4:
                avg_child_weight = patients_df['Вес ребенка'].mean()
                st.metric("Средний вес ребенка", f"{avg_child_weight:.0f} г")
        else:
            st.info("📝 Пока нет данных о роженицах")

# Страница дашборда
elif page == "📈 Дашборд":
    st.header("📈 Дашборд")
    
    patients_df = load_patients_data()
    
    if not patients_df.empty:
        # Основные метрики
        st.subheader("📊 Основные показатели")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Всего родов", len(patients_df))
        
        with col2:
            natural_births = len(patients_df[patients_df['Способ родоразрешения'] == 'Естественные роды'])
            st.metric("Естественные роды", natural_births)
        
        with col3:
            c_sections = len(patients_df[patients_df['Способ родоразрешения'] == 'Кесарево сечение'])
            st.metric("Кесарево сечение", c_sections)
        
        with col4:
            boys = len(patients_df[patients_df['Пол ребенка'] == 'Мальчик'])
            girls = len(patients_df[patients_df['Пол ребенка'] == 'Девочка'])
            st.metric("Мальчики/Девочки", f"{boys}/{girls}")
        
        # Графики
        st.subheader("📈 Аналитика")
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Способ родоразрешения")
            delivery_counts = patients_df['Способ родоразрешения'].value_counts()
            st.bar_chart(delivery_counts)
        
        with col2:
            st.subheader("Пол детей")
            gender_counts = patients_df['Пол ребенка'].value_counts()
            st.pie_chart(gender_counts)
        
        # Статистика заболеваний
        st.subheader("🏥 Статистика сопутствующих заболеваний")
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Основные заболевания:**")
            if 'Гестоз' in patients_df.columns:
                gestosis_count = len(patients_df[patients_df['Гестоз'] == 'Да'])
                st.write(f"• Гестоз: {gestosis_count}")
            
            if 'Сахарный диабет' in patients_df.columns:
                diabetes_count = len(patients_df[patients_df['Сахарный диабет'] == 'Да'])
                st.write(f"• Сахарный диабет: {diabetes_count}")
            
            if 'Гипертония' in patients_df.columns:
                hypertension_count = len(patients_df[patients_df['Гипертония'] == 'Да'])
                st.write(f"• Гипертония: {hypertension_count}")
            
            if 'Анемия' in patients_df.columns:
                anemia_count = len(patients_df[patients_df['Анемия'] == 'Да'])
                st.write(f"• Анемия: {anemia_count}")
        
        with col2:
            st.write("**Дополнительные патологии:**")
            if 'Инфекции' in patients_df.columns:
                infections_count = len(patients_df[patients_df['Инфекции'] == 'Да'])
                st.write(f"• Инфекции: {infections_count}")
            
            if 'Патология плаценты' in patients_df.columns:
                placenta_count = len(patients_df[patients_df['Патология плаценты'] == 'Да'])
                st.write(f"• Патология плаценты: {placenta_count}")
            
            if 'Многоводие' in patients_df.columns:
                poly_count = len(patients_df[patients_df['Многоводие'] == 'Да'])
                st.write(f"• Многоводие: {poly_count}")
            
            if 'Маловодие' in patients_df.columns:
                oligo_count = len(patients_df[patients_df['Маловодие'] == 'Да'])
                st.write(f"• Маловодие: {oligo_count}")
        
        # Дополнительная статистика
        st.subheader("📋 Детальная статистика")
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Средние показатели:**")
            st.write(f"• Средний возраст: {patients_df['Возраст'].mean():.1f} лет")
            st.write(f"• Средний срок беременности: {patients_df['Срок беременности'].mean():.1f} недель")
            st.write(f"• Средний вес ребенка: {patients_df['Вес ребенка'].mean():.0f} г")
            st.write(f"• Средняя кровопотеря: {patients_df['Кровопотеря'].mean():.0f} мл")
        
        with col2:
            st.write("**Продолжительность родов:**")
            st.write(f"• Средняя продолжительность: {patients_df['Продолжительность родов'].mean():.1f} часов")
            st.write(f"• Минимальная: {patients_df['Продолжительность родов'].min():.1f} часов")
            st.write(f"• Максимальная: {patients_df['Продолжительность родов'].max():.1f} часов")
            
            st.write("**Анестезия:**")
            anesthesia_counts = patients_df['Анестезия'].value_counts()
            for anesthesia, count in anesthesia_counts.items():
                st.write(f"• {anesthesia}: {count}")
    else:
        st.info("📝 Пока нет данных для отображения дашборда")

# Информация о текущем пользователе
if st.session_state.current_user:
    st.sidebar.success(f"👤 Текущий пользователь: {st.session_state.current_user}")
