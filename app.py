from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime
import requests
import secrets

# Инициализация приложения
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key')

# Instagram OAuth конфигурация
INSTAGRAM_CLIENT_ID = os.getenv('INSTAGRAM_CLIENT_ID', '')  # Получите в Meta Developer Console
INSTAGRAM_CLIENT_SECRET = os.getenv('INSTAGRAM_CLIENT_SECRET', '')  # Получите в Meta Developer Console
INSTAGRAM_REDIRECT_URI = os.getenv('INSTAGRAM_REDIRECT_URI', 'http://localhost:5100/instagram/callback')
INSTAGRAM_AUTH_URL = 'https://api.instagram.com/oauth/authorize'
INSTAGRAM_TOKEN_URL = 'https://api.instagram.com/oauth/access_token'

db = SQLAlchemy(app)

# Модели
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    projects = db.relationship('Project', backref='owner', lazy=True)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    bot_prompt = db.Column(db.Text, default='')
    bot_message = db.Column(db.Text, default='')
    temperature = db.Column(db.Float, default=0.5)
    max_tokens = db.Column(db.Integer, default=1024)
    disable_agent = db.Column(db.Boolean, default=False)
    agent_timeout = db.Column(db.Integer, default=1)
    model = db.Column(db.String(50), default='Gemini')
    message_buffer = db.Column(db.Integer, default=5)
    spam_protection = db.Column(db.Boolean, default=False)
    delayed_sending = db.Column(db.Boolean, default=False)
    api_key = db.Column(db.String(200), default='')
    instagram_token = db.Column(db.String(500), default='')  # Добавляем поле для токена Instagram

# Создание базы данных
with app.app_context():
    db.create_all()

# Маршрут для инициирования Instagram авторизации
@app.route('/project/<int:project_id>/instagram/auth')
def instagram_auth(project_id):
    if 'user_id' not in session:
        flash('Сначала войдите в систему.', 'error')
        return redirect(url_for('login'))
    
    project = Project.query.get_or_404(project_id)
    if project.user_id != session['user_id']:
        flash('У вас нет доступа к этому проекту.', 'error')
        return redirect(url_for('dashboard'))
    
    # Генерируем state для защиты от CSRF
    state = secrets.token_hex(16)
    session['instagram_state'] = state
    session['project_id'] = project_id
    
    # Формируем URL для авторизации в Instagram
    auth_url = f"{INSTAGRAM_AUTH_URL}?client_id={INSTAGRAM_CLIENT_ID}&redirect_uri={INSTAGRAM_REDIRECT_URI}&scope=user_profile,user_media&response_type=code&state={state}"
    
    return redirect(auth_url)

# Обработчик callback от Instagram
@app.route('/instagram/callback')
def instagram_callback():
    if 'user_id' not in session:
        flash('Сначала войдите в систему.', 'error')
        return redirect(url_for('login'))
    
    code = request.args.get('code')
    state = request.args.get('state')
    error = request.args.get('error')
    
    # Проверяем state для защиты от CSRF
    if state != session.get('instagram_state'):
        flash('Ошибка проверки безопасности.', 'error')
        return redirect(url_for('dashboard'))
    
    if error:
        flash(f'Ошибка авторизации Instagram: {error}', 'error')
        return redirect(url_for('project_settings', project_id=session.get('project_id')))
    
    # Получаем токен доступа
    token_payload = {
        'client_id': INSTAGRAM_CLIENT_ID,
        'client_secret': INSTAGRAM_CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'redirect_uri': INSTAGRAM_REDIRECT_URI,
        'code': code
    }
    
    try:
        response = requests.post(INSTAGRAM_TOKEN_URL, data=token_payload)
        token_data = response.json()
        
        if 'access_token' in token_data:
            # Сохраняем токен в базе данных
            project_id = session.get('project_id')
            project = Project.query.get_or_404(project_id)
            project.instagram_token = token_data['access_token']
            db.session.commit()
            
            flash('Instagram авторизация успешна!', 'success')
        else:
            flash(f'Не удалось получить токен Instagram: {token_data.get("error_message", "Неизвестная ошибка")}', 'error')
    
    except Exception as e:
        flash(f'Ошибка при обработке ответа Instagram: {str(e)}', 'error')
    
    return redirect(url_for('project_settings', project_id=session.get('project_id')))

# Маршрут для страницы настроек (GET)
@app.route('/project/<int:project_id>/settings', methods=['GET'])
def project_settings(project_id):
    if 'user_id' not in session:
        flash('Сначала войдите в систему.', 'error')
        return redirect(url_for('login'))
    
    project = Project.query.get_or_404(project_id)
    if project.user_id != session['user_id']:
        flash('У вас нет доступа к этому проекту.', 'error')
        return redirect(url_for('dashboard'))
    
    return render_template('project_settings.html', project=project)

# Маршрут для динамического сохранения настроек (POST)
@app.route('/project/<int:project_id>/save-settings', methods=['POST'])
def save_settings(project_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Сначала войдите в систему.'}), 403
    
    project = Project.query.get_or_404(project_id)
    if project.user_id != session['user_id']:
        return jsonify({'error': 'У вас нет доступа к этому проекту.'}), 403

    data = request.get_json()
    project.bot_prompt = data.get('bot_prompt', project.bot_prompt)
    project.bot_message = data.get('bot_message', project.bot_message)
    project.temperature = float(data.get('temperature', project.temperature))
    project.max_tokens = int(data.get('max_tokens', project.max_tokens))
    project.disable_agent = data.get('disable_agent', project.disable_agent)
    project.agent_timeout = int(data.get('agent_timeout', project.agent_timeout))
    project.model = data.get('model', project.model)
    project.message_buffer = int(data.get('message_buffer', project.message_buffer))
    project.spam_protection = data.get('spam_protection', project.spam_protection)
    project.delayed_sending = data.get('delayed_sending', project.delayed_sending)
    project.api_key = data.get('api_key', project.api_key)

    db.session.commit()
    return jsonify({'message': 'Настройки успешно сохранены!'}), 200

# Остальные маршруты остаются без изменений
@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            flash('Успешный вход!', 'success')
            return redirect(url_for('dashboard'))
        flash('Неверный email или пароль.', 'error')
    return render_template('index.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Вы вышли из системы.', 'success')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        if User.query.filter_by(email=email).first():
            flash('Этот email уже зарегистрирован.', 'error')
            return redirect(url_for('register'))
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('Регистрация успешна! Теперь войдите.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Сначала войдите в систему.', 'error')
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    projects = Project.query.filter_by(user_id=user.id).all() if user else []
    return render_template('dashboard.html', user=user, projects=projects)

@app.route('/add_project', methods=['POST'])
def add_project():
    if 'user_id' not in session:
        return jsonify({'error': 'Сначала войдите в систему.'}), 403
    project_name = request.form.get('project_name')
    if not project_name:
        return jsonify({'error': 'Название проекта обязательно.'}), 400
    user = User.query.get(session['user_id'])
    new_project = Project(name=project_name, user_id=user.id)
    db.session.add(new_project)
    db.session.commit()
    return jsonify({'message': 'Проект успешно создан!'}), 200

if __name__ == '__main__':
    app.run(debug=True, port=5100)