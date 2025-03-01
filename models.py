from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    projects = db.relationship('Project', backref='user', lazy=True)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Новые поля для настроек
    bot_prompt = db.Column(db.Text, default='')  # Инструкция для бота
    bot_message = db.Column(db.Text, default='')  # Стартовое сообщение бота
    temperature = db.Column(db.Float, default=0.5)  # Температура
    max_tokens = db.Column(db.Integer, default=1024)  # Максимальное количество токенов
    disable_agent = db.Column(db.Boolean, default=False)  # Остановить бота
    agent_timeout = db.Column(db.Integer, default=1)  # Время остановки (в часах)
    model = db.Column(db.String(50), default='Gemini')  # Выбор модели
    message_buffer = db.Column(db.Integer, default=5)  # Буфер сообщений
    spam_protection = db.Column(db.Boolean, default=False)  # Защита от спама
    delayed_sending = db.Column(db.Boolean, default=False)  # Отложенная отправка
    api_key = db.Column(db.String(200), default='')  # Свой API-ключ

    def __repr__(self):
        return f'<Project {self.name}>'
