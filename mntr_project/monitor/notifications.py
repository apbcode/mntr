from django.core.mail import send_mail
from django.template.loader import render_to_string
from .models import NotificationSettings
import requests
import os
import re

def escape_markdown_v2(text):
    # Escape all special characters for Telegram's MarkdownV2
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

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
            token = os.environ.get('TELEGRAM_BOT_TOKEN')
            if token:
                url = f"https://api.telegram.org/bot{token}/sendMessage"
                escaped_name = escape_markdown_v2(page.name)
                escaped_diff = escape_markdown_v2(diff)
                text = f'*Page Change Detected: {escaped_name}*\\n\\n`{escaped_diff}`'

                payload = {
                    'chat_id': settings.telegram_chat_id,
                    'text': text,
                    'parse_mode': 'MarkdownV2'
                }
                requests.post(url, json=payload)
    except NotificationSettings.DoesNotExist:
        pass
