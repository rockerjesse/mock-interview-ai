
# Career Footprint  
### AI-Powered Mock Interview & Career Management Tool  
*A Flask Web App for Job Seekers & Career Development*

---

## Overview

Career Footprint is a web application designed to help users practice job interviews, receive feedback, and manage their career progress.  

Users can:
- Register & Log in
- Upload their résumé
- Receive an AI-generated job title guess
- Participate in a mock interview (with AI-generated questions)
- Get constructive feedback & a performance score
- Hear their feedback using text-to-speech
- Store uploaded resumes (per user)

---

## Tech Stack

| Technology              | Purpose                              |
|-------------------------|--------------------------------------|
| Python + Flask          | Backend Web Framework                |
| Flask-SQLAlchemy        | Database Management (SQLite)         |
| Flask-Login             | User Authentication (Login/Logout)   |
| OpenAI API              | AI Chat & Text-to-Speech             |
| HTML + CSS + JavaScript | Frontend Pages                       |
| SQLite                  | Database for storing users & resumes |

---

## File Structure

```
career_footprint/
│
├── app.py                # Main Flask App (Routes & App Logic)
├── models/
│   ├── user.py           # User Model (User Accounts)
│   └── resume.py         # Resume Model (Uploaded Resumes)
│
├── services/
│   ├── resume_parser.py  # Load text from PDF, DOCX, TXT resumes
│   ├── ai_interview.py   # All AI Interview Functions
│   └── tts_service.py    # Text-to-Speech Service
│
├── templates/            # HTML Files (Flask Templates)
│
├── uploads/              # Temporary Storage for Uploaded Resumes
│
├── instance/             # SQLite Database Location
│   └── users.db
│
├── .env                  # Stores Environment Variables (API Keys)
└── requirements.txt      # Python Dependencies
```

---

## Setup Instructions

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/career_footprint.git
cd career_footprint
```

---

### 2. Create & Activate Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows
```

---

### 3. Install Required Packages
```bash
pip install -r requirements.txt
```

---

### 4. Create a `.env` File
```bash
cp .env.template .env
```

Inside `.env` update:
```
OPENAI_API_KEY=your_openai_api_key_here
```

---

### 5. Run the App
```bash
python app.py
```

Visit:  
http://localhost:5000  

---

## Usage Guide

| Feature            | How It Works                                                 |
|--------------------|--------------------------------------------------------------|
| Register           | Create an account with username & password.                  |
| Login              | Log in to access the interview tools.                        |
| Upload Resume      | Upload PDF, DOCX, or TXT.                                    |
| AI Job Title Guess | AI will guess your likely job title based on resume content. |
| Mock Interview     | AI asks tailored questions based on your resume & job title. |
| Feedback & Score   | AI evaluates your answers & gives a score with suggestions.  |
| Text-To-Speech     | Listen to your feedback using generated audio.               |
| Resumes            | Resumes are tied to your account & deleted after use.        |

---

## Developer Notes

- All sensitive data (API keys) should go in `.env`.
- This project uses temporary file storage for uploads to avoid storing user data long-term.
- SQLite is used for easy local development.
- OpenAI's GPT-3.5 powers the interview AI and feedback system.
- Text-to-Speech is provided using OpenAI's TTS service.

---

## Future Improvements (Ideas)

- User Profile Customization
- Resume Generator with AI Assistance
- AI Career Coach Avatar
- Persistent Career Progress Tracking
- Industry-Specific Interview Mode
- Adaptive Learning Materials Based on User Performance
