import streamlit as st
import pandas as pd
import os
from datetime import datetime, time, timedelta

# Настройка страницы
st.set_page_config(
    page_title="UMAY - Система отчетов для акушерок",
    page_icon="👶",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
    if os.path.exists('data/users.csv'):
        return pd.read_csv('data/users.csv')
    else:
        return pd.DataFrame(columns=['ФИО', 'Логин', 'Пароль', 'Должность', 'Медицинское учреждение'])

def save_user(user_data):
    # Создаем папку data, если её нет
    os.makedirs('data', exist_ok=True)
    df = load_users()
    new_row = pd.DataFrame([user_data], columns=['ФИО', 'Логин', 'Пароль', 'Должность', 'Медицинское учреждение'])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv('data/users.csv', index=False)

def check_user_login(login, password):
    df = load_users()
    # Отладочная информация
    st.write(f"Попытка входа: логин='{login}', пароль='{password}'")
    st.write(f"Всего пользователей в базе: {len(df)}")
    if not df.empty:
        st.write("Пользователи в базе:")
        st.write(df[['Логин', 'Пароль']].to_string())
    
    user = df[(df['Логин'] == login) & (df['Пароль'] == password)]
    if not user.empty:
        return user.iloc[0]['ФИО']
    return None

def save_registration(data):
    # Создаем папку data, если её нет
    os.makedirs('data', exist_ok=True)
    df = load_registrations()
    new_row = pd.DataFrame([data], columns=['ФИО', 'Должность', 'Медицинское учреждение'])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv('data/registrations.csv', index=False)

def load_patients_data():
    if os.path.exists('data/patients.csv'):
        return pd.read_csv('data/patients.csv')
    else:
        return pd.DataFrame(columns=[
            'Дата', 'ФИО роженицы', 'Возраст', 'Срок беременности', 
            'Вес до родов', 'Вес после родов', 'Осложнения', 'Примечания',
            'Акушерка', 'Дата родов', 'Время родов', 'Пол ребенка', 'Вес ребенка',
            'Способ родоразрешения', 'Анестезия', 'Кровопотеря', 'Продолжительность родов',
            'Сопутствующие заболевания', 'Гестоз', 'Сахарный диабет', 'Гипертония',
            'Анемия', 'Инфекции', 'Патология плаценты', 'Многоводие', 'Маловодие'
        ])

def save_patient_data(data):
    # Создаем папку data, если её нет
    os.makedirs('data', exist_ok=True)
    df = load_patients_data()
    new_row = pd.DataFrame([data], columns=[
        'Дата', 'ФИО роженицы', 'Возраст', 'Срок беременности', 
        'Вес до родов', 'Вес после родов', 'Осложнения', 'Примечания',
        'Акушерка', 'Дата родов', 'Время родов', 'Пол ребенка', 'Вес ребенка',
        'Способ родоразрешения', 'Анестезия', 'Кровопотеря', 'Продолжительность родов',
        'Сопутствующие заболевания', 'Гестоз', 'Сахарный диабет', 'Гипертония',
        'Анемия', 'Инфекции', 'Патология плаценты', 'Многоводие', 'Маловодие'
    ])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv('data/patients.csv', index=False)

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
                medical_institution = st.text_input("Медицинское учреждение", placeholder="Название больницы/клиники")
                user_password = st.text_input("Пароль", type="password", placeholder="Придумайте пароль")
                confirm_password = st.text_input("Подтвердите пароль", type="password", placeholder="Повторите пароль")
            
            submitted = st.form_submit_button("Зарегистрироваться", type="primary")
            
            if submitted:
                if full_name and medical_institution and user_login and user_password:
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
            if patient_name:
                patient_data = {
                    'Дата': datetime.now().strftime("%Y-%m-%d %H:%M"),
                    'ФИО роженицы': patient_name,
                    'Возраст': age,
                    'Срок беременности': pregnancy_weeks,
                    'Вес до родов': weight_before,
                    'Вес после родов': weight_after,
                    'Осложнения': complications,
                    'Примечания': notes,
                    'Акушерка': st.session_state.current_user,
                    'Дата родов': birth_date.strftime("%Y-%m-%d"),
                    'Время родов': birth_time.strftime("%H:%M"),
                    'Пол ребенка': child_gender,
                    'Вес ребенка': child_weight,
                    'Способ родоразрешения': delivery_method,
                    'Анестезия': anesthesia,
                    'Кровопотеря': blood_loss,
                    'Продолжительность родов': labor_duration,
                    'Сопутствующие заболевания': other_diseases,
                    'Гестоз': "Да" if gestosis else "Нет",
                    'Сахарный диабет': "Да" if diabetes else "Нет",
                    'Гипертония': "Да" if hypertension else "Нет",
                    'Анемия': "Да" if anemia else "Нет",
                    'Инфекции': "Да" if infections else "Нет",
                    'Патология плаценты': "Да" if placenta_pathology else "Нет",
                    'Многоводие': "Да" if polyhydramnios else "Нет",
                    'Маловодие': "Да" if oligohydramnios else "Нет"
                }
                save_patient_data(patient_data)
                st.success("✅ Данные роженицы успешно сохранены!")
            else:
                st.error("❌ Пожалуйста, введите ФИО роженицы!")

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
