from typing import Tuple

import requests


def download_file_from_url(url: str) -> Tuple[bytes, str]:
    """Download file from URL and return content with content type"""
    headers = {
        "User-Agent": "SecureScribe-Bot/1.0",
        "Accept": "audio/*, video/webm, */*",
    }

    response = requests.get(url, timeout=60, stream=True, headers=headers)
    response.raise_for_status()

    content_length = response.headers.get("content-length")
    if content_length and int(content_length) > 100 * 1024 * 1024:
        raise ValueError("File too large (>100MB)")

    file_content = bytearray()
    for chunk in response.iter_content(chunk_size=8192):
        file_content.extend(chunk)
        if len(file_content) > 100 * 1024 * 1024:
            raise ValueError("File too large (>100MB)")

    if len(file_content) == 0:
        raise ValueError("Downloaded file is empty")

    content_type = response.headers.get("content-type", "audio/webm")
    return bytes(file_content), content_type
