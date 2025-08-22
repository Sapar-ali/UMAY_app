from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import pandas as pd
import io
import os
import sys
import markdown
import requests
from bs4 import BeautifulSoup
import random
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from functools import wraps
try:
    import phonenumbers
    PHONENUMBERS_AVAILABLE = True
except ImportError:
    PHONENUMBERS_AVAILABLE = False
    print("⚠️  phonenumbers не доступен, используем упрощенную валидацию")

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Environment variables loaded from .env file")
except ImportError:
    print("⚠️  python-dotenv not installed, using system environment variables")
except Exception as e:
    print(f"⚠️  Error loading .env file: {e}")

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

# Database configuration
def get_database_uri():
    """Get database URI - use single database with different tables"""
    if os.getenv('DATABASE_URL'):
        # Production - use PostgreSQL with single database
        return os.getenv('DATABASE_URL')
    else:
        # Local development - use SQLite file
        data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
        os.makedirs(data_dir, exist_ok=True)
        return f'sqlite:///{os.path.join(data_dir, "umay.db")}'

# Create single database instance
def create_app_database():
    """Create database instance"""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')
    app.config['SQLALCHEMY_DATABASE_URI'] = get_database_uri()
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db = SQLAlchemy(app)
    return app, db

# Initialize single database
app, db = create_app_database()

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize Flask-Mail (configure after app.config is populated)
from flask_mail import Mail
mail = Mail()

# ======================
# Email Configuration
# ======================
MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
MAIL_PORT = int(os.getenv('MAIL_PORT', '587'))
MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'true').lower() == 'true'
MAIL_USE_SSL = os.getenv('MAIL_USE_SSL', 'false').lower() == 'true'
MAIL_USERNAME = os.getenv('MAIL_USERNAME', 'umay.med.gov@gmail.com')
MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', '87019090077Umay')
MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'umay.med.gov@gmail.com')
MAIL_MAX_EMAILS = int(os.getenv('MAIL_MAX_EMAILS', '100'))
MAIL_ASCII_ATTACHMENTS = False
MAIL_SUPPRESS_SEND = os.getenv('MAIL_SUPPRESS_SEND', 'false').lower() == 'true'

# Apply mail configuration to Flask app and initialize extension
app.config.update({
    'MAIL_SERVER': MAIL_SERVER,
    'MAIL_PORT': MAIL_PORT,
    'MAIL_USE_TLS': MAIL_USE_TLS,
    'MAIL_USE_SSL': MAIL_USE_SSL,
    'MAIL_USERNAME': MAIL_USERNAME,
    'MAIL_PASSWORD': MAIL_PASSWORD,
    'MAIL_DEFAULT_SENDER': MAIL_DEFAULT_SENDER,
    'MAIL_MAX_EMAILS': MAIL_MAX_EMAILS,
    'MAIL_ASCII_ATTACHMENTS': MAIL_ASCII_ATTACHMENTS,
    'MAIL_SUPPRESS_SEND': MAIL_SUPPRESS_SEND
})
mail.init_app(app)

# Email verification settings
EMAIL_VERIFICATION_TTL_HOURS = int(os.getenv('EMAIL_VERIFICATION_TTL_HOURS', '24'))

# Email verification functions
def generate_email_token():
    """Generate secure token for email verification"""
    from itsdangerous import URLSafeTimedSerializer
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    return serializer.dumps('email_verification', salt='email-verification')

def verify_email_token(token, expiration=EMAIL_VERIFICATION_TTL_HOURS * 3600):
    """Verify email verification token"""
    from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    try:
        data = serializer.loads(token, salt='email-verification', max_age=expiration)
        return True, data
    except SignatureExpired:
        return False, "Срок действия ссылки истек"
    except BadSignature:
        return False, "Неверная ссылка подтверждения"

