# Import the OpenAI library so we can use their AI services like text-to-speech
import openai

# Import Python’s built-in modules for temporary files and file system tools
import tempfile  # Lets us create temporary files
import os  # Used for working with file paths and environment variables

# Import the function to load environment variables from a .env file
from dotenv import load_dotenv

# Import a Flask tool that lets us send files (like audio) to the browser
from flask import send_file

# Load environment variables (like our secret API key) from a .env file
load_dotenv()

# Create a client to connect to OpenAI using the API key we loaded
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ------------------ Text-to-Speech Function ---------------------

# This function takes some text and returns an audio file that says the text out loud
def generate_tts_audio(text: str):
    # Create a temporary .mp3 file where the AI-generated voice will be saved
    # This file is stored temporarily and will be deleted later
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_audio:
        # Ask OpenAI to turn the input text into speech using their text-to-speech model
        # 'tts-1' is the model, 'nova' is the voice type, and 'text' is what the AI should say
        response = client.audio.speech.create(
            model="tts-1",
            voice="nova",
            input=text
        )

        # Write the generated audio into our temporary .mp3 file
        response.stream_to_file(temp_audio.name)

    # Send the audio file back to the user's web browser using Flask
    # This allows the user to hear the generated voice
    return send_file(
        temp_audio.name,  # The path to the temporary audio file
        mimetype="audio/mpeg",  # Tell the browser it’s an audio file
        as_attachment=False  # This tells the browser to play it instead of downloading it
    )
