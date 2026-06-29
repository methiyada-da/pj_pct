from django.contrib import admin

from .models import Inbox, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    fields = ('sender', 'msg', 'msg_img', 'msg_is_read', 'msg_sent_time')
    readonly_fields = ('msg_sent_time',)


@admin.register(Inbox)
class InboxAdmin(admin.ModelAdmin):
    list_display = ('ib_id', 'member1', 'member2')
    search_fields = ('member1__mb_full_name', 'member2__mb_full_name')
    inlines = (MessageInline,)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('msg_id', 'inbox', 'sender', 'msg_is_read', 'msg_sent_time')
    list_filter = ('msg_is_read', 'msg_sent_time')
    search_fields = ('msg', 'sender__mb_full_name', 'inbox__member1__mb_full_name', 'inbox__member2__mb_full_name')
    ordering = ('-msg_sent_time',)
