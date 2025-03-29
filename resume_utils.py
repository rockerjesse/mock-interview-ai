import openai
import os
import pdfplumber
import docx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up OpenAI client
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# -------- Helper Functions --------

def load_resume(path="resume.pdf"):
    _, ext = os.path.splitext(path)
    ext = ext.lower()

    if ext == ".pdf":
        return load_pdf(path)
    elif ext == ".docx":
        return load_docx(path)
    elif ext == ".txt":
        return load_txt(path)
    else:
        raise ValueError("Unsupported resume format. Use .pdf, .docx, or .txt")

def load_pdf(path):
    text = ""
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text.strip()

def load_docx(path):
    doc = docx.Document(path)
    return "\n".join([para.text for para in doc.paragraphs]).strip()

def load_txt(path):
    with open(path, "r", encoding="utf-8") as file:
        return file.read().strip()

def guess_job_title(resume_text):
    prompt = f"""
You are a professional career analyst.

Given the following resume, guess the most likely job title this candidate is applying for.
Be specific but realistic. Return only the job title.

--- Resume ---
{resume_text}
"""
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": prompt}],
        temperature=0.5
    )
    return response.choices[0].message.content.strip()

def ask_interview_question(resume_text, job_title, previous_questions):
    system_prompt = f"""
You are a professional recruiter conducting a mock interview for the position of {job_title}.

Use the candidate's resume to ask only one specific, realistic, and job-relevant interview question.

Do NOT list multiple questions or give examples. Only return a single interview question.

Avoid repeating these previous questions:
{chr(10).join(previous_questions)}

--- Resume ---
{resume_text}
"""
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": system_prompt}],
        temperature=0.7
    )
    return response.choices[0].message.content.strip()

def get_feedback(question, answer, resume_text, job_title):
    prompt = f"""
You're an expert interview coach.

The candidate is interviewing for the role of {job_title}.

Here’s the question they were asked:
{question}

Here’s their answer:
{answer}

Give constructive feedback considering their resume:
{resume_text}
"""
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": prompt}],
        temperature=0.7
    )
    return response.choices[0].message.content.strip()

def score_answer(question, answer, resume_text, job_title):
    prompt = f"""
You are a recruiter scoring a candidate's response to an interview question for the role of {job_title}.

Here is the question:
{question}

Here is the candidate's answer:
{answer}

Here is their resume:
{resume_text}

Give a score between 1 (very poor) and 10 (excellent), with no explanation. Just return the number.
"""
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": prompt}],
        temperature=0
    )
    return int(response.choices[0].message.content.strip())