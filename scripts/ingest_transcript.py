#!/usr/bin/env python3
"""Helper script to ingest a structured transcript via the SecureScribe public API."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import requests

DEFAULT_BASE_URL = os.environ.get("SECURESCRIBE_API_BASE_URL", "https://securescribe.wc504.io.vn/be")
API_VERSION = os.environ.get("SECURESCRIBE_API_VERSION", "v1")


def build_markdown(transcript_payload: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append(f"# {transcript_payload.get('meeting_title', 'Meeting Transcript')}")
    lines.append("")
    lines.append(f"- Meeting ID: {transcript_payload['meeting_id']}")
    lines.append(f"- Recorded At: {transcript_payload.get('meeting_timestamp', 'N/A')}")
    agenda = transcript_payload.get("agenda") or []
    if agenda:
        lines.append("")
        lines.append("## Agenda")
        for item in agenda:
            lines.append(f"- {item}")
    participants = transcript_payload.get("participants") or []
    if participants:
        lines.append("")
        lines.append("## Participants")
        for person in participants:
            lines.append(f"- {person.get('name')}: {person.get('role', 'Participant')}")
    lines.append("")
    lines.append("## Transcript")
    for entry in transcript_payload.get("transcript", []):
        timestamp = entry.get("timestamp", "--:--")
        speaker = entry.get("speaker", "Unknown")
        utterance = entry.get("utterance", "")
        lines.append(f"- [{timestamp}] {speaker}: {utterance}")
    return "\n".join(lines)


def upsert_transcript(*, base_url: str, token: str, meeting_id: str, content: str) -> Dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    create_url = f"{base_url}/api/{API_VERSION}/transcripts"
    payload = {"meeting_id": meeting_id, "content": content}
    response = requests.post(create_url, headers=headers, json=payload, timeout=60)
    if response.status_code == 409:
        # Transcript exists, attempt update path
        transcript_id = response.json().get("data", {}).get("id")
        if not transcript_id:
            response.raise_for_status()
        update_url = f"{create_url}/{transcript_id}"
        update_resp = requests.put(update_url, headers=headers, json={"content": content}, timeout=60)
        update_resp.raise_for_status()
        return update_resp.json()
    response.raise_for_status()
    return response.json()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest a transcript JSON file via SecureScribe public API")
    parser.add_argument("transcript_file", type=Path, help="Path to the structured transcript JSON")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="SecureScribe API base URL")
    parser.add_argument("--api-token", default=os.environ.get("SECURESCRIBE_API_TOKEN"), help="Bearer token for the API")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.api_token:
        raise SystemExit("SECURESCRIBE_API_TOKEN is required (env var or --api-token)")
    if not args.transcript_file.exists():
        raise SystemExit(f"Transcript file not found: {args.transcript_file}")
    payload = json.loads(args.transcript_file.read_text())
    meeting_id = payload["meeting_id"]
    content = build_markdown(payload)
    result = upsert_transcript(base_url=args.base_url.rstrip("/"), token=args.api_token, meeting_id=meeting_id, content=content)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