def send_verification_email(email, token, user_type, app_type, purpose='register'):
    """Send email verification email"""
    try:
        if purpose == 'reset':
            verification_url = url_for('reset_password', token=token, _external=True)
            subject = "Восстановление пароля - UMAY"
            header_text = "🔐 Восстановление пароля"
            content_text = f"Для восстановления пароля в системе UMAY {app_type.upper()} нажмите на кнопку ниже:"
            button_text = "🔄 Сбросить пароль"
            footer_text = "Если вы не запрашивали восстановление пароля, просто проигнорируйте это письмо."
            ttl_text = "Ссылка действительна в течение 1 часа."
        else:
            verification_url = url_for('verify_email', token=token, _external=True)
            subject = "Подтвердите ваш email - UMAY"
            header_text = "🎉 Добро пожаловать в UMAY!"
            content_text = f"Спасибо за регистрацию в системе UMAY {app_type.upper()}! Для завершения регистрации нажмите на кнопку ниже:"
            button_text = "✅ Подтвердить Email"
            footer_text = "Если вы не регистрировались в UMAY, просто проигнорируйте это письмо."
            ttl_text = f"Ссылка действительна в течение {EMAIL_VERIFICATION_TTL_HOURS} часов."
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{subject}</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .button {{ display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px 30px; text-decoration: none; border-radius: 25px; font-weight: bold; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{header_text}</h1>
                    <p>{'Подтвердите ваш email для завершения регистрации' if purpose == 'register' else 'Восстановите доступ к вашему аккаунту'}</p>
                </div>
                <div class="content">
                    <h2>Здравствуйте!</h2>
                    <p>{content_text}</p>
                    
                    <div style="text-align: center;">
                        <a href="{verification_url}" class="button">{button_text}</a>
                    </div>
                    
                    <p><strong>Или скопируйте эту ссылку в браузер:</strong></p>
                    <p style="word-break: break-all; background: #f0f0f0; padding: 10px; border-radius: 5px;">
                        {verification_url}
                    </p>
                    
                    <p><em>{ttl_text}</em></p>
                </div>
                <div class="footer">
                    <p>© 2024 UMAY. Все права защищены.</p>
                    <p>{footer_text}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        from flask_mail import Message
        msg = Message(subject, recipients=[email])
        msg.html = html_body
        
        mail.send(msg)
        return True, "Email отправлен успешно"
    except Exception as e:
        logger.error(f"Error sending verification email: {e}")
        return False, f"Ошибка отправки email: {str(e)}"

# Markdown filter for templates
@app.template_filter('markdown')
def markdown_filter(text):
    """Convert markdown text to HTML"""
    if not text:
        return ""
    return markdown.markdown(text, extensions=['extra', 'codehilite'])

# Mobile device detection
def is_mobile_device():
    """Detect if user is on mobile device"""
    user_agent = request.headers.get('User-Agent', '').lower()
    mobile_keywords = ['mobile', 'android', 'iphone', 'ipad', 'windows phone']
    return any(keyword in user_agent for keyword in mobile_keywords)

# iOS detection for Safari-specific fallbacks
def is_ios_device():
    user_agent = request.headers.get('User-Agent', '').lower()
    return any(keyword in user_agent for keyword in ['iphone', 'ipad', 'ipod'])

# PWA routes
@app.route('/mobile/')
@app.route('/mobile/index')
def mobile_index():
    """Mobile home page"""
    logger.info("📱 Mobile index page requested")
    try:
        # Показываем обычную красивую главную страницу
        return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"❌ Error rendering mobile simple: {e}")
        try:
            # Fallback: простая страница (на крайний случай)
            return render_template('mobile/simple.html')
        except Exception as e2:
            logger.error(f"❌ Error rendering mobile index fallback: {e2}")
            return f"Mobile Error: {e2}", 500

@app.route('/mobile/login')
def mobile_login():
    """Mobile login page"""
    logger.info("📱 Mobile login page requested")
    try:
        # Use the primary login page to avoid missing mobile-specific template
        return redirect(url_for('login'))
    except Exception as e:
        logger.error(f"❌ Error rendering mobile login: {e}")
        return f"Error: {e}", 500

@app.route('/mobile/register')
def mobile_register():
    """Mobile register page"""
    logger.info("📱 Mobile register page requested")
    try:
        return render_template('mobile/register.html')
    except Exception as e:
        logger.error(f"❌ Error rendering mobile register: {e}")
        return f"Error: {e}", 500

@app.route('/verify-email/<token>')
def verify_email(token):
    """Verify email address"""
    logger.info(f"Email verification requested with token: {token[:10]}...")
    
    ok, data = verify_email_token(token)
    if not ok:
        flash(data, 'error')
        return redirect(url_for('login'))
    
    # Find user by token
    user = None
    verification_record = db.session.query(EmailVerification).filter_by(token=token).first()
    
    if verification_record:
        # Mark verification as completed
        verification_record.verified = True
        
        # Find and update user
        if verification_record.purpose == 'register':
            user = db.session.query(UserPro).filter_by(email_verification_token=token).first()
            if not user:
                user = db.session.query(UserMama).filter_by(email_verification_token=token).first()
            
            if user:
                user.is_email_verified = True
                user.email_verification_token = None
                user.email_verification_expires = None
                db.session.commit()
                
                flash('Email успешно подтвержден! Теперь вы можете войти в систему.', 'success')
                return redirect(url_for('login'))
    
    flash('Ошибка подтверждения email. Попробуйте зарегистрироваться снова.', 'error')
    return redirect(url_for('register'))

@app.route('/resend-verification', methods=['POST'])
def resend_verification():
    """Resend email verification link to user"""
    try:
        email = request.form.get('email', '').strip().lower()
        app_type = request.form.get('app_type', '').strip()

        if not email:
            flash('Укажите email для повторной отправки письма.', 'error')
            return redirect(url_for('login'))

        # Find user by email in both tables
        user = db.session.query(UserPro).filter_by(email=email).first()
        if not user:
            user = db.session.query(UserMama).filter_by(email=email).first()

        if not user:
            flash('Пользователь с таким email не найден.', 'error')
            return redirect(url_for('login'))

        if getattr(user, 'is_email_verified', False):
            flash('Email уже подтвержден. Можете войти в систему.', 'success')
            return redirect(url_for('login'))

        # Throttle repeat sends (min interval 60 seconds)
        last = (
            db.session.query(EmailVerification)
            .filter_by(email=email, purpose='register')
            .order_by(EmailVerification.created_at.desc())
            .first()
        )
        if last:
            from datetime import datetime
            delta_sec = (datetime.utcnow() - last.created_at).total_seconds()
            if delta_sec < 60:
                remaining = 60 - int(delta_sec)
                flash(f'Пожалуйста, подождите {remaining} сек перед повторной отправкой.', 'error')
                return redirect(url_for('login'))

        # Generate new token and update user + create verification record
        token = generate_email_token()
        from datetime import datetime, timedelta
        expires = datetime.utcnow() + timedelta(hours=EMAIL_VERIFICATION_TTL_HOURS)
        user.email_verification_token = token
        user.email_verification_expires = expires

        verification = EmailVerification(
            email=email,
            token=token,
            purpose='register',
            expires_at=expires
        )
        db.session.add(verification)
        db.session.commit()

        ok, message = send_verification_email(email, token, user.user_type, user.app_type, purpose='register')
        if not ok:
            flash(message, 'error')
        else:
            flash('Письмо с подтверждением отправлено повторно.', 'success')
        return redirect(url_for('login'))
    except Exception as e:
        logger.exception(f"Resend verification error: {e}")
        flash('Ошибка при повторной отправке письма.', 'error')
        return redirect(url_for('login'))

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Reset password with token"""
    logger.info(f"Password reset requested with token: {token[:10]}...")
    
    ok, data = verify_email_token(token, expiration=3600)  # 1 hour for reset
    if not ok:
        flash(data, 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if len(new_password) < 6:
            flash('Пароль должен содержать минимум 6 символов!', 'error')
            return render_template('reset_password.html')
        
        if new_password != confirm_password:
            flash('Пароли не совпадают!', 'error')
            return render_template('reset_password.html')
        
        # Find verification record
        verification_record = db.session.query(EmailVerification).filter_by(token=token).first()
        if verification_record and verification_record.purpose == 'reset':
            # Find user by email
            user = db.session.query(UserPro).filter_by(email=verification_record.email).first()
            if not user:
                user = db.session.query(UserMama).filter_by(email=verification_record.email).first()
            
            if user:
                # Update password
                user.password = generate_password_hash(new_password)
                
                # Mark verification as completed and delete
                db.session.delete(verification_record)
                db.session.commit()
                
                flash('Пароль успешно обновлен! Теперь вы можете войти в систему.', 'success')
                return redirect(url_for('login'))
        
        flash('Ошибка сброса пароля. Попробуйте снова.', 'error')
        return redirect(url_for('recover'))
    
    return render_template('reset_password.html')

@app.route('/mobile/dashboard')
def mobile_dashboard():
    """Mobile dashboard page"""
    logger.info("📱 Mobile dashboard page requested")
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    try:
        return render_template('mobile/dashboard.html')
    except Exception as e:
        logger.error(f"❌ Error rendering mobile dashboard: {e}")
        return f"Error: {e}", 500

@app.route('/mobile/test')
def mobile_test():
    """Mobile test page"""
    logger.info("📱 Mobile test page requested")
    return render_template('mobile/test.html')

@app.route('/mobile/simple')
def mobile_simple():
    """Simple mobile page for testing"""
    logger.info("📱 Simple mobile page requested")
    return render_template('mobile/simple.html')

@app.route('/mobile/debug')
def mobile_debug():
    """Debug mobile routes"""
    logger.info("📱 Mobile debug page requested")
    import os
    template_dir = os.path.join(os.path.dirname(__file__), 'templates', 'mobile')
    templates = []
    if os.path.exists(template_dir):
        templates = [f for f in os.listdir(template_dir) if f.endswith('.html')]
    
    debug_info = f"""
    <html>
    <head><title>UMAY Mobile Debug</title></head>
    <body style="font-family: monospace; padding: 20px;">
        <h1>UMAY Mobile Debug Info</h1>
        <h2>Available Templates:</h2>
        <ul>
            {''.join(f'<li>{t}</li>' for t in templates)}
        </ul>
        <h2>Current Routes:</h2>
        <ul>
            <li><a href="/mobile/">/mobile/</a></li>
            <li><a href="/mobile/index">/mobile/index</a></li>
            <li><a href="/mobile/simple">/mobile/simple</a></li>
            <li><a href="/mobile/test">/mobile/test</a></li>
            <li><a href="/mobile/hello">/mobile/hello</a></li>
            <li><a href="/mobile/login">/mobile/login</a></li>
            <li><a href="/mobile/register">/mobile/register</a></li>
            <li><a href="/mobile/status">/mobile/status</a></li>
            <li><a href="/mobile/resources">/mobile/resources</a></li>
            <li><a href="/mobile/debug">/mobile/debug</a></li>
        </ul>
        <h2>Server Info:</h2>
        <p>Python: {os.sys.version}</p>
        <p>Flask: {app.config.get('ENV', 'unknown')}</p>
        <p>Debug: {app.debug}</p>
    </body>
    </html>
    """
    return debug_info

@app.route('/mobile/status')
def mobile_status():
    """Simple mobile status check"""
    logger.info("📱 Mobile status check requested")
    return "UMAY Mobile is working! ✅"

@app.route('/mobile/resources')
def mobile_resources():
    """Check mobile resources"""
    logger.info("📱 Mobile resources check requested")
    import os
    
    # Check if static files exist
    static_dir = os.path.join(os.path.dirname(__file__), 'static')
    css_exists = os.path.exists(os.path.join(static_dir, 'css', 'mobile.css'))
    js_exists = os.path.exists(os.path.join(static_dir, 'js', 'mobile.js'))
    sw_exists = os.path.exists(os.path.join(static_dir, 'js', 'sw.js'))
    manifest_exists = os.path.exists(os.path.join(static_dir, 'manifest.json'))
    
    return f"""
    <html>
    <head><title>UMAY Mobile Resources</title></head>
    <body style="font-family: monospace; padding: 20px;">
        <h1>UMAY Mobile Resources Status</h1>
        <h2>Static Files:</h2>
        <ul>
            <li>CSS: {'✅' if css_exists else '❌'} mobile.css</li>
            <li>JS: {'✅' if js_exists else '❌'} mobile.js</li>
            <li>SW: {'✅' if sw_exists else '❌'} sw.js</li>
            <li>Manifest: {'✅' if manifest_exists else '❌'} manifest.json</li>
        </ul>
        <h2>Test Links:</h2>
        <ul>
            <li><a href="/static/css/mobile.css">CSS File</a></li>
            <li><a href="/static/js/mobile.js">JS File</a></li>
            <li><a href="/static/js/sw.js">Service Worker</a></li>
            <li><a href="/static/manifest.json">Manifest</a></li>
        </ul>
        <p><a href="/mobile/">← Вернуться на мобильную главную</a></p>
    </body>
    </html>
    """

@app.route('/mobile/hello')
def mobile_hello():
    """Simple hello world for mobile"""
    logger.info("📱 Mobile hello page requested")
    from datetime import datetime
    return """
    <html>
    <head><title>UMAY Mobile Hello</title></head>
    <body style="font-family: Arial, sans-serif; padding: 20px; text-align: center;">
        <h1>👋 Hello from UMAY Mobile!</h1>
        <p>Если вы видите эту страницу, значит Flask работает!</p>
        <p>Время: """ + str(datetime.utcnow()) + """</p>
        <p><a href="/mobile/">← На главную</a></p>
    </body>
    </html>
    """

@app.route('/mobile/<path:subpath>')
def mobile_routes(subpath):
    """Catch-all mobile routes"""
    logger.info(f"📱 Mobile catch-all route requested: /mobile/{subpath}")
    try:
        # Try to render a simple fallback page
        return f"""
        <html>
        <head><title>UMAY Mobile - {subpath}</title></head>
        <body style="font-family: Arial, sans-serif; padding: 20px; text-align: center;">
            <h1>UMAY Mobile</h1>
            <p>Страница <strong>{subpath}</strong> не найдена</p>
            <p>Доступные страницы:</p>
            <ul style="list-style: none; padding: 0;">
                <li><a href="/mobile/">Главная</a></li>
                <li><a href="/mobile/simple">Простая версия</a></li>
                <li><a href="/mobile/test">Тест</a></li>
                <li><a href="/mobile/hello">Hello</a></li>
                <li><a href="/mobile/status">Статус</a></li>
                <li><a href="/mobile/resources">Ресурсы</a></li>
                <li><a href="/mobile/debug">Отладка</a></li>
            </ul>
            <p><a href="/">← Вернуться на главную</a></p>
        </body>
        </html>
        """
    except Exception as e:
        logger.error(f"❌ Error in mobile catch-all: {e}")
        return f"Mobile Error: {e}", 500

@app.route('/manifest.json')
def manifest():
    """Serve PWA manifest"""
    return send_file('static/manifest.json', mimetype='application/json')

@app.route('/sw.js')
def service_worker():
    """Serve Service Worker"""
    return send_file('static/js/sw.js', mimetype='application/javascript')

# ======================
# OTP helpers
# ======================
# Email verification helpers
# ======================
# (Functions moved to email verification section above)
    phone = ''.join(c for c in (raw_phone or '') if c.isdigit() or c == '+')
    
    if PHONENUMBERS_AVAILABLE:
        try:
            if ONLY_KZ_NUMBERS:
                if phone.startswith('8'):
                    phone = '+7' + phone[1:]
                parsed = phonenumbers.parse(phone, 'KZ')
            else:
                parsed = phonenumbers.parse(phone, None)
            if not phonenumbers.is_possible_number(parsed) or not phonenumbers.is_valid_number(parsed):
                return ''
            e164 = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
            if ONLY_KZ_NUMBERS and not e164.startswith('+7'):
                return ''
            return e164
        except Exception:
            return ''
    else:
        # Упрощенная валидация без phonenumbers
        if phone.startswith('8'):
            phone = '+7' + phone[1:]
        elif phone.startswith('7'):
            phone = '+7' + phone[1:]
        elif not phone.startswith('+'):
            phone = '+7' + phone
        return phone if len(phone) >= 10 else ''

def can_resend_otp(last_sent_at: datetime) -> bool:
    if not last_sent_at:
        return True
    return (datetime.utcnow() - last_sent_at).total_seconds() >= OTP_RESEND_COOLDOWN_SEC

def count_otp_sent_today(phone: str, purpose: str) -> int:
    start_of_day = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    return OTPCode.query.filter(
        OTPCode.phone == phone,
        OTPCode.purpose == purpose,
        OTPCode.created_at >= start_of_day
    ).count()

def generate_otp_code() -> str:
    return f"{random.randint(100000, 999999)}"

def send_sms_infobip(phone: str, text: str) -> bool:
    if not SMS_BASE_URL or not SMS_API_KEY:
        logger.error('SMS config is missing')
        return False
    try:
        url = SMS_BASE_URL.rstrip('/') + '/sms/2/text/advanced'
        headers = {
            'Authorization': f'App {SMS_API_KEY}',
            'Content-Type': 'application/json'
        }
        message_obj = {
            'destinations': [{'to': phone}],
            'text': text
        }
        # Временно убираем отправителя, пока не зарегистрируем в Infobip
        # if SMS_SENDER:
        #     message_obj['from'] = SMS_SENDER
        payload = {'messages': [message_obj]}
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        if resp.status_code in (200, 201):
            return True
        logger.error(f"Infobip send failed: {resp.status_code} {resp.text}")
        return False
    except Exception as e:
        logger.error(f"Infobip send exception: {e}")
        return False

def send_sms_mobizon(phone: str, text: str) -> bool:
    if not SMS_BASE_URL or not SMS_API_KEY:
        logger.error('SMS config is missing')
        return False
    
    logger.info(f"🔧 Начинаем отправку SMS через Mobizon")
    logger.info(f"🔧 SMS_PROVIDER: {SMS_PROVIDER}")
    logger.info(f"🔧 SMS_BASE_URL: {SMS_BASE_URL}")
    logger.info(f"🔧 SMS_API_KEY: {'*' * 10 if SMS_API_KEY else 'НЕ_УСТАНОВЛЕН'}")
    
    try:
        # Mobizon API: https://api.mobizon.kz/service/message/sendSmsMessage
        url = SMS_BASE_URL.rstrip('/') + '/service/message/sendSmsMessage'
        logger.info(f"🔧 Отправка SMS через Mobizon: {url}")
        
        data = {
            'apiKey': SMS_API_KEY,
            'recipient': phone,
            'text': text
        }
        # Временно отключаем from, пока подпись не одобрена
        # if SMS_SENDER:
        #     data['from'] = SMS_SENDER
        
        logger.info(f"📱 Данные для отправки: recipient={phone}, from=НЕ_УКАЗАН (подпись не одобрена), text_length={len(text)}")
        logger.info(f"📱 Полный URL: {url}")
        logger.info(f"📱 Данные запроса: {data}")
        
        # Добавляем заголовки для лучшей совместимости
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'UMAY-App/1.0'
        }
        
        logger.info(f"📤 Отправляем POST запрос...")
        resp = requests.post(url, data=data, headers=headers, timeout=30)
        logger.info(f"📡 Mobizon ответ: статус={resp.status_code}, размер={len(resp.text)}")
        logger.info(f"📡 Заголовки ответа: {dict(resp.headers)}")
        
        if resp.status_code in (200, 201):
            # Typical Mobizon success payload contains code == 0 and data.messageId
            try:
                payload = resp.json()
                logger.info(f"📋 Mobizon JSON ответ: {payload}")
                
                code_val = str(payload.get('code', '')).lower()
                message_val = str(payload.get('message', '')).lower()
                has_id = isinstance(payload.get('data', {}), dict) and (
                    'messageId' in payload.get('data', {}) or 'messages' in payload.get('data', {})
                )
                
                if code_val in ('0', 'success') or message_val in ('ok', 'success') or has_id:
                    logger.info("✅ Mobizon SMS отправлен успешно")
                    return True
                else:
                    logger.error(f"❌ Mobizon вернул ошибку: code={code_val}, message={message_val}")
                    logger.error(f"❌ Полный ответ: {payload}")
                    return False
                    
            except Exception as json_error:
                logger.error(f"❌ Ошибка парсинга JSON ответа Mobizon: {json_error}")
                # If response is not JSON but HTTP 200, consider failure with details
                logger.error(f"📄 Сырой ответ: {resp.text[:500]}")
                return False
        else:
            logger.error(f"❌ Mobizon HTTP ошибка: {resp.status_code}")
            logger.error(f"❌ Текст ошибки: {resp.text[:500]}")
            return False
    except requests.exceptions.Timeout:
        logger.error("⏰ Mobizon timeout - сервер не ответил за 30 секунд")
        return False
    except requests.exceptions.ConnectionError as e:
        logger.error(f"🔌 Mobizon connection error: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Mobizon общая ошибка: {e}")
        import traceback
        logger.error(f"❌ Stack trace: {traceback.format_exc()}")
        return False

def send_sms(phone: str, text: str) -> bool:
    provider = (SMS_PROVIDER or 'infobip').lower()
    logger.info(f"📱 Отправка SMS через провайдера: {provider}")
    
    if provider == 'mobizon':
        logger.info("📱 Пробуем Mobizon...")
        result = send_sms_mobizon(phone, text)
        if result:
            return True
        else:
            logger.warning("⚠️ Mobizon не сработал, пробуем Infobip как fallback...")
            return send_sms_infobip(phone, text)
    
    # default to infobip for backward compatibility
    logger.info("📱 Используем Infobip...")
    return send_sms_infobip(phone, text)

def send_otp(phone: str, purpose: str):
    try:
        normalized = normalize_phone(phone)
        if not normalized:
            return False, 'Некорректный номер телефона'
        
        sent_today = count_otp_sent_today(normalized, purpose)
        if sent_today >= OTP_MAX_PER_DAY:
            return False, 'Превышен дневной лимит отправки кодов'
        
        last = OTPCode.query.filter_by(phone=normalized, purpose=purpose).order_by(OTPCode.created_at.desc()).first()
        if last and not can_resend_otp(last.last_sent_at):
            return False, 'Пожалуйста, подождите перед повторной отправкой'
        
        code = generate_otp_code()
        text = f"UMAY: ваш код подтверждения {code}. Никому его не сообщайте."
        
        logger.info(f"📱 Попытка отправки OTP: phone={normalized}, purpose={purpose}, provider={SMS_PROVIDER}")
        
        sent = send_sms(normalized, text)
        if not sent:
            logger.error(f"❌ Не удалось отправить SMS для {normalized}")
            return False, 'Не удалось отправить СМС. Попробуйте позже'
        
        logger.info(f"✅ SMS отправлен успешно для {normalized}")
        
        otp = OTPCode(phone=normalized, code=code, purpose=purpose,
                      expires_at=datetime.utcnow() + timedelta(seconds=OTP_TTL_SEC),
                      last_sent_at=datetime.utcnow())
        db.session.add(otp)
        db.session.commit()
        return True, 'Код отправлен'
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка в send_otp: {e}")
        return False, 'Внутренняя ошибка сервера. Попробуйте позже'

def verify_otp(phone: str, code: str, purpose: str):
    normalized = normalize_phone(phone)
    if not normalized:
        return False, 'Некорректный номер телефона'
    otp = OTPCode.query.filter_by(phone=normalized, purpose=purpose, verified=False).order_by(OTPCode.created_at.desc()).first()
    if not otp:
        return False, 'Код не найден. Отправьте новый'
    if datetime.utcnow() > otp.expires_at:
        return False, 'Срок действия кода истек'
    if otp.attempts >= OTP_MAX_ATTEMPTS:
        return False, 'Превышено число попыток. Отправьте новый код'
    if otp.code != (code or '').strip():
        otp.attempts += 1
        db.session.commit()
        return False, 'Неверный код'
    otp.verified = True
    db.session.commit()
    return True, normalized

# Система ролей и ограничений доступа
def pro_required(f):
    """Декоратор для доступа только пользователям UMAY Pro"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        
        # Проверяем, что пользователь из UMAY Pro
        if hasattr(current_user, 'app_type') and current_user.app_type != 'pro':
            flash('Доступ запрещен. Эта функция доступна только для медицинского персонала UMAY Pro.', 'error')
            return redirect(url_for('index'))
        
        return f(*args, **kwargs)
    return decorated_function

def mama_required(f):
    """Декоратор для доступа только пользователям UMAY Mama"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        
        # Проверяем, что пользователь из UMAY Mama
        if hasattr(current_user, 'app_type') and current_user.app_type != 'mama':
            flash('Доступ запрещен. Эта функция доступна только для пользователей UMAY Mama.', 'error')
            return redirect(url_for('index'))
        
        return f(*args, **kwargs)
    return decorated_function

def pro_clinical_required(f):
    """Доступ только медицинскому персоналу UMAY Pro (не управленцам)."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        # Должен быть пользователь UMAY Pro
        if hasattr(current_user, 'app_type') and current_user.app_type != 'pro':
            flash('Доступ запрещен. Эта функция доступна только для медицинского персонала UMAY Pro.', 'error')
            return redirect(url_for('index'))
        # Запрет для управленцев (кроме супер-админа Joker)
        if getattr(current_user, 'user_type', '') == 'manager' and getattr(current_user, 'login', '') != 'Joker':
            flash('Доступ запрещен. Эта функция доступна только медицинскому персоналу.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Декоратор для доступа только администраторам"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        
        # Проверяем, что пользователь администратор или Joker
        if hasattr(current_user, 'user_type') and current_user.user_type != 'admin' and current_user.login != 'Joker':
            flash('Доступ запрещен. Эта функция доступна только для администраторов.', 'error')
            return redirect(url_for('index'))
        
        return f(*args, **kwargs)
    return decorated_function

# Initialize database tables
def init_database():
    """Initialize database with all tables"""
    try:
        with app.app_context():
            db.create_all()
            logger.info("✅ UMAY database initialized")
            # Ensure email columns exist (best-effort)
            try:
                from sqlalchemy import inspect, text
                inspector = inspect(db.engine)
                def add_column_if_missing(table_name: str, column_ddl: str):
                    columns = [col['name'] for col in inspector.get_columns(table_name)]
                    col_name = column_ddl.split()[0]
                    if col_name not in columns:
                        with db.engine.connect() as conn:
                            conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_ddl}"))
                            conn.commit()
                            logger.info(f"Added column {col_name} to {table_name}")
                if 'sqlite' in db.engine.url.drivername:
                    add_column_if_missing('user_pro', 'email VARCHAR(120)')
                    add_column_if_missing('user_pro', 'is_email_verified BOOLEAN DEFAULT 0')
                    add_column_if_missing('user_pro', 'email_verification_token VARCHAR(100)')
                    add_column_if_missing('user_pro', 'email_verification_expires DATETIME')
                    add_column_if_missing('user_mama', 'email VARCHAR(120)')
                    add_column_if_missing('user_mama', 'is_email_verified BOOLEAN DEFAULT 0')
                    add_column_if_missing('user_mama', 'email_verification_token VARCHAR(100)')
                    add_column_if_missing('user_mama', 'email_verification_expires DATETIME')
                else:
                    add_column_if_missing('user_pro', 'email VARCHAR(120)')
                    add_column_if_missing('user_pro', 'is_email_verified BOOLEAN DEFAULT FALSE')
                    add_column_if_missing('user_pro', 'email_verification_token VARCHAR(100)')
                    add_column_if_missing('user_pro', 'email_verification_expires TIMESTAMP')
                    add_column_if_missing('user_mama', 'email VARCHAR(120)')
                    add_column_if_missing('user_mama', 'is_email_verified BOOLEAN DEFAULT FALSE')
                    add_column_if_missing('user_mama', 'email_verification_token VARCHAR(100)')
                    add_column_if_missing('user_mama', 'email_verification_expires TIMESTAMP')
            except Exception as e:
                logger.warning(f"Could not ensure email columns: {e}")
            
            # Create admin user if not exists
            admin_user = db.session.query(UserPro).filter_by(login='Joker').first()
            if not admin_user:
                hashed_password = generate_password_hash('19341934')
                admin_user = UserPro(
                    full_name='Super Admin',
                    login='Joker',
                    password=hashed_password,
                    user_type='admin',
                    position='Super Admin',
                    city='Шымкент',
                    medical_institution='UMAY System',
                    department='Administration',
                    app_type='pro',
                    email='admin@umay.kz',
                    is_email_verified=True
                )
                db.session.add(admin_user)
                db.session.commit()
                logger.info("✅ Admin user created")
            
            # Add test patients if table is empty
            patient_count = db.session.query(Patient).count()
            if patient_count == 0:
                logger.info("📊 Adding test patients...")
                
                test_patients = [
                    Patient(
                        date='2024-01-15',
                        patient_name='Анна Иванова',
                        age=28,
                        pregnancy_weeks=39,
                        weight_before=65.5,
                        weight_after=70.2,
                        complications='Нет',
                        notes='Нормальные роды',
                        midwife='Доктор Петрова',
                        birth_date='2024-01-15',
                        birth_time='14:30',
                        child_gender='Девочка',
                        child_weight=3200,
                        delivery_method='Естественные роды',
                        anesthesia='Эпидуральная анестезия',
                        blood_loss=450,
                        labor_duration=8.5,
                        other_diseases='Нет',
                        gestosis='Нет',
                        diabetes='Нет',
                        hypertension='Нет',
                        anemia='Нет',
                        infections='Нет',
                        placenta_pathology='Нет',
                        polyhydramnios='Нет',
                        oligohydramnios='Нет',
                        pls='Нет',
                        pts='Нет',
                        eclampsia='Нет',
                        gestational_hypertension='Нет',
                        placenta_previa='Нет',
                        shoulder_dystocia='Нет',
                        third_degree_tear='Нет',
                        cord_prolapse='Нет',
                        postpartum_hemorrhage='Нет',
                        placental_abruption='Нет'
                    ),
                    Patient(
                        date='2024-02-20',
                        patient_name='Мария Сидорова',
                        age=32,
                        pregnancy_weeks=38,
                        weight_before=68.0,
                        weight_after=72.5,
                        complications='Гестоз',
                        notes='Осложненные роды',
                        midwife='Доктор Козлова',
                        birth_date='2024-02-20',
                        birth_time='16:45',
                        child_gender='Мальчик',
                        child_weight=3500,
                        delivery_method='Кесарево сечение',
                        anesthesia='Общая анестезия',
                        blood_loss=800,
                        labor_duration=12.0,
                        other_diseases='Нет',
                        gestosis='Да',
                        diabetes='Нет',
                        hypertension='Да',
                        anemia='Нет',
                        infections='Нет',
                        placenta_pathology='Нет',
                        polyhydramnios='Нет',
                        oligohydramnios='Нет',
                        pls='Да',
                        pts='Нет',
                        eclampsia='Нет',
                        gestational_hypertension='Нет',
                        placenta_previa='Нет',
                        shoulder_dystocia='Нет',
                        third_degree_tear='Нет',
                        cord_prolapse='Нет',
                        postpartum_hemorrhage='Нет',
                        placental_abruption='Нет'
                    ),
                    Patient(
                        date='2024-03-10',
                        patient_name='Елена Петрова',
                        age=25,
                        pregnancy_weeks=40,
                        weight_before=62.0,
                        weight_after=66.8,
                        complications='ПРК',
                        notes='Послеродовое кровотечение',
                        midwife='Доктор Иванова',
                        birth_date='2024-03-10',
                        birth_time='09:15',
                        child_gender='Девочка',
                        child_weight=3100,
                        delivery_method='Естественные роды',
                        anesthesia='Без анестезии',
                        blood_loss=1200,
                        labor_duration=6.5,
                        other_diseases='Нет',
                        gestosis='Нет',
                        diabetes='Нет',
                        hypertension='Нет',
                        anemia='Нет',
                        infections='Нет',
                        placenta_pathology='Нет',
                        polyhydramnios='Нет',
                        oligohydramnios='Нет',
                        pls='Нет',
                        pts='Нет',
                        eclampsia='Нет',
                        gestational_hypertension='Нет',
                        placenta_previa='Нет',
                        shoulder_dystocia='Нет',
                        third_degree_tear='Нет',
                        cord_prolapse='Нет',
                        postpartum_hemorrhage='Да',
                        placental_abruption='Нет'
                    )
                ]
                
                for patient in test_patients:
                    db.session.add(patient)
                
                db.session.commit()
                logger.info(f"✅ Added {len(test_patients)} test patients")
            else:
                logger.info(f"✅ Database already has {patient_count} patients")
            
    except Exception as e:
        logger.error(f"❌ Error initializing database: {e}")

# Global error handlers
@app.errorhandler(500)
def internal_error(error):
    logger.exception(f"❌ 500 Internal Server Error: {error}")
    return render_template('error.html', error="Внутренняя ошибка сервера"), 500

@app.errorhandler(404)
def not_found_error(error):
    logger.warning(f"⚠️ 404 Not Found: {request.url}")
    return render_template('error.html', error="Страница не найдена"), 404

@app.errorhandler(Exception)
def handle_exception(e):
    logger.exception(f"❌ Необработанное исключение: {e}")
    return render_template('error.html', error="Произошла ошибка"), 500

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



# Модели базы данных - отдельные для каждой системы
class UserPro(UserMixin, db.Model):
    __tablename__ = 'user_pro'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    login = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    user_type = db.Column(db.String(10), default='user')
    position = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    medical_institution = db.Column(db.String(200), nullable=False)
    department = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    app_type = db.Column(db.String(10), default='pro')
    # Email auth
    email = db.Column(db.String(120), unique=True, nullable=False)
    is_email_verified = db.Column(db.Boolean, default=False)
    email_verification_token = db.Column(db.String(100), unique=True)
    email_verification_expires = db.Column(db.DateTime)

class UserMama(UserMixin, db.Model):
    __tablename__ = 'user_mama'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    login = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    user_type = db.Column(db.String(10), default='user')
    position = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    medical_institution = db.Column(db.String(200), nullable=False)
    department = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    app_type = db.Column(db.String(10), default='mama')
    # Email auth
    email = db.Column(db.String(120), unique=True, nullable=False)
    is_email_verified = db.Column(db.Boolean, default=False)
    email_verification_token = db.Column(db.String(100), unique=True)
    email_verification_expires = db.Column(db.DateTime)

class EmailVerification(db.Model):
    __tablename__ = 'email_verification'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), index=True, nullable=False)
    token = db.Column(db.String(100), unique=True, nullable=False)
    purpose = db.Column(db.String(20), default='register')  # register, reset
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    verified = db.Column(db.Boolean, default=False)

