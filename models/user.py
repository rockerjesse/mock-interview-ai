# models/user.py

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id       = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    streak_count        = db.Column(db.Integer, default=0, nullable=False)
    last_interview_time = db.Column(db.DateTime, nullable=True)
    longest_streak = db.Column(db.Integer, default=0, nullable=False)


class InterviewHistory(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    job_title  = db.Column(db.String(255), nullable=False)
    score      = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # backref so you can do current_user.interviews
    user = db.relationship('User', backref=db.backref('interviews', lazy='dynamic'))
