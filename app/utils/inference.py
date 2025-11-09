import os
import time

import requests

from app.core.config import settings


def transcriber(audio_path):
    # Submit the audio file for transcription
    url = f"{settings.TRANSCRIBE_API_BASE_URL}/transcribe"

    with open(audio_path, "rb") as f:
        files = {"file": (os.path.basename(audio_path), f, "audio/wav")}
        response = requests.post(url, files=files)

    if response.status_code != 200:
        raise Exception(f"Failed to submit transcription: {response.text}")

    data = response.json()
    if not data.get("success"):
        raise Exception(f"API error: {data.get('message', 'Unknown error')}")

    task_id = data["data"]["task_id"]
    polling_url = f"{settings.TRANSCRIBE_API_BASE_URL}/transcribe/task/{task_id}"

    # Poll for completion
    max_polls = 120  # Maximum 10 minutes (120 * 5 seconds)
    poll_count = 0

    while poll_count < max_polls:
        print("Polling transcription status...")
        response = requests.get(polling_url)
        print(f"Poll response: {response.text}")
        if response.status_code != 200:
            raise Exception(f"Failed to poll transcription status: {response.text}")

        data = response.json()
        if not data.get("success"):
            raise Exception(f"API polling error: {data.get('message', 'Unknown error')}")

        status = data["data"]["status"]

        if status == "completed":
            break
        elif status == "failed":
            error_msg = data["data"].get("error", "Unknown error")
            raise Exception(f"Transcription failed: {error_msg}")

        time.sleep(30)
        poll_count += 1

    if poll_count >= max_polls:
        raise Exception("Transcription polling timed out")

    # Parse and format the results
    transcriptions = data["data"]["results"].get("transcriptions", [])

    if not transcriptions:
        return "No transcription available"

    formatted_text = ""
    for transcription in transcriptions:
        speaker = transcription.get("speaker", "UNKNOWN")
        text = transcription.get("transcription", "")
        start_time = transcription.get("start_time", 0)
        end_time = transcription.get("end_time", 0)

        # Format with speaker and timestamps
        formatted_text += f"{speaker} [{start_time:.2f}s - {end_time:.2f}s]: {text}\n\n"

    return formatted_text.strip()
