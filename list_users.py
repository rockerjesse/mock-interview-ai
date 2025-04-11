# Import the Flask app instance and database object from your main app
from app import app, db

# Import the User model (this represents your users in the database)
from models.user import User

# This line ensures the following code runs within the Flask app context.
# Why? Because certain operations like querying the database require access
# to the app's settings (like the database location).
with app.app_context():
    # Query all users from the database.
    # This returns a list of all User records stored in the database.
    users = User.query.all()

    print("Registered Users:")

    # Loop through each user found and print their username to the console.
    for user in users:
        print(user.username)

# Instructions for the developer:
# To run this file and see all registered users, open your terminal/console
# and type:
#
# python list_users.py
#
# This is helpful for debugging or quickly checking which users exist in your database.