# CMS Модели для контента - используем основную базу данных (UMAY Pro)
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
    pls = db.Column(db.String(10), nullable=False)  # ПЛС - преэклампсия легкой степени
    pts = db.Column(db.String(10), nullable=False)  # ПТС - преэклампсия тяжелой степени
    eclampsia = db.Column(db.String(10), nullable=False)
    gestational_hypertension = db.Column(db.String(10), nullable=False)
    placenta_previa = db.Column(db.String(10), nullable=False)  # Плотное прикрепление последа
    shoulder_dystocia = db.Column(db.String(10), nullable=False)
    third_degree_tear = db.Column(db.String(10), nullable=False)
    cord_prolapse = db.Column(db.String(10), nullable=False)
    postpartum_hemorrhage = db.Column(db.String(10), nullable=False)
    placental_abruption = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    # Check both databases for the user with safe error handling
    try:
        user = None
        # First check UMAY Pro database
        with app.app_context():
            user = db.session.query(UserPro).get(int(user_id))
        # Then check UMAY Mama database
        if not user:
            with app.app_context():
                user = db.session.query(UserMama).get(int(user_id))
        return user
    except Exception as e:
        logger.warning(f"load_user failed: {e}")
        return None

# Маршруты
@app.route('/')
def index():
    # Безопасный рендер главной: при ошибке БД показываем страницу без новостей
    try:
        latest_news = News.query.filter_by(is_published=True).order_by(News.published_at.desc()).limit(6).all()
    except Exception as e:
        logger.warning(f"Index news query failed: {e}")
        latest_news = []
    return render_template('index.html', news=latest_news)

