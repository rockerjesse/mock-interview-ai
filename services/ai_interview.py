# Import OpenAI library to interact with their AI models
import openai

# Import modules for environment variables and file handling
import os
from dotenv import load_dotenv  # Loads sensitive API keys from .env file

# Load environment variables (like your API key)
load_dotenv()

# Create an OpenAI client instance using your API key from the .env file
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ---------------------- AI Function 1 ----------------------

# Guess a Job Title based on the user's resume text
def guess_job_title(resume_text: str):
    # Create a prompt that tells the AI its role and task
    # The AI will act like a career analyst and guess a realistic job title
    prompt = f"""
You are a professional career analyst.

Given the following resume, guess the most likely job title this candidate is applying for.
Be specific but realistic. Return only the job title.

--- Resume ---
{resume_text}
"""

    # Send the prompt to OpenAI's chat model
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": prompt}],
        temperature=0.5  # Controls creativity (lower = more accurate)
    )

    # Extract and return the generated job title from the response
    return response.choices[0].message.content.strip()


# ---------------------- AI Function 2 ----------------------

# Ask a custom interview question based on the resume and job title
def ask_interview_question(resume_text: str, job_title: str, previous_questions: list[str]):
    # Prompt the AI to act like a recruiter conducting a mock interview
    # It avoids repeating any previous questions asked
    prompt = f"""
You are a professional recruiter conducting a mock interview for the position of {job_title}.

Use the candidate's resume to ask only one specific, realistic, and job-relevant interview question.

Avoid repeating these previous questions:
{chr(10).join(previous_questions)}

--- Resume ---
{resume_text}
"""

    # Send the prompt to OpenAI's chat model
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": prompt}],
        temperature=0.7  # More creative to vary the questions
    )

    # Extract and return the generated interview question
    return response.choices[0].message.content.strip()


# ---------------------- AI Function 3 ----------------------

# Provide feedback on the candidate's interview answer
def get_feedback(questions: str, answer: str, resume_text: str, job_title: str):
    # Prompt the AI to act like an expert interview coach
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

    # Send the prompt to OpenAI's chat model
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": prompt}],
        temperature=0.7  # Slightly creative for natural feedback
    )

    # Return the generated feedback
    return response.choices[0].message.content.strip()


# ---------------------- AI Function 4 ----------------------

# Score the candidate's answer on a scale of 1-10
def score_answer(questions: str, answer: str, resume_text: str, job_title: str):
    # Prompt the AI to act like a professional recruiter grading the interview
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

    # Send the prompt to OpenAI's chat model
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": prompt}],
        temperature=0.7
    )

    # Get the full response text from the AI
    full_text = response.choices[0].message.content.strip()

    # Split the response into lines for easier parsing
    lines = full_text.splitlines()

    # Look for the line that starts with "Score:" to extract the score value
    score_line = next((line for line in lines if line.lower().startswith("score:")), "Score: 0")

    # Extract the score number from that line
    try:
        score = int(score_line.split(":")[1].strip())
    except:
        score = 0  # Fallback if parsing fails

    # Create the breakdown text by joining all lines that aren't the score line
    breakdown = "\n".join(line for line in lines if not line.lower().startswith("score:"))

    # Return both the numerical score and the detailed breakdown
    return score, breakdown
