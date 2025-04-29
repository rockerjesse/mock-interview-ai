# ------------------- IMPORTS -------------------

# Import modules from Python's standard library
import os               # To interact with the operating system (like folders, files)
import time             # For time-related functions
from datetime import datetime, timedelta  # To work with dates and times

# Import parts of Flask (a web framework) to help build the website
from flask import (
    Flask, render_template, request, jsonify,
    redirect, url_for, flash, after_this_request
)
# Import database tools from Flask
from flask_sqlalchemy import SQLAlchemy
# Import user authentication tools from Flask
from flask_login import (
    LoginManager, login_user, logout_user,
    login_required, current_user
)
# Import tools for safe file uploads
from werkzeug.utils import secure_filename
# Import tools for password security
from werkzeug.security import generate_password_hash, check_password_hash
# Import tool to load secret environment variables
from dotenv import load_dotenv

# ------------------- SETUP -------------------

# Load secret environment variables from a .env file (like SECRET_KEY)
load_dotenv()

# Create a Flask application
app = Flask(__name__)
# Set a secret key to keep sessions safe (pulled from the .env file)
app.secret_key = os.getenv("SECRET_KEY")

# ------------------- FOLDER SETUP -------------------

# Find the folder where this script lives
basedir = os.path.abspath(os.path.dirname(__file__))

# Make sure an 'instance' folder exists (used for database files)
os.makedirs(os.path.join(basedir, "instance"), exist_ok=True)

# ------------------- CONFIGURATION -------------------

# Set where uploaded files (like resumes) will be saved
app.config["UPLOAD_FOLDER"] = os.path.join(basedir, "uploads")
# Make sure the uploads folder exists
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Tell the app where the database will be stored (inside the instance folder)
app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"sqlite:///{os.path.join(basedir, 'instance', 'users.db')}"
)

# ------------------- DATABASE SETUP -------------------

# Import the database models (User, InterviewHistory)
from models.user import db, User, InterviewHistory
# Connect the database to the Flask app
db.init_app(app)

# ------------------- LOGIN MANAGER SETUP -------------------

# Set up the login manager (to handle logins and logouts)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "index"  # If not logged in, send user to "index" page

# What to do if someone tries to access protected content without being logged in
@login_manager.unauthorized_handler
def ajax_unauthorized():
    return jsonify({"error": "Authentication required"}), 401

# Tell Flask how to find a user in the database by ID
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ------------------- AI & SERVICES SETUP -------------------

# Import services for handling resumes and AI interviews
from services.resume_parser import load_resume
from services.ai_interview import (
    guess_job_title,
    start_interview,
    process_interview_message
)
# Import the text-to-speech service
from services.tts_service import generate_tts_audio

# ------------------- STREAK SETTINGS -------------------

# Define how long a "daily streak" lasts (1 day)
STREAK_INCREMENT_THRESHOLD = timedelta(days=1)
# Define when a streak is considered broken (also 1 day gap)
STREAK_BREAK_THRESHOLD     = timedelta(days=1)

# ------------------- HELPER FUNCTIONS -------------------

# List of allowed file types to upload
ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}

# Check if uploaded file is an allowed type
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# Delete old uploaded files (older than 10 minutes) to save space
def delete_old_files(folder, max_age_seconds=600):
    if not os.path.isdir(folder):
        return
    now = time.time()
    for fname in os.listdir(folder):
        path = os.path.join(folder, fname)
        if os.path.isfile(path) and now - os.path.getmtime(path) > max_age_seconds:
            try:
                os.remove(path)
            except:
                pass

# ------------------- ROUTES -------------------

# Home page
@app.route("/", methods=["GET"])
def index():
    # If the user is already logged in, send them to career home
    if current_user.is_authenticated:
        return redirect(url_for("career_home"))
    # Otherwise, show the index page (login/register)
    return render_template("index.html")

# Login page
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form["username"]  # Get username from form
        p = request.form["password"]  # Get password from form
        user = User.query.filter_by(username=u).first()  # Find user in database
        if user and check_password_hash(user.password, p):
            login_user(user)  # Log the user in
            return redirect(url_for("career_home"))
        flash("Login failed. Please check your credentials.")  # Show error
        return redirect(url_for("login"))
    return render_template("login.html")

# Register page
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]
        # Check if the username already exists
        if User.query.filter_by(username=u).first():
            flash("Username already exists.")
            return redirect(url_for("register"))
        # Create a new user with hashed password
        new_user = User(username=u, password=generate_password_hash(p))
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)  # Log the new user in
        return redirect(url_for("career_home"))
    return render_template("register.html")

# Logout route
@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.")
    return redirect(url_for("index"))

