# models/user.py

# Import SQLAlchemy to define and work with the database
from flask_sqlalchemy import SQLAlchemy

# Import UserMixin so we can use built-in login features from Flask-Login
from flask_login import UserMixin

# Import datetime to store dates and times
from datetime import datetime

# Create a database object (used to define tables and interact with the database)
db = SQLAlchemy()

# -------------------- User Model --------------------

# Define a table in the database called 'User'
# This class represents a person using the app
# UserMixin gives this model helpful features like is_authenticated and get_id()
class User(UserMixin, db.Model):
    # Unique ID for each user (automatically generated)
    id = db.Column(db.Integer, primary_key=True)

    # Username for login — must be unique and cannot be empty
    username = db.Column(db.String(150), unique=True, nullable=False)

    # Hashed password — stored securely, cannot be empty
    password = db.Column(db.String(150), nullable=False)

    # Number of consecutive days the user has completed an interview
    # Starts at 0 by default and must always have a value
    streak_count = db.Column(db.Integer, default=0, nullable=False)

    # Date and time of the user's last interview
    # This can be empty (nullable=True) if they haven't done one yet
    last_interview_time = db.Column(db.DateTime, nullable=True)

    # Longest streak the user has ever achieved
    # Starts at 0 and must always have a value
    longest_streak = db.Column(db.Integer, default=0, nullable=False)


# -------------------- InterviewHistory Model --------------------

# This class defines a table to keep track of each interview a user takes
class InterviewHistory(db.Model):
    # Unique ID for each interview record
    id = db.Column(db.Integer, primary_key=True)

    # Link to the user who did the interview (foreign key from the 'User' table)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # The guessed job title from the resume
    job_title = db.Column(db.String(255), nullable=False)

    # The score the AI gave for the user's answer
    score = db.Column(db.Integer, nullable=False)

    # When the interview was created (set automatically to current time)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Create a relationship to the User so we can easily do:
    # current_user.interviews to get all interviews for a user
    user = db.relationship('User', backref=db.backref('interviews', lazy='dynamic'))
