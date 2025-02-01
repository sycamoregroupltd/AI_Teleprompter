import os
import json
import re
import logging
from pathlib import Path
from typing import List, Dict, Any
import torch

# Import models and NLP libraries
from faster_whisper import WhisperModel
import spacy

class SpeechProcessor:
    """
    SpeechProcessor handles transcription, speaker diarisation, 
    entity extraction, and transcript cleaning for audio files.
    
    It leverages the faster-whisper model for transcription,
    SpeechBrain for speaker diarisation (if available), and spaCy 
    for named entity recognition.
    """
    def __init__(self, unwanted_phrases: List[str] = None) -> None:
        """
        Initialize the SpeechProcessor.
        
        - Configures logging.
        - Sets up device for torch (cuda if available, otherwise cpu).
        - Loads the Whisper transcription model.
        - Attempts to load environment variables (.env) for configuration.
        - Retrieves the Hugging Face token either from environment or file.
        - Loads the SpeechBrain diarisation model; if failing, sets diarisation to None.
        - Loads the spaCy model for NER.
        - Sets default unwanted phrases that will be filtered from transcripts.
        
        Parameters:
            unwanted_phrases (List[str], optional): Custom list of phrases to remove from transcripts.
        """
        # Setup logging with timestamp and level info.
        logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

        # Determine device: use CUDA if available, else fallback to CPU.
        self.device: str = "cuda" if torch.cuda.is_available() else "cpu"

        # Load the Whisper transcription model.
        try:
            # 'small.en' model is used for English transcription.
            self.whisper_model = WhisperModel("small.en", device=self.device)
        except Exception as e:
            logging.error("Error loading Whisper model: %s", e)
            raise

        # Attempt to load environment variables from a .env file if available.
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            logging.info("python-dotenv not installed; skipping .env loading")

        # Retrieve the Hugging Face token from environment variable.
        hf_token = os.getenv("HF_TOKEN")
        if not hf_token:
            # Fallback: read token from a local file if available.
            token_path = "config/hf_token.txt"
            if os.path.exists(token_path):
                with open(token_path, "r") as f:
                    hf_token = f.read().strip()
                if hf_token:
                    logging.info("Hugging Face token loaded from config/hf_token.txt")
            if not hf_token:
                raise ValueError("Hugging Face token not found. Please set the HF_TOKEN environment variable or place the token in config/hf_token.txt")

        # Load SpeechBrain's diarisation model.
        try:
            from speechbrain.inference.speaker_diarization import SpeakerDiarization
            self.diarization_model = SpeakerDiarization.from_hparams(
                source="speechbrain/diarization-diar",
                savedir="pretrained_models/diarization",
                run_opts={"device": self.device},
                hf_token=hf_token
            )
        except Exception as e:
            logging.error("Error loading SpeechBrain diarisation model: %s", e)
            # Instead of failing, fallback to None to allow processing without diarisation.
            self.diarization_model = None

        # Load spaCy model for Named Entity Recognition.
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except Exception as e:
            logging.error("Error loading spaCy model: %s", e)
            raise

        # Set unwanted phrases that will be removed from transcripts.
        self.unwanted_phrases: List[str] = unwanted_phrases or [
            "Thank you for calling",
            "Please press",
            "You have an incoming call",
            "Our office is currently closed",
            "Welcome to the",
            "Please leave a message"
        ]

    def transcribe_wav(self, wav_path: str) -> List[Dict[str, Any]]:
        """
        Transcribe the given WAV file using the faster-whisper model.
        
        Parameters:
            wav_path (str): Path to the WAV file.
        
        Returns:
            List[Dict[str, Any]]: A list of transcript segments containing start,
                                  end times, and the transcribed text.
        """
        logging.info(f"Transcribing: {wav_path}")
        # Get transcription segments and additional info (unused) from the model.
        segments, info = self.whisper_model.transcribe(wav_path)
        # Process each segment to form a dictionary with start, end and cleaned text.
        transcript_segments = [
            {"start": seg.start, "end": seg.end, "text": seg.text.strip()} for seg in segments
        ]
        return transcript_segments

    def diarise_audio(self, wav_path: str) -> List[Dict[str, Any]]:
        """
        Run speaker diarisation on the audio file using SpeechBrain.
        
        Parameters:
            wav_path (str): Path to the WAV file.
        
        Returns:
            List[Dict[str, Any]]: A list of diarisation segments with start, end times, and speaker labels.
                                  Returns an empty list if the diarisation model is not loaded.
        """
        if self.diarization_model is None:
            logging.warning("Diarisation model not loaded; skipping diarisation")
            return []
        logging.info(f"Running diarisation on: {wav_path}")
        try:
            diarisation_result = self.diarization_model.diarize_file(wav_path)
        except Exception as e:
            logging.error("Diarisation error for %s: %s", wav_path, e)
            raise

        segments = []
        # Convert each diarisation segment into a dictionary.
        for seg in diarisation_result:
            segments.append({
                "start": seg.start,
                "end": seg.end,
                "speaker": seg.speaker
            })
        return segments

    def assign_speaker_labels(self, transcription_segments: List[Dict[str, Any]],
                                diarisation_segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Assign speaker labels to each transcription segment based on overlapping diarisation segments.
        
        This function computes the overlap duration between transcription segments and 
        diarisation segments and assigns the speaker label with the maximum overlap.
        
        Parameters:
            transcription_segments (List[Dict[str, Any]]): Transcribed segments from the audio.
            diarisation_segments (List[Dict[str, Any]]): Diarisation segments with speaker labels.
        
        Returns:
            List[Dict[str, Any]]: Transcription segments enriched with speaker labels.
        """
        enriched_segments = []
        for seg in transcription_segments:
            seg_start = seg["start"]
            seg_end = seg["end"]
            # Identify all diarisation segments that overlap with the transcription segment.
            overlapping = [d for d in diarisation_segments if d["end"] > seg_start and d["start"] < seg_end]
            best_speaker = "Unknown"
            max_overlap = 0
            # Determine which overlapping segment has the most overlap.
            for d in overlapping:
                overlap = min(seg_end, d["end"]) - max(seg_start, d["start"])
                if overlap > max_overlap:
                    max_overlap = overlap
                    best_speaker = d["speaker"]
            # Assign the determined speaker label to the segment.
            seg["speaker"] = best_speaker
            enriched_segments.append(seg)
        return enriched_segments

    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Extract entities from the text using spaCy and regex.
        
        Processes:
          - Uses spaCy to extract named entities like PERSON, ORG, and PRODUCT.
          - Applies regex to detect emails and phone numbers.
          - Removes duplicate entities.
        
        Parameters:
            text (str): Input text for entity extraction.
        
        Returns:
            Dict[str, List[str]]: Dictionary containing lists of emails, phone numbers, names, and products.
        """
        doc = self.nlp(text)
        entities = {
            "emails": [],
            "phone_numbers": [],
            "names": [],
            "products": []
        }
        # Extract entities using spaCy's entity recognition.
        for ent in doc.ents:
            if ent.label_ in ["PERSON", "ORG"]:
                entities["names"].append(ent.text)
            elif ent.label_ == "PRODUCT":
                entities["products"].append(ent.text)
        
        # Define regex patterns for emails and phone numbers.
        email_pattern = r"[\w\.-]+@[\w\.-]+\.\w+"
        phone_pattern = r"\+?\d[\d\s\-\(\)]{7,}\d"
        # Use regex to find emails and phone numbers in the text.
        entities["emails"].extend(re.findall(email_pattern, text))
        entities["phone_numbers"].extend(re.findall(phone_pattern, text))
        
        # Eliminate duplicate entries in each category.
        for key in entities:
            entities[key] = list(set(entities[key]))
        
        return entities

    def clean_transcript(self, text: str) -> str:
        """
        Remove unwanted phrases from the transcript.
        
        Splits the transcript into lines, filters out lines that start with any of the unwanted phrases,
        and then recombines the remaining lines into a single cleaned string.
        
        Parameters:
            text (str): Original transcript text.
        
        Returns:
            str: Cleaned transcript with unwanted phrases removed.
        """
        lines = text.splitlines()
        cleaned_lines = []
        for line in lines:
            # Only include the line if it does NOT start with any unwanted phrase.
            if not any(line.strip().startswith(phrase) for phrase in self.unwanted_phrases):
                cleaned_lines.append(line.strip())
        # Combine the cleaned lines into a single string separated by spaces.
        return " ".join(cleaned_lines)

    def process_wav_file(self, wav_file: Path) -> Dict[str, Any]:
        """
        Process a single WAV file through the following pipeline:
          - Transcribe the audio using faster-whisper.
          - Diarise the audio using SpeechBrain (if available).
          - Assign speaker labels based on overlap between transcription and diarisation.
          - Clean the full transcript text.
          - Extract specific entities from the cleaned transcript.
        
        Parameters:
            wav_file (Path): Path object representing the WAV file.
        
        Returns:
            Dict[str, Any]: Dictionary containing the file name, cleaned transcript, 
                            customer transcript, enriched segments, and extracted entities.
        """
        logging.info(f"Processing file: {wav_file.name}")
        
        # Step 1: Transcribe the audio file to get text segments.
        transcription_segments = self.transcribe_wav(str(wav_file))
        
        # Step 2: Perform speaker diarisation on the audio file.
        diarisation_segments = self.diarise_audio(str(wav_file))
        
        # Step 3: Enrich transcription by assigning speaker labels.
        enriched_segments = self.assign_speaker_labels(transcription_segments, diarisation_segments)
        
        # Combine all segment texts to form the full transcript.
        full_transcript = " ".join(seg["text"] for seg in enriched_segments)
        # Clean the full transcript by removing unwanted phrases.
        cleaned_transcript = self.clean_transcript(full_transcript)
        # Extract customer-specific transcript if speaker label contains "Customer".
        customer_transcript = " ".join(seg["text"] for seg in enriched_segments if "Customer" in seg["speaker"])
        
        # Extract various entities from the cleaned transcript.
        entities = self.extract_entities(cleaned_transcript)
        
        return {
            "file": wav_file.name,
            "transcript": cleaned_transcript,
            "customer_transcript": customer_transcript,
            "segments": enriched_segments,
            "entities": entities
        }

    def process_all_files(self, wav_directory: str = "data/wav", output_file: str = "data/enriched_transcripts.json") -> None:
        """
        Process all WAV files in the specified directory that have not been processed before.
        
        The function performs the following steps:
          - Reads existing enriched transcripts from a JSON file, if available.
          - Iterates over each WAV file in the directory.
          - Skips files that have already been processed.
          - Processes new files and adds the enriched data.
          - Writes the combined data back to the JSON file.
        
        Parameters:
            wav_directory (str): Directory containing WAV files.
            output_file (str): Path to the JSON file where enriched transcripts are saved.
        """
        wav_dir = Path(wav_directory)
        output_path = Path(output_file)
        # Attempt to load existing enriched data if available.
        if output_path.exists():
            try:
                with output_path.open("r") as f:
                    existing_data = json.load(f)
                processed_files = { entry["file"] for entry in existing_data }
            except Exception as e:
                logging.error("Error reading existing enriched transcripts: %s", e)
                existing_data = []
                processed_files = set()
        else:
            existing_data = []
            processed_files = set()

        new_entries = []
        # Iterate over all WAV files in the directory.
        for wav_file in wav_dir.glob("*.wav"):
            if wav_file.name in processed_files:
                logging.info(f"Skipping already processed file: {wav_file.name}")
                continue
            try:
                result = self.process_wav_file(wav_file)
                logging.info(f"Processed file: {wav_file.name} with {len(result.get('segments', []))} segments.")
                new_entries.append(result)
            except Exception as e:
                logging.error("Error processing %s: %s", wav_file.name, e)
        
        # If new entries were processed, combine with existing data and save to JSON.
        if new_entries:
            combined_data = existing_data + new_entries
            with output_path.open("w") as f:
                json.dump(combined_data, f, indent=2)
            logging.info(f"Saved enriched transcripts to {output_path}")
        else:
            logging.info("No new files to process.")

def main() -> None:
    """
    Main execution entry point.
    
    Instantiates the SpeechProcessor and triggers the processing of all WAV files.
    """
    processor = SpeechProcessor()
    processor.process_all_files()

if __name__ == "__main__":
    main()
