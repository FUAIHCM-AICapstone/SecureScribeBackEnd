"""Email HTML templates for different email types."""

from typing import Any, Dict

LOGO_URL = "https://mom.meobeo.ai/images/logos/logo.png"
BRAND_PRIMARY = "#1F3A7D"
BRAND_SECONDARY = "#4A90E2"
ACCENT_COLOR = "#F39C12"
TEXT_DARK = "#2c3e50"
TEXT_LIGHT = "#666666"
BORDER_COLOR = "#E5E7EB"


def get_notification_template(context: Dict[str, Any]) -> str:
    """
    Get HTML template for notification email (Vietnamese).

    Context keys:
    - notification_type: str (e.g., "meeting_reminder", "action_item_due", "new_transcript")
    - title: str
    - message: str
    - action_url: str (optional)
    - action_text: str (optional, default: "Xem chi tiết")
    - icon: str (optional emoji)
    """
    action_button_html = ""
    if context.get("action_url"):
        action_text = context.get("action_text", "Xem chi tiết")
        action_button_html = f"""
        <div style="text-align: center; margin-top: 16px;">
            <a href="{context["action_url"]}" style="background-color: {BRAND_SECONDARY}; color: white; padding: 12px 32px; border-radius: 4px; text-decoration: none; font-weight: 600; display: inline-block; font-size: 14px;">
                {action_text}
            </a>
        </div>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{context.get("title", "Thông báo")}</title>
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; line-height: 1.5; color: {TEXT_DARK}; margin: 0; padding: 0; background-color: #FFFFFF;">
        <div style="max-width: 600px; margin: 0 auto;">
            <!-- Header -->
            <div style="padding: 24px; border-bottom: 1px solid {BORDER_COLOR}; text-align: center;">
                <img src="{LOGO_URL}" alt="SecureScribe" style="height: 40px;">
            </div>
            
            <!-- Content -->
            <div style="padding: 24px;">
                <h1 style="font-size: 20px; font-weight: 600; color: {BRAND_PRIMARY}; margin: 0 0 12px 0;">
                    {context.get("title", "Thông báo")}
                </h1>
                
                <p style="color: {TEXT_LIGHT}; font-size: 14px; line-height: 1.6; margin: 0 0 16px 0;">
                    {context.get("message", "Bạn có một thông báo mới")}
                </p>
                
                {action_button_html}
            </div>
            
            <!-- Footer -->
            <div style="padding: 16px 24px; border-top: 1px solid {BORDER_COLOR}; background-color: #F9FAFB; font-size: 12px; color: #999999;">
                <p style="margin: 0;">SecureScribe Meeting Management System</p>
                <p style="margin: 4px 0 0 0;">© 2024 SecureScribe. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """


def get_meeting_note_template(context: Dict[str, Any]) -> str:
    """
    Get HTML template for meeting note email (Vietnamese).

    Context keys:
    - meeting_title: str
    - meeting_date: str
    - meeting_time: str (optional)
    - attendees_count: int (optional)
    - action_url: str (optional)
    """
    action_button_html = ""
    if context.get("action_url"):
        action_button_html = f"""
        <div style="text-align: center; margin-top: 16px;">
            <a href="{context["action_url"]}" style="background-color: {BRAND_SECONDARY}; color: white; padding: 12px 32px; border-radius: 4px; text-decoration: none; font-weight: 600; display: inline-block; font-size: 14px;">
                Xem cuộc họp
            </a>
        </div>
        """

    details_html = f"""
    <div style="background-color: #F9FAFB; border-left: 3px solid {ACCENT_COLOR}; padding: 12px 16px; margin: 12px 0; font-size: 14px;">
        <p style="margin: 0 0 8px 0;"><strong>Tiêu đề:</strong> {context.get("meeting_title", "Cuộc họp")}</p>
        <p style="margin: 0 0 8px 0;"><strong>Ngày:</strong> {context.get("meeting_date", "N/A")}</p>
    """

    if context.get("meeting_time"):
        details_html += f"""
        <p style="margin: 0 0 8px 0;"><strong>Thời gian:</strong> {context.get("meeting_time")}</p>
        """

    if context.get("attendees_count"):
        details_html += f"""
        <p style="margin: 0;"><strong>Số người tham gia:</strong> {context.get("attendees_count")} người</p>
        """

    details_html += """
    </div>
    """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Biên bản cuộc họp - {context.get("meeting_title", "Cuộc họp")}</title>
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; line-height: 1.5; color: {TEXT_DARK}; margin: 0; padding: 0; background-color: #FFFFFF;">
        <div style="max-width: 600px; margin: 0 auto;">
            <!-- Header -->
            <div style="padding: 24px; border-bottom: 1px solid {BORDER_COLOR}; text-align: center;">
                <img src="{LOGO_URL}" alt="SecureScribe" style="height: 40px;">
            </div>
            
            <!-- Content -->
            <div style="padding: 24px;">
                <h1 style="font-size: 20px; font-weight: 600; color: {BRAND_PRIMARY}; margin: 0 0 12px 0;">
                    Biên bản cuộc họp đã sẵn sàng
                </h1>
                
                {details_html}
                
                <p style="color: {TEXT_LIGHT}; font-size: 14px; line-height: 1.6; margin: 16px 0;">
                    Biên bản cuộc họp cho "<strong>{context.get("meeting_title", "cuộc họp")}</strong>" đã được tạo và được gắn kèm trong email này dưới dạng file PDF.
                </p>
                
                {action_button_html}
            </div>
            
            <!-- Footer -->
            <div style="padding: 16px 24px; border-top: 1px solid {BORDER_COLOR}; background-color: #F9FAFB; font-size: 12px; color: #999999;">
                <p style="margin: 0;">SecureScribe Meeting Management System</p>
                <p style="margin: 4px 0 0 0;">© 2024 SecureScribe. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