@app.route('/healthz')
def healthz():
    return 'ok', 200

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
        login = request.form.get('login')
        password = request.form.get('password')
        is_medic = request.form.get('is_medic') == 'on'  # Переключатель "Медик"
        
        # Определяем, какую базу данных проверять на основе переключателя
        user = None
        app_type = None
        
        if is_medic:
            # Если переключатель "Медик" включен - ищем в UMAY Pro
            with app.app_context():
                user = db.session.query(UserPro).filter_by(login=login).first()
                if user:
                    app_type = 'pro'
        else:
            # Если переключатель "Медик" выключен - ищем в UMAY Mama
            with app.app_context():
                user = db.session.query(UserMama).filter_by(login=login).first()
                if user:
                    app_type = 'mama'
        
        if user and check_password_hash(user.password, password):
            # Always skip email verification for Joker and admin users
            require_email_verification = True
            try:
                if getattr(user, 'login', '') == 'Joker' or getattr(user, 'user_type', '') == 'admin':
                    require_email_verification = False
            except Exception:
                require_email_verification = True

            # Check if email is verified (unless bypassed)
            if require_email_verification and not getattr(user, 'is_email_verified', False):
                flash('Ваш email не подтвержден. Проверьте почту и подтвердите email адрес.', 'error')
                return render_template('login.html', unverified_email=getattr(user, 'email', ''), unverified_app_type=app_type)
            
            login_user(user)
            
            # Store app type in session
            session['app_type'] = app_type
            
            if getattr(user, 'login', '') == 'Joker':
                flash('Добро пожаловать, Супер Администратор!', 'success')
                return redirect(url_for('admin_panel'))
            elif getattr(user, 'user_type', '') == 'admin':
                flash('Добро пожаловать в админ панель!', 'success')
                return redirect(url_for('admin_panel'))
            elif app_type == 'mama':
                flash('Добро пожаловать в UMAY Mama!', 'success')
                return redirect(url_for('mama_dashboard'))
            else:
                flash('Добро пожаловать в UMAY Pro!', 'success')
                return redirect(url_for('dashboard'))
        else:
            if is_medic:
                flash('Неверный логин или пароль для медицинского персонала!', 'error')
            else:
                flash('Неверный логин или пароль для рожениц!', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    # Lightweight debug
    if request.args.get('debug') == '1':
        return f"REGISTER_DEBUG: method={request.method}, user={getattr(current_user, 'login', 'anon')}, ios={is_ios_device()}"
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        login = request.form.get('login', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user_type = request.form.get('user_type', 'user')
        app_type = request.form.get('app_type', 'pro')  # 'pro' or 'mama'
        
        # Validation
        if not full_name:
            flash('Имя обязательно для заполнения!', 'error')
            return render_template('register.html')
        
        if not login:
            flash('Логин обязателен для заполнения!', 'error')
            return render_template('register.html')
        
        if not email:
            flash('Email обязателен для заполнения!', 'error')
            return render_template('register.html')
        
        # Basic email validation
        if '@' not in email or '.' not in email:
            flash('Введите корректный email адрес!', 'error')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('Пароль должен содержать минимум 6 символов!', 'error')
            return render_template('register.html')
        
        confirm_password = request.form.get('confirm_password', '')
        if password != confirm_password:
            flash('Пароли не совпадают!', 'error')
            return render_template('register.html')
        
        # Ограничиваем длину полей для PostgreSQL
        if len(full_name) > 100:
            flash('Имя слишком длинное! Максимум 100 символов.', 'error')
            return render_template('register.html')
        
        if len(login) > 50:
            flash('Логин слишком длинный! Максимум 50 символов.', 'error')
            return render_template('register.html')
        
        if len(email) > 120:
            flash('Email слишком длинный! Максимум 120 символов.', 'error')
            return render_template('register.html')

        # Проверяем существование пользователя и выполняем операции с БД безопасно
        try:
            existing_user = None
            if app_type == 'mama':
                with app.app_context():
                    existing_user = db.session.query(UserMama).filter_by(login=login).first()
                    if not existing_user:
                        existing_user = db.session.query(UserMama).filter_by(email=email).first()
            else:
                with app.app_context():
                    existing_user = db.session.query(UserPro).filter_by(login=login).first()
                    if not existing_user:
                        existing_user = db.session.query(UserPro).filter_by(email=email).first()
            
            if existing_user:
                flash('Пользователь с таким логином или email уже существует!', 'error')
                return render_template('register.html')
            
            hashed_password = generate_password_hash(password)

            # Generate email verification token
            email_token = generate_email_token()
            token_expires = datetime.utcnow() + timedelta(hours=EMAIL_VERIFICATION_TTL_HOURS)
            
            if user_type == 'user' and app_type == 'mama':
                # UMAY Mama user registration
                with app.app_context():
                    new_user = UserMama(
                        full_name=full_name[:100],
                        login=login[:50],
                        password=hashed_password,
                        user_type='user',
                        position='Пользователь',
                        city='Не указан',
                        medical_institution='Не указано',
                        department='Не указано',
                        app_type='mama',
                        email=email,
                        is_email_verified=False,
                        email_verification_token=email_token,
                        email_verification_expires=token_expires
                    )
                    db.session.add(new_user)
                    
                    # Create email verification record
                    verification = EmailVerification(
                        email=email,
                        token=email_token,
                        purpose='register',
                        expires_at=token_expires
                    )
                    db.session.add(verification)
                    db.session.commit()
                
            elif user_type in ('midwife', 'manager') and app_type == 'pro':
                # UMAY Pro registration (midwife or manager)
                position = request.form.get('position', '').strip()
                city = request.form.get('city', '').strip()
                medical_institution = request.form.get('medical_institution', '').strip()
                department = request.form.get('department', '').strip()
                
                # Validate required fields for professionals
                if not position:
                    flash('Должность обязательна для заполнения!', 'error')
                    return render_template('register.html')
                
                if not city:
                    flash('Город обязателен для заполнения!', 'error')
                    return render_template('register.html')
                
                if not medical_institution:
                    flash('Медицинское учреждение обязательно для заполнения!', 'error')
                    return render_template('register.html')
                
                if not department:
                    flash('Отделение обязательно для заполнения!', 'error')
                    return render_template('register.html')
                
                # Ограничиваем длину полей
                if len(position) > 100:
                    flash('Должность слишком длинная! Максимум 100 символов.', 'error')
                    return render_template('register.html')
                
                if len(city) > 100:
                    flash('Город слишком длинный! Максимум 100 символов.', 'error')
                    return render_template('register.html')
                
                if len(medical_institution) > 200:
                    flash('Название медицинского учреждения слишком длинное! Максимум 200 символов.', 'error')
                    return render_template('register.html')
                
                if len(department) > 200:
                    flash('Название отделения слишком длинное! Максимум 200 символов.', 'error')
                    return render_template('register.html')
                
                with app.app_context():
                    new_user = UserPro(
                        full_name=full_name[:100],
                        login=login[:50],
                        password=hashed_password,
                        user_type=user_type,
                        position=position[:100],
                        city=city[:100],
                        medical_institution=medical_institution[:200],
                        department=department[:200],
                        app_type='pro',
                        email=email,
                        is_email_verified=False,
                        email_verification_token=email_token,
                        email_verification_expires=token_expires
                    )
                    db.session.add(new_user)
                    
                    # Create email verification record
                    verification = EmailVerification(
                        email=email,
                        token=email_token,
                        purpose='register',
                        expires_at=token_expires
                    )
                    db.session.add(verification)
                    db.session.commit()
            else:
                flash('Неверный тип пользователя или приложения!', 'error')
                return render_template('register.html')
            
            # Send verification email
            ok, message = send_verification_email(email, email_token, user_type, app_type)
            if not ok:
                # If email fails, delete user and show error
                db.session.delete(new_user)
                db.session.delete(verification)
                db.session.commit()
                flash(f'Ошибка отправки email: {message}', 'error')
                return render_template('register.html')
            
            flash('Регистрация успешна! Проверьте ваш email для подтверждения адреса.', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            logger.exception(f"Registration error: {e}")
            flash('Ошибка при регистрации. Попробуйте позже.', 'error')
            return render_template('register.html')
    
    try:
        logger.info("Rendering register.html")
        # iOS Safari fallback: avoid heavy animations if needed
        template_name = 'register.html'
        return render_template(template_name)
    except Exception as e:
        logger.error(f"Register GET render failed: {e}")
        return f"Register render error: {e}", 500



@app.route('/recover', methods=['GET', 'POST'])
def recover():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not email:
            flash('Введите корректный email адрес!', 'error')
            return render_template('recover.html')

        if new_password and (len(new_password) < 6 or new_password != confirm_password):
            flash('Пароль некорректен или не совпадает', 'error')
            return render_template('recover.html')

        # Find user by email
        user = db.session.query(UserPro).filter_by(email=email).first()
        if not user:
            user = db.session.query(UserMama).filter_by(email=email).first()
        if not user:
            flash('Пользователь с таким email не найден', 'error')
            return render_template('recover.html')

        # Generate reset token and send email
        reset_token = generate_email_token()
        token_expires = datetime.utcnow() + timedelta(hours=1)
        
        # Create reset verification record
        verification = EmailVerification(
            email=email,
            token=reset_token,
            purpose='reset',
            expires_at=token_expires
        )
        db.session.add(verification)
        db.session.commit()
        
        # Send reset email
        ok, message = send_verification_email(email, reset_token, user.user_type, user.app_type, purpose='reset')
        if not ok:
            flash(f'Ошибка отправки email: {message}', 'error')
            return render_template('recover.html')
        
        flash('Инструкции по восстановлению пароля отправлены на ваш email.', 'success')
        return redirect(url_for('login'))

    return render_template('recover.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы!', 'success')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
@pro_required
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

@app.route('/mama-dashboard')
@login_required
@mama_required
def mama_dashboard():
    """Дашборд для пользователей UMAY Mama"""
    logger.info(f"Mama Dashboard accessed by user: {current_user.full_name} (login: {current_user.login})")
    try:
        # Получаем ВСЕ статьи для отладки (убираем фильтр is_published)
        mama_content = MamaContent.query.order_by(MamaContent.created_at.desc()).limit(6).all()
        
        # Отладочная информация
        logger.info(f"Found {len(mama_content)} articles in mama_content")
        for article in mama_content:
            logger.info(f"Article: {article.title}, Published: {article.is_published}, Category: {article.category}")
        
        # Статистика контента (убираем фильтр is_published)
        total_content = MamaContent.query.count()
        sport_content = MamaContent.query.filter_by(category='sport').count()
        nutrition_content = MamaContent.query.filter_by(category='nutrition').count()
        vitamins_content = MamaContent.query.filter_by(category='vitamins').count()
        
        logger.info(f"Statistics - Total: {total_content}, Sport: {sport_content}, Nutrition: {nutrition_content}, Vitamins: {vitamins_content}")
        
        return render_template('mama/dashboard.html',
                             mama_content=mama_content,
                             total_content=total_content,
                             sport_content=sport_content,
                             nutrition_content=nutrition_content,
                             vitamins_content=vitamins_content)
    except Exception as e:
        logger.error(f"Error in mama dashboard: {e}")
        flash('Ошибка при загрузке панели управления UMAY Mama', 'error')
        return redirect(url_for('index'))

@app.route('/add_patient', methods=['GET', 'POST'])
@app.route('/добавить_пациента', methods=['GET', 'POST'])  # alias for Russian URL to avoid 404/blank
@login_required
def add_patient():
    # Allow all авторизованные пользователи, кроме управленцев (кроме Joker)
    if getattr(current_user, 'user_type', '') == 'manager' and getattr(current_user, 'login', '') != 'Joker':
        flash('Доступ запрещен. Эта функция доступна только медицинскому персоналу.', 'error')
        return redirect(url_for('index'))
    # Check if mobile version is requested
    mobile_requested = request.args.get('mobile') == '1'
    # Server-side fallback: if no param but user-agent is mobile, serve mobile template
    if not mobile_requested and is_mobile_device():
        mobile_requested = True

    # Lightweight debug endpoint (safe): /add_patient?debug=1
    if request.args.get('debug') == '1':
        return f"ADD_PATIENT_DEBUG: mobile_requested={mobile_requested}, ios={is_ios_device()}, user={getattr(current_user, 'login', 'anon')}"
    
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
            pls = "Да" if 'pls' in request.form else "Нет"
            pts = "Да" if 'pts' in request.form else "Нет"
            eclampsia = "Да" if 'eclampsia' in request.form else "Нет"
            gestational_hypertension = "Да" if 'gestational_hypertension' in request.form else "Нет"
            placenta_previa = "Да" if 'placenta_previa' in request.form else "Нет"
            shoulder_dystocia = "Да" if 'shoulder_dystocia' in request.form else "Нет"
            third_degree_tear = "Да" if 'third_degree_tear' in request.form else "Нет"
            cord_prolapse = "Да" if 'cord_prolapse' in request.form else "Нет"
            postpartum_hemorrhage = "Да" if 'postpartum_hemorrhage' in request.form else "Нет"
            placental_abruption = "Да" if 'placental_abruption' in request.form else "Нет"
            
            # Валидация обязательных полей
            if not request.form['patient_name'] or request.form['patient_name'].strip() == "":
                flash('ФИО роженицы обязательно для заполнения', 'error')
                return render_template('mobile/add_patient.html' if mobile_requested else 'add_patient.html')
            
            if not request.form['child_gender'] or request.form['child_gender'] == "":
                flash('Необходимо выбрать пол ребенка', 'error')
                return render_template('mobile/add_patient.html' if mobile_requested else 'add_patient.html')
            
            if not request.form['delivery_method'] or request.form['delivery_method'] == "":
                flash('Необходимо выбрать способ родоразрешения', 'error')
                return render_template('mobile/add_patient.html' if mobile_requested else 'add_patient.html')
            
            if not request.form['anesthesia'] or request.form['anesthesia'] == "":
                flash('Необходимо выбрать тип анестезии', 'error')
                return render_template('mobile/add_patient.html' if mobile_requested else 'add_patient.html')
            
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
                oligohydramnios=oligohydramnios,
                pls=pls,
                pts=pts,
                eclampsia=eclampsia,
                gestational_hypertension=gestational_hypertension,
                placenta_previa=placenta_previa,
                shoulder_dystocia=shoulder_dystocia,
                third_degree_tear=third_degree_tear,
                cord_prolapse=cord_prolapse,
                postpartum_hemorrhage=postpartum_hemorrhage,
                placental_abruption=placental_abruption
            )
            
            db.session.add(new_patient)
            db.session.commit()
            flash('Пациент успешно добавлен!', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка при добавлении пациента: {e}")
            flash('Ошибка при добавлении пациента. Проверьте данные.', 'error')
    
    # Render appropriate template based on mobile request
    prefer_mobile = mobile_requested
    # iOS fallback to avoid potential blank screen
    if prefer_mobile and is_ios_device() and request.args.get('force') != 'mobile':
        logger.info('iOS detected -> fallback to desktop add_patient; use ?force=mobile to override')
        prefer_mobile = False

    template_name = 'mobile/add_patient.html' if prefer_mobile else 'add_patient.html'
    try:
        logger.info(f"Rendering add_patient template: {template_name}, mobile={mobile_requested}")
        return render_template(template_name)
    except Exception as e:
        logger.error(f"Add patient GET render failed: {e}")
        return f"Render error: {e}", 500

@app.route('/edit_patient/<int:patient_id>', methods=['GET', 'POST'])
@login_required
@pro_clinical_required
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
            pls = "Да" if 'pls' in request.form else "Нет"
            pts = "Да" if 'pts' in request.form else "Нет"
            eclampsia = "Да" if 'eclampsia' in request.form else "Нет"
            gestational_hypertension = "Да" if 'gestational_hypertension' in request.form else "Нет"
            placenta_previa = "Да" if 'placenta_previa' in request.form else "Нет"
            shoulder_dystocia = "Да" if 'shoulder_dystocia' in request.form else "Нет"
            third_degree_tear = "Да" if 'third_degree_tear' in request.form else "Нет"
            cord_prolapse = "Да" if 'cord_prolapse' in request.form else "Нет"
            postpartum_hemorrhage = "Да" if 'postpartum_hemorrhage' in request.form else "Нет"
            placental_abruption = "Да" if 'placental_abruption' in request.form else "Нет"
            
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
            patient.pls = pls
            patient.pts = pts
            patient.eclampsia = eclampsia
            patient.gestational_hypertension = gestational_hypertension
            patient.placenta_previa = placenta_previa
            patient.shoulder_dystocia = shoulder_dystocia
            patient.third_degree_tear = third_degree_tear
            patient.cord_prolapse = cord_prolapse
            patient.postpartum_hemorrhage = postpartum_hemorrhage
            patient.placental_abruption = placental_abruption
            
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
@pro_clinical_required
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
@pro_required
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
@pro_required
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
@admin_required
def admin_panel():
    """Главная страница админ-панели"""
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
@admin_required
def admin_news():
    """Управление новостями"""
    news = News.query.order_by(News.created_at.desc()).all()
    return render_template('admin/news.html', news=news)

@app.route('/admin/news/add', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_news_add():
    """Добавление новости"""
    
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
@admin_required
def admin_news_edit(news_id):
    """Редактирование новости"""
    
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
@admin_required
def admin_news_delete(news_id):
    """Удаление новости"""
    
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
@admin_required
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

@app.route('/admin/mama-content/list')
@login_required
@admin_required
def admin_mama_content_list():
    """Список всех статей с возможностью редактирования/удаления"""
    if current_user.user_type != 'admin' and current_user.login != 'Joker':
        flash('Доступ запрещен', 'error')
        return redirect(url_for('dashboard'))
    
    # Получаем все статьи
    all_content = MamaContent.query.order_by(MamaContent.created_at.desc()).all()
    
    # Категории для отображения
    categories = {
        'sport': '🏃 Спорт',
        'nutrition': '🍎 Питание',
        'vitamins': '💊 Витамины',
        'body_care': '💅 Уход за телом',
        'baby_care': '👶 Уход за малышом',
        'doctor_advice': '👨‍⚕️ Советы врачей'
    }
    
    return render_template('admin/mama_content_list.html',
                         content_list=all_content,
                         categories=categories)

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
@admin_required
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
@admin_required
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

def get_latest_news(category):
    """Получение актуальных новостей из интернета"""
    try:
        # Поисковые запросы для разных категорий
        search_queries = {
            'sport': ['беременность спорт упражнения', 'фитнес для беременных', 'йога беременность'],
            'nutrition': ['питание беременных', 'диета беременность', 'витамины беременность'],
            'vitamins': ['витамины беременность', 'фолиевая кислота', 'витамин D беременность'],
            'body_care': ['уход за телом беременность', 'кожа беременность', 'растяжки беременность'],
            'baby_care': ['уход за новорожденным', 'кормление грудью', 'сон новорожденного'],
            'doctor_advice': ['советы врача беременность', 'беременность рекомендации', 'роды подготовка']
        }
        
        if category not in search_queries:
            return []
        
        news_items = []
        for query in search_queries[category][:2]:  # Берем первые 2 запроса
            try:
                # Используем Google News API или RSS-ленты
                url = f"https://news.google.com/search?q={query}&hl=ru&gl=RU&ceid=RU:ru"
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    articles = soup.find_all('article', limit=3)
                    
                    for article in articles:
                        title_elem = article.find('h3')
                        if title_elem:
                            title = title_elem.get_text().strip()
                            if title and len(title) > 10:
                                news_items.append({
                                    'title': title,
                                    'source': 'Актуальные новости',
                                    'date': datetime.now().strftime('%Y-%m-%d')
                                })
            except Exception as e:
                logger.error(f"Ошибка при получении новостей для {query}: {e}")
                continue
        
        return news_items
    except Exception as e:
        logger.error(f"Ошибка при получении актуальных новостей: {e}")
        return []

def generate_ai_content(category, trimester, count):
    """ПРОФЕССИОНАЛЬНЫЙ ИИ-генератор контента с картинками и журналистским стилем"""
    
    # Богатые шаблоны для генерации профессиональных статей
    templates = {
        'sport': {
            'titles': [
                '🏃‍♀️ Полное руководство по упражнениям для беременных в {trimester} триместре',
                '💪 Безопасная гимнастика для будущих мам: комплекс упражнений',
                '🧘‍♀️ Йога для беременных: {trimester} триместр - техники и позы',
                '🫁 Дыхательные упражнения для подготовки к родам',
                '🏊‍♀️ Аквааэробика для беременных: безопасные упражнения в воде',
                '🚶‍♀️ Прогулки и ходьба во время беременности: правильная техника',
                '🤸‍♀️ Растяжка для беременных: гибкость и расслабление'
            ],
            'images': [
                'https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=800&h=600&fit=crop',
                'https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?w=800&h=600&fit=crop',
                'https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=800&h=600&fit=crop',
                'https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?w=800&h=600&fit=crop'
            ],
            'content': [
                '''# 🏃‍♀️ Полное руководство по упражнениям для беременных в {trimester} триместре

![Беременная женщина занимается йогой](https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=800&h=600&fit=crop)

Беременность - это особое время, когда физическая активность не только разрешена, но и **крайне полезна**. В {trimester} триместре ваш организм претерпевает значительные изменения, и правильные упражнения помогут вам чувствовать себя лучше, подготовиться к родам и быстрее восстановиться после них.

---

## 🎯 Почему упражнения важны во время беременности?

Физическая активность во время беременности приносит множество преимуществ:

### ✅ **Улучшение кровообращения**
Снижает риск отеков и варикозного расширения вен, улучшает снабжение кислородом малыша.

### 💪 **Укрепление мышц**
Особенно важны мышцы тазового дна и брюшного пресса - они играют ключевую роль в родах.

### ⚖️ **Контроль веса**
Помогает поддерживать здоровый набор веса и быстрее вернуться к форме после родов.

### 😊 **Улучшение настроения**
Физическая активность повышает уровень эндорфинов - гормонов счастья.

### 👶 **Подготовка к родам**
Укрепляет мышцы, участвующие в процессе родов, улучшает выносливость.

---

## ⚠️ Меры предосторожности

![Консультация с врачом](https://images.unsplash.com/photo-1559757148-5c350d0d3c56?w=800&h=600&fit=crop)

**Перед началом любых упражнений обязательно проконсультируйтесь с врачом.** Особенно важно это сделать, если у вас есть:

- 🚨 **Угроза прерывания беременности**
- 💧 **Многоводие или маловодие**
- 📍 **Предлежание плаценты**
- 🏥 **Любые хронические заболевания**

---

## 🎯 Рекомендуемые упражнения для {trimester} триместра

### 1. 🫁 Дыхательные упражнения

![Дыхательные упражнения](https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?w=800&h=600&fit=crop)

Правильное дыхание - **основа подготовки к родам**. Выполняйте эти упражнения ежедневно:

#### **Диафрагмальное дыхание:**
1. Сядьте удобно, положите руки на живот
2. Вдохните глубоко через нос, почувствуйте, как поднимается живот
3. Выдохните медленно через рот
4. Повторите 10-15 раз

#### **Техника "4-7-8":**
1. Вдохните на 4 счета
2. Задержите дыхание на 7 счетов
3. Выдохните на 8 счетов
4. Повторите 5-10 раз

### 2. 💪 Упражнения Кегеля

Эти упражнения укрепляют **мышцы тазового дна**:

- Сожмите мышцы тазового дна (как будто сдерживаете мочеиспускание)
- Удерживайте 5-10 секунд
- Расслабьтесь на 5 секунд
- Повторите 10-15 раз, 3 раза в день

### 3. 🐱 Поза кошки-коровы

![Поза кошки-коровы](https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=800&h=600&fit=crop)

Отличное упражнение для спины:

1. Встаньте на четвереньки
2. На вдохе прогните спину, подняв голову и копчик
3. На выдохе округлите спину, опустив голову
4. Повторите 10-15 раз

---

## 📋 Программа тренировок

### **День 1-2:**
- 🚶‍♀️ **Разминка:** 5-10 минут легкой ходьбы
- 🫁 **Основная часть:** дыхательные упражнения + упражнения Кегеля
- 🤸‍♀️ **Заминка:** растяжка

### **День 3-4:**
- 🚶‍♀️ **Разминка:** 5-10 минут легкой ходьбы
- 🐱 **Основная часть:** поза кошки-коровы + упражнения для рук
- 😌 **Заминка:** расслабление

### **День 5-7:**
- 🛌 **Отдых или легкая прогулка**

---

## 🚨 Когда прекратить упражнения

**Немедленно прекратите упражнения и обратитесь к врачу**, если почувствуете:

- 😰 **Боль в животе или тазу**
- 💫 **Головокружение или тошноту**
- 🩸 **Кровотечение**
- 🤰 **Схватки**
- 😮‍💨 **Одышку**

---

## 💡 Советы для эффективных тренировок

![Тренировка беременной](https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=800&h=600&fit=crop)

1. **🎧 Слушайте свое тело** - если что-то вызывает дискомфорт, прекратите упражнение
2. **❄️ Не перегревайтесь** - занимайтесь в прохладном помещении
3. **💧 Пейте достаточно воды** - до, во время и после тренировки
4. **👕 Носите удобную одежду** - специальную одежду для беременных
5. **📅 Занимайтесь регулярно** - лучше 15 минут каждый день, чем 2 часа раз в неделю

---

## 🎯 Ожидаемые результаты

При регулярных занятиях вы заметите:

- 😊 **Улучшение общего самочувствия**
- 💆‍♀️ **Снижение болей в спине**
- 🫁 **Лучший контроль дыхания**
- ⚡ **Повышение энергии**
- 😴 **Улучшение сна**

---

> **💡 Помните:** Каждая беременность уникальна. То, что подходит одной женщине, может не подойти другой. Всегда консультируйтесь с врачом и прислушивайтесь к своему организму.

---

*Статья подготовлена экспертами UMAY Mama для безопасных и эффективных тренировок во время беременности.*'''
            ]
        },
        'nutrition': {
            'titles': [
                '🥗 Правильное питание для беременных в {trimester} триместре',
                '🍎 Витамины и минералы: что нужно будущей маме',
                '🥩 Белки в рационе беременной: источники и нормы',
                '🥑 Полезные жиры для развития мозга малыша',
                '🌾 Сложные углеводы: энергия для мамы и малыша',
                '💧 Питьевой режим во время беременности',
                '🍽️ Планирование меню для беременных'
            ],
            'images': [
                'https://images.unsplash.com/photo-1490645935967-10de6ba17061?w=800&h=600&fit=crop',
                'https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=800&h=600&fit=crop',
                'https://images.unsplash.com/photo-1490645935967-10de6ba17061?w=800&h=600&fit=crop',
                'https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=800&h=600&fit=crop'
            ],
            'content': [
                '''# 🥗 Правильное питание для беременных в {trimester} триместре

![Здоровое питание для беременных](https://images.unsplash.com/photo-1490645935967-10de6ba17061?w=800&h=600&fit=crop)

Правильное питание во время беременности - **основа здоровья мамы и малыша**. В {trimester} триместре потребности организма меняются, и важно обеспечить все необходимые питательные вещества.

---

## 🎯 Основные принципы питания

### ✅ **Сбалансированность**
Рацион должен содержать белки, жиры, углеводы, витамины и минералы в правильных пропорциях.

### 🍎 **Разнообразие**
Включайте в меню разные группы продуктов для получения всех необходимых веществ.

### ⏰ **Регулярность**
Питайтесь 5-6 раз в день небольшими порциями для лучшего усвоения.

### 💧 **Достаточное питье**
Выпивайте 2-2.5 литра воды в день для поддержания обмена веществ.

---

## 🥩 Белки: строительный материал

![Белковые продукты](https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=800&h=600&fit=crop)

**Белки** - основа для роста и развития малыша. В день нужно потреблять 1.5-2 г белка на кг веса.

### **Источники белка:**
- 🥩 **Мясо:** говядина, телятина, индейка, курица
- 🐟 **Рыба:** лосось, треска, минтай, сельдь
- 🥚 **Яйца:** 1-2 яйца в день
- 🥛 **Молочные продукты:** творог, йогурт, кефир
- 🫘 **Бобовые:** фасоль, чечевица, горох

---

## 🥑 Полезные жиры

**Жиры** необходимы для развития мозга и нервной системы малыша.

### **Источники полезных жиров:**
- 🥑 **Авокадо:** содержит мононенасыщенные жиры
- 🥜 **Орехи:** грецкие, миндаль, кешью
- 🫒 **Оливковое масло:** для заправки салатов
- 🐟 **Жирная рыба:** лосось, скумбрия, сардины

---

## 🌾 Сложные углеводы

![Углеводы для энергии](https://images.unsplash.com/photo-1490645935967-10de6ba17061?w=800&h=600&fit=crop)

**Сложные углеводы** обеспечивают энергию и предотвращают резкие скачки сахара в крови.

### **Источники сложных углеводов:**
- 🍞 **Цельнозерновой хлеб**
- 🍚 **Крупы:** гречка, овсянка, бурый рис
- 🥔 **Картофель** (в умеренных количествах)
- 🥕 **Овощи:** морковь, свекла, тыква

---

## 🍎 Витамины и минералы

### **Витамин C**
Укрепляет иммунитет, помогает усвоению железа.
**Источники:** цитрусовые, болгарский перец, брокколи

### **Фолиевая кислота**
Критически важна для развития нервной системы.
**Источники:** зелень, бобовые, орехи

### **Железо**
Предотвращает анемию.
**Источники:** красное мясо, печень, шпинат

### **Кальций**
Для крепких костей мамы и малыша.
**Источники:** молочные продукты, кунжут, миндаль

---

## 🚫 Что ограничить или исключить

### **Ограничить:**
- ☕ **Кофеин:** не более 200 мг в день
- 🍰 **Сладости:** сахар, конфеты, выпечка
- 🍟 **Жареное:** фастфуд, жареные блюда
- 🧂 **Соль:** не более 5 г в день

### **Исключить:**
- 🍷 **Алкоголь:** полностью исключить
- 🚬 **Курение:** пассивное и активное
- 🥩 **Сырое мясо:** суши, тартар, стейки с кровью
- 🥛 **Непастеризованные продукты:** сырые яйца, непастеризованное молоко

---

## 📋 Примерное меню на день

### **Завтрак:**
- 🥣 Овсяная каша с фруктами и орехами
- 🥛 Стакан молока или йогурта
- 🍎 Яблоко или банан

### **Второй завтрак:**
- 🥪 Бутерброд с творогом и зеленью
- 🥛 Чай или компот

### **Обед:**
- 🥩 Суп с мясом и овощами
- 🍚 Гречка с куриной грудкой
- 🥗 Салат из свежих овощей
- 🥖 Хлеб

### **Полдник:**
- 🥛 Творог с фруктами
- 🥜 Горсть орехов

### **Ужин:**
- 🐟 Запеченная рыба с овощами
- 🍚 Бурый рис
- 🥗 Салат

### **Перед сном:**
- 🥛 Стакан кефира или йогурта

---

## 💡 Советы по питанию

![Планирование питания](https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=800&h=600&fit=crop)

1. **📝 Ведите дневник питания** - записывайте что и когда едите
2. **🛒 Планируйте покупки** - составляйте список продуктов на неделю
3. **👨‍🍳 Готовьте дома** - так вы контролируете качество и состав блюд
4. **🍽️ Ешьте медленно** - тщательно пережевывайте пищу
5. **🚰 Пейте воду** - между приемами пищи

---

## 🚨 Когда обращаться к врачу

**Немедленно обратитесь к врачу**, если:

- 🤢 **Постоянная тошнота и рвота**
- 🍽️ **Полная потеря аппетита**
- 💧 **Сильная жажда и частое мочеиспускание**
- 🩸 **Кровь в стуле**
- 😰 **Сильные боли в животе**

---

> **💡 Помните:** Каждая беременность уникальна. Консультируйтесь с врачом для составления индивидуального плана питания.

---

*Статья подготовлена экспертами UMAY Mama для здорового питания во время беременности.*'''
            ]
        },
        'vitamins': {
            'titles': [
                '💊 Витамины для беременных: полный гид по {trimester} триместру',
                '🥬 Фолиевая кислота: зачем она нужна будущей маме',
                '🌞 Витамин D: солнечный витамин для здоровья мамы и малыша',
                '🩸 Железо: профилактика анемии во время беременности',
                '🦷 Кальций: крепкие кости для мамы и малыша',
                '🧠 Омега-3: развитие мозга и зрения ребенка',
                '💪 Витаминно-минеральные комплексы: как выбрать'
            ],
            'images': [
                'https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?w=800&h=600&fit=crop',
                'https://images.unsplash.com/photo-1559757148-5c350d0d3c56?w=800&h=600&fit=crop',
                'https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?w=800&h=600&fit=crop',
                'https://images.unsplash.com/photo-1559757148-5c350d0d3c56?w=800&h=600&fit=crop'
            ],
            'content': [
                '''# 💊 Витамины для беременных: полный гид по {trimester} триместру

![Витамины для беременных](https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?w=800&h=600&fit=crop)

Витамины и минералы играют **критически важную роль** во время беременности. В {trimester} триместре потребности организма меняются, и важно обеспечить все необходимые питательные вещества для здоровья мамы и правильного развития малыша.

---

## 🎯 Почему витамины так важны?

### ✅ **Правильное развитие плода**
Витамины участвуют в формировании всех органов и систем малыша.

### 🛡️ **Защита здоровья мамы**
Поддерживают иммунитет и предотвращают осложнения беременности.

### 💪 **Подготовка к родам**
Укрепляют организм и помогают быстрее восстановиться после родов.

---

## 🥬 Фолиевая кислота (Витамин B9)

![Фолиевая кислота](https://images.unsplash.com/photo-1559757148-5c350d0d3c56?w=800&h=600&fit=crop)

**Фолиевая кислота** - самый важный витамин для беременных.

### **Роль в организме:**
- 🧠 **Развитие нервной системы** плода
- 🩸 **Образование красных кровяных телец**
- 🧬 **Синтез ДНК** и деление клеток

### **Норма потребления:**
- 📊 **400-800 мкг** в день
- 📊 **Начинать прием** за 3 месяца до зачатия
- 📊 **Продолжать** весь первый триместр

### **Источники:**
- 🥬 **Зелень:** шпинат, салат, петрушка
- 🫘 **Бобовые:** фасоль, чечевица, горох
- 🥜 **Орехи:** грецкие, миндаль
- 🍊 **Цитрусовые:** апельсины, лимоны

---

## 🌞 Витамин D

**Витамин D** необходим для крепких костей и зубов.

### **Роль в организме:**
- 🦷 **Усвоение кальция** и фосфора
- 🦴 **Развитие костной системы** малыша
- 🛡️ **Укрепление иммунитета**

### **Норма потребления:**
- 📊 **600-800 МЕ** в день
- 📊 **Увеличить дозу** при недостатке солнца

### **Источники:**
- ☀️ **Солнечный свет** - 15-20 минут в день
- 🐟 **Жирная рыба:** лосось, скумбрия, сардины
- 🥛 **Молочные продукты:** молоко, йогурт, сыр
- 🥚 **Яичные желтки**

---

## 🩸 Железо

**Железо** предотвращает анемию и обеспечивает кислородом малыша.

### **Роль в организме:**
- 🩸 **Образование гемоглобина**
- 💨 **Транспорт кислорода** к тканям
- 🧠 **Развитие мозга** плода

### **Норма потребления:**
- 📊 **27 мг** в день
- 📊 **Увеличить** при анемии

### **Источники:**
- 🥩 **Красное мясо:** говядина, баранина
- 🐟 **Рыба:** тунец, лосось
- 🥬 **Зелень:** шпинат, брокколи
- 🫘 **Бобовые:** фасоль, чечевица

---

## 🦷 Кальций

**Кальций** необходим для крепких костей и зубов.

### **Роль в организме:**
- 🦴 **Развитие костной системы** малыша
- 🦷 **Формирование зубов**
- 💪 **Сокращение мышц**

### **Норма потребления:**
- 📊 **1000-1300 мг** в день
- 📊 **Увеличить** в третьем триместре

### **Источники:**
- 🥛 **Молочные продукты:** молоко, йогурт, творог
- 🧀 **Сыр:** твердые сорта
- 🥬 **Зелень:** капуста, брокколи
- 🥜 **Орехи:** миндаль, кешью

---

## 🧠 Омега-3 жирные кислоты

**Омега-3** критически важны для развития мозга и зрения.

### **Роль в организме:**
- 🧠 **Развитие мозга** и нервной системы
- 👁️ **Формирование зрения**
- 🛡️ **Укрепление иммунитета**

### **Норма потребления:**
- 📊 **200-300 мг** DHA в день
- 📊 **Особенно важно** в третьем триместре

### **Источники:**
- 🐟 **Жирная рыба:** лосось, скумбрия, сардины
- 🥜 **Орехи:** грецкие орехи
- 🥑 **Авокадо**
- 🫒 **Оливковое масло**

---

## 💊 Витаминно-минеральные комплексы

![Витаминные комплексы](https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?w=800&h=600&fit=crop)

### **Когда принимать:**
- ✅ **При планировании беременности**
- ✅ **Весь первый триместр**
- ✅ **При недостатке витаминов**
- ✅ **По назначению врача**

### **Как выбрать:**
- 🏥 **Консультация с врачом** - обязательна
- 📊 **Содержание фолиевой кислоты** - 400-800 мкг
- 🩸 **Железо** - 27 мг
- 🦷 **Кальций** - 1000-1300 мг

---

## 🚫 Что ограничить

### **Витамин A:**
- ⚠️ **Не более 3000 МЕ** в день
- ⚠️ **Избегать** высоких доз ретинола
- ⚠️ **Безопасен** бета-каротин из овощей

### **Витамин E:**
- ⚠️ **Не более 15 мг** в день
- ⚠️ **Избегать** высоких доз

---

## 💡 Советы по приему витаминов

![Прием витаминов](https://images.unsplash.com/photo-1559757148-5c350d0d3c56?w=800&h=600&fit=crop)

1. **⏰ Принимайте в одно время** - лучше утром после еды
2. **💧 Запивайте водой** - не чаем или кофе
3. **🍽️ Принимайте с едой** - для лучшего усвоения
4. **📝 Ведите дневник** - записывайте прием витаминов
5. **🏥 Консультируйтесь с врачом** - при любых сомнениях

---

## 🚨 Когда обращаться к врачу

**Немедленно обратитесь к врачу**, если:

- 🤢 **Тошнота после приема витаминов**
- 🩸 **Аллергические реакции**
- 😰 **Боли в животе**
- 💊 **Передозировка витаминов**

---

## 📋 План приема витаминов по триместрам

### **Первый триместр:**
- 🥬 **Фолиевая кислота** - 400-800 мкг
- 🌞 **Витамин D** - 600-800 МЕ
- 🩸 **Железо** - по назначению врача

### **Второй триместр:**
- 🦷 **Кальций** - 1000-1300 мг
- 🧠 **Омега-3** - 200-300 мг DHA
- 🩸 **Железо** - 27 мг

### **Третий триместр:**
- 🦷 **Кальций** - увеличить дозу
- 🧠 **Омега-3** - особенно важно
- 🩸 **Железо** - контроль уровня

---

> **💡 Помните:** Витамины - это дополнение к правильному питанию, а не замена ему. Консультируйтесь с врачом для составления индивидуального плана.

---

*Статья подготовлена экспертами UMAY Mama на основе рекомендаций ведущих акушеров-гинекологов.*'''
            ]
        },
        'body_care': {
            'titles': [
                '🧴 Уход за телом во время беременности: {trimester} триместр',
                '🫧 Растяжки: профилактика и уход за кожей',
                '💆‍♀️ Массаж для беременных: техники и приемы',
                '🛁 Гигиена беременной: правила и рекомендации',
                '👙 Уход за грудью: подготовка к кормлению',
                '🦶 Отеки ног: причины и способы борьбы',
                '💄 Косметика для беременных: что безопасно'
            ],
            'images': [
                'https://images.unsplash.com/photo-1559757148-5c350d0d3c56?w=800&h=600&fit=crop',
                'https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=800&h=600&fit=crop',
                'https://images.unsplash.com/photo-1559757148-5c350d0d3c56?w=800&h=600&fit=crop',
                'https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=800&h=600&fit=crop'
            ],
        },
        'baby_care': {
            'titles': [
                '👶 Уход за новорожденным: первые дни жизни',
                '🍼 Кормление грудью: основы и техники',
                '😴 Сон новорожденного: режим и безопасность',
                '🛁 Купание малыша: пошаговое руководство',
                '👕 Одежда для новорожденного: как выбрать',
                '🚼 Подгузники и гигиена: что нужно знать',
                '🏥 Первый месяц жизни: развитие и уход'
            ],
            'images': [
                'https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?w=800&h=600&fit=crop',
                'https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=800&h=600&fit=crop',
                'https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?w=800&h=600&fit=crop',
                'https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=800&h=600&fit=crop'
            ],
                },
        'doctor_advice': {
            'titles': [
                '👨‍⚕️ Советы врача: подготовка к родам в {trimester} триместре',
                '🏥 Посещение врача: что спросить на приеме',
                '📋 Анализы и обследования: график и важность',
                '🚨 Тревожные симптомы: когда обращаться к врачу',
                '💊 Лекарства во время беременности: что безопасно',
                '🏃‍♀️ Физическая активность: рекомендации врача',
                '😴 Отдых и сон: советы для беременных'
            ],
            'images': [
                'https://images.unsplash.com/photo-1559757148-5c350d0d3c56?w=800&h=600&fit=crop',
                'https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=800&h=600&fit=crop',
                'https://images.unsplash.com/photo-1559757148-5c350d0d3c56?w=800&h=600&fit=crop',
                'https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=800&h=600&fit=crop'
            ],
            'content': [
                '''# 👨‍⚕️ Советы врача: подготовка к родам в {trimester} триместре

![Консультация с врачом](https://images.unsplash.com/photo-1559757148-5c350d0d3c56?w=800&h=600&fit=crop)

Регулярные консультации с врачом во время беременности - **основа безопасного вынашивания малыша**. В {trimester} триместре особенно важно следить за своим здоровьем и выполнять все рекомендации специалиста.

---

## 🏥 График посещений врача

### **{trimester} триместр:**
- 📅 **До 28 недель:** каждые 4 недели
- 📅 **28-36 недель:** каждые 2-3 недели  
- 📅 **После 36 недель:** каждую неделю

---

## 📋 Обязательные анализы и обследования

### **Анализы крови:**
- 🩸 **Общий анализ крови** - контроль гемоглобина
- 🩸 **Биохимический анализ** - проверка работы печени и почек
- 🩸 **Анализ на сахар** - контроль уровня глюкозы
- 🩸 **Анализ на группу крови и резус-фактор**

### **УЗИ обследования:**
- 📊 **12-14 недель** - первый скрининг
- 📊 **18-21 неделя** - второй скрининг  
- 📊 **30-32 недели** - третий скрининг

---

## 🚨 Тревожные симптомы

**Немедленно обратитесь к врачу**, если заметите:

### **Кровотечения:**
- 🩸 **Любые кровянистые выделения**
- 🩸 **Кровотечение из носа** (если не было раньше)

### **Боли:**
- 😰 **Сильные боли в животе**
- 😰 **Головные боли** (особенно с тошнотой)
- 😰 **Боли в пояснице** (если новые и сильные)

### **Другие симптомы:**
- 🤢 **Сильная тошнота и рвота**
- 💧 **Отеки лица и рук**
- 😮‍💨 **Одышка в покое**
- 🌡️ **Температура выше 37.5°C**

---

## 💊 Лекарства во время беременности

### **Что безопасно:**
- ✅ **Парацетамол** - при головной боли и температуре
- ✅ **Витамины** - назначенные врачом
- ✅ **Препараты железа** - при анемии

### **Что запрещено:**
- ❌ **Аспирин** - может вызвать кровотечения
- ❌ **Ибупрофен** - небезопасен во время беременности
- ❌ **Антибиотики** - только по назначению врача

---

## 🏃‍♀️ Физическая активность

### **Рекомендуется:**
- 🚶‍♀️ **Прогулки** - 30-60 минут в день
- 🧘‍♀️ **Йога для беременных** - под руководством инструктора
- 🏊‍♀️ **Плавание** - отличная нагрузка без вреда для суставов

### **Ограничить:**
- ⚠️ **Бег** - только если занимались до беременности
- ⚠️ **Поднятие тяжестей** - не более 5 кг
- ⚠️ **Конный спорт** - риск падения

---

## 😴 Отдых и сон

### **Правила здорового сна:**
- 🛏️ **Спите 8-9 часов** в сутки
- 🛏️ **Ложитесь спать** в одно и то же время
- 🛏️ **Используйте подушки** для беременных
- 🛏️ **Проветривайте комнату** перед сном

### **Дневной отдых:**
- 😌 **Прилягте** на 30-60 минут днем
- 😌 **Поднимите ноги** для уменьшения отеков
- 😌 **Сделайте дыхательные упражнения**

---

## 📱 Подготовка к родам

### **Что нужно знать:**
- 📚 **Изучите признаки родов** - схватки, отхождение вод
- 📚 **Подготовьте сумку** в роддом
- 📚 **Выберите роддом** и познакомьтесь с врачом
- 📚 **Изучите техники дыхания** для родов

### **Партнерские роды:**
- 👫 **Обсудите с партнером** возможность совместных родов
- 👫 **Подготовьте документы** для партнера
- 👫 **Изучите роль партнера** в родах

---

## 💡 Советы от врачей

![Советы врача](https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=800&h=600&fit=crop)

1. **📝 Ведите дневник беременности** - записывайте все изменения
2. **📱 Установите приложение** для отслеживания беременности
3. **📞 Сохраните номер врача** в быстром наборе
4. **🏥 Знайте адрес роддома** и как туда добраться
5. **📋 Подготовьте документы** заранее

---

## 🎯 План действий на {trimester} триместр

### **Еженедельно:**
- 📊 **Контролируйте вес** - взвешивайтесь раз в неделю
- 📊 **Измеряйте давление** - если есть тонометр
- 📊 **Следите за шевелениями** - записывайте активность малыша

### **Ежемесячно:**
- 🏥 **Посещайте врача** по графику
- 🏥 **Сдавайте анализы** по назначению
- 🏥 **Делайте УЗИ** в назначенные сроки

---

> **💡 Помните:** Каждая беременность уникальна. Доверяйте своему врачу и не стесняйтесь задавать вопросы.

---

*Статья подготовлена экспертами UMAY Mama на основе рекомендаций ведущих акушеров-гинекологов.*'''
            ]
        }
    }
    
    # Генерируем контент
    generated_content = []
    
    if category in templates:
        template = templates[category]
        titles = template['titles']
        images = template['images']
        contents = template.get('content', [])
        
        # Получаем актуальные новости
        latest_news = get_latest_news(category)
        
        for i in range(min(count, len(titles))):
            title = titles[i].format(trimester=trimester)
            image_url = images[i % len(images)]
            
            # Если есть готовый контент, используем его
            if i < len(contents):
                content = contents[i].format(trimester=trimester)
            else:
                # Генерируем контент на основе актуальных новостей
                if latest_news:
                    news_item = latest_news[i % len(latest_news)]
                    content = f'''# {title}

![Актуальные новости]({image_url})

## 📰 Актуальные новости

{news_item['title']}

*Источник: {news_item['source']}*
*Дата: {news_item['date']}*

---

## 💡 Основная информация

Этот материал основан на актуальных исследованиях и рекомендациях экспертов в области беременности и материнства.

---

## 🎯 Ключевые моменты

- ✅ **Научно обоснованные рекомендации**
- ✅ **Актуальная информация**
- ✅ **Практические советы**
- ✅ **Безопасность для мамы и малыша**

---

## 📚 Дополнительные ресурсы

Для получения более подробной информации обратитесь к своему врачу или специалисту по беременности.

---

*Статья подготовлена экспертами UMAY Mama на основе актуальных исследований.*'''
                else:
                    # Генерируем базовый контент
                    content = f'''# {title}

![Информация для беременных]({image_url})

## 📋 Основная информация

Этот материал содержит важную информацию для беременных женщин в {trimester} триместре.

---

## 🎯 Ключевые моменты

- ✅ **Безопасность для мамы и малыша**
- ✅ **Научно обоснованные рекомендации**
- ✅ **Практические советы**
- ✅ **Профессиональная поддержка**

---

## 💡 Рекомендации

Для получения индивидуальных рекомендаций обратитесь к своему врачу.

---

*Статья подготовлена экспертами UMAY Mama.*'''
            
            # Создаем новый контент
            new_content = MamaContent(
                title=title,
                content=content,
                category=category,
                image_url=image_url,
                trimester=trimester,
                difficulty_level='medium',
                duration='15-30 минут',
                author='UMAY Mama',
                is_published=True
            )
            
            db.session.add(new_content)
            generated_content.append(new_content)
    
    db.session.commit()
    return generated_content

@app.route('/admin/media')
@login_required
@admin_required
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
        category=selected_category
    ).order_by(MamaContent.created_at.desc()).all()
    
    return render_template('mama/content.html', 
                         content=content, 
                         categories=categories,
                         selected_category=selected_category)

@app.route('/mama/article/<int:content_id>')
def mama_article_detail(content_id):
    """Детальный просмотр статьи UMAY Mama"""
    article = MamaContent.query.get_or_404(content_id)
    
    # Увеличиваем счетчик просмотров
    article.views = (article.views or 0) + 1
    db.session.commit()
    
    # Получаем категории для навигации
    categories = {
        'sport': 'Спорт',
        'nutrition': 'Питание', 
        'vitamins': 'Витамины',
        'body_care': 'Уход за телом',
        'baby_care': 'Уход за новорождённым',
        'doctor_advice': 'Советы врачей'
    }
    
    # Получаем похожие статьи
    similar_articles = MamaContent.query.filter_by(
        category=article.category
    ).filter(
        MamaContent.id != article.id
    ).order_by(MamaContent.created_at.desc()).limit(3).all()
    
    return render_template('mama/article_detail.html',
                         article=article,
                         categories=categories,
                         similar_articles=similar_articles)

@app.route('/export_csv')
@login_required
@pro_required
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
        midwife_info = None
        with app.app_context():
            midwife_info = db.session.query(UserPro).filter_by(full_name=patient.midwife).first()
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
@pro_required
def analytics():
    """Улучшенная аналитика с графиками"""
    try:
        # Получаем все пациентов
        patients = Patient.query.all()
        
        if not patients:
            logger.warning("⚠️ No patients found in database")
            return render_template('analytics.html', 
                                total_patients=0,
                                male_count=0, female_count=0, avg_age=0,
                                delivery_methods={}, complications={}, anesthesia_types={},
                                avg_child_weight=0, avg_pregnancy_weeks=0, avg_blood_loss=0, avg_labor_duration=0,
                                monthly_trends={}, blood_loss_stats={})
        
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
            if patient.pls == 'Да':
                complications['ПЛС'] = complications.get('ПЛС', 0) + 1
            if patient.pts == 'Да':
                complications['ПТС'] = complications.get('ПТС', 0) + 1
            if patient.eclampsia == 'Да':
                complications['Эклампсия'] = complications.get('Эклампсия', 0) + 1
            if patient.gestational_hypertension == 'Да':
                complications['Гестационная гипертензия'] = complications.get('Гестационная гипертензия', 0) + 1
            if patient.placenta_previa == 'Да':
                complications['Плотное прикрепление последа'] = complications.get('Плотное прикрепление последа', 0) + 1
            if patient.shoulder_dystocia == 'Да':
                complications['Дистоция плечиков'] = complications.get('Дистоция плечиков', 0) + 1
            if patient.third_degree_tear == 'Да':
                complications['Разрыв 3 степени'] = complications.get('Разрыв 3 степени', 0) + 1
            if patient.cord_prolapse == 'Да':
                complications['Выпадение петель пуповины'] = complications.get('Выпадение петель пуповины', 0) + 1
            if patient.postpartum_hemorrhage == 'Да':
                complications['ПРК'] = complications.get('ПРК', 0) + 1
            if patient.placental_abruption == 'Да':
                complications['ПОНРП'] = complications.get('ПОНРП', 0) + 1
        
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
        
        # Статистика кровопотери
        blood_loss_stats = {
            'Нормальная (до 500 мл)': sum(1 for p in patients if p.blood_loss <= 500),
            'Повышенная (500-1000 мл)': sum(1 for p in patients if 500 < p.blood_loss <= 1000),
            'Значительная (1000+ мл)': sum(1 for p in patients if p.blood_loss > 1000)
        }
        
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
                            blood_loss_stats=blood_loss_stats,
                            monthly_trends=monthly_trends)
    
    except Exception as e:
        logger.error(f"Ошибка при загрузке аналитики: {e}")
        flash('Ошибка при загрузке аналитики', 'error')
        return redirect(url_for('dashboard'))

@app.route('/export_pdf')
@login_required
@pro_required
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
            midwife_info = None
            with app.app_context():
                midwife_info = db.session.query(UserPro).filter_by(full_name=patient.midwife).first()
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
        
        # ========================================
        # ДОБАВЛЯЕМ ГРАФИКИ И ДИАГРАММЫ
        # ========================================
        
        # График распределения по возрастам
        story.append(Paragraph("📈 Распределение пациентов по возрастам", subtitle_style))
        
        # Группируем по возрастам
        age_groups = {}
        for patient in patients:
            age_group = f"{(patient.age // 5) * 5}-{(patient.age // 5) * 5 + 4}"
            age_groups[age_group] = age_groups.get(age_group, 0) + 1
        
        age_data = [['Возрастная группа', 'Количество пациентов']]
        for age_group, count in sorted(age_groups.items()):
            age_data.append([age_group, str(count)])
        
        age_table = Table(age_data)
        age_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#8b5cf6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), font_name),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f3f4f6')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#d1d5db')),
            ('FONTNAME', (0, 1), (-1, -1), font_name),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')])
        ]))
        
        story.append(age_table)
        story.append(Spacer(1, 20))
        
        # График распределения по срокам беременности
        story.append(Paragraph("🤰 Распределение по срокам беременности", subtitle_style))
        
        trimester_data = [['Триместр', 'Количество пациентов', 'Процент']]
        first_trimester = sum(1 for p in patients if p.pregnancy_weeks <= 13)
        second_trimester = sum(1 for p in patients if 14 <= p.pregnancy_weeks <= 27)
        third_trimester = sum(1 for p in patients if p.pregnancy_weeks >= 28)
        
        trimester_data.extend([
            ['I триместр (1-13 нед)', str(first_trimester), f'{first_trimester/total_patients*100:.1f}%'],
            ['II триместр (14-27 нед)', str(second_trimester), f'{second_trimester/total_patients*100:.1f}%'],
            ['III триместр (28+ нед)', str(third_trimester), f'{third_trimester/total_patients*100:.1f}%']
        ])
        
        trimester_table = Table(trimester_data)
        trimester_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ec4899')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), font_name),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#fdf2f8')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#fbcfe8')),
            ('FONTNAME', (0, 1), (-1, -1), font_name),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fdf2f8')])
        ]))
        
        story.append(trimester_table)
        story.append(Spacer(1, 20))
        
        # График осложнений
        story.append(Paragraph("⚠️ Анализ осложнений", subtitle_style))
        
        complications_summary = [['Осложнение', 'Количество', 'Процент']]
        complications_list = [
            ('Гестоз', gestosis_count),
            ('Сахарный диабет', diabetes_count),
            ('Гипертония', hypertension_count),
            ('Анемия', anemia_count)
        ]
        
        for complication, count in complications_list:
            complications_summary.append([
                complication,
                str(count),
                f'{count/total_patients*100:.1f}%'
            ])
        
        complications_summary_table = Table(complications_summary)
        complications_summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ef4444')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), font_name),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#fef2f2')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#fecaca')),
            ('FONTNAME', (0, 1), (-1, -1), font_name),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fef2f2')])
        ]))
        
        story.append(complications_summary_table)
        story.append(Spacer(1, 30))
        
        # Рекомендации на основе данных
        story.append(Paragraph("💡 Рекомендации на основе анализа", subtitle_style))
        
        recommendations = []
        
        if gestosis_count > total_patients * 0.1:  # Если больше 10%
            recommendations.append("• Высокий процент гестоза - рекомендуется усилить мониторинг артериального давления")
        
        if diabetes_count > total_patients * 0.05:  # Если больше 5%
            recommendations.append("• Повышенный риск гестационного диабета - усилить контроль уровня сахара")
        
        if hypertension_count > total_patients * 0.08:  # Если больше 8%
            recommendations.append("• Частые случаи гипертонии - рекомендуется консультация кардиолога")
        
        if anemia_count > total_patients * 0.15:  # Если больше 15%
            recommendations.append("• Высокая распространенность анемии - рекомендовать препараты железа")
        
        if not recommendations:
            recommendations.append("• Показатели в пределах нормы, продолжайте текущую практику")
        
        for rec in recommendations:
            story.append(Paragraph(rec, normal_style))
        
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
    logger.info("=== UMAY APP STARTING - SIMPLE VERSION v5.0 ===")
    
    # Create data directory
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    os.makedirs(data_dir, exist_ok=True)
    logger.info("Data directory created/verified")
    
    print("⚠️  Для запуска используйте: python run_local.py")
    print("📱 Или: python run_public.py для публичной ссылки")
    sys.exit(1)

