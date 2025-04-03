# Importing necessary libraries
import openai  # OpenAI library to interact with their models (e.g., GPT-3 for generating text).
import os  # Provides operating system-related functionality, such as file path handling.
import pdfplumber  # Library to extract text from PDF files.
import docx  # Library to handle Microsoft Word documents (DOCX format).
from dotenv import load_dotenv  # Loads environment variables from a .env file, like the OpenAI API key.

# Load environment variables from the .env file (such as the OpenAI API key)
load_dotenv()

# Set up OpenAI client using the API key stored in environment variables
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# -------- Helper Functions --------

# Function to load a resume file based on its extension (PDF, DOCX, or TXT)
def load_resume(path="resume.pdf"):
    # Extract the file extension to determine the file type.
    _, ext = os.path.splitext(path)
    ext = ext.lower()  # Convert the extension to lowercase for consistency.

    # Call the appropriate function based on the file extension to load the resume text.
    if ext == ".pdf":
        return load_pdf(path)  # If it's a PDF, use the load_pdf function.
    elif ext == ".docx":
        return load_docx(path)  # If it's a DOCX, use the load_docx function.
    elif ext == ".txt":
        return load_txt(path)  # If it's a TXT file, use the load_txt function.
    else:
        raise ValueError("Unsupported resume format. Use .pdf, .docx, or .txt")  # Raise an error for unsupported file types.

# Function to extract text from a PDF file using the pdfplumber library
def load_pdf(path):
    text = ""  # Initialize an empty string to store the extracted text.
    with pdfplumber.open(path) as pdf:  # Open the PDF file.
        for page in pdf.pages:  # Loop through each page in the PDF.
            text += page.extract_text() or ""  # Extract text from the page and add it to the text variable.
    return text.strip()  # Return the extracted text after trimming whitespace.

# Function to extract text from a DOCX (Word) file using the python-docx library
def load_docx(path):
    doc = docx.Document(path)  # Open the DOCX file using python-docx.
    # Join the text of each paragraph in the document and return it as a single string.
    return "\n".join([para.text for para in doc.paragraphs]).strip()

# Function to extract text from a plain TXT file
def load_txt(path):
    with open(path, "r", encoding="utf-8") as file:  # Open the TXT file with UTF-8 encoding.
        return file.read().strip()  # Read the entire content and return it as a string.

# Function to guess the most likely job title based on the resume text
def guess_job_title(resume_text):
    # Prepare the prompt for OpenAI's model. This instructs the model to analyze the resume and predict a job title.
    prompt = f"""
You are a professional career analyst.

Given the following resume, guess the most likely job title this candidate is applying for.
Be specific but realistic. Return only the job title.

--- Resume ---
{resume_text}
"""
    # Send the prompt to OpenAI's model and get the response.
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",  # Specify the GPT-3.5 model.
        messages=[{"role": "system", "content": prompt}],  # Pass the prompt as a system message.
        temperature=0.5  # Adjust the creativity of the response (lower value means more focused).
    )
    # Extract and return the job title from the response.
    return response.choices[0].message.content.strip()

# Function to ask a relevant interview question based on the resume text and job title.
def ask_interview_question(resume_text, job_title, previous_questions):
    # Prepare the prompt for OpenAI to generate a job-relevant interview question.
    system_prompt = f"""
You are a professional recruiter conducting a mock interview for the position of {job_title}.

Use the candidate's resume to ask only one specific, realistic, and job-relevant interview question.

Do NOT list multiple questions or give examples. Only return a single interview question.

Avoid repeating these previous questions:
{chr(10).join(previous_questions)}  # Join the list of previous questions into a string.

--- Resume ---
{resume_text}
"""
    # Send the prompt to OpenAI and get the response with a follow-up question.
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",  # Use the GPT-3.5 model for generating the question.
        messages=[{"role": "system", "content": system_prompt}],  # Pass the prompt as a system message.
        temperature=0.7  # Adjust creativity for the response.
    )
    # Return the generated interview question from the response.
    return response.choices[0].message.content.strip()

# Function to provide constructive feedback on a candidate's answer based on their resume.
def get_feedback(question, answer, resume_text, job_title):
    # Prepare the prompt for OpenAI to provide feedback based on the user's response to the interview question.
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
    # Send the prompt to OpenAI and get feedback on the answer.
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",  # Use GPT-3.5 for generating the feedback.
        messages=[{"role": "system", "content": prompt}],  # Pass the prompt as a system message.
        temperature=0.7  # Adjust creativity for the response.
    )
    # Return the feedback generated by OpenAI.
    return response.choices[0].message.content.strip()

# Function to score the candidate's answer to the interview question.
def score_answer(question, answer, resume_text, job_title):
    # Prepare the prompt to generate a score for the answer on a scale from 1 to 10.
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
    # Send the prompt to OpenAI and get a score for the answer.
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",  # Use GPT-3.5 to generate the score.
        messages=[{"role": "system", "content": prompt}],  # Pass the prompt as a system message.
        temperature=0  # Set creativity to 0, as we want a straightforward numerical score.
    )
    # Return the score from the response.
    return int(response.choices[0].message.content.strip())
