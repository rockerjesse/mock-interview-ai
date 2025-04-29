# Import the library that lets us define and use a database in Flask
from flask_sqlalchemy import SQLAlchemy

# Import the datetime library so we can track when resumes are uploaded
from datetime import datetime

# Import the User model so we can link resumes to the person who uploaded them
from models.user import User


# Create a database object using SQLAlchemy
# This will help us define tables and interact with the database
db = SQLAlchemy()


# ---------------------- Resume Model ------------------------

# Define a Python class called Resume that represents a database table
# This table stores uploaded resumes and their information
class Resume(db.Model):
    # Create a column called 'id'
    # It's an integer and the primary key (a unique identifier for each row)
    id = db.Column(db.Integer, primary_key=True)

    # Create a column to store which user this resume belongs to
    # It uses a foreign key that links to the 'id' column in the User table
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Create a column to store the original name of the resume file
    # String up to 255 characters, cannot be empty (nullable=False)
    filename = db.Column(db.String(255), nullable=False)

    # Create a column to store the full path on the server where the file is saved
    # Also a string up to 255 characters, and required
    storage_path = db.Column(db.String(255), nullable=False)

    # Create a column that automatically saves the time the resume was uploaded
    # It uses the current time in UTC (universal time) by default
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)

    # Define a relationship between this Resume and the User it belongs to
    # This lets us do things like `resume.user` to get the user who uploaded it
    # Or `user.resumes` to get all resumes a user has uploaded
    user = db.relationship('User', backref=db.backref('resumes', lazy=True))