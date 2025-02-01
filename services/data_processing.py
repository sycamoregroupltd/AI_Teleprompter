from pathlib import Path
from faster_whisper import WhisperModel
import json
import logging

# Set up logging to print progress messages with timestamps.
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

def transcribe_wav(wav_path: str) -> str:
    logging.info(f"Starting transcription for {wav_path}")
    # Create the model instance for each file if needed.
    # For efficiency you might want to initialize the model once outside the loop.
    model = WhisperModel("small.en")
    segments, info = model.transcribe(wav_path)
    transcript = " ".join(segment.text for segment in segments)
    logging.info(f"Completed transcription for {wav_path}")
    return transcript

if __name__ == "__main__":
    wav_dir = Path("data/wav")
    transcripts_path = Path("data/transcripts.json")
    transcripts = []

    # If transcripts.json exists, load it and determine which files are already processed.
    if transcripts_path.exists():
        logging.info(f"Loading existing transcripts from {transcripts_path}")
        transcripts = json.load(transcripts_path.open("r"))
        processed_files = {entry["file"] for entry in transcripts}
    else:
        processed_files = set()

    # List all WAV files in the data/wav directory.
    wav_files = list(wav_dir.glob("*.wav"))
    total_files = len(wav_files)
    logging.info(f"Found {total_files} WAV files in directory.")

    # Filter out files that have already been transcribed.
    remaining_files = [wav_file for wav_file in wav_files if wav_file.name not in processed_files]
    remaining_total = len(remaining_files)
    logging.info(f"{remaining_total} files remaining to process.")

    # Process only the remaining files.
    for index, wav_file in enumerate(remaining_files, start=1):
        logging.info(f"Processing file {index}/{remaining_total}: {wav_file.name}")
        transcript_text = transcribe_wav(str(wav_file))
        transcripts.append({
            "file": wav_file.name,
            "text": transcript_text
        })
        # Save progress after processing each file.
        with transcripts_path.open("w") as f:
            json.dump(transcripts, f, indent=2)
        logging.info(f"Updated {transcripts_path} with transcript for {wav_file.name}")

    logging.info(f"All files processed. Final transcripts saved to {transcripts_path}")
