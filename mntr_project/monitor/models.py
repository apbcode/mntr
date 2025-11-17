from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class MonitoredPage(models.Model):
    FREQUENCY_UNITS = (
        ('minute', 'Minutes'),
        ('hour', 'Hours'),
        ('day', 'Days'),
        ('week', 'Weeks'),
        ('month', 'Months'),
        ('year', 'Years'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    url = models.URLField(max_length=2000)
    frequency_number = models.PositiveIntegerField()
    frequency_unit = models.CharField(max_length=10, choices=FREQUENCY_UNITS)
    last_checked = models.DateTimeField(null=True, blank=True)
    has_changed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class PageSnapshot(models.Model):
    monitored_page = models.ForeignKey(MonitoredPage, on_delete=models.CASCADE, related_name='snapshots')
    created_at = models.DateTimeField(auto_now_add=True)
    content = models.TextField(blank=True)

    def __str__(self):
        return f'Snapshot of {self.monitored_page.name} at {self.created_at}'

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
