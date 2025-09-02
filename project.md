# Project Context

* User có thể tham gia nhiều project và mỗi record user lưu `id`, `email`, `name`, `avatar_url`, `bio`, `position`, `created_at`, `updated_at`.
* Hỗ trợ đa identity: bảng `user_identities` lưu `provider`, `provider_user_id`, `provider_email`, `provider_profile`, `tenant_id`, `created_at`, `updated_at` với unique (provider, provider\_user\_id) để map nhiều external login vào 1 user.
* Quản lý đa thiết bị: bảng `user_devices` lưu `user_id`, `device_name`, `device_type`, `fcm_token`, `last_active_at`, `is_active`, `created_at`, `updated_at` để gửi push và revoke token khi cần.
* Project có `id`, `name`, `description`, `is_archived`, `created_by`, `created_at`, `updated_at` và user join project qua `users_projects` (composite PK user\_id+project\_id) kèm `role` enum {admin, member} và `joined_at`.
* Quyền project đơn giản: admin chỉ khác ở chức năng quản lý member; guest/external user không quản lý trong hệ thống.
* Meeting có `id`, `title`, `description`, `url` (meeting link), `start_time`, `created_by`, `is_personal`, `created_at`, `updated_at`; meeting có thể độc lập hoặc liên kết nhiều project qua `projects_meetings` (composite PK).
* Khi meeting share giữa nhiều project, tất cả user thuộc các project liên kết sẽ có quyền view & edit meeting note—quyền kiểm soát thực thi ở service layer.
* Mỗi meeting có duy nhất một transcript (bảng `transcripts` với meeting\_id unique) chứa `content`/`transcript_text`, `diarization_json`, `audio_concat_file_id`, `extracted_text_for_search`, `qdrant_vector_id`, `created_at`, `updated_at`.
* Transcript tạo từ nhiều audio part: bảng `audio_files` lưu `meeting_id`, `uploaded_by`, `file_url`, `seq_order`, `duration_seconds`, `is_concatenated`, `created_at`; khi meeting kết thúc tạo file concat (`is_concatenated=true`) và tham chiếu trong transcript để giảm lưu trữ.
* Speaker diarization lưu dạng text/JSON trong `transcripts.diarization_json` và không map trực tiếp tới user hệ thống.
* Mỗi meeting có duy nhất một meeting note (bảng `meeting_notes` với meeting\_id unique) lưu `content` (text/json), `last_editor_id`, `last_edited_at`, `created_at`, `updated_at`.
* Meeting note: tất cả user trong các project liên kết có quyền view & edit; last\_editor lưu id user chỉnh sửa cuối cùng.
* Không lưu attendance join/leave; hệ thống chỉ giữ danh sách liên kết user↔meeting qua project membership hoặc explicit linking nếu cần.
* Meeting chỉ lưu URL (online); không cần quản lý địa điểm offline; hỗ trợ tạo meeting từ UI hoặc dùng URL do user nhập; nếu user nhập URL mới thì tạo record meeting mới trước khi bot join.
* Meeting hỗ trợ tagging: bảng `tags` + `meeting_tags` lưu `name`, `scope` và mapping để phân loại (kickoff, weekly, retro, keyword).
* Task model: bảng `tasks` lưu `title`, `description`, `creator_id`, `assignee_id`, `status` enum {todo,in\_progress,done}, `meeting_id` (nullable), `due_date`, `reminder_at`, `created_at`, `updated_at`.
* Task có thể thuộc nhiều project qua `tasks_projects` (composite PK task\_id+project\_id) để xử lý trường hợp meeting thuộc nhiều project; nếu meeting không thuộc project thì task chỉ liên kết trực tiếp tới meeting.
* Task behavior: người tạo và assignee phải là user hệ thống; có deadline và reminder; cập nhật status cho phép workflow cơ bản.
* File context hợp nhất: bảng `files` lưu `filename`, `mime_type`, `size_bytes`, `storage_url`, `file_type` enum {project,meeting,user}, `project_id`, `meeting_id`, `uploaded_by`, `extracted_text`, `qdrant_vector_id`, `created_at`; quy tắc ứng dụng đảm bảo field liên quan không null tùy `file_type`.
* File context không versioning—chỉ giữ bản mới nhất; nếu muốn versioning phải thêm bảng version riêng (không bật mặc định).
* File access inheritance: file quyền kế thừa từ project hoặc meeting (không có ACL per-file mặc định); nếu cần quyền từng file phải mở rộng logic quyền.
* File indexing & search: `files.extracted_text` và bảng `search_documents` hợp nhất nội dung để full-text search; semantic vectors lưu trên Qdrant với `qdrant_vector_id` tham chiếu trong `files`/`transcripts`/`search_documents`.
* `search_documents` lưu `owner_type`, `owner_id`, `content_text`, `qdrant_vector_id`, `indexed_at` để làm chỉ mục cho AI/RAG.
* Notification system lưu bản ghi trong `notifications` với `user_id`, `type`, `payload`, `is_read`, `channel` enum {in\_app,email,push}, `created_at` và gửi thực tế qua email service hoặc FCM lấy token từ `user_devices`.
* Triggers notification: task reminders, bot join/success/fail, file upload, meeting created/updated; hệ thống có thể hỗ trợ both in-app & email & push channels.
* Audit log cơ bản: bảng `audit_logs` lưu `actor_user_id`, `action` (ví dụ meeting.created,file.uploaded,task.assigned,bot.event), `target_type`, `target_id`, `metadata`, `created_at` để tra cứu và compliance.
* Integrations: bảng `integrations` lưu cấu hình sync calendar per project (`type` enum google\_calendar|outlook, `credentials_meta` encrypted/json, `created_at`); không lưu secret raw nếu không mã hoá—khuyến nghị lưu ref đến Key Vault.
* Bot feature: bảng `meeting_bots` lưu `meeting_id`, `scheduled_start_time`, `actual_start_time`, `actual_end_time`, `status` enum {pending,joining,joined,recording,ended,failed\_to\_join,cancelled}, `meeting_url`, `retry_count`, `last_error`, `created_by`, `created_at`, `updated_at`.
* Bot lifecycle logging: bảng `meeting_bot_logs` lưu `meeting_bot_id`, `action` (scheduled,attempt\_join,joined,recording\_started,failed,ended), `message`, `created_at` để UI hiển thị timeline và debug.
* Bot behavior: mỗi bot session join một meeting tại một thời điểm; có thể có nhiều bot sessions cho cùng meeting (retry); nếu join fail chuyển status `failed_to_join` và chờ retry thủ công.
* Audio do bot tạo sẽ lưu vào `audio_files` và đánh dấu `recorded_by_bot=true` để phân biệt với user-uploaded audio.
* Khi bot upload audio, process sẽ tạo/append transcript; cuối meeting hệ thống thực hiện concatenation audio parts và cập nhật `transcripts.audio_concat_file_id`.
* Transcripts và meeting\_notes là 1:1 với meetings; enforce uniqueness trên `transcripts.meeting_id` và `meeting_notes.meeting_id`.
* Indexing pipeline: khi file/transcript/note thay đổi, push `content_text` vào `search_documents` và gửi vectorization job đến Qdrant; lưu `qdrant_vector_id` trả về để liên kết.
* Quy tắc xóa/archive: khi project archived `is_archived=true` dữ liệu vẫn giữ nguyên; không auto delete file/transcript/notes; xóa vật lý cần policy riêng.
* Database constraints chính: composite PK cho `users_projects`, `projects_meetings`, `meeting_tags`, `tasks_projects`; FK ràng buộc giữa tất cả bảng liên quan; unique constraints cho `users.email` (tùy chọn), `user_identities(provider,provider_user_id)`, `transcripts.meeting_id`, `meeting_notes.meeting_id`.
* Index khuyến nghị: index `user_devices.fcm_token`, `files.project_id`, `files.meeting_id`, `transcripts.qdrant_vector_id`, `search_documents.owner_type,owner_id` để truy vấn nhanh; index thời gian cho các bảng lịch và log.
* Không lưu attendance/participant join/leave timeline; nếu cần sau này thêm bảng `meeting_participants` với join/leave timestamps.
* Không quản lý guest/external account; chỉ quản lý users đã đăng ký trong DB; nếu muốn guest support phải mở rộng `users`/`user_identities` logic.
* Security & secrets: không lưu client\_secret/refresh\_token raw trong DB; dùng Azure Key Vault hoặc encrypted `credentials_meta` trong `integrations`.
* GDPR/retention: phải có policy cho purge `provider_profile`/`provider_email`/raw profile JSON nếu yêu cầu; log retention chính sách cần định nghĩa.
* API behavior & service-layer rules: quyền truy cập file/note/transcript được kiểm tra bằng service logic dựa trên project membership và `projects_meetings` liên kết; UI hiển thị quyền edit dựa trên đó.
* Scheduler & job queue: bot scheduler có thể quét `meeting_bots` theo `scheduled_start_time` để dispatch jobs; có thể thêm job queue table nếu cần reliability.
* Retry semantics: `meeting_bots.retry_count` tăng khi user yêu cầu retry; hệ thống không auto retry sau failed\_to\_join trừ khi user trigger.
* Notification delivery: khi gửi push, lookup `user_devices` với `is_active=true` và gửi FCM đến `fcm_token`; khi token invalid mark `is_active=false` và ghi audit log.
* Client responsibilities: client gửi `device_name` + `device_type` + `fcm_token` để upsert `user_devices` khi login; client chịu trách nhiệm refresh token khi thay đổi.
* Task reminders: scheduler đọc `tasks.reminder_at` để gửi `notifications` và email; reminder và due\_date có timezone handling theo project/user preference.
* UI surfaces: UI cần endpoint để xem `meeting_bots` status timeline (dựa trên `meeting_bot_logs`), trigger retry/cancel, start/stop recording manually if allowed.
* Reporting & analytics: có thể aggregate `audit_logs` + `meeting_bots` + `tasks` để thống kê meeting count, recording success rate, task completion rate per project.
* Backup & storage: `storage_url` cho files nên trỏ tới object storage (S3/GCS) với lifecycle policy; audio concat lớn lưu tạm và cleanup theo policy.
* Observability: instrument bot join/record/upload with logs and metrics; store last\_error và timestamps trong `meeting_bots` để debug nhanh.
