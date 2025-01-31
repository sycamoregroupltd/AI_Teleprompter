from pathlib import Path
from faster_whisper import WhisperModel
import json

def transcribe_wav(wav_path: str) -> str:
    # Choose a model size, e.g., "small.en" or "base.en"
    model = WhisperModel("small.en")  
    segments, info = model.transcribe(wav_path)
    # Concatenate all text segments
    return " ".join(segment.text for segment in segments)

if __name__ == "__main__":
    wav_dir = Path("data/wav")
    transcripts = []
    
    # Create "data/wav" folder and place your .wav files there
    for wav_file in wav_dir.glob("*.wav"):
        transcript_text = transcribe_wav(str(wav_file))
        transcripts.append({
            "file": wav_file.name,
            "text": transcript_text
        })
    
    # Save transcripts to JSON
    out_path = Path("data/transcripts.json")
    with out_path.open("w") as f:
        json.dump(transcripts, f, indent=2)
    print(f"Saved transcripts to {out_path}")
