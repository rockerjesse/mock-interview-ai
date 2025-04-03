# Importing necessary libraries
from flask import Flask, render_template, request, jsonify, send_file, after_this_request
# Flask: The web framework for building the server and handling HTTP requests.
from werkzeug.utils import secure_filename  # Used to ensure uploaded file names are safe.
from dotenv import load_dotenv  # Loads environment variables, like sensitive keys, from a .env file.
import os  # Provides operating system-related functionality, such as file path handling.
import time  # Helps with time-based operations (like file age management).
import openai  # OpenAI library to interact with their models (GPT-3, for instance).
import tempfile  # Helps with handling temporary files, useful for generating and saving audio files.

# Importing custom utility functions from the 'resume_utils.py' file.
from resume_utils import (
    load_resume,         # Function to load and extract text from a resume file.
    guess_job_title,     # Function to guess the job title based on the resume text.
    ask_interview_question, # Function to generate an interview question based on the resume and job title.
    get_feedback,        # Function to generate feedback for the user's answers.
    score_answer         # Function to generate a score based on how well the user answered the interview questions.
)

# Load environment variables from the .env file (such as the OpenAI API key)
load_dotenv()

# Initialize OpenAI client with the API key loaded from environment variables.
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Create a Flask app instance, which is the core of our web application.
app = Flask(__name__)

# Set the folder where uploaded files (resumes) will be saved.
app.config['UPLOAD_FOLDER'] = 'uploads'

# Define allowed file types for resume uploads (PDF, DOCX, and TXT).
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt'}

# In-memory session state for storing user data throughout the interview process.
user_data = {
    "resume_text": "",   # Holds the resume's text content.
    "job_title": "",     # Holds the job title (either selected by the user or guessed by the AI).
    "previous_questions": [], # List of previous questions asked during the interview.
    "current_question": "",  # Holds the current question being asked in the interview.
    "main_answer": "",   # Stores the user's answer to the main question.
    "stage": "initial"   # Tracks the interview stage (initial → followup → done).
}

# Helper function to check if the uploaded file has an allowed extension (PDF, DOCX, or TXT).
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Function to clean up old files in the uploads folder (e.g., older than 10 minutes).
def delete_old_files(folder, max_age_seconds=600):
    now = time.time()  # Get the current time in seconds.
    for filename in os.listdir(folder):
        path = os.path.join(folder, filename)
        # If the file is older than the allowed age, delete it.
        if os.path.isfile(path) and now - os.path.getmtime(path) > max_age_seconds:
            try:
                os.remove(path)  # Remove the file if it's too old.
                app.logger.info(f"Deleted old file: {path}")
            except Exception as e:
                app.logger.error(f"Failed to delete {path}: {e}")

# Route for the main page of the website (when accessed via a GET request).
@app.route("/", methods=["GET"])
def index():
    # Renders the index.html page when the user visits the root URL ("/").
    return render_template("index.html")

# Route for handling file uploads from the user (the resume).
@app.route("/upload", methods=["POST"])
def upload():
    # First, delete any old files in the upload folder to keep it clean.
    delete_old_files(app.config['UPLOAD_FOLDER'])

    # Get the uploaded file (resume) from the form data.
    file = request.files["resume"]
    # Check if the file is valid (has an allowed extension).
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)  # Ensure the filename is safe.
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)  # Define the path to save the file.
        file.save(path)  # Save the file to the server.

        # Remove the uploaded file after the request is processed.
        @after_this_request
        def remove_file(response):
            try:
                os.remove(path)  # Try to remove the file after it's processed.
            except Exception as e:
                app.logger.error(f"Failed to delete {path}: {e}")
            return response

        # Process the resume to extract its text content using the load_resume function.
        resume_text = load_resume(path)
        # Use the AI to guess the job title based on the resume text.
        job_title = guess_job_title(resume_text)
        # Generate an initial interview question based on the resume and the guessed job title.
        question = ask_interview_question(resume_text, job_title, [])

        # Update the in-memory session state with the resume text, job title, and generated question.
        user_data.update({
            "resume_text": resume_text,
            "job_title": job_title,
            "previous_questions": [question],
            "current_question": question,
            "main_answer": "",
            "stage": "initial"
        })

        # Format the question to be returned to the frontend (so it can be displayed).
        formatted_question = f"<br><br><strong>Interview Question:</strong><br>{question}"
        return jsonify({"job_title": job_title, "question": formatted_question})

    # If the file is invalid (not a supported type), return an error message.
    return jsonify({"error": "Invalid file"}), 400

# Route to handle the chat interaction (the interview process).
@app.route("/chat", methods=["POST"])
def chat():
    # Get the user's message (response) from the frontend.
    message = request.json["message"]
    # Retrieve user session data (e.g., resume text, job title, current stage).
    resume_text = user_data["resume_text"]
    job_title = user_data["job_title"]
    stage = user_data["stage"]

    # If the interview is in the "initial" stage (the first question).
    if stage == "initial":
        user_data["main_answer"] = message  # Save the user's answer to the first question.

        # Generate a follow-up question based on the user's answer and resume text.
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
        # Send the prompt to the OpenAI API (GPT-3) to generate the follow-up question.
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Use the GPT-3.5 model.
            messages=[{"role": "system", "content": followup_prompt}],  # The AI prompt.
            temperature=0.7  # Controls how creative or random the response is.
        )

        # Extract the generated follow-up question from the API response.
        followup_q = response.choices[0].message.content.strip()

        # Update session data with the new follow-up question.
        user_data["stage"] = "followup"
        user_data["current_question"] = followup_q
        user_data["previous_questions"].append(followup_q)

        # Return the follow-up question to the frontend.
        return jsonify({"feedback": f"<strong>Follow-up Question:</strong><br>{followup_q}"})

    # If the interview is in the "followup" stage (user has answered the first and follow-up questions).
    elif stage == "followup":
        full_answer = f"{user_data['main_answer']}\n\nFollow-up Answer:\n{message}"  # Combine the answers.
        combined_questions = "\n\n".join(user_data["previous_questions"])  # Combine all questions asked so far.

        # Generate feedback and a score for the user's answers.
        feedback = get_feedback(combined_questions, full_answer, resume_text, job_title)
        score = score_answer(combined_questions, full_answer, resume_text, job_title)

        # Mark the interview as complete.
        user_data["stage"] = "done"

        # Return the feedback and score to the frontend.
        return jsonify({
            "feedback": f"{feedback}<br><br><strong>Total Score:</strong> {score}/10"
        })

    # If the interview is complete (no more questions).
    else:
        return jsonify({
            "feedback": " Interview complete. Refresh the page to try another resume."
        })

# TEXT-TO-SPEECH (TTS) ENDPOINT
@app.route("/speak", methods=["POST"])
def speak():
    # Get the text to be converted to speech from the frontend request.
    text = request.json.get("text")
    if not text:
        return jsonify({"error": "No text provided"}), 400  # Return an error if no text is provided.

    try:
        # Create a temporary file to store the generated audio (TTS output).
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_audio:
            response = client.audio.speech.create(
                model="tts-1",  # The model used for text-to-speech (TTS).
                voice="nova",   # Voice type for the TTS (could be "nova", "alloy", etc.).
                input=text  # The text to be converted into speech.
            )
            response.stream_to_file(temp_audio.name)  # Stream the audio into the temporary file.

        # Return the generated audio file as the response (so it can be played).
        return send_file(temp_audio.name, mimetype="audio/mpeg", as_attachment=False)

    except Exception as e:
        return jsonify({"error": str(e)}), 500  # Handle any errors that occur.

# Make the app listen on all network interfaces (necessary for deployment).
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
