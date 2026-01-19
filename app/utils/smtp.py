from typing import Any, Dict, List, Optional

import yagmail
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.utils.logging import logger


class SMTPClient:
    """Generic SMTP client for sending emails with retry logic and attachment support."""

    def __init__(self):
        """Initialize SMTP client with yagmail."""
        if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
            logger.warning("SMTP credentials not configured. Email functionality will be disabled.")
            self.client = None
        else:
            try:
                self.client = yagmail.SMTP(
                    user=settings.SMTP_USER,
                    password=settings.SMTP_PASSWORD,
                    host=settings.SMTP_HOST,
                    port=settings.SMTP_PORT
                )
                logger.info("SMTP client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize SMTP client: {str(e)}")
                self.client = None

    @retry(
        wait=wait_exponential(multiplier=1, min=1, max=10),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def send_email(
        self,
        to: str | List[str],
        subject: str,
        contents: str | List[str],
        attachments: Optional[List[str]] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
    ) -> bool:
        """
        Send email with retry mechanism.

        Args:
            to: Recipient email address(es)
            subject: Email subject
            contents: Email body (text or HTML)
            attachments: List of file paths to attach
            cc: CC recipients
            bcc: BCC recipients

        Returns:
            bool: True if sent successfully, False otherwise
        """
        if not self.client:
            logger.warning("SMTP client not initialized. Email not sent.")
            return False

        try:
            if isinstance(contents, str):
                contents = [contents]

            self.client.send(
                to=to,
                subject=subject,
                contents=contents,
                attachments=attachments,
                cc=cc,
                bcc=bcc,
            )
            logger.info(f"Email sent successfully to {to}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {to}: {str(e)}")
            raise

    def send_html_email(
        self,
        to: str | List[str],
        subject: str,
        html_content: str,
        attachments: Optional[List[str]] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
    ) -> bool:
        """
        Send HTML email.

        Args:
            to: Recipient email address(es)
            subject: Email subject
            html_content: HTML email body
            attachments: List of file paths to attach
            cc: CC recipients
            bcc: BCC recipients

        Returns:
            bool: True if sent successfully, False otherwise
        """
        return self.send_email(
            to=to,
            subject=subject,
            contents=html_content,
            attachments=attachments,
            cc=cc,
            bcc=bcc,
        )

    def send_bulk_email(
        self,
        recipients: List[Dict[str, Any]],
    ) -> Dict[str, int]:
        """
        Send emails to multiple recipients.

        Args:
            recipients: List of dicts with keys: to, subject, contents, attachments (optional)

        Returns:
            Dict with success and failed counts
        """
        success_count = 0
        failed_count = 0

        for recipient in recipients:
            try:
                result = self.send_email(
                    to=recipient["to"],
                    subject=recipient["subject"],
                    contents=recipient["contents"],
                    attachments=recipient.get("attachments"),
                    cc=recipient.get("cc"),
                    bcc=recipient.get("bcc"),
                )
                if result:
                    success_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                logger.error(f"Error sending bulk email to {recipient['to']}: {str(e)}")
                failed_count += 1

        return {"success": success_count, "failed": failed_count}

    def close(self):
        """Close SMTP connection."""
        if self.client:
            self.client.close()
            logger.info("SMTP client closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
