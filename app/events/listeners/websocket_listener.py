import asyncio

from app.events.base import BaseListener
from app.events.project_events import UserAddedToProjectEvent, UserRemovedFromProjectEvent
from app.services.project import get_project_members
from app.utils.redis import publish_to_user_channel


class WebSocketListener(BaseListener):
    def __init__(self):
        super().__init__()

    def handle(self, event):
        event_type = type(event).__name__

        try:
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            if isinstance(event, UserAddedToProjectEvent):
                loop.run_until_complete(self._handle_user_added(event))
            elif isinstance(event, UserRemovedFromProjectEvent):
                loop.run_until_complete(self._handle_user_removed(event))
        except Exception as e:
            print(f"{self.colors.RED}[WebSocketListener] Error handling event {event_type}: {str(e)}{self.colors.RESET}")

    async def _handle_user_added(self, event: UserAddedToProjectEvent):
        try:
            db = event.db
            members = get_project_members(db, event.project_id)

            message = {
                "type": "user_joined",
                "data": {"project_id": str(event.project_id), "user_id": str(event.user_id)},
            }

            confirmation_message = {
                "type": "you_added_to_project",
                "data": {"project_id": str(event.project_id), "added_by_user_id": str(event.added_by_user_id), "message": f"You were added to project {event.project_id}"},
            }

            await publish_to_user_channel(str(event.user_id), confirmation_message)

            for member in members:
                if member.user_id != event.user_id:
                    member_id = str(member.user_id)

                    await publish_to_user_channel(member_id, message)

        except Exception:
            pass

    async def _handle_user_removed(self, event: UserRemovedFromProjectEvent):
        try:
            db = event.db
            members = get_project_members(db, event.project_id)

            message = {
                "type": "user_removed",
                "data": {"project_id": str(event.project_id), "user_id": str(event.user_id), "is_self_removal": event.is_self_removal},
            }

            removal_confirmation_message = {
                "type": "you_removed_from_project",
                "data": {"project_id": str(event.project_id), "removed_by_user_id": str(event.removed_by_user_id), "is_self_removal": event.is_self_removal, "message": f"You were removed from project {event.project_id}" if not event.is_self_removal else f"You left project {event.project_id}"},
            }

            await publish_to_user_channel(str(event.user_id), removal_confirmation_message)

            for member in members:
                member_id = str(member.user_id)

                await publish_to_user_channel(member_id, message)

        except Exception:
            pass
