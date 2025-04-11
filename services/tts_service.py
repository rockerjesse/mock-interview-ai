# Import the OpenAI library to interact with their AI services
import openai

# Import built-in modules for creating temporary files and working with the file system
import tempfile
import os

# Import environment variable loader
from dotenv import load_dotenv

# Import Flask's send_file function to send audio files back to the user
from flask import send_file

# Load environment variables from the .env file
# This lets us safely store sensitive information like API keys outside of our code
load_dotenv()

# Initialize the OpenAI client using the API key loaded from the .env file
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ------------------ Text-to-Speech Function ---------------------

# This function generates speech audio from text input using OpenAI's TTS (Text-To-Speech) service
def generate_tts_audio(text: str):
    # Create a temporary .mp3 file to store the generated audio
    # tempfile.NamedTemporaryFile() creates a temporary file we can write to
    # delete=False means we will delete the file manually later
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_audio:
        # Call the OpenAI API to generate speech audio
        # model="tts-1" is the specific Text-To-Speech model we're using
        # voice="nova" is a specific voice option provided by OpenAI
        # input=text is the text the AI will turn into speech
        response = client.audio.speech.create(
            model="tts-1",
            voice="nova",
            input=text
        )

        # Stream the generated audio directly into the temporary file we created
        response.stream_to_file(temp_audio.name)

    # Once the audio is generated, send the file back to the user
    # Flask's send_file() function makes this easy
    return send_file(
        temp_audio.name,  # Path to the generated audio file
        mimetype="audio/mpeg",  # Tell the browser it's an audio file
        as_attachment=False  # Play directly in the browser instead of downloading
    )
