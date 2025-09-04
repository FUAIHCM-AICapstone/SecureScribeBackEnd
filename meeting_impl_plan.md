Implementation Plan for Meeting CRUD
Tôi sẽ implement theo approach A (Service-first design) với minimal code style từ codingrule.md:
Phase 1: Model Enhancement
File: app/models/meeting.py
Thêm status enum: active, cancelled, completed
Thêm is_deleted field cho soft delete
Update existing Meeting model
Phase 2: Schema Design
File: app/schemas/meeting.py (new)
MeetingCreate: project_ids, title, description, url, start_time, is_personal
MeetingUpdate: partial fields với Optional
MeetingFilter: flexible kwargs + tag filtering
MeetingResponse: include project info, access status (tham khảo user.py pattern)
Phase 3: Utility Functions
File: app/utils/meeting.py (new)
validate_meeting_url(): #TODO placeholder
check_meeting_access(): personal vs project logic
get_meeting_projects(): helper cho project relationships
notify_meeting_members(): notification helper
Phase 4: Service Layer
File: app/services/meeting.py (new)
create_meeting(): business logic với project linking
get_meeting(): access control check
get_meetings(): pagination + filtering với kwargs
update_meeting(): partial update + notifications
delete_meeting(): soft delete với permission check
add_meeting_to_project(): relationship management
remove_meeting_from_project(): relationship management
Phase 5: API Endpoints
File: app/api/endpoints/meeting.py (new)
Standard CRUD: /meetings/ với pagination
Project-specific: /projects/{project_id}/meetings/
Tag filtering: ?tag_ids=uuid1,uuid2
Flexible filtering: kwargs support
Phase 6: Dependencies
File: app/api/dependencies/meeting.py (new)
get_meeting_or_404(): dependency injection
check_meeting_permissions(): access control dependency
validate_meeting_data(): data validation dependency
Implementation Checklist:
Model Enhancement
[ ] Add status enum to Meeting model
[ ] Add is_deleted field to Meeting model
[ ] Update database schema
Schema Creation
[ ] Create MeetingCreate schema with project_ids
[ ] Create MeetingUpdate schema with partial fields
[ ] Create MeetingFilter schema with kwargs
[ ] Create MeetingResponse schema with project info
[ ] Create MeetingWithProjects schema for detailed response
Utility Functions
[ ] Create validate_meeting_url() placeholder
[ ] Create check_meeting_access() function
[ ] Create get_meeting_projects() helper
[ ] Create notify_meeting_members() function
Service Functions
[ ] Implement create_meeting() with project linking
[ ] Implement get_meeting() with access control
[ ] Implement get_meetings() with flexible filtering
[ ] Implement update_meeting() with notifications
[ ] Implement delete_meeting() with permission check
[ ] Implement relationship management functions
API Endpoints
[ ] Create standard CRUD endpoints (/meetings/)
[ ] Create project-specific endpoints (/projects/{project_id}/meetings/)
[ ] Implement tag filtering (?tag_ids=...)
[ ] Implement flexible filtering support
Dependencies
[ ] Create get_meeting_or_404() dependency
[ ] Create check_meeting_permissions() dependency
[ ] Create validate_meeting_data() dependency
Error Handling
[ ] Add proper HTTPException handling
[ ] Add permission error messages
[ ] Add validation error messages
Testing
[ ] Test all CRUD operations
[ ] Test access control logic
[ ] Test notification integration
[ ] Test relationship management