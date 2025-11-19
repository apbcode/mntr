from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class MonitoredPage(models.Model):
    """
    Represents a web page that is being monitored for changes.
    """
    FREQUENCY_UNITS = (
        ('minute', 'Minutes'),
        ('hour', 'Hours'),
        ('day', 'Days'),
        ('week', 'Weeks'),
        ('month', 'Months'),
        ('year', 'Years'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)  # The user who owns this monitored page.
    name = models.CharField(max_length=255)  # A custom name for the monitored page.
    url = models.URLField(max_length=2000)  # The URL of the page to monitor.
    frequency_number = models.PositiveIntegerField()  # The number of units for the monitoring frequency (e.g., 5).
    frequency_unit = models.CharField(max_length=10, choices=FREQUENCY_UNITS)  # The unit for the monitoring frequency (e.g., 'minutes').
    last_checked = models.DateTimeField(null=True, blank=True)  # The last time the page was checked for changes.
    has_changed = models.BooleanField(default=False)  # A flag indicating if the page has changed since the last check.
    last_seen_snapshot = models.ForeignKey('PageSnapshot', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')  # The last snapshot the user has seen.
    created_at = models.DateTimeField(auto_now_add=True)  # The timestamp when the monitored page was created.

    def __str__(self):
        return self.name

class PageSnapshot(models.Model):
    """
    Represents a snapshot of a monitored page at a specific point in time.
    """
    monitored_page = models.ForeignKey(MonitoredPage, on_delete=models.CASCADE, related_name='snapshots')  # The monitored page this snapshot belongs to.
    created_at = models.DateTimeField(auto_now_add=True)  # The timestamp when the snapshot was created.
    content = models.TextField(blank=True)  # The HTML content of the page at the time of the snapshot.

    def __str__(self):
        return f'Snapshot of {self.monitored_page.name} at {self.created_at}'

class NotificationSettings(models.Model):
    """
    Represents the notification settings for a user.
    """
    NOTIFICATION_TYPES = (
        ('email', 'Email'),
        ('slack', 'Slack'),
        ('telegram', 'Telegram'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)  # The user these settings belong to.
    notification_type = models.CharField(max_length=10, choices=NOTIFICATION_TYPES)  # The type of notification to send.
    email_address = models.EmailField(blank=True, null=True)  # The email address to send notifications to.
    slack_webhook_url = models.URLField(blank=True, null=True)  # The Slack webhook URL to send notifications to.
    telegram_chat_id = models.CharField(max_length=255, blank=True, null=True)  # The Telegram chat ID to send notifications to.

    def __str__(self):
        return f"{self.user.username}'s Notification Settings"
