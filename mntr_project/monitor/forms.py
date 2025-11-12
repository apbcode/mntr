from django import forms
from .models import MonitoredPage, NotificationSettings

class MonitoredPageForm(forms.ModelForm):
    class Meta:
        model = MonitoredPage
        fields = ['name', 'url', 'frequency_number', 'frequency_unit']

class NotificationSettingsForm(forms.ModelForm):
    class Meta:
        model = NotificationSettings
        fields = ['notification_type', 'email_address', 'slack_webhook_url', 'telegram_chat_id']
