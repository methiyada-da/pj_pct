# messaging/views.py - views จัดการกล่องข้อความและแชท
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from datetime import datetime, timezone as dt_timezone
from django.utils import timezone
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist
from django.contrib import messages

from apps.accounts.models import Member
from .models import Inbox, Message
from .forms import MessageForm


def _display_name_for_user(user):
    full_name = user.get_full_name().strip()
    if full_name:
        return full_name
    if user.email:
        return user.email.split('@')[0]
    return user.username


def _email_for_user(user):
    email = (user.email or '').strip()
    if email:
        return email[:50]
    return f'{user.username}@admin.local'[:50]


def _get_current_member(request):
    """
    Messaging is stored between Member records. Admin users created outside the
    member registration flow may not have one, so create a lightweight member
    profile for staff accounts when they first open chat.
    """
    try:
        return request.user.member
    except (Member.DoesNotExist, ObjectDoesNotExist):
        if request.user.is_staff or request.user.is_superuser:
            member, _ = Member.objects.get_or_create(
                user=request.user,
                defaults={
                    'mb_full_name': _display_name_for_user(request.user),
                    'mb_email': _email_for_user(request.user),
                    'mb_status': 1,
                    'mj_id': None,
                }
            )
            return member
        messages.error(request, 'ไม่พบข้อมูลสมาชิกของบัญชีนี้ กรุณาติดต่อผู้ดูแลระบบ')
        return None


def _build_inbox_data(me):
    """helper: สร้าง inbox list สำหรับ sidebar"""
    inboxes = (
        Inbox.objects
        .filter(Q(member1=me) | Q(member2=me))
        .select_related('member1', 'member2')
        .prefetch_related('message_set')
        .distinct()
    )
    inbox_data = []
    for ib in inboxes:
        other_mb = ib.get_other_member(me)
        last_msg = ib.last_message()
        unread   = ib.unread_count_for(me)
        inbox_data.append({
            'inbox':    ib,
            'other':    other_mb,
            'last_msg': last_msg,
            'unread':   unread,
        })
    inbox_data.sort(
        key=lambda x: x['last_msg'].msg_sent_time if x['last_msg']
                      else datetime.min.replace(tzinfo=dt_timezone.utc),
        reverse=True
    )
    return inbox_data


@login_required
def inbox_list(request):
    """
    หน้ารายการแชททั้งหมด
    URL: /messaging/
    """
    me = _get_current_member(request)
    if not me:
        return redirect('home')
    return render(request, 'messaging/inbox.html', {
        'inbox_data': _build_inbox_data(me),
        'is_admin':   request.user.is_staff,
    })


@login_required
def chat_with(request, mb_id):
    """
    หน้าแชทกับ member คนใดคนหนึ่ง (get_or_create inbox)
    URL: /messaging/with/<mb_id>/
    """
    me = _get_current_member(request)
    if not me:
        return redirect('home')
    other = get_object_or_404(Member, pk=mb_id)

    # ป้องกันแชทกับตัวเอง
    if me == other:
        return redirect('messaging:inbox')

    # get_or_create inbox (member1 id น้อยกว่าเสมอ เพื่อป้องกัน duplicate)
    if me.pk < other.pk:
        m1, m2 = me, other
    else:
        m1, m2 = other, me

    inbox, _ = Inbox.objects.get_or_create(member1=m1, member2=m2)

    # รับข้อความ POST
    if request.method == 'POST':
        form = MessageForm(request.POST, request.FILES)
        if form.is_valid():
            msg_obj        = form.save(commit=False)
            msg_obj.sender = me
            msg_obj.inbox  = inbox
            msg_obj.msg    = form.cleaned_data.get('msg', '').strip()
            msg_obj.save()
            return redirect('messaging:chat_with', mb_id=mb_id)
    else:
        form = MessageForm()

    # mark as read
    inbox.message_set.filter(msg_is_read=0).exclude(sender=me).update(msg_is_read=1)

    # เพิ่ม flag show_date_sep — ขึ้น date separator เฉพาะเมื่อวันเปลี่ยน
    raw_msgs = list(inbox.message_set.select_related("sender").order_by("msg_sent_time"))
    for i, m in enumerate(raw_msgs):
        m.show_date_sep = (
            i == 0 or
            raw_msgs[i-1].msg_sent_time.date() != m.msg_sent_time.date()
        )
    messages_qs = raw_msgs

    return render(request, 'messaging/chat.html', {
        'inbox':         inbox,
        'other':         other,
        'chat_messages': messages_qs,
        'form':          form,
        'me':            me,
        'inbox_data':    _build_inbox_data(me),
        'is_admin':      request.user.is_staff,
    })


@login_required
def poll_messages(request, ib_id):
    """
    AJAX polling — คืนข้อความและสถานะ read ที่อัปเดตล่าสุด
    URL: /messaging/poll/<ib_id>/?after=<msg_id>
    """
    from django.http import JsonResponse

    me = _get_current_member(request)
    if not me:
        return JsonResponse({'error': 'member_not_found'}, status=403)
    inbox = get_object_or_404(Inbox, pk=ib_id)

    # ตรวจสิทธิ์
    if me not in (inbox.member1, inbox.member2):
        return JsonResponse({'error': 'forbidden'}, status=403)

    # mark as read
    inbox.message_set.filter(msg_is_read=0).exclude(sender=me).update(msg_is_read=1)

    after_id = int(request.GET.get('after', 0))
    msgs_qs  = inbox.message_set.select_related('sender').order_by('msg_sent_time')

    result = []
    for m in msgs_qs:
        result.append({
            'msg_id':        m.msg_id,
            'msg':           m.msg,
            'msg_img_url':   m.msg_img.url if m.msg_img else None,
            'msg_is_read':   m.msg_is_read,
            'msg_sent_time': m.msg_sent_time.isoformat(),
            'sender_id':     m.sender.pk,
            'sender_name':   m.sender.mb_full_name,
            'sender_img':    m.sender.mb_img.url if m.sender.mb_img else None,
        })

    filtered = [m for m in result if m['msg_id'] > after_id or m['msg_is_read'] == 1]
    return JsonResponse({'messages': filtered})

@login_required
def unread_count(request):
    """
    AJAX endpoint คืน total unread สำหรับ header badge polling
    URL: /messaging/unread-count/
    """
    from django.http import JsonResponse
    me = _get_current_member(request)
    if not me:
        return JsonResponse({'total_unread': 0})
    inboxes = Inbox.objects.filter(Q(member1=me) | Q(member2=me))
    total = sum(ib.unread_count_for(me) for ib in inboxes)
    return JsonResponse({'total_unread': total})