# Инициализация базы данных при импорте модуля
init_database()

# Обработчик ошибок для отладки
@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal Server Error: {error}")
    return render_template('error.html', error_code=500, error_message="Внутренняя ошибка сервера"), 500

@app.errorhandler(404)
def not_found_error(error):
    logger.error(f"Not Found Error: {error}")
    return render_template('error.html', error_code=404, error_message="Страница не найдена"), 404 

# ======================
# PWA ROUTES - КРУТОЕ МОБИЛЬНОЕ ПРИЛОЖЕНИЕ
# ======================
@app.route('/pwa/')
@app.route('/pwa/dashboard')
def pwa_dashboard():
    """PWA Dashboard - главная страница приложения"""
    logger.info("🚀 PWA Dashboard requested")
    try:
        if current_user.is_authenticated:
            # Получаем данные для дашборда
            user_data = {
                'name': current_user.full_name,
                'email': current_user.login,
                'app_type': session.get('app_type', 'pro')
            }
            return render_template('pwa/dashboard.html', user=user_data)
        else:
            return redirect(url_for('pwa_login'))
    except Exception as e:
        logger.error(f"❌ Error in PWA dashboard: {e}")
        return f"PWA Error: {e}", 500

@app.route('/pwa/login')
def pwa_login():
    """PWA Login - красивая форма входа"""
    logger.info("🚀 PWA Login requested")
    return render_template('pwa/login.html')

