# Import built-in modules for file handling
import os  # For working with file paths and extensions

# Import libraries to read different document types
import pdfplumber  # For extracting text from PDF files
import docx        # For extracting text from Word (.docx) files


# Main function that loads and reads a resume file
# Accepts a file path and returns the extracted text from the file
def load_resume(path="resume.pdf"):
    # Split the file name and extension
    _, ext = os.path.splitext(path)

    # Convert the extension to lowercase for consistency
    ext = ext.lower()

    # Determine which function to use based on file type
    if ext == ".pdf":
        return load_pdf(path)
    elif ext == ".docx":
        return load_docx(path)
    elif ext == ".txt":
        return load_txt(path)
    else:
        # If the file is not a supported type, raise an error
        raise ValueError("Unsupported resume format. Use .pdf, .docx, or .txt")


# Function to extract text from PDF files
def load_pdf(path: str):
    text = ""  # Create an empty string to store the extracted text

    # Open the PDF file
    with pdfplumber.open(path) as pdf:
        # Loop through each page of the PDF
        for page in pdf.pages:
            # Extract text from the page
            # If nothing is found, add an empty string
            text += page.extract_text() or ""

    # Remove extra whitespace from the start and end of the text
    return text.strip()


# Function to extract text from Word (.docx) files
def load_docx(path: str):
    # Open the Word document
    doc = docx.Document(path)

    # Loop through each paragraph in the document
    # Extract the text from each paragraph and join them with a newline
    return "\n".join([para.text for para in doc.paragraphs]).strip()


# Function to read plain text (.txt) files
def load_txt(path: str):
    # Open the text file in read mode with UTF-8 encoding
    with open(path, "r", encoding="utf-8") as file:
        # Read the entire file content and remove extra whitespace
        return file.read().strip()
