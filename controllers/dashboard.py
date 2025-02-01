from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from pathlib import Path
import json
from collections import defaultdict

# Initialize FastAPI application instance.
app = FastAPI()
# Set up Jinja2 templates directory.
templates = Jinja2Templates(directory="templates")

def load_json(file_path: str):
    """
    Load JSON data from the specified file.
    
    This function checks if the file exists, and if so, attempts to read and parse its contents as JSON.
    In case of any error during file reading or JSON parsing, it prints an error message and returns an empty list.
    
    Parameters:
        file_path (str): The path to the JSON file.
    
    Returns:
        The parsed JSON data if successful; otherwise, an empty list.
    """
    path = Path(file_path)
    if path.exists():
        try:
            # Read the file's text and parse it as JSON.
            return json.loads(path.read_text())
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
    return []

@app.get("/dashboard")
async def dashboard(request: Request):
    """
    Render the dashboard view with data loaded from JSON files.
    
    This endpoint performs the following steps:
      1. Loads transcripts and call data from JSON files.
      2. Calculates summary metrics such as total calls, total transcripts, and average transcript length.
      3. Aggregates call data by date to prepare call volume metrics.
      4. Renders the 'dashboard.html' template with the collected data.
    
    Parameters:
        request (Request): The incoming request object.
    
    Returns:
        The rendered HTML page for the dashboard.
    """
    # Load data from JSON files.
    transcripts = load_json("data/transcripts.json")
    calls = load_json("data/calls.json")
    
    # Calculate basic summary metrics.
    total_calls = len(calls)
    total_transcripts = len(transcripts)
    if transcripts:
        # Calculate average transcript length based on the 'text' field.
        avg_transcript_length = round(sum(len(t.get("text", "")) for t in transcripts) / len(transcripts), 2)
    else:
        avg_transcript_length = 0

    # Prepare data for the call volume chart.
    # Group calls by date (assuming timestamp is ISO formatted, e.g. "2025-01-31T21:07:00").
    call_date_counts = defaultdict(int)
    for call in calls:
        # Extract date from timestamp (first 10 characters represent YYYY-MM-DD).
        date_str = call.get("timestamp", "")[:10]
        if date_str:
            call_date_counts[date_str] += 1
    
    # Sort dates and prepare corresponding call counts.
    sorted_dates = sorted(call_date_counts.keys())
    call_counts = [call_date_counts[date] for date in sorted_dates]

    # Render the 'dashboard.html' template with all the data for display.
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "transcripts": transcripts,
        "calls": calls,
        "total_calls": total_calls,
        "total_transcripts": total_transcripts,
        "avg_transcript_length": avg_transcript_length,
        "call_dates": sorted_dates,
        "call_counts": call_counts,
    })
