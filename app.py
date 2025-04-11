# Import required libraries for web development and OpenAI interaction
from flask import Flask, render_template, request, jsonify, send_file, after_this_request
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import os
import time
import openai
import tempfile

# Import helper functions defined in resume_utils.py
from resume_utils import (
    load_resume,
    guess_job_title,
    ask_interview_question,
    get_feedback,
    score_answer
)

# Load environment variables from the .env file (e.g., API key)
load_dotenv()

# Connect to OpenAI API using your API key from environment variables
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Create the Flask web application
app = Flask(__name__)

# Define the folder where resumes will be temporarily uploaded
app.config['UPLOAD_FOLDER'] = 'uploads'

# List of file extensions we will accept for resumes
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt'}

# Dictionary to hold all user session data (in-memory for now, not saved to a database)
user_data = {
    "resume_text": "",  # Full text of the uploaded resume
    "job_title": "",  # Job title guessed by AI
    "previous_questions": [],  # All questions asked so far
    "current_question": "",  # Most recent question being answered
    "main_answer": "",  # First user answer
    "stage": "initial"  # Current stage: "initial", "followup", or "done"
}


# Check if the file has one of the allowed extensions
def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Clean up old resume files from the upload folder
def delete_old_files(folder: str, max_age_seconds=600):
    now = time.time()
    for filename in os.listdir(folder):
        path = os.path.join(folder, filename)
        if os.path.isfile(path) and now - os.path.getmtime(path) > max_age_seconds:
            try:
                os.remove(path)
                app.logger.info(f"Deleted old file: {path}")
            except Exception as e:
                app.logger.error(f"Failed to delete {path}: {e}")


# Home page: portal where user picks a tool
@app.route("/", methods=["GET"])
def portal():
    return render_template("career_home.html")


# Interview tool page
@app.route("/interview", methods=["GET"])
def interview():
    return render_template("interview.html")


# Upload endpoint: receives resume file, processes it, and generates first interview question
@app.route("/upload", methods=["POST"])
def upload():
    # Clean up old files first
    delete_old_files(app.config['UPLOAD_FOLDER'])

    file = request.files["resume"]

    # Only process the file if it's a supported type
    if file and allowed_file(file.filename):
        # Sanitize filename
        filename = secure_filename(file.filename)
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(path)

        # Schedule the file to be deleted after request finishes
        @after_this_request
        def remove_file(response):
            try:
                os.remove(path)
            except Exception as e:
                app.logger.error(f"Failed to delete {path}: {e}")
            return response

        # Extract resume text and ask first question
        resume_text = load_resume(path)
        job_title = guess_job_title(resume_text)
        question = ask_interview_question(resume_text, job_title, [])

        # Store all necessary info for the interview session
        user_data.update({
            "resume_text": resume_text,
            "job_title": job_title,
            "previous_questions": [question],
            "current_question": question,
            "main_answer": "",
            "stage": "initial"
        })

        # Send first question and job title back to front-end
        formatted_question = f"<br><br><strong>Interview Question:</strong><br>{question}"
        return jsonify({"job_title": job_title, "question": formatted_question})

    return jsonify({"error": "Invalid file"}), 400


# Chat endpoint: processes either the first or second (follow-up) answer and returns feedback
@app.route("/chat", methods=["POST"])
def chat():
    message = request.json["message"]
    resume_text = user_data["resume_text"]
    job_title = user_data["job_title"]
    stage = user_data["stage"]

    # Handle the initial answer (first question)
    if stage == "initial":
        user_data["main_answer"] = message

        # Create a prompt asking for a follow-up question based on the first answer and resume
        followup_prompt = f"""
You are a mock interviewer.

The candidate answered this question:
"{user_data['current_question']}"

With:
"{message}"

Now ask one clear and realistic follow-up question based on their answer and resume.

Do NOT repeat the original question.
Do NOT list multiple options.
Return only the follow-up question itself, with no extra explanation.

--- Resume ---
{resume_text}
"""

        # Ask OpenAI to generate the follow-up question
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": followup_prompt}],
            temperature=0.7
        )

        # Save and return the follow-up question
        followup_q = response.choices[0].message.content.strip()
        user_data["stage"] = "followup"
        user_data["current_question"] = followup_q
        user_data["previous_questions"].append(followup_q)

        return jsonify({"feedback": f"<strong>Follow-up Question:</strong><br>{followup_q}"})

    # Handle the follow-up answer (second question)
    elif stage == "followup":
        full_answer = f"{user_data['main_answer']}\n\nFollow-up Answer:\n{message}"
        combined_questions = "\n\n".join(user_data["previous_questions"])

        # Ask OpenAI for feedback and a score
        feedback = get_feedback(combined_questions, full_answer, resume_text, job_title)
        score, breakdown = score_answer(combined_questions, full_answer, resume_text, job_title)

        user_data["stage"] = "done"

        # Send full response back including score breakdown
        return jsonify({
            "feedback": f"{feedback}<br><br><strong>Total Score:</strong> {score}/10<br><br><strong>Score Breakdown:</strong><br>{breakdown.replace(chr(10), '<br><br>')}"
        })

    # If interview is already completed
    else:
        return jsonify({
            "feedback": " Interview complete. Refresh the page to try another resume."
        })


# Endpoint for Text-to-Speech: converts given text to audio and sends back as a file
@app.route("/speak", methods=["POST"])
def speak():
    text = request.json.get("text")
    if not text:
        return jsonify({"error": "No text provided"}), 400

    try:
        # Create temporary mp3 file
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_audio:
            response = client.audio.speech.create(
                model="tts-1",
                voice="nova",
                input=text
            )
            response.stream_to_file(temp_audio.name)

        # Send mp3 back to browser
        return send_file(temp_audio.name, mimetype="audio/mpeg", as_attachment=False)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Run the application when you execute this file directly (localhost:5000)
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