# Main user dashboard (Career Home)
@app.route("/career_home")
@login_required
def career_home():
    # Get all past interviews sorted by newest first
    history_desc = current_user.interviews.order_by(
        InterviewHistory.created_at.desc()
    ).all()
    # Make a list sorted oldest first
    history_asc = list(reversed(history_desc))
    # Prepare labels and scores for graph display
    labels = [h.created_at.strftime("%Y-%m-%d %H:%M") for h in history_asc]
    scores = [h.score for h in history_asc]

    # Gather user stats
    total_interviews = len(history_desc)
    current_streak   = current_user.streak_count or 0
    longest_streak   = current_user.longest_streak or 0
    highest_score    = max((h.score for h in history_desc), default=0)

    # Check for special "runs" (long streaks of good scores)
    runs = {}
    for min_score, run_len in [(5,5), (6,10), (7,20), (8,50)]:
        max_run = cur = 0
        for h in history_asc:
            if h.score >= min_score:
                cur += 1
                max_run = max(max_run, cur)
            else:
                cur = 0
        runs[(min_score, run_len)] = (max_run >= run_len)

    # Define possible badges user can earn
    badge_defs = [
        (total_interviews >= 1,   "First Interview",   "🥇"),
        (total_interviews >= 5,   "5 Interviews",      "🥈"),
        (total_interviews >= 20,  "20 Interviews",     "🥉"),
        (total_interviews >= 100, "100 Interviews",    "🏆"),
        (current_streak >= 1,    "1‑Day Streak",   "🔥"),
        (current_streak >= 5,    "5‑Day Streak",   "🔥🔥"),
        (current_streak >= 20,   "20‑Day Streak",  "🔥🔥🔥"),
        (current_streak >= 100,  "100‑Day Streak", "🔥🔥🔥🔥"),
        (highest_score >= 5,  "First 5+ Score",  "⭐"),
        (highest_score >= 7,  "First 7+ Score",  "🌟"),
        (highest_score >= 9,  "First 9+ Score",  "✨"),
        (highest_score >= 10, "Perfect Score",    "💯"),
        (runs[(5,5)],   "Run of 5×≥5",   "🏁"),
        (runs[(6,10)],  "Run of 10×≥6",  "🏅"),
        (runs[(7,20)],  "Run of 20×≥7",  "🎖️"),
        (runs[(8,50)],  "Run of 50×≥8",  "🏆"),
    ]

    # Prepare badge data for the template
    potential_badges = [
        {"name": n, "icon": i, "earned": c}
        for c,n,i in badge_defs
    ]

    # Send everything to the career_home.html template
    return render_template(
        "career_home.html",
        interviews=history_desc,
        labels=labels,
        scores=scores,
        streak=current_streak,
        longest=longest_streak,
        potential_badges=potential_badges
    )

# Interview page
@app.route("/interview")
@login_required
def interview():
    return render_template("interview.html")

# Upload a resume
@app.route("/upload", methods=["POST"])
@login_required
def upload():
    # Clean up old files
    delete_old_files(app.config["UPLOAD_FOLDER"])
    resume_text = ""
    # Check if a resume file was uploaded
    if "resume" in request.files:
        file = request.files["resume"]
        # Check file type
        if not allowed_file(file.filename):
            return jsonify(error="Invalid file type"), 400
        # Save the file securely
        fn   = secure_filename(file.filename)
        path = os.path.join(app.config["UPLOAD_FOLDER"], fn)
        file.save(path)
        # Delete file after request is done
        @after_this_request
        def rm(r):
            try: os.remove(path)
            except: pass
            return r
        # Try to load resume text
        try:
            resume_text = load_resume(path)
        except Exception as e:
            return jsonify(error=f"Failed to parse resume: {e}"), 500
    # Or if user directly pasted resume text
    elif "resume_text" in request.form:
        resume_text = request.form["resume_text"]

    # If no resume found
    if not resume_text:
        return jsonify(error="No resume text found"), 400

    # Start an interview
    job_title      = guess_job_title(resume_text)
    first_question = start_interview(resume_text, job_title)
    formatted      = f"<br><br><strong>Interview Question:</strong><br>{first_question}"

    return jsonify({
        "job_title":   job_title,
        "question":    formatted,
        "resume_text": resume_text
    })

# Chat route (answer interview questions)
@app.route("/chat", methods=["POST"])
@login_required
def chat():
    msg    = request.json.get("message", "")
    result = process_interview_message(msg)

    # If a score is returned, save the interview result
    if result.get("score") is not None:
        hist = InterviewHistory(
            user_id   = current_user.id,
            job_title = result["job_title"],
            score     = result["score"]
        )
        db.session.add(hist)

        # Update user's streak info
        now  = datetime.utcnow()
        last = current_user.last_interview_time
        if last is None:
            current_user.streak_count = 1
        else:
            delta = now - last
            if delta > STREAK_BREAK_THRESHOLD:
                current_user.streak_count = 1
            elif delta >= STREAK_INCREMENT_THRESHOLD:
                current_user.streak_count += 1
        if current_user.streak_count > current_user.longest_streak:
            current_user.longest_streak = current_user.streak_count
        current_user.last_interview_time = now
        db.session.commit()

    return jsonify(result)

# Text-to-speech route
@app.route("/speak", methods=["POST"])
@login_required
def speak():
    text = request.json.get("text")
    if not text:
        return jsonify(error="No text provided"), 400
    return generate_tts_audio(text)

# ------------------- RUN THE APP -------------------

if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Create database tables if they don't exist
    app.run(debug=True, host="0.0.0.0", port=5000)  # Start the app!
