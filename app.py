from flask import Flask, render_template, request, jsonify, send_file, after_this_request
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import os
import time
import openai
import tempfile

from resume_utils import (
    load_resume,
    guess_job_title,
    ask_interview_question,
    get_feedback,
    score_answer
)

# Load .env variables
load_dotenv()

# Setup OpenAI client
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt'}

# In-memory session state
user_data = {
    "resume_text": "",
    "job_title": "",
    "previous_questions": [],
    "current_question": "",
    "main_answer": "",
    "stage": "initial"  # stages: initial → followup → done
}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def delete_old_files(folder, max_age_seconds=600):
    now = time.time()
    for filename in os.listdir(folder):
        path = os.path.join(folder, filename)
        if os.path.isfile(path) and now - os.path.getmtime(path) > max_age_seconds:
            try:
                os.remove(path)
                app.logger.info(f"Deleted old file: {path}")
            except Exception as e:
                app.logger.error(f"Failed to delete {path}: {e}")

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload():
    delete_old_files(app.config['UPLOAD_FOLDER'])

    file = request.files["resume"]
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(path)

        @after_this_request
        def remove_file(response):
            try:
                os.remove(path)
            except Exception as e:
                app.logger.error(f"Failed to delete {path}: {e}")
            return response

        resume_text = load_resume(path)
        job_title = guess_job_title(resume_text)
        question = ask_interview_question(resume_text, job_title, [])

        user_data.update({
            "resume_text": resume_text,
            "job_title": job_title,
            "previous_questions": [question],
            "current_question": question,
            "main_answer": "",
            "stage": "initial"
        })

        formatted_question = f"<br><br><strong>Interview Question:</strong><br>{question}"
        return jsonify({"job_title": job_title, "question": formatted_question})

    return jsonify({"error": "Invalid file"}), 400

@app.route("/chat", methods=["POST"])
def chat():
    message = request.json["message"]
    resume_text = user_data["resume_text"]
    job_title = user_data["job_title"]
    stage = user_data["stage"]

    if stage == "initial":
        user_data["main_answer"] = message

        followup_prompt = f"""
You are a mock interviewer.

The candidate answered this question:
"{user_data['current_question']}"

With:
"{message}"

Now ask one clear and realistic follow-up question based on their answer and resume.

❌ Do NOT repeat the original question.
❌ Do NOT list multiple options.
✅ Return only the follow-up question itself, with no extra explanation.

--- Resume ---
{resume_text}
"""
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": followup_prompt}],
            temperature=0.7
        )

        followup_q = response.choices[0].message.content.strip()
        user_data["stage"] = "followup"
        user_data["current_question"] = followup_q
        user_data["previous_questions"].append(followup_q)

        return jsonify({"feedback": f"<strong>Follow-up Question:</strong><br>{followup_q}"})

    elif stage == "followup":
        full_answer = f"{user_data['main_answer']}\n\nFollow-up Answer:\n{message}"
        combined_questions = "\n\n".join(user_data["previous_questions"])

        feedback = get_feedback(combined_questions, full_answer, resume_text, job_title)
        score = score_answer(combined_questions, full_answer, resume_text, job_title)

        user_data["stage"] = "done"

        return jsonify({
            "feedback": f"{feedback}<br><br><strong>Total Score:</strong> {score}/10"
        })

    else:
        return jsonify({
            "feedback": "✅ Interview complete. Refresh the page to try another resume."
        })

# 🔊 TEXT TO SPEECH ENDPOINT
@app.route("/speak", methods=["POST"])
def speak():
    text = request.json.get("text")
    if not text:
        return jsonify({"error": "No text provided"}), 400

    try:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_audio:
            response = client.audio.speech.create(
                model="tts-1",
                voice="nova",  # or "alloy", "echo", "fable", "onyx", "shimmer"
                input=text
            )
            response.stream_to_file(temp_audio.name)

        return send_file(temp_audio.name, mimetype="audio/mpeg", as_attachment=False)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Make the app listen on all interfaces (necessary for Render)
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
