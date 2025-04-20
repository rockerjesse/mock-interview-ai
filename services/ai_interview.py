import openai
import os
from dotenv import load_dotenv

# Load env vars & init client
load_dotenv()
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ---------------------- AI Utilities ----------------------

def guess_job_title(resume_text: str) -> str:
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

def ask_interview_question(
    resume_text: str,
    job_title: str,
    previous_questions: list[str]
) -> str:
    prompt = f"""
You are a professional recruiter conducting a mock interview for the position of {job_title}.

Use the candidate's resume to ask only one specific, realistic, and job-relevant interview question.

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

def get_feedback(
    questions: str,
    answer: str,
    resume_text: str,
    job_title: str
) -> str:
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
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": prompt}],
        temperature=0.7
    )
    return response.choices[0].message.content.strip()

def score_answer(
    questions: str,
    answer: str,
    resume_text: str,
    job_title: str
) -> tuple[int, str]:
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
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": prompt}],
        temperature=0.7
    )
    lines = response.choices[0].message.content.strip().splitlines()
    score_line = next((l for l in lines if l.lower().startswith("score:")), "Score: 0")
    try:
        score = int(score_line.split(":")[1].strip())
    except:
        score = 0
    breakdown = "\n".join(l for l in lines if not l.lower().startswith("score:"))
    return score, breakdown

# ---------------------- Interview Session Handling ----------------------

user_data = {
    "resume_text": "",
    "job_title": "",
    "previous_questions": [],
    "current_question": "",
    "main_answer": "",
    "stage": "initial"
}

def start_interview(resume_text: str, job_title: str) -> str:
    """
    Initialize a new interview session and return the first question.
    """
    user_data.update({
        "resume_text": resume_text,
        "job_title": job_title,
        "previous_questions": [],
        "current_question": "",
        "main_answer": "",
        "stage": "initial"
    })
    first_q = ask_interview_question(resume_text, job_title, [])
    user_data["previous_questions"] = [first_q]
    user_data["current_question"]  = first_q
    return first_q

def process_interview_message(message: str) -> dict:
    """
    Advance the interview based on the incoming user message.
    Returns a dict ready for jsonify(), including job_title and score.
    """
    rt    = user_data["resume_text"]
    jt    = user_data["job_title"]
    stage = user_data["stage"]

    if stage == "initial":
        user_data["main_answer"] = message
        followup = ask_interview_question(rt, jt, user_data["previous_questions"])
        user_data["stage"]             = "followup"
        user_data["current_question"]  = followup
        user_data["previous_questions"].append(followup)
        return {"feedback": f"<strong>Follow‑up Question:</strong><br>{followup}"}

    elif stage == "followup":
        full_ans  = f"{user_data['main_answer']}\n\nFollow‑up Answer:\n{message}"
        combo_q   = "\n\n".join(user_data["previous_questions"])
        fb        = get_feedback(combo_q, full_ans, rt, jt)
        score, breakdown = score_answer(combo_q, full_ans, rt, jt)
        user_data["stage"] = "done"
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

    else:
        return {"feedback": "Interview complete. Refresh the page to try another resume."}