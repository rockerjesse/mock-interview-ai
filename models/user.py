# Import SQLAlchemy for working with databases
from flask_sqlalchemy import SQLAlchemy

# Import UserMixin from Flask-Login
# UserMixin provides helpful default implementations for user authentication
from flask_login import UserMixin


# Initialize the database object
# This will be used in your main app to connect to your database
db = SQLAlchemy()


# ---------------------- User Model ------------------------

# This class defines the structure of a "User" in your database
# It inherits from:
# - db.Model → Tells SQLAlchemy this is a database model/table
# - UserMixin → Provides useful login-related methods for Flask-Login

class User(UserMixin, db.Model):
    # Unique ID for each user in the database
    # This will auto-increment as new users are added
    id = db.Column(db.Integer, primary_key=True)

    # Username field:
    # - String type (max length 150 characters)
    # - Must be unique (no two users can have the same username)
    # - Cannot be left empty (nullable=False)
    username = db.Column(db.String(150), unique=True, nullable=False)

    # Password field:
    # - String type (max length 150 characters)
    # - Cannot be left empty (nullable=False)
    # NOTE: The password stored here is hashed (encrypted) for security.
    password = db.Column(db.String(150), nullable=False)
