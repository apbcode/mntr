from django.db import models
from django.contrib.auth.models import User

class MonitoredPage(models.Model):
    FREQUENCY_UNITS = (
        ('min', 'Minutes'),
        ('day', 'Days'),
        ('month', 'Months'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    url = models.URLField(max_length=2000)
    frequency_number = models.PositiveIntegerField()
    frequency_unit = models.CharField(max_length=5, choices=FREQUENCY_UNITS)
    last_checked = models.DateTimeField(null=True, blank=True)
    last_content = models.TextField(blank=True)
    has_changed = models.BooleanField(default=False)

    def __str__(self):
        return self.name

class NotificationSettings(models.Model):
    NOTIFICATION_TYPES = (
        ('email', 'Email'),
        ('slack', 'Slack'),
        ('telegram', 'Telegram'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    notification_type = models.CharField(max_length=10, choices=NOTIFICATION_TYPES)
    email_address = models.EmailField(blank=True, null=True)
    slack_webhook_url = models.URLField(blank=True, null=True)
    telegram_chat_id = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username}'s Notification Settings"
