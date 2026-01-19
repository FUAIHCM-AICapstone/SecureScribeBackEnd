"""Email service for handling all email sending operations."""

from app.utils.email_templates import (
    get_meeting_note_template,
)
from app.utils.logging import logger
from app.utils.smtp import SMTPClient


def send_meeting_note_email(
    to_email: str,
    meeting_title: str,
    meeting_date: str,
    pdf_attachment_path: str,
    meeting_id: str = None,
    meeting_time: str = None,
    attendees_count: int = None,
) -> bool:
    """
    Send meeting note email with PDF attachment (Vietnamese).

    This is the test function to send meeting notes immediately after generation.

    Args:
        to_email: Recipient email address
        meeting_title: Title of the meeting
        meeting_date: Date of the meeting
        pdf_attachment_path: Full path to PDF file containing meeting note
        meeting_id: UUID of the meeting (optional, for action button link)
        meeting_time: Meeting time (optional)
        attendees_count: Number of attendees (optional)

    Returns:
        bool: True if sent successfully, False otherwise
    """
    meeting_data = {
        "meeting_title": meeting_title,
        "meeting_date": meeting_date,
    }

    # Add optional details
    if meeting_time:
        meeting_data["meeting_time"] = meeting_time
    if attendees_count:
        meeting_data["attendees_count"] = attendees_count

    # Add action button if meeting_id is provided
    if meeting_id:
        meeting_data["action_url"] = f"https://changee.wc504.io.vn/meetings/{meeting_id}"

    try:
        html_content = get_meeting_note_template(meeting_data)
        subject = f"📋 Biên bản cuộc họp: {meeting_title}"

        with SMTPClient() as client:
            return client.send_html_email(
                to=to_email,
                subject=subject,
                html_content=html_content,
                attachments=[pdf_attachment_path] if pdf_attachment_path else None,
            )
    except Exception as e:
        logger.error(f"Failed to send meeting note email to {to_email}: {str(e)}")
        return False
