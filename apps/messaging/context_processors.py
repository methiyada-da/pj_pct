from django.db.models import Q
from .models import Inbox


def unread_message_count(request):
    """
    ส่ง total_unread ไปทุกหน้าอัตโนมัติ
    ใช้ใน template: {{ total_unread }}
    """
    if not request.user.is_authenticated:
        return {'total_unread': 0}

    try:
        me = request.user.member
        inboxes = Inbox.objects.filter(Q(member1=me) | Q(member2=me))
        total = sum(ib.unread_count_for(me) for ib in inboxes)
    except Exception:
        total = 0

    return {'total_unread': total}
