from app.events.base import BaseListener
from app.events.project_events import UserAddedToProjectEvent, UserRemovedFromProjectEvent
from app.models.project import Project
from app.services.notification import create_notifications_bulk, send_fcm_notification
from app.services.project import get_project_members
from app.services.user import get_user_by_id


class NotificationListener(BaseListener):
    def handle(self, event):
        if isinstance(event, UserAddedToProjectEvent):
            self._handle_user_added(event)
        elif isinstance(event, UserRemovedFromProjectEvent):
            self._handle_user_removed(event)

    def _handle_user_added(self, event: UserAddedToProjectEvent):
        try:
            db = event.db
            project = db.query(Project).filter(Project.id == event.project_id).first()
            if not project:
                return

            added_user = get_user_by_id(db, event.user_id)
            added_by_user = get_user_by_id(db, event.added_by_user_id)

            if not added_user or not added_by_user:
                return

            members = get_project_members(db, event.project_id)

            # 1. Notify other members
            other_member_ids = [m.user_id for m in members if m.user_id != event.user_id]

            if other_member_ids:
                notification_data = {
                    "type": "user_joined_project",
                    "payload": {
                        "event_type": "user_joined_project",
                        "project_id": str(event.project_id),
                        "project_name": project.name,
                        "user_id": str(event.user_id),
                        "user_name": added_user.name or added_user.email,
                    },
                    "channel": "in_app",
                }

                create_notifications_bulk(db, other_member_ids, **notification_data)

                send_fcm_notification(
                    other_member_ids,
                    "user_joined_project",
                    f"{added_user.name or added_user.email}",
                    notification_data["payload"],
                )

            # 2. Notify added user
            added_notification_data = {
                "type": "added_to_project",
                "payload": {
                    "event_type": "added_to_project",
                    "project_id": str(event.project_id),
                    "project_name": project.name,
                    "added_by_id": str(event.added_by_user_id),
                    "added_by_name": added_by_user.name or added_by_user.email,
                },
                "channel": "in_app",
            }

            create_notifications_bulk(db, [event.user_id], **added_notification_data)

            send_fcm_notification(
                [event.user_id],
                "added_to_project",
                f"{added_by_user.name or added_by_user.email}",
                added_notification_data["payload"],
            )

        except Exception:
            pass

    def _handle_user_removed(self, event: UserRemovedFromProjectEvent):
        try:
            db = event.db
            project = db.query(Project).filter(Project.id == event.project_id).first()
            if not project:
                return

            removed_user = get_user_by_id(db, event.user_id)
            removed_by_user = get_user_by_id(db, event.removed_by_user_id)

            if not removed_user or not removed_by_user:
                return

            members = get_project_members(db, event.project_id)

            # 1. Notify remaining members
            remaining_member_ids = [m.user_id for m in members if m.user_id != event.user_id]

            if remaining_member_ids:
                notification_data = {
                    "type": "user_removed_project",
                    "payload": {
                        "event_type": "user_removed_project",
                        "project_id": str(event.project_id),
                        "project_name": project.name,
                        "user_id": str(event.user_id),
                        "user_name": removed_user.name or removed_user.email,
                        "is_self_removal": event.is_self_removal,
                    },
                    "channel": "in_app",
                }

                create_notifications_bulk(db, remaining_member_ids, **notification_data)

                send_fcm_notification(
                    remaining_member_ids,
                    "user_removed_project",
                    f"{removed_user.name or removed_user.email}",
                    notification_data["payload"],
                )

            # 2. Notify removed user (if removed by admin, not self-removal)
            if not event.is_self_removal:
                removed_notification_data = {
                    "type": "removed_from_project",
                    "payload": {
                        "event_type": "removed_from_project",
                        "project_id": str(event.project_id),
                        "project_name": project.name,
                        "removed_by_id": str(event.removed_by_user_id),
                        "removed_by_name": removed_by_user.name or removed_by_user.email,
                    },
                    "channel": "in_app",
                }

                create_notifications_bulk(db, [event.user_id], **removed_notification_data)

                send_fcm_notification(
                    [event.user_id],
                    "removed_from_project",
                    f"{project.name}",
                    removed_notification_data["payload"],
                )


        except Exception:
            pass
