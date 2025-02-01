"""
This module contains tests for the SpeechProcessor service.
It verifies that processing a set number of WAV files produces the expected output.
"""

import os
import json
import glob
from pathlib import Path
import pytest
from tqdm import tqdm
from services.rich_processing_speechbrain import SpeechProcessor

def test_process_10_files_creates_test_output():
    """
    Test that processing 10 WAV files creates a test output file with the expected content.

    The test performs the following steps:
      1. Instantiates the SpeechProcessor.
      2. Defines a test output file path and removes any existing test output to avoid conflicts.
      3. Retrieves exactly 10 WAV files from the data/wav directory (fail if not exactly 10).
      4. Processes each WAV file using the SpeechProcessor, with progress bar feedback.
      5. Saves the processing results into a JSON file.
      6. Asserts that the output file exists and contains a list of 10 processed entries.
    """
    # Create an instance of SpeechProcessor to handle audio file processing.
    processor = SpeechProcessor()
    
    # Define the test output file path (ensure this does not overlap with production data).
    test_output = "data/enriched_transcripts_test.json"
    
    # Remove any existing test output file to ensure a fresh test environment.
    if os.path.exists(test_output):
        os.remove(test_output)
        
    # Obtain a sorted list of WAV files from the designated directory and take the first 10 for testing.
    wav_files = sorted(glob.glob("data/wav/*.wav"))[:10]
    assert len(wav_files) == 10, "Expected exactly 10 WAV files for the test."
    
    results = []
    # Process each WAV file while displaying a progress bar.
    for wav_file in tqdm(wav_files, desc="Processing test WAV files"):
        # Process the file and collect the resulting data.
        result = processor.process_wav_file(Path(wav_file))
        print(f"Processed file: {wav_file} with {len(result.get('segments', []))} segments.")
        results.append(result)
    
    # Save the processing results to the test output file in JSON format.
    with open(test_output, "w") as f:
        json.dump(results, f, indent=2)
    
    # Output the absolute path for debugging purposes.
    output_path = os.path.abspath(test_output)
    print(f"Test output written to: {output_path}")
    print(f"Total processed files: {len(results)}")
    
    # Verify that the test output file was successfully created.
    assert os.path.exists(test_output)
    with open(test_output, "r") as f:
        data = json.load(f)
    # Assert that the file contains a list of processed entries.
    assert isinstance(data, list), "Test output should be a list of processed entries."
    # Assert that exactly 10 files were processed.
    assert len(data) == 10, f"Expected 10 processed files, but got {len(data)}."