@app.route('/pwa/patients')
def pwa_patients():
    """PWA Patients - список пациентов"""
    logger.info("🚀 PWA Patients requested")
    if not current_user.is_authenticated:
        return redirect(url_for('pwa_login'))
    try:
        # Получаем список пациентов
        patients = []
        if session.get('app_type') == 'pro':
            # Здесь будет логика получения пациентов
            pass
        return render_template('pwa/patients.html', patients=patients)
    except Exception as e:
        logger.error(f"❌ Error in PWA patients: {e}")
        return f"PWA Error: {e}", 500

@app.route('/pwa/analytics')
def pwa_analytics():
    """PWA Analytics - аналитика и графики"""
    logger.info("🚀 PWA Analytics requested")
    if not current_user.is_authenticated:
        return redirect(url_for('pwa_login'))
    try:
        # Данные для аналитики
        analytics_data = {
            'total_patients': 0,
            'new_this_month': 0,
            'complications_rate': 0
        }
        return render_template('pwa/analytics.html', data=analytics_data)
    except Exception as e:
        logger.error(f"❌ Error in PWA analytics: {e}")
        return f"PWA Error: {e}", 500

@app.route('/pwa/settings')
def pwa_settings():
    """PWA Settings - настройки приложения"""
    logger.info("🚀 PWA Settings requested")
    if not current_user.is_authenticated:
        return redirect(url_for('pwa_login'))
    try:
        user_data = {
            'name': current_user.full_name,
            'email': current_user.login,
            'phone': getattr(current_user, 'phone', 'Не указан')
        }
        return render_template('pwa/settings.html', user=user_data)
    except Exception as e:
        logger.error(f"❌ Error in PWA settings: {e}")
        return f"PWA Error: {e}", 500

@app.route('/pwa/profile')
def pwa_profile():
    """PWA Profile - профиль пользователя"""
    logger.info("🚀 PWA Profile requested")
    if not current_user.is_authenticated:
        return redirect(url_for('pwa_login'))
    try:
        user_data = {
            'name': current_user.full_name,
            'email': current_user.login,
            'position': getattr(current_user, 'position', 'Пользователь'),
            'city': getattr(current_user, 'city', 'Не указан')
        }
        return render_template('pwa/profile.html', user=user_data)
    except Exception as e:
        logger.error(f"❌ Error in PWA profile: {e}")
        return f"PWA Error: {e}", 500