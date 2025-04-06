import openai
import os
import pdfplumber
import docx
from dotenv import load_dotenv

load_dotenv()
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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
    prompt = f"""
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
        messages=[{"role": "system", "content": prompt}],
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
You are a professional recruiter evaluating a candidate's interview performance for the role of {job_title}.

Here are the interview questions asked:
{question}

Here is the candidate's full response, including both the initial and follow-up answers:
{answer}

Here is their resume:
{resume_text}

Please give a final score between 1 (very poor) and 10 (excellent), and provide a brief breakdown across the following categories:

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
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": prompt}],
        temperature=0.7
    )

    full_text = response.choices[0].message.content.strip()
    lines = full_text.splitlines()

    score_line = next((line for line in lines if line.lower().startswith("score:")), "Score: 0")
    try:
        score = int(score_line.split(":")[1].strip())
    except:
        score = 0

    breakdown = "\n".join(line for line in lines if not line.lower().startswith("score:"))

    return score, breakdown
