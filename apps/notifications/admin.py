from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display  = ('notif_type', 'recipient', 'admin_recipient', 'notif_text', 'notif_is_read', 'notif_created_at')
    list_filter   = ('notif_type', 'notif_is_read')
    search_fields = ('notif_text',)
    ordering      = ('-notif_created_at',)