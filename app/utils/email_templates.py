"""Email HTML templates for different email types."""

from typing import Any, Dict

LOGO_URL = "https://mom.meobeo.ai/images/logos/logo.png"
BRAND_PRIMARY = "#1F3A7D"
BRAND_SECONDARY = "#4A90E2"
BRAND_ACCENT = "#F39C12"
BRAND_SUCCESS = "#10B981"
BRAND_LIGHT = "#F3F4F6"
BRAND_DARK = "#1F2937"


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
    icon = context.get("icon", "🔔")

    action_button_html = ""
    if context.get("action_url"):
        action_text = context.get("action_text", "Xem chi tiết")
        action_button_html = f"""
        <div style="text-align: center; margin-top: 32px;">
            <a href="{context["action_url"]}" style="background: linear-gradient(135deg, #4A90E2 0%, #1F3A7D 100%); color: white; padding: 16px 48px; border-radius: 8px; text-decoration: none; font-weight: 600; display: inline-block; box-shadow: 0 6px 20px rgba(74, 144, 226, 0.35); transition: all 0.3s ease; font-size: 15px; border: none; cursor: pointer;">
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
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: {BRAND_DARK}; }}
            a:hover {{ opacity: 0.9; }}
            @media only screen and (max-width: 640px) {{
                .container {{ padding: 12px !important; }}
                .content {{ padding: 30px 20px !important; }}
                h1 {{ font-size: 22px !important; }}
            }}
        </style>
    </head>
    <body style="background: linear-gradient(135deg, #f0f4f8 0%, #d9e2ec 100%); padding: 40px 0; margin: 0;">
        <div style="max-width: 640px; margin: 0 auto; padding: 20px;" class="container">
            <!-- Header with Logo & Decoration -->
            <div style="background: linear-gradient(135deg, white 0%, #f8fafb 100%); border-radius: 16px 16px 0 0; padding: 40px 30px; text-align: center; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08); position: relative; overflow: hidden;">
                <div style="position: absolute; top: -50px; right: -50px; width: 150px; height: 150px; background: radial-gradient(circle, rgba(74, 144, 226, 0.05) 0%, transparent 70%); border-radius: 50%;"></div>
                <img src="{LOGO_URL}" alt="SecureScribe" style="height: 48px; margin-bottom: 15px; position: relative; z-index: 1;">
                <p style="color: #888; font-size: 12px; margin: 0; text-transform: uppercase; letter-spacing: 1px; font-weight: 500;">Quản lý Cuộc họp</p>
            </div>
            
            <!-- Main Content Card -->
            <div style="background: white; padding: 45px 35px; border-left: 6px solid {BRAND_SECONDARY}; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08);" class="content">
                <!-- Icon Circle -->
                <div style="text-align: center; margin-bottom: 28px;">
                    <div style="width: 100px; height: 100px; background: linear-gradient(135deg, #e8f1fc 0%, #f0f7ff 100%); border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 20px; font-size: 50px;">
                        {icon}
                    </div>
                    <h1 style="font-size: 26px; font-weight: 700; color: {BRAND_PRIMARY}; margin: 0 0 12px 0; letter-spacing: -0.3px;">
                        {context.get("title", "Thông báo")}
                    </h1>
                    <div style="width: 50px; height: 3px; background: linear-gradient(90deg, {BRAND_SECONDARY}, {BRAND_ACCENT}); margin: 0 auto; border-radius: 2px;"></div>
                </div>
                
                <!-- Message -->
                <div style="color: #555; line-height: 1.85; margin-bottom: 32px; font-size: 15px; background: {BRAND_LIGHT}; padding: 20px; border-radius: 10px; border-left: 4px solid {BRAND_SECONDARY};">
                    {context.get("message", "Bạn có một thông báo mới")}
                </div>
                
                <!-- Action Button -->
                {action_button_html}
            </div>
            
            <!-- Footer -->
            <div style="background: linear-gradient(135deg, {BRAND_PRIMARY} 0%, #2c5aa0 100%); border-radius: 0 0 16px 16px; padding: 30px 35px; text-align: center; color: white; box-shadow: 0 4px 15px rgba(31, 58, 125, 0.2);">
                <p style="margin: 0 0 8px 0; font-size: 13px; opacity: 0.95;">
                    SecureScribe Meeting Management System
                </p>
                <p style="margin: 0; font-size: 11px; opacity: 0.85;">
                    © 2024 SecureScribe. Bảo vệ và quản lý thông tin cuộc họp của bạn.
                </p>
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
        <div style="text-align: center; margin-top: 32px;">
            <a href="{context["action_url"]}" style="background: linear-gradient(135deg, #4A90E2 0%, #1F3A7D 100%); color: white; padding: 16px 48px; border-radius: 8px; text-decoration: none; font-weight: 600; display: inline-block; box-shadow: 0 6px 20px rgba(74, 144, 226, 0.35); transition: all 0.3s ease; font-size: 15px; border: none;">
                Xem cuộc họp
            </a>
        </div>
        """

    meeting_time_html = ""
    if context.get("meeting_time"):
        meeting_time_html = f"""
        <div style="display: flex; justify-content: space-between; padding: 14px 16px; border-bottom: 1px solid #e5e7eb; align-items: center;">
            <span style="color: #6b7280; font-weight: 500;">⏰ Thời gian</span>
            <span style="color: {BRAND_PRIMARY}; font-weight: 600;">{context.get("meeting_time")}</span>
        </div>
        """

    attendees_html = ""
    if context.get("attendees_count"):
        attendees_html = f"""
        <div style="display: flex; justify-content: space-between; padding: 14px 16px; align-items: center;">
            <span style="color: #6b7280; font-weight: 500;">👥 Số người tham gia</span>
            <span style="color: {BRAND_PRIMARY}; font-weight: 600;">{context.get("attendees_count")} người</span>
        </div>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Biên bản cuộc họp - {context.get("meeting_title", "Cuộc họp")}</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: {BRAND_DARK}; }}
            @media only screen and (max-width: 640px) {{
                .container {{ padding: 12px !important; }}
                .content {{ padding: 30px 20px !important; }}
                h1 {{ font-size: 22px !important; }}
                .details-grid {{ flex-direction: column !important; }}
            }}
        </style>
    </head>
    <body style="background: linear-gradient(135deg, #f0f4f8 0%, #d9e2ec 100%); padding: 40px 0; margin: 0;">
        <div style="max-width: 640px; margin: 0 auto; padding: 20px;" class="container">
            <!-- Header with Logo & Decoration -->
            <div style="background: linear-gradient(135deg, white 0%, #f8fafb 100%); border-radius: 16px 16px 0 0; padding: 40px 30px; text-align: center; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08); position: relative; overflow: hidden;">
                <div style="position: absolute; top: -50px; right: -50px; width: 150px; height: 150px; background: radial-gradient(circle, rgba(74, 144, 226, 0.05) 0%, transparent 70%); border-radius: 50%;"></div>
                <img src="{LOGO_URL}" alt="SecureScribe" style="height: 48px; margin-bottom: 15px; position: relative; z-index: 1;">
                <p style="color: #888; font-size: 12px; margin: 0; text-transform: uppercase; letter-spacing: 1px; font-weight: 500;">Quản lý Cuộc họp</p>
            </div>
            
            <!-- Main Content Card -->
            <div style="background: white; padding: 45px 35px; border-left: 6px solid {BRAND_ACCENT}; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08);" class="content">
                <!-- Icon Circle -->
                <div style="text-align: center; margin-bottom: 28px;">
                    <div style="width: 100px; height: 100px; background: linear-gradient(135deg, #fef3c7 0%, #fef8e7 100%); border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 20px; font-size: 50px;">
                        📋
                    </div>
                    <h1 style="font-size: 26px; font-weight: 700; color: {BRAND_PRIMARY}; margin: 0 0 12px 0;">
                        Biên bản cuộc họp đã sẵn sàng
                    </h1>
                    <div style="width: 50px; height: 3px; background: linear-gradient(90deg, {BRAND_ACCENT}, {BRAND_SECONDARY}); margin: 0 auto; border-radius: 2px;"></div>
                </div>
                
                <!-- Meeting Details Card -->
                <div style="background: linear-gradient(135deg, #f9fafb 0%, #f3f4f6 100%); border-radius: 12px; margin-bottom: 28px; overflow: hidden; border-left: 5px solid {BRAND_ACCENT};">
                    <div style="padding: 16px 16px; background: linear-gradient(135deg, rgba(243, 156, 18, 0.08) 0%, rgba(243, 156, 18, 0.04) 100%); border-bottom: 1px solid #e5e7eb;">
                        <span style="color: #6b7280; font-weight: 600; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;">📅 Thông tin cuộc họp</span>
                    </div>
                    
                    <div style="display: flex; justify-content: space-between; padding: 14px 16px; border-bottom: 1px solid #e5e7eb; align-items: center;">
                        <span style="color: #6b7280; font-weight: 500;">📌 Tiêu đề</span>
                        <span style="color: {BRAND_PRIMARY}; font-weight: 700;">{context.get("meeting_title", "Cuộc họp")}</span>
                    </div>
                    
                    <div style="display: flex; justify-content: space-between; padding: 14px 16px; border-bottom: 1px solid #e5e7eb; align-items: center;">
                        <span style="color: #6b7280; font-weight: 500;">📆 Ngày</span>
                        <span style="color: {BRAND_PRIMARY}; font-weight: 600;">{context.get("meeting_date", "N/A")}</span>
                    </div>
                    
                    {meeting_time_html}
                    {attendees_html}
                </div>
                
                <!-- Success Message -->
                <div style="background: linear-gradient(135deg, #f0fdf4 0%, #f7ffec 100%); padding: 20px; border-radius: 10px; border-left: 4px solid {BRAND_SUCCESS}; margin-bottom: 28px;">
                    <div style="color: {BRAND_SUCCESS}; font-weight: 600; margin-bottom: 8px; font-size: 14px;">
                        ✓ Biên bản đã được tạo thành công
                    </div>
                    <div style="color: #555; font-size: 14px; line-height: 1.6;">
                        Biên bản cuộc họp cho "<strong>{context.get("meeting_title", "cuộc họp")}</strong>" ({context.get("meeting_date", "N/A")}) đã được tạo và được gắn kèm trong email này dưới dạng file PDF.
                    </div>
                </div>
                
                <!-- Action Button -->
                {action_button_html}
            </div>
            
            <!-- Footer -->
            <div style="background: linear-gradient(135deg, {BRAND_PRIMARY} 0%, #2c5aa0 100%); border-radius: 0 0 16px 16px; padding: 30px 35px; text-align: center; color: white; box-shadow: 0 4px 15px rgba(31, 58, 125, 0.2);">
                <p style="margin: 0 0 8px 0; font-size: 13px; opacity: 0.95;">
                    SecureScribe Meeting Management System
                </p>
                <p style="margin: 0; font-size: 11px; opacity: 0.85;">
                    © 2024 SecureScribe. Bảo vệ và quản lý thông tin cuộc họp của bạn.
                </p>
            </div>
        </div>
    </body>
    </html>
    """
