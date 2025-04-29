# Import the OpenAI library to talk to ChatGPT or other OpenAI models
import openai

# Import os to access environment variables (like API keys)
import os

# Load environment variables from a .env file (keeps secrets hidden)
from dotenv import load_dotenv

# Load secret settings like the OpenAI API key
load_dotenv()

# Create a client to talk to OpenAI using the API key
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ---------------------- AI Utilities ----------------------

# This function tries to guess the job title based on the resume
def guess_job_title(resume_text: str) -> str:
    # Create a prompt (instructions for the AI)
    prompt = f"""
You are a professional career analyst.

Given the following resume, guess the most likely job title this candidate is applying for.
Be specific but realistic. Return only the job title.

--- Resume ---
{resume_text}
"""
    # Send the prompt to ChatGPT using OpenAI API
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",  # Use this version of ChatGPT
        messages=[{"role": "system", "content": prompt}],
        temperature=0.5  # How creative the AI is (lower = more focused)
    )
    # Return the AI's answer, cleaned of extra whitespace
    return response.choices[0].message.content.strip()

# This function asks a realistic interview question using the resume and job title
def ask_interview_question(
    resume_text: str,
    job_title: str,
    previous_questions: list[str]
) -> str:
    # Create a prompt for the AI to generate one job-specific question
    prompt = f"""
You are a professional recruiter conducting a mock interview for the position of {job_title}.

Use the candidate's resume to ask only one specific, realistic, and job-relevant interview question.

Avoid repeating these previous questions:
{chr(10).join(previous_questions)}

--- Resume ---
{resume_text}
"""
    # Ask ChatGPT to generate the question
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": prompt}],
        temperature=0.7  # Slightly more creative
    )
    return response.choices[0].message.content.strip()

# This function gives feedback on the candidate's answer
def get_feedback(
    questions: str,
    answer: str,
    resume_text: str,
    job_title: str
) -> str:
    # Create a prompt for the AI to critique the candidate’s response
    prompt = f"""
You are an expert interview coach.

The candidate was asked these question(s):
{questions}

They answered with:
"{answer}"

Strictly analyze their response.

If the answer is irrelevant, empty, nonsensical, or clearly a placeholder like "1234", "asdf", or "n/a" — explicitly state this and give direct feedback on why that is unacceptable in a professional interview.

If the answer was valid, give constructive feedback on how to improve it further.

Focus only on the quality of their answer. Do not comment on their resume unless it directly relates to the quality of the answer.

Return your feedback using clear bullet points.
"""
    # Ask the AI for feedback
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": prompt}],
        temperature=0.7
    )
    return response.choices[0].message.content.strip()

# This function scores the answer from 1–10 and gives a breakdown
def score_answer(
    questions: str,
    answer: str,
    resume_text: str,
    job_title: str
) -> tuple[int, str]:
    # Prompt for AI to judge and score the interview answer
    prompt = f"""
You are a professional recruiter evaluating a candidate's interview performance for the role of {job_title}.

Here are the interview questions asked:
{questions}

Here is the candidate's full response:
{answer}

Here is their resume:
{resume_text}

First, if the answer is empty, irrelevant, or contains placeholders like "1234", "asdf", or "n/a", assign a very low score between 1-3 and explain why.

Otherwise, score the response from 1 (very poor) to 10 (excellent) based on the following categories:

1. Clarity
2. Professionalism
3. Relevance to the question
4. Technical/Role-Specific Accuracy
5. Problem-Solving & Critical Thinking
6. Experience & Resume Alignment

Format your response like this:

Score: X  
Breakdown:
- Clarity: ...
- Professionalism: ...
- Relevance: ...
- Technical/Role-Specific Accuracy: ...
- Problem-Solving & Critical Thinking: ...
- Experience & Resume Alignment: ...
"""
    # Get the AI's response
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": prompt}],
        temperature=0.7
    )

    # Process the response to extract the score
    lines = response.choices[0].message.content.strip().splitlines()
    score_line = next((l for l in lines if l.lower().startswith("score:")), "Score: 0")
    try:
        score = int(score_line.split(":")[1].strip())
    except:
        score = 0  # fallback if score can't be extracted

    # Get everything except the "Score:" line as the breakdown
    breakdown = "\n".join(l for l in lines if not l.lower().startswith("score:"))
    return score, breakdown


# ---------------------- Interview Session Handling ----------------------

# Store session state in a dictionary (resets when the app restarts)
user_data = {
    "resume_text": "",           # The uploaded resume as plain text
    "job_title": "",             # Job title guessed from resume
    "previous_questions": [],    # List of already asked questions
    "current_question": "",      # The most recent question asked
    "main_answer": "",           # The user's main answer (before follow-up)
    "stage": "initial"           # Stage of the interview: initial → followup → done
}

# Start a new interview by asking the first question
def start_interview(resume_text: str, job_title: str) -> str:
    """
    Initialize a new interview session and return the first question.
    """
    # Reset all user session data
    user_data.update({
        "resume_text": resume_text,
        "job_title": job_title,
        "previous_questions": [],
        "current_question": "",
        "main_answer": "",
        "stage": "initial"
    })
    # Ask the first interview question
    first_q = ask_interview_question(resume_text, job_title, [])
    # Save that question to memory
    user_data["previous_questions"] = [first_q]
    user_data["current_question"]  = first_q
    return first_q

# Handle the user's response and move through interview stages
def process_interview_message(message: str) -> dict:
    """
    Advance the interview based on the incoming user message.
    Returns a dict ready for jsonify(), including job_title and score.
    """
    # Grab current state info
    rt    = user_data["resume_text"]
    jt    = user_data["job_title"]
    stage = user_data["stage"]

    # If this is the first answer to the first question
    if stage == "initial":
        user_data["main_answer"] = message  # Save their main answer

        # Ask a follow-up question (to dig deeper)
        followup = ask_interview_question(rt, jt, user_data["previous_questions"])
        user_data["stage"]             = "followup"  # Move to next stage
        user_data["current_question"]  = followup
        user_data["previous_questions"].append(followup)
        return {"feedback": f"<strong>Follow‑up Question:</strong><br>{followup}"}

    # If we're now handling the follow-up response
    elif stage == "followup":
        # Combine the two answers into one
        full_ans  = f"{user_data['main_answer']}\n\nFollow‑up Answer:\n{message}"
        # Combine all asked questions
        combo_q   = "\n\n".join(user_data["previous_questions"])
        # Get feedback and score from AI
        fb        = get_feedback(combo_q, full_ans, rt, jt)
        score, breakdown = score_answer(combo_q, full_ans, rt, jt)
        user_data["stage"] = "done"  # Mark interview complete

        # Return feedback and score to front-end
        return {
            "feedback": (
                f"{fb}<br><br>"
                f"<strong>Total Score:</strong> {score}/10<br><br>"
                f"<strong>Score Breakdown:</strong><br>"
                f"{breakdown.replace(chr(10), '<br><br>')}"
            ),
            "job_title": jt,
            "score":     score
        }

    # If the interview is already done
    else:
        return {"feedback": "Interview complete. Refresh the page to try another resume."}
