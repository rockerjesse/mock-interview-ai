# Import built-in modules for file handling
import os  # This helps us work with file paths and file extensions

# Import external libraries that can read different types of resume documents
import pdfplumber  # Used to extract text from PDF files
import docx        # Used to extract text from Word (.docx) files


# ---------------------- MAIN FUNCTION ----------------------

# This is the main function that handles resume reading.
# It accepts the file path of a resume and returns the text content.
def load_resume(path="resume.pdf"):
    # Split the file path into the name and extension (like ".pdf")
    _, ext = os.path.splitext(path)

    # Convert the extension to lowercase (so ".PDF" and ".pdf" are treated the same)
    ext = ext.lower()

    # Choose the correct text-extraction function based on file type
    if ext == ".pdf":
        return load_pdf(path)       # Call the PDF reader if it's a PDF
    elif ext == ".docx":
        return load_docx(path)      # Call the Word reader if it's a DOCX
    elif ext == ".txt":
        return load_txt(path)       # Call the text reader if it's a plain text file
    else:
        # If the file is not one of the supported types, show an error
        raise ValueError("Unsupported resume format. Use .pdf, .docx, or .txt")


# ---------------------- PDF PARSER ----------------------

# This function handles reading a PDF file
def load_pdf(path: str):
    text = ""  # Start with an empty string to collect text

    # Open the PDF file using pdfplumber
    with pdfplumber.open(path) as pdf:
        # Loop through each page in the PDF
        for page in pdf.pages:
            # Extract text from the current page
            # If no text is found, add an empty string instead
            text += page.extract_text() or ""

    # Remove any extra spaces from the beginning and end
    return text.strip()


# ---------------------- DOCX PARSER ----------------------

# This function handles reading Word (.docx) files
def load_docx(path: str):
    # Open the Word document using the python-docx library
    doc = docx.Document(path)

    # Loop through every paragraph in the document
    # Extract text from each one and join them with a newline
    return "\n".join([para.text for para in doc.paragraphs]).strip()


# ---------------------- TXT PARSER ----------------------

# This function handles reading plain text (.txt) files
def load_txt(path: str):
    # Open the file in read mode using UTF-8 encoding (for most characters)
    with open(path, "r", encoding="utf-8") as file:
        # Read the entire file into a string, then strip off extra whitespace
        return file.read().strip()
