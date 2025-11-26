"""Unit tests for inference utility functions"""

import os
import tempfile
from unittest.mock import Mock, patch

import pytest

from app.utils.inference import transcriber


class TestTranscriber:
    """Tests for transcriber function"""

    def test_transcriber_success(self):
        """Test successful transcription"""
        # Create a temporary audio file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_file.write(b"fake audio data")
            temp_audio_path = temp_file.name

        try:
            mock_response_data = {"success": True, "data": {"task_id": "test_task_123", "results": {"transcriptions": [{"speaker": "SPEAKER_1", "transcription": "Hello world", "start_time": 0.0, "end_time": 2.5}, {"speaker": "SPEAKER_2", "transcription": "How are you?", "start_time": 3.0, "end_time": 4.5}]}}}

            with patch("requests.post") as mock_post, patch("requests.get") as mock_get, patch("app.utils.inference.settings") as mock_settings:
                # Mock settings
                mock_settings.TRANSCRIBE_API_BASE_URL = "https://api.test.com"

                # Mock initial POST request
                mock_post_response = Mock()
                mock_post_response.status_code = 200
                mock_post_response.json.return_value = {"success": True, "data": {"task_id": "test_task_123"}}
                mock_post.return_value = mock_post_response

                # Mock polling GET requests
                mock_get_response = Mock()
                mock_get_response.status_code = 200
                mock_get_response.json.side_effect = [{"success": True, "data": {"status": "processing"}}, {"success": True, "data": {"status": "completed", "results": mock_response_data["data"]["results"]}}]
                mock_get.return_value = mock_get_response

                result = transcriber(temp_audio_path)

                # Verify the result format
                assert "SPEAKER_1 [0.00s - 2.50s]: Hello world" in result
                assert "SPEAKER_2 [3.00s - 4.50s]: How are you?" in result

                # Verify API calls
                assert mock_post.call_count == 1
                assert mock_get.call_count == 2

        finally:
            # Clean up temp file
            os.unlink(temp_audio_path)

    def test_transcriber_api_submit_failure(self):
        """Test transcription failure during API submission"""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_file.write(b"fake audio data")
            temp_audio_path = temp_file.name

        try:
            with patch("requests.post") as mock_post, patch("app.utils.inference.settings") as mock_settings:
                mock_settings.TRANSCRIBE_API_BASE_URL = "https://api.test.com"

                mock_response = Mock()
                mock_response.status_code = 500
                mock_response.text = "Internal Server Error"
                mock_post.return_value = mock_response

                with pytest.raises(Exception, match="Failed to submit transcription"):
                    transcriber(temp_audio_path)

        finally:
            os.unlink(temp_audio_path)

    def test_transcriber_api_response_failure(self):
        """Test transcription failure due to API response indicating failure"""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_file.write(b"fake audio data")
            temp_audio_path = temp_file.name

        try:
            with patch("requests.post") as mock_post, patch("app.utils.inference.settings") as mock_settings:
                mock_settings.TRANSCRIBE_API_BASE_URL = "https://api.test.com"

                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"success": False, "message": "Invalid audio format"}
                mock_post.return_value = mock_response

                with pytest.raises(Exception, match="API error: Invalid audio format"):
                    transcriber(temp_audio_path)

        finally:
            os.unlink(temp_audio_path)

    def test_transcriber_polling_timeout(self):
        """Test transcription polling timeout"""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_file.write(b"fake audio data")
            temp_audio_path = temp_file.name

        try:
            with patch("requests.post") as mock_post, patch("requests.get") as mock_get, patch("app.utils.inference.settings") as mock_settings, patch("time.sleep") as mock_sleep:
                mock_settings.TRANSCRIBE_API_BASE_URL = "https://api.test.com"

                # Mock initial POST
                mock_post_response = Mock()
                mock_post_response.status_code = 200
                mock_post_response.json.return_value = {"success": True, "data": {"task_id": "test_task_123"}}
                mock_post.return_value = mock_post_response

                # Mock GET to always return processing
                mock_get_response = Mock()
                mock_get_response.status_code = 200
                mock_get_response.json.return_value = {"success": True, "data": {"status": "processing"}}
                mock_get.return_value = mock_get_response

                with pytest.raises(Exception, match="Transcription polling timed out"):
                    transcriber(temp_audio_path)

                # Should have polled max times
                assert mock_get.call_count == 120

        finally:
            os.unlink(temp_audio_path)

    def test_transcriber_processing_failure(self):
        """Test transcription failure during processing"""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_file.write(b"fake audio data")
            temp_audio_path = temp_file.name

        try:
            with patch("requests.post") as mock_post, patch("requests.get") as mock_get, patch("app.utils.inference.settings") as mock_settings:
                mock_settings.TRANSCRIBE_API_BASE_URL = "https://api.test.com"

                # Mock initial POST
                mock_post_response = Mock()
                mock_post_response.status_code = 200
                mock_post_response.json.return_value = {"success": True, "data": {"task_id": "test_task_123"}}
                mock_post.return_value = mock_post_response

                # Mock GET to return failure
                mock_get_response = Mock()
                mock_get_response.status_code = 200
                mock_get_response.json.return_value = {"success": True, "data": {"status": "failed", "error": "Audio processing failed"}}
                mock_get.return_value = mock_get_response

                with pytest.raises(Exception, match="Transcription failed: Audio processing failed"):
                    transcriber(temp_audio_path)

        finally:
            os.unlink(temp_audio_path)

    def test_transcriber_polling_api_error(self):
        """Test transcription polling API error"""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_file.write(b"fake audio data")
            temp_audio_path = temp_file.name

        try:
            with patch("requests.post") as mock_post, patch("requests.get") as mock_get, patch("app.utils.inference.settings") as mock_settings:
                mock_settings.TRANSCRIBE_API_BASE_URL = "https://api.test.com"

                # Mock initial POST
                mock_post_response = Mock()
                mock_post_response.status_code = 200
                mock_post_response.json.return_value = {"success": True, "data": {"task_id": "test_task_123"}}
                mock_post.return_value = mock_post_response

                # Mock GET to return API error
                mock_get_response = Mock()
                mock_get_response.status_code = 500
                mock_get_response.text = "Internal Server Error"
                mock_get.return_value = mock_get_response

                with pytest.raises(Exception, match="Failed to poll transcription status"):
                    transcriber(temp_audio_path)

        finally:
            os.unlink(temp_audio_path)

    def test_transcriber_polling_response_error(self):
        """Test transcription polling response error"""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_file.write(b"fake audio data")
            temp_audio_path = temp_file.name

        try:
            with patch("requests.post") as mock_post, patch("requests.get") as mock_get, patch("app.utils.inference.settings") as mock_settings:
                mock_settings.TRANSCRIBE_API_BASE_URL = "https://api.test.com"

                # Mock initial POST
                mock_post_response = Mock()
                mock_post_response.status_code = 200
                mock_post_response.json.return_value = {"success": True, "data": {"task_id": "test_task_123"}}
                mock_post.return_value = mock_post_response

                # Mock GET to return response error
                mock_get_response = Mock()
                mock_get_response.status_code = 200
                mock_get_response.json.return_value = {"success": False, "message": "Task not found"}
                mock_get.return_value = mock_get_response

                with pytest.raises(Exception, match="API polling error: Task not found"):
                    transcriber(temp_audio_path)

        finally:
            os.unlink(temp_audio_path)

    def test_transcriber_no_transcriptions(self):
        """Test transcription with no transcription results"""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_file.write(b"fake audio data")
            temp_audio_path = temp_file.name

        try:
            with patch("requests.post") as mock_post, patch("requests.get") as mock_get, patch("app.utils.inference.settings") as mock_settings:
                mock_settings.TRANSCRIBE_API_BASE_URL = "https://api.test.com"

                # Mock initial POST
                mock_post_response = Mock()
                mock_post_response.status_code = 200
                mock_post_response.json.return_value = {"success": True, "data": {"task_id": "test_task_123"}}
                mock_post.return_value = mock_post_response

                # Mock GET to return success with empty transcriptions
                mock_get_response = Mock()
                mock_get_response.status_code = 200
                mock_get_response.json.return_value = {"success": True, "data": {"status": "completed", "results": {"transcriptions": []}}}
                mock_get.return_value = mock_get_response

                result = transcriber(temp_audio_path)

                assert result == "No transcription available"

        finally:
            os.unlink(temp_audio_path)

    def test_transcriber_single_transcription(self):
        """Test transcription with single transcription result"""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_file.write(b"fake audio data")
            temp_audio_path = temp_file.name

        try:
            with patch("requests.post") as mock_post, patch("requests.get") as mock_get, patch("app.utils.inference.settings") as mock_settings:
                mock_settings.TRANSCRIBE_API_BASE_URL = "https://api.test.com"

                # Mock initial POST
                mock_post_response = Mock()
                mock_post_response.status_code = 200
                mock_post_response.json.return_value = {"success": True, "data": {"task_id": "test_task_123"}}
                mock_post.return_value = mock_post_response

                # Mock GET to return single transcription
                mock_get_response = Mock()
                mock_get_response.status_code = 200
                mock_get_response.json.return_value = {"success": True, "data": {"status": "completed", "results": {"transcriptions": [{"speaker": "SPEAKER_1", "transcription": "This is a test transcription.", "start_time": 1.5, "end_time": 4.2}]}}}
                mock_get.return_value = mock_get_response

                result = transcriber(temp_audio_path)

                expected = "SPEAKER_1 [1.50s - 4.20s]: This is a test transcription."
                assert result == expected

        finally:
            os.unlink(temp_audio_path)

    def test_transcriber_missing_fields(self):
        """Test transcription with missing fields in transcription data"""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_file.write(b"fake audio data")
            temp_audio_path = temp_file.name

        try:
            with patch("requests.post") as mock_post, patch("requests.get") as mock_get, patch("app.utils.inference.settings") as mock_settings:
                mock_settings.TRANSCRIBE_API_BASE_URL = "https://api.test.com"

                # Mock initial POST
                mock_post_response = Mock()
                mock_post_response.status_code = 200
                mock_post_response.json.return_value = {"success": True, "data": {"task_id": "test_task_123"}}
                mock_post.return_value = mock_post_response

                # Mock GET with missing fields
                mock_get_response = Mock()
                mock_get_response.status_code = 200
                mock_get_response.json.return_value = {
                    "success": True,
                    "data": {
                        "status": "completed",
                        "results": {
                            "transcriptions": [
                                {
                                    "transcription": "Missing speaker and times",
                                    # Missing speaker, start_time, end_time
                                }
                            ]
                        },
                    },
                }
                mock_get.return_value = mock_get_response

                result = transcriber(temp_audio_path)

                # Should handle missing fields gracefully
                assert "UNKNOWN [0.00s - 0.00s]: Missing speaker and times" in result

        finally:
            os.unlink(temp_audio_path)
