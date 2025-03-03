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
    
    # Настройки бота
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
    
    # Интеграция с Instagram
    instagram_token = db.Column(db.String(500), default='')

    def __repr__(self):
        return f'<Project {self.name}>'