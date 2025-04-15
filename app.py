# Import necessary libraries from Flask and other tools
from flask import Flask, render_template, request, jsonify, send_file, after_this_request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy  # For database management
from flask_login import LoginManager, login_user, logout_user, login_required, current_user  # For user login handling
from werkzeug.utils import secure_filename  # For safely handling uploaded file names
from werkzeug.security import generate_password_hash, check_password_hash  # For password encryption
from dotenv import load_dotenv  # For loading environment variables from .env file
import os  # Built-in module for file paths and operations
import time  # For handling timestamps

# Load environment variables from a .env file (for sensitive data like API keys)
load_dotenv()

# Initialize the Flask web app
app = Flask(__name__)

# Secret key is used to protect sensitive data like user sessions
# NOTE: This should be changed to something secure in production
app.secret_key = os.getenv("SECRET_KEY")

# Define absolute paths for file storage and the database
basedir = os.path.abspath(os.path.dirname(__file__))

# Ensure the instance folder exists (for the SQLite DB)
os.makedirs(os.path.join(basedir, 'instance'), exist_ok=True)


# Folder where uploaded resumes will be stored temporarily
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'uploads')

# Define the location of the SQLite database file
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(basedir, 'instance', 'users.db')}"

# Import database models (User model)
from models.user import db, User

# Initialize the database with the app
db.init_app(app)

# Setup Flask-Login for user authentication management
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "index"  # Where to redirect if a user isn't logged in

# Import AI service modules used by the app
from services.resume_parser import load_resume
from services.ai_interview import (
    guess_job_title,
    ask_interview_question,
    get_feedback,
    score_answer
)
from services.tts_service import generate_tts_audio  # Text-to-speech service


# This tells Flask-Login how to load a user from the database
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Allowed file types for resume uploads
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt'}

# Temporary storage for interview session data (resets per session)
user_data = {
    "resume_text": "",
    "job_title": "",
    "previous_questions": [],
    "current_question": "",
    "main_answer": "",
    "stage": "initial"  # Tracks if user is answering first question, follow-up, or done
}


# Checks if uploaded file is allowed (based on file extension)
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Deletes old uploaded files to save space (files older than 10 minutes by default)
def delete_old_files(folder, max_age_seconds=600):
    now = time.time()
    for filename in os.listdir(folder):
        path = os.path.join(folder, filename)
        if os.path.isfile(path) and now - os.path.getmtime(path) > max_age_seconds:
            try:
                os.remove(path)
            except Exception as e:
                app.logger.error(f"Failed to delete {path}: {e}")


# ------------------- ROUTES (App Pages) ------------------------

# Home page
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


# Login page
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()

        # Check if user exists and password is correct
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for("career_home"))
        else:
            flash("Login failed. Please check your username and password.")
            return redirect(url_for("login"))

    return render_template("login.html")


# Registration page (create new user)
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        # Check if user already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("Username already exists.")
            return redirect(url_for("register"))

        # Hash the password for security
        hashed_pw = generate_password_hash(password)
        new_user = User(username=username, password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()

        # Automatically log in the new user
        login_user(new_user)
        return redirect(url_for("career_home"))

    return render_template("register.html")


# Log out the current user
@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('index'))


# Main career planner home page (after login)
@app.route("/career_home")
@login_required
def career_home():
    return render_template("career_home.html")


# Interview page (AI Interview happens here)
@app.route("/interview")
@login_required
def interview():
    return render_template("interview.html")


# Upload resume route (called when user uploads a resume)
@app.route("/upload", methods=["POST"])
@login_required
def upload():
    # Clean up old files
    delete_old_files(app.config['UPLOAD_FOLDER'])

    resume_text = ""
    if "resume" in request.files:
        file = request.files["resume"]
        if not allowed_file(file.filename):
            return jsonify({"error": "Invalid file type"}), 400
        filename = secure_filename(file.filename)
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(path)

        # Delete the uploaded file after it's used
        @after_this_request
        def remove_file(response):
            try:
                os.remove(path)
            except Exception as e:
                app.logger.error(f"Failed to delete {path}: {e}")
            return response

        # Extract resume text using AI services
        resume_text = load_resume(path)
    elif "resume_text" in request.form:
        resume_text = request.form["resume_text"]

    if not resume_text:
        return jsonify({"error": "No resume text found"}), 400
    job_title = guess_job_title(resume_text)
    question = ask_interview_question(resume_text, job_title, [])

    # Save interview data for this session
    user_data.update({
        "resume_text": resume_text,
        "job_title": job_title,
        "previous_questions": [question],
        "current_question": question,
        "main_answer": "",
        "stage": "initial"
    })

    # Return question to frontend
    formatted_question = f"<br><br><strong>Interview Question:</strong><br>{question}"
    return jsonify({"job_title": job_title, "question": formatted_question, "resume_text": resume_text})


# Chat route - Handles messages from user during interview
@app.route("/chat", methods=["POST"])
@login_required
def chat():
    message = request.json["message"]
    resume_text = user_data["resume_text"]
    job_title = user_data["job_title"]
    stage = user_data["stage"]

    # First answer stage
    if stage == "initial":
        user_data["main_answer"] = message

        followup_q = ask_interview_question(resume_text, job_title, user_data["previous_questions"])

        user_data["stage"] = "followup"
        user_data["current_question"] = followup_q
        user_data["previous_questions"].append(followup_q)

        return jsonify({"feedback": f"<strong>Follow-up Question:</strong><br>{followup_q}"})

    # Follow-up answer stage
    elif stage == "followup":
        full_answer = f"{user_data['main_answer']}\n\nFollow-up Answer:\n{message}"
        combined_questions = "\n\n".join(user_data["previous_questions"])

        feedback = get_feedback(combined_questions, full_answer, resume_text, job_title)
        score, breakdown = score_answer(combined_questions, full_answer, resume_text, job_title)

        user_data["stage"] = "done"

        return jsonify({
            "feedback": f"{feedback}<br><br><strong>Total Score:</strong> {score}/10<br><br><strong>Score Breakdown:</strong><br>{breakdown.replace(chr(10), '<br><br>')}"
        })

    # Interview is done
    else:
        return jsonify({
            "feedback": "Interview complete. Refresh the page to try another resume."
        })


# Text-to-speech route - Converts text to audio
@app.route("/speak", methods=["POST"])
@login_required
def speak():
    text = request.json.get("text")
    if not text:
        return jsonify({"error": "No text provided"}), 400

    return generate_tts_audio(text)


# Run the app (only when directly running this file)
if __name__ == "__main__":
    # Create database tables if they don't exist
    with app.app_context():
        db.create_all()

    # Start Flask web server
    app.run(debug=True, host="0.0.0.0", port=5000)