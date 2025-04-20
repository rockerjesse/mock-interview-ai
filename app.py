# app.py
import os
import time
from datetime import datetime, timedelta

from flask import (
    Flask, render_template, request, jsonify,
    redirect, url_for, flash, after_this_request
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, login_user, logout_user,
    login_required, current_user
)
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

# Load env vars
load_dotenv()

# Flask setup
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

# Ensure instance folder
basedir = os.path.abspath(os.path.dirname(__file__))
os.makedirs(os.path.join(basedir, "instance"), exist_ok=True)

# Config
app.config["UPLOAD_FOLDER"] = os.path.join(basedir, "uploads")
app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"sqlite:///{os.path.join(basedir, 'instance', 'users.db')}"
)

# DB & models
from models.user import db, User, InterviewHistory
db.init_app(app)

# Login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "index"

@login_manager.unauthorized_handler
def ajax_unauthorized():
    # For AJAX calls, return JSON 401 instead of redirect HTML
    return jsonify({"error": "Authentication required"}), 401

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# AI & resume services
from services.resume_parser import load_resume
from services.ai_interview import (
    guess_job_title,
    start_interview,
    process_interview_message
)
from services.tts_service import generate_tts_audio

# Streak thresholds
STREAK_INCREMENT_THRESHOLD = timedelta(days=1)
STREAK_BREAK_THRESHOLD     = timedelta(days=1)

# Helpers
ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def delete_old_files(folder, max_age_seconds=600):
    now = time.time()
    for fname in os.listdir(folder):
        path = os.path.join(folder, fname)
        if os.path.isfile(path) and now - os.path.getmtime(path) > max_age_seconds:
            try:
                os.remove(path)
            except:
                pass

# ------------------- ROUTES -------------------

@app.route("/", methods=["GET"])
def index():
    if current_user.is_authenticated:
        return redirect(url_for("career_home"))
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]
        user = User.query.filter_by(username=u).first()
        if user and check_password_hash(user.password, p):
            login_user(user)
            return redirect(url_for("career_home"))
        flash("Login failed. Please check your credentials.")
        return redirect(url_for("login"))
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]
        if User.query.filter_by(username=u).first():
            flash("Username already exists.")
            return redirect(url_for("register"))
        new_user = User(username=u, password=generate_password_hash(p))
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for("career_home"))
    return render_template("register.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.")
    return redirect(url_for("index"))

@app.route("/career_home")
@login_required
def career_home():
    history_desc = current_user.interviews.order_by(
        InterviewHistory.created_at.desc()
    ).all()
    history_asc = list(reversed(history_desc))
    labels = [h.created_at.strftime("%Y-%m-%d %H:%M") for h in history_asc]
    scores = [h.score for h in history_asc]

    total_interviews = len(history_desc)
    current_streak   = current_user.streak_count or 0
    longest_streak   = current_user.longest_streak or 0
    highest_score    = max((h.score for h in history_desc), default=0)

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
    potential_badges = [
        {"name": n, "icon": i, "earned": c}
        for c,n,i in badge_defs
    ]

    return render_template(
        "career_home.html",
        interviews=history_desc,
        labels=labels,
        scores=scores,
        streak=current_streak,
        longest=longest_streak,
        potential_badges=potential_badges
    )

@app.route("/interview")
@login_required
def interview():
    return render_template("interview.html")

@app.route("/upload", methods=["POST"])
@login_required
def upload():
    delete_old_files(app.config["UPLOAD_FOLDER"])
    resume_text = ""
    if "resume" in request.files:
        file = request.files["resume"]
        if not allowed_file(file.filename):
            return jsonify(error="Invalid file type"), 400
        fn   = secure_filename(file.filename)
        path = os.path.join(app.config["UPLOAD_FOLDER"], fn)
        file.save(path)
        @after_this_request
        def rm(r):
            try: os.remove(path)
            except: pass
            return r
        try:
            resume_text = load_resume(path)
        except Exception as e:
            return jsonify(error=f"Failed to parse resume: {e}"), 500
    elif "resume_text" in request.form:
        resume_text = request.form["resume_text"]

    if not resume_text:
        return jsonify(error="No resume text found"), 400

    job_title      = guess_job_title(resume_text)
    first_question = start_interview(resume_text, job_title)
    formatted      = f"<br><br><strong>Interview Question:</strong><br>{first_question}"

    return jsonify({
        "job_title":   job_title,
        "question":    formatted,
        "resume_text": resume_text
    })

@app.route("/chat", methods=["POST"])
@login_required
def chat():
    msg    = request.json.get("message", "")
    result = process_interview_message(msg)

    if result.get("score") is not None:
        hist = InterviewHistory(
            user_id   = current_user.id,
            job_title = result["job_title"],
            score     = result["score"]
        )
        db.session.add(hist)
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
#updates
@app.route("/speak", methods=["POST"])
@login_required
def speak():
    text = request.json.get("text")
    if not text:
        return jsonify(error="No text provided"), 400
    return generate_tts_audio(text)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, host="0.0.0.0", port=5000)
