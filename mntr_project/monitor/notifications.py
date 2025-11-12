from django.core.mail import send_mail
from django.template.loader import render_to_string
from .models import NotificationSettings
import requests

def send_notification(page, diff):
    user = page.user
    try:
        settings = user.notificationsettings
        if settings.notification_type == 'email' and settings.email_address:
            subject = f'Page Change Detected: {page.name}'
            html_message = render_to_string('monitor/notification_email.html', {'page': page, 'diff': diff})
            plain_message = f'The page "{page.name}" ({page.url}) has changed.\\n\\nDiff:\\n{diff}'
            send_mail(
                subject,
                plain_message,
                'noreply@mntr.com',
                [settings.email_address],
                html_message=html_message
            )
        elif settings.notification_type == 'slack' and settings.slack_webhook_url:
            payload = {
                "text": f"Page Change Detected: {page.name}",
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Page Change Detected: <{page.url}|{page.name}>*"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"```{diff}```"
                        }
                    }
                ]
            }
            requests.post(settings.slack_webhook_url, json=payload)
        elif settings.notification_type == 'telegram' and settings.telegram_chat_id:
            # Note: This requires a Telegram bot token, which is not stored in the database.
            # This implementation assumes the token is stored in an environment variable.
            # For now, I'll leave this as a placeholder.
            pass
    except NotificationSettings.DoesNotExist:
        pass
