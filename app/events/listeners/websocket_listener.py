import asyncio
import time

from app.events.base import BaseListener
from app.events.project_events import UserAddedToProjectEvent, UserRemovedFromProjectEvent
from app.services.project import get_project_members
from app.utils.redis import publish_to_user_channel


# ANSI color codes for colorful logging
class Colors:
    RESET = "\033[0m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BOLD = "\033[1m"


class WebSocketListener(BaseListener):
    def __init__(self):
        self.colors = Colors()
        print(f"{self.colors.CYAN}[WebSocketListener]{self.colors.RESET} {self.colors.GREEN}Initialized WebSocket event listener{self.colors.RESET}")

    def handle(self, event):
        start_time = time.time()
        event_type = type(event).__name__

        print(f"{self.colors.CYAN}[WebSocketListener]{self.colors.RESET} {self.colors.BLUE}▶ Processing event:{self.colors.RESET} {self.colors.BOLD}{event_type}{self.colors.RESET}")

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
            else:
                print(f"{self.colors.CYAN}[WebSocketListener]{self.colors.RESET} {self.colors.YELLOW}⚠ Unhandled event type:{self.colors.RESET} {event_type}")
        except Exception as e:
            print(f"{self.colors.CYAN}[WebSocketListener]{self.colors.RESET} {self.colors.RED}✗ Error in handle: {e}{self.colors.RESET}")
            print(f"{self.colors.CYAN}[WebSocketListener]{self.colors.RESET} {self.colors.RED}   └─ Error type: {type(e).__name__}{self.colors.RESET}")

        processing_time = time.time() - start_time
        print(f"{self.colors.CYAN}[WebSocketListener]{self.colors.RESET} {self.colors.GREEN}✓ Event processing completed in {processing_time:.3f}s{self.colors.RESET}")

    async def _handle_user_added(self, event: UserAddedToProjectEvent):
        start_time = time.time()
        print(f"{self.colors.CYAN}[WebSocketListener]{self.colors.RESET} {self.colors.MAGENTA}👤 Handling UserAddedToProjectEvent{self.colors.RESET}")
        print(f"{self.colors.CYAN}[WebSocketListener]{self.colors.RESET} {self.colors.BLUE}   └─ Project ID:{self.colors.RESET} {event.project_id}")
        print(f"{self.colors.CYAN}[WebSocketListener]{self.colors.RESET} {self.colors.BLUE}   └─ User ID:{self.colors.RESET} {event.user_id}")

        try:
            print(f"{self.colors.CYAN}[WebSocketListener]{self.colors.RESET} {self.colors.MAGENTA}📡 Starting Redis publishing for user addition{self.colors.RESET}")
            print(f"{self.colors.CYAN}[WebSocketListener]{self.colors.RESET} {self.colors.BLUE}   └─ Event details: Project {event.project_id}, User {event.user_id}{self.colors.RESET}")

            print(f"{self.colors.CYAN}[WebSocketListener]{self.colors.RESET} {self.colors.BLUE}   ┌─ Fetching project members from database...{self.colors.RESET}")
            db = event.db
            members = get_project_members(db, event.project_id)
            member_count = len(members)
            print(f"{self.colors.CYAN}[WebSocketListener]{self.colors.RESET} {self.colors.GREEN}   └─ ✓ Found {member_count} project members{self.colors.RESET}")

            message = {
                "type": "user_joined",
                "data": {"project_id": str(event.project_id), "user_id": str(event.user_id)},
            }
            print(f"{self.colors.CYAN}[WebSocketListener]{self.colors.RESET} {self.colors.BLUE}   ┌─ Prepared message: {message}{self.colors.RESET}")

            confirmation_message = {
                "type": "you_added_to_project",
                "data": {
                    "project_id": str(event.project_id),
                    "added_by_user_id": str(event.added_by_user_id),
                    "message": f"You were added to project {event.project_id}"
                },
            }
            print(f"{self.colors.CYAN}[WebSocketListener]{self.colors.RESET} {self.colors.BLUE}   ┌─ Prepared confirmation message for added user: {confirmation_message}{self.colors.RESET}")

            print(f"{self.colors.CYAN}[WebSocketListener]{self.colors.RESET} {self.colors.BLUE}   ┌─ Publishing confirmation to added user {event.user_id}...{self.colors.RESET}", end="")
            publish_start = time.time()
            confirm_success = await publish_to_user_channel(str(event.user_id), confirmation_message)
            confirm_time = time.time() - publish_start
            if confirm_success:
                print(f" {self.colors.GREEN}✓ ({confirm_time:.3f}s){self.colors.RESET}")
            else:
                print(f" {self.colors.RED}✗ ({confirm_time:.3f}s){self.colors.RESET}")
                print(f"{self.colors.CYAN}[WebSocketListener]{self.colors.RESET} {self.colors.RED}   │       └─ Failed to publish confirmation to added user {event.user_id}{self.colors.RESET}")

            print(f"{self.colors.CYAN}[WebSocketListener]{self.colors.RESET} {self.colors.BLUE}   ┌─ Publishing to {member_count} members (excluding sender)...{self.colors.RESET}")

            success_count = 0
            failure_count = 0

            for i, member in enumerate(members, 1):
                if member.user_id != event.user_id:
                    member_id = str(member.user_id)
                    print(f"{self.colors.CYAN}[WebSocketListener]{self.colors.RESET} {self.colors.BLUE}   │   [{i}/{member_count - 1}] Publishing to user {member_id}...{self.colors.RESET}", end="")

                    publish_start = time.time()
                    success = await publish_to_user_channel(member_id, message)
                    publish_time = time.time() - publish_start

                    if success:
                        success_count += 1
                        print(f" {self.colors.GREEN}✓ ({publish_time:.3f}s){self.colors.RESET}")
                    else:
                        failure_count += 1
                        print(f" {self.colors.RED}✗ ({publish_time:.3f}s){self.colors.RESET}")
                        print(f"{self.colors.CYAN}[WebSocketListener]{self.colors.RESET} {self.colors.RED}   │       └─ Failed to publish to user {member_id}{self.colors.RESET}")

            total_time = time.time() - start_time
            print(f"{self.colors.CYAN}[WebSocketListener]{self.colors.RESET} {self.colors.GREEN}✓ Redis publishing completed in {total_time:.3f}s{self.colors.RESET}")
            print(f"{self.colors.CYAN}[WebSocketListener]{self.colors.RESET} {self.colors.GREEN}   └─ Success: {success_count}, Failures: {failure_count}{self.colors.RESET}")

        except Exception as e:
            total_time = time.time() - start_time
            print(f"{self.colors.CYAN}[WebSocketListener]{self.colors.RESET} {self.colors.RED}✗ Redis publishing failed after {total_time:.3f}s{self.colors.RESET}")
            print(f"{self.colors.CYAN}[WebSocketListener]{self.colors.RESET} {self.colors.RED}   └─ Error: {e}{self.colors.RESET}")
            print(f"{self.colors.CYAN}[WebSocketListener]{self.colors.RESET} {self.colors.RED}   └─ Error type: {type(e).__name__}{self.colors.RESET}")

    async def _handle_user_removed(self, event: UserRemovedFromProjectEvent):
        start_time = time.time()
        removal_type = "self-removal" if event.is_self_removal else "admin removal"
        print(f"{self.colors.CYAN}[WebSocketListener]{self.colors.RESET} {self.colors.MAGENTA}👤 Handling UserRemovedFromProjectEvent ({removal_type}){self.colors.RESET}")
        print(f"{self.colors.CYAN}[WebSocketListener]{self.colors.RESET} {self.colors.BLUE}   └─ Project ID:{self.colors.RESET} {event.project_id}")
        print(f"{self.colors.CYAN}[WebSocketListener]{self.colors.RESET} {self.colors.BLUE}   └─ User ID:{self.colors.RESET} {event.user_id}")
        print(f"{self.colors.CYAN}[WebSocketListener]{self.colors.RESET} {self.colors.BLUE}   └─ Self removal:{self.colors.RESET} {event.is_self_removal}")

        try:
            print(f"{self.colors.CYAN}[WebSocketListener]{self.colors.RESET} {self.colors.MAGENTA}📡 Starting Redis publishing for user removal ({removal_type}){self.colors.RESET}")
            print(f"{self.colors.CYAN}[WebSocketListener]{self.colors.RESET} {self.colors.BLUE}   └─ Event details: Project {event.project_id}, User {event.user_id}{self.colors.RESET}")

            print(f"{self.colors.CYAN}[WebSocketListener]{self.colors.RESET} {self.colors.BLUE}   ┌─ Fetching project members from database...{self.colors.RESET}")
            db = event.db
            members = get_project_members(db, event.project_id)
            member_count = len(members)
            print(f"{self.colors.CYAN}[WebSocketListener]{self.colors.RESET} {self.colors.GREEN}   └─ ✓ Found {member_count} project members{self.colors.RESET}")

            message = {
                "type": "user_removed",
                "data": {"project_id": str(event.project_id), "user_id": str(event.user_id), "is_self_removal": event.is_self_removal},
            }
            print(f"{self.colors.CYAN}[WebSocketListener]{self.colors.RESET} {self.colors.BLUE}   ┌─ Prepared removal message: {message}{self.colors.RESET}")

            removal_confirmation_message = {
                "type": "you_removed_from_project",
                "data": {
                    "project_id": str(event.project_id),
                    "removed_by_user_id": str(event.removed_by_user_id),
                    "is_self_removal": event.is_self_removal,
                    "message": f"You were removed from project {event.project_id}" if not event.is_self_removal else f"You left project {event.project_id}"
                },
            }
            print(f"{self.colors.CYAN}[WebSocketListener]{self.colors.RESET} {self.colors.BLUE}   ┌─ Prepared removal confirmation message: {removal_confirmation_message}{self.colors.RESET}")

            print(f"{self.colors.CYAN}[WebSocketListener]{self.colors.RESET} {self.colors.BLUE}   ┌─ Publishing removal confirmation to user {event.user_id}...{self.colors.RESET}", end="")
            publish_start = time.time()
            confirm_success = await publish_to_user_channel(str(event.user_id), removal_confirmation_message)
            confirm_time = time.time() - publish_start
            if confirm_success:
                print(f" {self.colors.GREEN}✓ ({confirm_time:.3f}s){self.colors.RESET}")
            else:
                print(f" {self.colors.RED}✗ ({confirm_time:.3f}s){self.colors.RESET}")
                print(f"{self.colors.CYAN}[WebSocketListener]{self.colors.RESET} {self.colors.RED}   │       └─ Failed to publish removal confirmation to user {event.user_id}{self.colors.RESET}")

            print(f"{self.colors.CYAN}[WebSocketListener]{self.colors.RESET} {self.colors.BLUE}   ┌─ Publishing removal to {member_count} members...{self.colors.RESET}")

            success_count = 0
            failure_count = 0

            for i, member in enumerate(members, 1):
                member_id = str(member.user_id)
                print(f"{self.colors.CYAN}[WebSocketListener]{self.colors.RESET} {self.colors.BLUE}   │   [{i}/{member_count}] Publishing removal to user {member_id}...{self.colors.RESET}", end="")

                publish_start = time.time()
                success = await publish_to_user_channel(member_id, message)
                publish_time = time.time() - publish_start

                if success:
                    success_count += 1
                    print(f" {self.colors.GREEN}✓ ({publish_time:.3f}s){self.colors.RESET}")
                else:
                    failure_count += 1
                    print(f" {self.colors.RED}✗ ({publish_time:.3f}s){self.colors.RESET}")
                    print(f"{self.colors.CYAN}[WebSocketListener]{self.colors.RESET} {self.colors.RED}   │       └─ Failed to publish removal to user {member_id}{self.colors.RESET}")

            total_time = time.time() - start_time
            print(f"{self.colors.CYAN}[WebSocketListener]{self.colors.RESET} {self.colors.GREEN}✓ Redis removal publishing completed in {total_time:.3f}s{self.colors.RESET}")
            print(f"{self.colors.CYAN}[WebSocketListener]{self.colors.RESET} {self.colors.GREEN}   └─ Success: {success_count}, Failures: {failure_count}{self.colors.RESET}")

        except Exception as e:
            total_time = time.time() - start_time
            print(f"{self.colors.CYAN}[WebSocketListener]{self.colors.RESET} {self.colors.RED}✗ Redis removal publishing failed after {total_time:.3f}s{self.colors.RESET}")
            print(f"{self.colors.CYAN}[WebSocketListener]{self.colors.RESET} {self.colors.RED}   └─ Error: {e}{self.colors.RESET}")
            print(f"{self.colors.CYAN}[WebSocketListener]{self.colors.RESET} {self.colors.RED}   └─ Error type: {type(e).__name__}{self.colors.RESET}")

