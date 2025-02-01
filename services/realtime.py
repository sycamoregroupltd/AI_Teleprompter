import json
import asyncio
import os
import tempfile
import requests
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from twilio.rest import Client
from faster_whisper import WhisperModel

app = FastAPI()

# Load the faster-whisper model globally.
model = WhisperModel("small", device="cpu")  # Change device to "cuda" if you have a GPU

html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Real-Time Transcript and Prompts</title>
        <style>
          body { font-family: Arial, sans-serif; margin: 20px; }
          #transcript, #suggestions { 
              border: 1px solid #ccc; 
              padding: 10px; 
              margin-bottom: 20px; 
              min-height: 100px; 
              background-color: #f9f9f9;
          }
        </style>
    </head>
    <body>
        <h1>Live Call Transcript</h1>
        <div id="transcript">Waiting for transcript...</div>
        <h2>Admin Prompt Suggestions</h2>
        <div id="suggestions">Waiting for suggestions...</div>

        <script>
            var ws = new WebSocket("ws://" + location.host + "/ws");
            ws.onmessage = function(event) {
                var data = JSON.parse(event.data);
                document.getElementById("transcript").innerHTML = data.transcript;
                document.getElementById("suggestions").innerHTML = data.suggestion;
            };
            ws.onopen = function() {
                console.log("WebSocket connection established");
            };
            ws.onerror = function(error) {
                console.error("WebSocket error:", error);
            };
        </script>
    </body>
</html>
"""

@app.get("/")
async def get():
    return HTMLResponse(html)

# Function to transcribe a local file (for testing purposes).
async def transcribe_recording_local(file_path: str) -> str:
    segments, info = await asyncio.to_thread(model.transcribe, file_path)
    transcript = " ".join(segment.text for segment in segments)
    return transcript

# Existing function to download and transcribe a recording from Twilio.
async def transcribe_recording(recording_url: str, account_sid: str, auth_token: str) -> str:
    response = await asyncio.to_thread(requests.get, recording_url, auth=(account_sid, auth_token))
    if response.status_code != 200:
        return f"Error downloading recording: {response.status_code}"
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
        tmp_file.write(response.content)
        tmp_file.flush()
        audio_file_path = tmp_file.name
    segments, info = await asyncio.to_thread(model.transcribe, audio_file_path)
    transcript = " ".join(segment.text for segment in segments)
    return transcript

# Filter the transcript to extract only the caller's speech.
def extract_caller_transcript(full_transcript: str) -> str:
    # If the transcript starts with a known operator/voiceover phrase, discard it.
    if full_transcript.strip().lower().startswith("thank you for calling"):
        return ""
    # If speaker labels are present (e.g., "Caller:"), extract those lines.
    lines = full_transcript.splitlines()
    caller_lines = [line for line in lines if line.strip().startswith("Caller:")]
    if caller_lines:
        return "\n".join(caller_lines)
    # Otherwise, return the full transcript if it doesn't match operator patterns.
    return full_transcript

# Get a transcript update either from a local file or from Twilio.
async def get_transcript_update(current_transcript: str) -> str:
    test_file = "test_recording.mp3"
    if os.path.exists(test_file):
        # Use the local file for testing.
        full_transcript = await transcribe_recording_local(test_file)
        caller_transcript = extract_caller_transcript(full_transcript)
        return caller_transcript if caller_transcript else "[No caller transcript detected in test file.]"
    else:
        # Fall back to fetching the latest recording from Twilio.
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        if not account_sid or not auth_token:
            return current_transcript + " [No Twilio credentials provided.]"
        
        try:
            client = Client(account_sid, auth_token)
            recordings = client.recordings.list(limit=1)
        except Exception as e:
            return current_transcript + f" [Error fetching recording: {e}]"
        
        if recordings:
            latest_recording = recordings[0]
            recording_url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Recordings/{latest_recording.sid}.mp3"
            full_transcript = await transcribe_recording(recording_url, account_sid, auth_token)
            caller_transcript = extract_caller_transcript(full_transcript)
            return caller_transcript if caller_transcript else "[No caller transcript detected.]"
        else:
            return current_transcript + " [No new recording found.]"

# Generate a prompt suggestion based on the caller transcript.
async def get_prompt_suggestion(transcript: str) -> str:
    if not transcript.strip():
        return "No caller transcript detected."
    if "hello" in transcript.lower():
        return "Prompt: Greet the caller warmly."
    else:
        return "Prompt: Please verify the caller's details."

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    transcript = ""
    while True:
        transcript = await get_transcript_update(transcript)
        suggestion = await get_prompt_suggestion(transcript)
        data = {
            "transcript": transcript,
            "suggestion": suggestion
        }
        await websocket.send_text(json.dumps(data))
        await asyncio.sleep(5)