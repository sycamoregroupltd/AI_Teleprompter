import os
import json
import re
import tempfile
import logging
from pathlib import Path
import torch
device = "cuda" if torch.cuda.is_available() else "cpu"

# Import the transcription model from faster-whisper
from faster_whisper import WhisperModel

# Import pyannote for diarisation
from pyannote.audio import Pipeline

# Import spaCy for NER
import spacy

# -----------------------------
# 1. Setup logging and load models
# -----------------------------
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

# Load the Whisper transcription model (adjust model size and device as needed)
whisper_model = WhisperModel("small.en", device=device)

# Retrieve the Hugging Face token from the environment
hf_token = os.getenv("HF_TOKEN")
if not hf_token:
    raise ValueError("Hugging Face token not found. Please set the HF_TOKEN environment variable.")

diarisation_pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization", use_auth_token=hf_token)

# Load spaCy model for NER
nlp = spacy.load("en_core_web_sm")

# -----------------------------
# 2. Define helper functions
# -----------------------------
def transcribe_wav(wav_path: str) -> list:
    """
    Transcribe the given WAV file using faster-whisper.
    Returns a list of transcription segments with start, end, and text.
    """
    logging.info(f"Transcribing: {wav_path}")
    segments, info = whisper_model.transcribe(wav_path)
    transcript_segments = [
        {"start": seg.start, "end": seg.end, "text": seg.text.strip()} for seg in segments
    ]
    return transcript_segments

def diarise_audio(wav_path: str):
    """
    Run speaker diarisation on the audio file.
    Returns a list of segments with start, end, and speaker label.
    """
    logging.info(f"Running diarisation on: {wav_path}")
    diarisation = diarisation_pipeline(wav_path)
    segments = []
    for segment, _, speaker in diarisation.itertracks(yield_label=True):
        segments.append({
            "start": segment.start,
            "end": segment.end,
            "speaker": speaker
        })
    return segments

def assign_speaker_labels(transcription_segments, diarisation_segments):
    """
    For each transcription segment, assign a speaker label based on overlapping diarisation segments.
    Returns a list of enriched segments.
    """
    enriched_segments = []
    for seg in transcription_segments:
        seg_start = seg["start"]
        seg_end = seg["end"]
        overlapping = [d for d in diarisation_segments if d["end"] > seg_start and d["start"] < seg_end]
        best_speaker = "Unknown"
        max_overlap = 0
        for d in overlapping:
            overlap = min(seg_end, d["end"]) - max(seg_start, d["start"])
            if overlap > max_overlap:
                max_overlap = overlap
                best_speaker = d["speaker"]
        seg["speaker"] = best_speaker
        enriched_segments.append(seg)
    return enriched_segments

def extract_entities(text: str) -> dict:
    """
    Use spaCy and regex to extract entities such as emails, phone numbers, names, and product keywords.
    """
    doc = nlp(text)
    entities = {
        "emails": [],
        "phone_numbers": [],
        "names": [],
        "products": []
    }
    for ent in doc.ents:
        if ent.label_ in ["PERSON", "ORG"]:
            entities["names"].append(ent.text)
        elif ent.label_ == "PRODUCT":
            entities["products"].append(ent.text)
    
    email_pattern = r"[\w\.-]+@[\w\.-]+\.\w+"
    phone_pattern = r"\+?\d[\d\s\-\(\)]{7,}\d"
    emails = re.findall(email_pattern, text)
    phones = re.findall(phone_pattern, text)
    entities["emails"].extend(emails)
    entities["phone_numbers"].extend(phones)
    
    # Remove duplicates
    for key in entities:
        entities[key] = list(set(entities[key]))
    
    return entities

def clean_transcript(text: str) -> str:
    """
    Remove unwanted hold scripts or automated instructions from the transcript.
    """
    unwanted_phrases = [
        "Thank you for calling",
        "Please press",
        "You have an incoming call",
        "Our office is currently closed",
        "Welcome to the",
        "Please leave a message"
    ]
    lines = text.splitlines()
    cleaned_lines = []
    for line in lines:
        # Check if line starts with any unwanted phrase
        if not any(line.strip().startswith(phrase) for phrase in unwanted_phrases):
            cleaned_lines.append(line.strip())
    return " ".join(cleaned_lines)

# -----------------------------
# 3. Main processing function for a single WAV file
# -----------------------------
def process_wav_file(wav_file: Path) -> dict:
    """
    Process a single WAV file: transcribe, run diarisation, merge results, clean transcript, and extract entities.
    Returns a dictionary with the enriched data.
    """
    logging.info(f"Processing file: {wav_file.name}")
    
    # Transcribe the audio
    transcription_segments = transcribe_wav(str(wav_file))
    
    # Run diarisation to get speaker segments
    diarisation_segments = diarise_audio(str(wav_file))
    
    # Merge transcription segments with speaker labels
    enriched_segments = assign_speaker_labels(transcription_segments, diarisation_segments)
    
    # Build the full transcript
    full_transcript = " ".join(seg["text"] for seg in enriched_segments)
    
    # Clean the transcript to remove hold/automated messages
    cleaned_transcript = clean_transcript(full_transcript)
    
    # Optionally, extract only customer dialogue if your diarisation labels allow it.
    customer_transcript = " ".join(seg["text"] for seg in enriched_segments if "Customer" in seg["speaker"])
    
    # Extract entities from the cleaned transcript
    entities = extract_entities(cleaned_transcript)
    
    output = {
        "file": wav_file.name,
        "transcript": cleaned_transcript,
        "customer_transcript": customer_transcript,
        "segments": enriched_segments,
        "entities": entities
    }
    return output

# -----------------------------
# 4. Process all WAV files and save the enriched data
# -----------------------------
def main():
    wav_dir = Path("data/wav")
    output_data = []
    
    # Process each WAV file in the directory
    for wav_file in wav_dir.glob("*.wav"):
        try:
            result = process_wav_file(wav_file)
            output_data.append(result)
        except Exception as e:
            logging.error(f"Error processing {wav_file.name}: {e}")
    
    # Save the enriched data as JSON.
    output_path = Path("data/enriched_transcripts.json")
    with output_path.open("w") as f:
        json.dump(output_data, f, indent=2)
    logging.info(f"Saved enriched transcripts to {output_path}")

if __name__ == "__main__":
    main()