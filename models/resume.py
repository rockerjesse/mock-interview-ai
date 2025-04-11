# Import SQLAlchemy for database modeling
from flask_sqlalchemy import SQLAlchemy

# Import datetime so we can store upload dates
from datetime import datetime

# Import the User model so we can link resumes to users
from models.user import User


# Initialize the database object
db = SQLAlchemy()


# ---------------------- Resume Model ------------------------

# This class defines the structure of a "Resume" in your database
# Each Resume record belongs to a specific User
class Resume(db.Model):
    # Unique ID for each resume (Primary Key)
    id = db.Column(db.Integer, primary_key=True)

    # Foreign Key linking this resume to a User
    # 'user.id' refers to the 'id' column of the User model
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # The original filename of the uploaded resume
    filename = db.Column(db.String(255), nullable=False)

    # The path on the server where the resume file is stored
    storage_path = db.Column(db.String(255), nullable=False)

    # Automatically store the date & time this resume was uploaded
    # datetime.utcnow gives the current time (universal coordinated time)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)

    # Define the relationship between Resume and User
    # This allows you to easily access resume.user to get the associated User
    # It also allows user.resumes to get a list of all resumes belonging to a user
    user = db.relationship('User', backref=db.backref('resumes', lazy=True))
