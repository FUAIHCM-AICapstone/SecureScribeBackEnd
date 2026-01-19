"""Email service for handling all email sending operations."""


from app.utils.email_templates import (
    get_notification_template,
)
from app.utils.logging import logger
from app.utils.smtp import SMTPClient


def send_meeting_note_email(
    to_email: str,
    meeting_title: str,
    meeting_date: str,
    pdf_attachment_path: str,
    meeting_id: str = None,
) -> bool:
    """
    Send meeting note email with PDF attachment.

    This is the test function to send meeting notes immediately after generation.

    Args:
        to_email: Recipient email address
        meeting_title: Title of the meeting
        meeting_date: Date of the meeting
        pdf_attachment_path: Full path to PDF file containing meeting note
        meeting_id: UUID of the meeting (optional, for action button link)

    Returns:
        bool: True if sent successfully, False otherwise
    """
    notification_data = {
        "notification_type": "meeting_note_ready",
        "title": "Meeting Note Ready",
        "message": f"The meeting note for '{meeting_title}' ({meeting_date}) has been generated and is attached.",
        "icon": "📄",
    }

    # Add action button if meeting_id is provided
    if meeting_id:
        notification_data["action_url"] = f"https://changee.wc504.io.vn/meetings/{meeting_id}"
        notification_data["action_text"] = "View Meeting"

    try:
        html_content = get_notification_template(notification_data)
        subject = f"Meeting Note: {meeting_title}"

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
