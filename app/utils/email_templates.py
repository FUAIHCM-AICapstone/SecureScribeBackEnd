"""Email HTML templates for different email types."""

from typing import Any, Dict


def get_notification_template(context: Dict[str, Any]) -> str:
    """
    Get HTML template for notification email.

    Context keys:
    - notification_type: str (e.g., "meeting_reminder", "action_item_due", "new_transcript")
    - title: str
    - message: str
    - action_url: str (optional)
    - action_text: str (optional, default: "View Details")
    - icon: str (optional emoji)
    """
    notification_type = context.get("notification_type", "notification")
    icon = context.get("icon", "🔔")

    action_button_html = ""
    if context.get("action_url"):
        action_text = context.get("action_text", "View Details")
        action_button_html = f"""
        <div style="text-align: center; margin-top: 20px;">
            <a href="{context["action_url"]}" style="background-color: #007bff; color: white; padding: 12px 30px; border-radius: 4px; text-decoration: none; font-weight: bold; display: inline-block;">
                {action_text}
            </a>
        </div>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                color: #333;
            }}
            .container {{
                max-width: 500px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f9f9f9;
            }}
            .notification-card {{
                background-color: white;
                border-left: 4px solid #007bff;
                border-radius: 8px;
                padding: 30px;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            }}
            .notification-icon {{
                font-size: 40px;
                margin-bottom: 15px;
                text-align: center;
            }}
            .notification-title {{
                font-size: 20px;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 15px;
                text-align: center;
            }}
            .notification-message {{
                color: #555;
                line-height: 1.8;
                margin-bottom: 20px;
            }}
            .footer {{
                text-align: center;
                font-size: 12px;
                color: #999;
                margin-top: 20px;
                padding-top: 15px;
                border-top: 1px solid #ddd;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="notification-card">
                <div class="notification-icon">{icon}</div>
                <div class="notification-title">{context.get("title", "Notification")}</div>
                <div class="notification-message">{context.get("message", "You have a new notification")}</div>
                {action_button_html}
                <div class="footer">
                    <p>This is an automated email from SecureScribe Meeting Management System.</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
