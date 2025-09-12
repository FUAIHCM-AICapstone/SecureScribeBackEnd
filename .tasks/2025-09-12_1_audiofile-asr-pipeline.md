# Context
File name: 2025-09-12_1_audiofile-asr-pipeline.md
Created at: 2025-09-12_00:00:00
Created by: AI Assistant
Main branch: main
Task Branch: task/audiofile-asr-pipeline_2025-09-12_1
Yolo Mode: Off

# Task Description
Thiết kế và triển khai flow AudioFile cho Meeting:
- CRUD AudioFile
- Upload audio → lưu MinIO → tạo record `audio_files`
- Kích hoạt job ASR (giai đoạn này mock transcript) bằng Celery
- Report tiến độ qua Redis/WebSocket (`task_progress.py`/`websocket_manager.py`)
- Lưu kết quả vào bảng `transcripts` (1:1 với meeting), cập nhật `audio_concat_file_id` khi cần (tạm thời bỏ qua concat)

# Project Overview
SecureScribe là hệ thống quản lý meeting/file với FastAPI, PostgreSQL (SQLModel), MinIO, Redis, Qdrant. Flow mong muốn: audio được upload và xử lý nền, tiến độ hiển thị real-time, kết quả transcript lưu DB và (nếu bật) được index để search/RAG.

⚠️ WARNING: NEVER MODIFY THIS SECTION ⚠️
Core protocol rules: Follow strict mode-based workflow (RESEARCH -> INNOVATE -> PLAN -> EXECUTE -> REVIEW). No unauthorized changes. Always get user confirmation before proceeding to next mode.
⚠️ WARNING: NEVER MODIFY THIS SECTION ⚠️

# Analysis
- Models đã có: `AudioFile`, `Transcript`, `Meeting` trong `app/models/meeting.py`.
- MinIO utils đã có (`app/utils/minio.py`), Redis/WebSocket đã có (`app/utils/redis.py`, `app/services/websocket_manager.py`).
- Celery worker đã cấu hình (`app/jobs/celery_worker.py`), có ví dụ tiến độ với `task_progress.py`.
- Chưa thấy endpoint CRUD cho `AudioFile` và pipeline xử lý ASR → Transcript.
- ASR giai đoạn này sẽ mock nội dung, nhưng vẫn cần task Celery để minh họa tiến độ/end-to-end.

# Proposed Solution

# Current execution step: "1. Create the task file"

# Task Progress

# Final Review:


