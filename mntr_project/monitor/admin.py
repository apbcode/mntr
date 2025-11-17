from django.contrib import admin
from .models import MonitoredPage, PageSnapshot, NotificationSettings

class MonitoredPageAdmin(admin.ModelAdmin):
    list_display = ('name', 'url', 'user', 'last_checked', 'has_changed')
    list_filter = ('has_changed', 'user')
    search_fields = ('name', 'url')

class PageSnapshotAdmin(admin.ModelAdmin):
    list_display = ('monitored_page', 'created_at')
    list_filter = ('monitored_page',)

class NotificationSettingsAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_type')

admin.site.register(MonitoredPage, MonitoredPageAdmin)
admin.site.register(PageSnapshot, PageSnapshotAdmin)
admin.site.register(NotificationSettings, NotificationSettingsAdmin)
