from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404

from .models import Notification


@login_required
def api_list(request):
    """
    GET /notifications/api/
    คืน JSON รายการแจ้งเตือน 20 รายการล่าสุด (ทั้ง read และ unread)
    พร้อม unread_count แยกต่างหาก
    """
    user = request.user

    if hasattr(user, 'system'):
        qs_all       = Notification.objects.filter(admin_recipient=user)
        unread_count = qs_all.filter(notif_is_read=False).count()
    else:
        try:
            member       = user.member
            qs_all       = Notification.objects.filter(recipient=member)
            unread_count = qs_all.filter(notif_is_read=False).count()
        except Exception:
            return JsonResponse({'unread_count': 0, 'notifications': []})

    notifications = qs_all.order_by('-notif_created_at')[:20]

    data = {
        'unread_count': unread_count,
        'notifications': [
            {
                'id':         n.pk,
                'type':       n.notif_type,
                'text':       n.notif_text,
                'url':        n.notif_url,
                'is_read':    n.notif_is_read,
                'created_at': n.notif_created_at.strftime('%d/%m/%Y %H:%M'),
            }
            for n in notifications
        ],
    }
    return JsonResponse(data)


@login_required
@require_POST
def api_mark_read(request, pk):
    """POST /notifications/api/<pk>/read/ — mark อ่านแล้ว"""
    user = request.user

    if hasattr(user, 'system'):
        notif = get_object_or_404(Notification, pk=pk, admin_recipient=user)
    else:
        try:
            member = user.member
            notif  = get_object_or_404(Notification, pk=pk, recipient=member)
        except Exception:
            return JsonResponse({'success': False}, status=403)

    notif.notif_is_read = True
    notif.save(update_fields=['notif_is_read'])
    return JsonResponse({'success': True})


@login_required
@require_POST
def api_mark_all_read(request):
    """POST /notifications/api/read-all/ — mark ทั้งหมดว่าอ่านแล้ว"""
    user = request.user

    if hasattr(user, 'system'):
        Notification.objects.filter(admin_recipient=user, notif_is_read=False).update(notif_is_read=True)
    else:
        try:
            member = user.member
            Notification.objects.filter(recipient=member, notif_is_read=False).update(notif_is_read=True)
        except Exception:
            return JsonResponse({'success': False}, status=403)

    return JsonResponse({'success': True})