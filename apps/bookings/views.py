# bookings/views.py - views จัดการการจอง และกิจกรรมติว
import logging
from types import SimpleNamespace
from urllib import request

from django.conf import settings
from django.http import Http404
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db import transaction

from apps import bookings
from apps.accounts.models import Member
from apps.tutoring.models import TimeSlot

from .models import Booking, BookingReportStatement, TutoringActivity, JobCompletion, Review
from .forms import TutoringActivityForm, ReviewForm
from .services import (
    append_booking_closed_comment,
    get_booking_closed_at,
    get_member_booking_state_token,
    get_remaining_seats,
    get_tutor_response_deadline_at,
    process_overdue_pending_bookings,
    process_time_based_bookings,
    strip_booking_closed_at,
)


logger = logging.getLogger(__name__)

TUTOR_PROBLEM_REPORT_MARKER = '[รายงานโดยติวเตอร์]'
FREE_REPORT_AUTO_CLOSE_NOTE = 'ระบบปิดคำจองรายงานปัญหาการสอนฟรีอัตโนมัติหลังครบ 24 ชั่วโมง'
BOOKING_TIMEOUT_MARKER = '[เลยกำหนดตอบรับ]'
STUDENT_CANCEL_REASON_MARKER = '[เหตุผลการยกเลิกโดยผู้เรียน]'
STUDENT_ACTIVE_REPORT_CODES = {'2', '6', '7', '8'}
STUDENT_COMPLETION_REPORT_CODES = {'1', '2', '3', '6', '7', '8'}
TUTOR_REPORT_CODES = {'6', '7', '8'}
REPORT_ACKNOWLEDGEMENT_TEXT = 'รับทราบรายงาน ยอมรับผิด และไม่มีข้อโต้แย้ง'
REPORT_REASON_NORMALIZE = {
    '4': '8',
    't_no_show': '2',
    's_no_show': '5',
    'contact': '6',
    'cannot_contact': '6',
    'agree': '7',
    'other': '8',
    'cancel': '5',
}


def _get_lesson_end_datetime(booking):
    if not booking.bk_stu_datetime:
        return None
    if not booking.ts_id or not booking.ts_id.ts_end_time:
        return None

    local_start = timezone.localtime(booking.bk_stu_datetime)
    lesson_end = timezone.datetime.combine(
        local_start.date(),
        booking.ts_id.ts_end_time,
    )
    if timezone.is_aware(booking.bk_stu_datetime):
        lesson_end = timezone.make_aware(
            lesson_end,
            timezone.get_current_timezone(),
        )
    return lesson_end


def _decorate_cancel_flags(bookings):
    now = timezone.now()

    for bk in bookings:
        cmt = strip_booking_closed_at(bk.bk_cmt)
        bk.student_cancel_reason = ''
        if STUDENT_CANCEL_REASON_MARKER in cmt:
            display_cmt, bk.student_cancel_reason = cmt.split(
                STUDENT_CANCEL_REASON_MARKER,
                1,
            )
            bk.display_cmt = display_cmt.strip()
            bk.student_cancel_reason = bk.student_cancel_reason.strip()
        else:
            bk.display_cmt = cmt
        bk.closed_at = get_booking_closed_at(bk.bk_cmt)
        bk.has_started = bool(bk.bk_stu_datetime and now >= bk.bk_stu_datetime)

                # เวลาสิ้นสุดการสอนจริง = วันที่นัดเรียน + เวลาจบของ TimeSlot
        bk.lesson_end_datetime = _get_lesson_end_datetime(bk)
        bk.can_finish_teaching = bool(
            bk.lesson_end_datetime and now >= bk.lesson_end_datetime
        )

        bk.tutor_cancel_for_student_available = (
            bk.bk_status == 1
            and bk.bk_stu_datetime
            and bk.bk_stu_datetime - timezone.timedelta(hours=24) <= now < bk.bk_stu_datetime
            and not bk.bk_report_date
        )

        bk.rejection_label = 'ติวเตอร์ปฏิเสธ'
        if cmt.startswith(BOOKING_TIMEOUT_MARKER):
            bk.rejection_label = 'เลยกำหนดตอบรับ'
        elif cmt == 'ผู้เรียนยกเลิกการจอง':
            bk.rejection_label = 'ยกเลิกโดยผู้เรียน'
        elif cmt.startswith('ผู้เรียนยกเลิกก่อน 24 ชั่วโมง'):
            bk.rejection_label = 'ยกเลิกโดยผู้เรียน'
        elif cmt.startswith((
            'ผู้เรียนยกเลิกการเรียน ก่อนถึงเวลาเริ่มเรียนมากกว่า 24 ชั่วโมง',
            'ผู้เรียนยกเลิกหลังรับงานล่วงหน้ามากกว่า 24 ชั่วโมง',
        )):
            bk.rejection_label = 'ยกเลิกโดยผู้เรียน'
        elif cmt == 'ติวเตอร์อนุมัติการยกเลิกตามคำขอผู้เรียน':
            bk.rejection_label = 'ยกเลิกตามคำขอ'
        elif cmt in ('ติวเตอร์ยกเลิกการเรียน', 'ติวเตอร์ยกเลิกการเรียนตามคำขอผู้เรียน'):
            bk.rejection_label = 'ยกเลิกโดยติวเตอร์'

        completion = None
        review_record = None
        try:
            completion = bk.jobcompletion
        except JobCompletion.DoesNotExist:
            pass
        try:
            review_record = bk.review
        except Review.DoesNotExist:
            pass

        # วันที่ด้านหน้าการ์ดต้องสื่อถึงเหตุการณ์ของสถานะปัจจุบัน
        if bk.bk_report_date:
            bk.card_event_label = 'รายงานเมื่อ'
            bk.card_event_date = bk.bk_report_date
        elif bk.bk_status == 6:
            if bk.rejection_label == 'เลยกำหนดตอบรับ':
                bk.card_event_label = 'ยกเลิกอัตโนมัติเมื่อ'
            elif 'ยกเลิก' in bk.rejection_label:
                bk.card_event_label = 'ยกเลิกเมื่อ'
            else:
                bk.card_event_label = 'ปฏิเสธเมื่อ'
            bk.card_event_date = bk.closed_at
        elif bk.bk_status in (4, 5):
            bk.card_event_label = 'เสร็จสิ้นเมื่อ'
            bk.card_event_date = (
                completion.jc_confirm_date if completion else None
            )
            if not bk.card_event_date and review_record:
                bk.card_event_date = review_record.rv_date
        elif bk.bk_status == 3:
            bk.card_event_label = 'แจ้งจบงานเมื่อ'
            bk.card_event_date = (
                completion.jc_complete_date if completion else None
            )
        elif bk.bk_status == 2:
            bk.card_event_label = 'เรียนสิ้นสุดเมื่อ'
            bk.card_event_date = bk.lesson_end_datetime
        elif bk.bk_status == 1:
            bk.card_event_label = 'รับงานเมื่อ'
            bk.card_event_date = bk.bk_accepted_date
        else:
            bk.card_event_label = 'ส่งคำขอเมื่อ'
            bk.card_event_date = bk.bk_date

        bk.tutor_can_report_after_end = (
            bk.bk_status in (1, 2)
            and bk.lesson_end_datetime
            and now >= bk.lesson_end_datetime
            and not bk.bk_report_date
        )

        bk.can_report_problem_after_end = _can_report_problem(bk, now)
        first_statement = None
        try:
            first_statement = next(iter(bk.report_statements.all()), None)
        except Exception:
            first_statement = None

        bk.report_by_tutor = (
            cmt.startswith(TUTOR_PROBLEM_REPORT_MARKER)
            or (first_statement and first_statement.brs_role == 'tutor')
        )

    return bookings


def _can_report_problem(booking, now=None):
    now = now or timezone.now()
    lesson_end = _get_lesson_end_datetime(booking)
    return (
        booking.bk_status in (1, 2, 3)
        and lesson_end
        and now >= lesson_end
        and not booking.bk_report_date
    )


def _auto_close_free_reports():
    cutoff = timezone.now() - timezone.timedelta(hours=24)
    free_reports = (
        Booking.objects
        .filter(
            bk_rate_per_person=0,
            bk_report_date__isnull=False,
            bk_report_resolved_date__isnull=True,
            bk_report_date__lte=cutoff,
        )
        .select_related('ts_id')
    )

    for bk in free_reports:
        update_fields = ['bk_status', 'bk_cmt', 'bk_report_resolved_date']
        bk.bk_status = 4
        bk.bk_cmt = FREE_REPORT_AUTO_CLOSE_NOTE
        bk.bk_report_resolved_date = timezone.now()
        bk.save(update_fields=update_fields)


def _notify_member(member, notif_type, message, url):
    try:
        from apps.notifications.signals import _notif_member
        _notif_member(member, notif_type, message, url)
    except Exception:
        logger.exception('สร้าง Notification ไม่สำเร็จ: type=%s member=%s', notif_type, member.pk)


def _normalize_report_reason(reason):
    reason = (reason or '').strip()
    return REPORT_REASON_NORMALIZE.get(reason, reason)


def _refund_locked_credit_to_student(booking):
    total_credit = booking.total_credit
    # ล็อกยอดเครดิตและช่วงเวลาไว้ใน transaction เดียวกับ Booking
    student = Member.objects.select_for_update().get(pk=booking.member_id)
    student.mb_locked_crd = max(0, student.mb_locked_crd - total_credit)
    student.save(update_fields=['mb_locked_crd'])

    return total_credit


def _build_slot_groups(bookings):
    """จัด Booking เป็นรอบเรียน โดยยังเก็บการตัดสินใจของแต่ละ Booking แยกกัน"""
    groups = {}
    for booking in bookings:
        key = f'ts-{booking.ts_id_id}' if booking.ts_id_id else f'legacy-{booking.bk_id}'
        if key not in groups:
            slot = booking.ts_id
            capacity = booking.tutc_id.tutc_max_stu
            groups[key] = SimpleNamespace(
                key=key,
                slot=slot,
                course=booking.tutc_id,
                lesson_datetime=booking.bk_stu_datetime,
                capacity=capacity,
                reserved_seats=0,
                remaining_seats=get_remaining_seats(slot) if slot else 0,
                meeting_detail=(
                    (slot.ts_meeting_detail if slot else '')
                    or booking.tutc_id.tutc_meeting_detail
                    or ''
                ),
                pending=[],
                accepted=[],
                awaiting_activity=[],
                all_bookings=[],
            )
        group = groups[key]
        group.all_bookings.append(booking)
        if booking.bk_status == 0:
            group.pending.append(booking)
        elif booking.bk_status == 1:
            group.accepted.append(booking)
        elif booking.bk_status == 2:
            group.awaiting_activity.append(booking)

    now = timezone.now()
    for group in groups.values():
        group.pending_seats = sum(item.bk_stu_count for item in group.pending)
        group.accepted_seats = sum(item.bk_stu_count for item in group.accepted)
        group.awaiting_activity_seats = sum(
            item.bk_stu_count for item in group.awaiting_activity
        )
        group.completion_items = group.accepted + group.awaiting_activity
        group.completion_seats = sum(
            item.bk_stu_count for item in group.completion_items
        )
        group.has_started = bool(group.lesson_datetime and now >= group.lesson_datetime)
        # เปิดปุ่มบันทึกผลเมื่อสิ้นสุดเวลาเรียนของรอบเท่านั้น
        group.lesson_end_datetime = (
            timezone.make_aware(
                timezone.datetime.combine(group.slot.sd_id.sd_date, group.slot.ts_end_time),
                timezone.get_current_timezone(),
            )
            if group.slot and group.slot.ts_end_time else None
        )
        group.can_finish_teaching = bool(
            group.lesson_end_datetime and now >= group.lesson_end_datetime
        )
        group.reserved_seats = group.capacity - group.remaining_seats if group.slot else sum(
            item.bk_stu_count for item in group.all_bookings
        )
        group.total_credit = sum(item.total_credit for item in group.all_bookings)
        group.pending_credit = sum(item.total_credit for item in group.pending)
        group.response_deadline = (
            get_tutor_response_deadline_at(group.slot) if group.slot else None
        )
    return list(groups.values())


def _get_report_statement_role(booking, member):
    if booking.member_id == member.pk:
        return 'student', 'bookings:student_bookings'

    try:
        tutor_member = booking.tutc_id.tut_id.tut_id
    except Exception:
        tutor_member = None

    if tutor_member and tutor_member.pk == member.pk:
        return 'tutor', 'bookings:tutor_requests'

    return None, 'home'


def _create_report_statement(booking, member, role, detail):
    return BookingReportStatement.objects.create(
        bk_id=booking,
        member=member,
        brs_role=role,
        brs_desc=detail,
        brs_date=timezone.now(),
    )


# ─── ฝั่งติวเตอร์: คำขอจองทั้งหมด ───────────────────────────────────────────
@login_required
def tutor_requests(request):
    try:
        tutor = request.user.member.tutor
    except Exception:
        messages.error(request, 'คุณไม่มีสิทธิ์เข้าถึงหน้านี้')
        return redirect('home')

    process_time_based_bookings()
    _auto_close_free_reports()

    bookings = list(
        Booking.objects
        .filter(tutc_id__tut_id=tutor)
        .select_related(
            'member', 'tutc_id', 'tutc_id__crs_id',
            'ts_id', 'ts_id__sd_id', 'jobcompletion', 'review',
        )
        .prefetch_related('report_statements', 'report_statements__member')
        .order_by('-bk_date')
    )
    _decorate_cancel_flags(bookings)

    reported_bookings = [b for b in bookings if b.bk_report_date]
    normal_bookings   = [b for b in bookings if not b.bk_report_date]

    pending   = [b for b in normal_bookings if b.bk_status == 0]   # รอยืนยัน
    accepted  = [
        b for b in normal_bookings
        if b.bk_status == 1 and not b.can_finish_teaching
    ]   # รับงานแล้วและยังไม่สิ้นสุดเวลาเรียน
    studying  = [b for b in normal_bookings if b.bk_status == 2]   # รอแจ้งจบงาน (เรียนแล้ว)
    notified  = [b for b in normal_bookings if b.bk_status == 3]   # แจ้งจบงานแล้ว
    completion_bookings = [
        b for b in normal_bookings
        if b.bk_status == 3 or (b.bk_status == 2 and not b.ts_id_id)
    ]
    done      = [b for b in normal_bookings if b.bk_status in (4, 5)]  # เสร็จสิ้น + รีวิวแล้ว
    rejected  = [b for b in normal_bookings if b.bk_status == 6]
    slot_groups = _build_slot_groups(normal_bookings)
    pending_groups = [group for group in slot_groups if group.pending]
    accepted_groups = [
        group for group in slot_groups
        if group.accepted and not group.can_finish_teaching
    ]
    completion_pending_groups = [
        group for group in slot_groups
        if (
            (group.accepted and group.can_finish_teaching)
            or group.awaiting_activity
        )
    ]
    # เรียงรอบที่รับงานแล้วตามวันเวลาเรียนที่ใกล้ปัจจุบันที่สุด
    current_time = timezone.now()
    accepted_groups.sort(key=lambda group: (
        abs((group.lesson_datetime - current_time).total_seconds())
        if group.lesson_datetime else float('inf')
    ))
    completion_pending_groups.sort(key=lambda group: (
        group.lesson_end_datetime or group.lesson_datetime
    ), reverse=True)
    accepted_count = sum(len(group.accepted) for group in accepted_groups)
    completion_count = (
        len(completion_bookings)
        + sum(len(group.completion_items) for group in completion_pending_groups)
    )

    return render(request, 'bookings/tutor_requests.html', {
        'pending':      pending,
        'accepted':     accepted,
        'studying':     studying,
        'notified':     notified,
        'completion_bookings': completion_bookings,
        'done':         done,
        'rejected':     rejected,
        'pending_groups': pending_groups,
        'accepted_groups': accepted_groups,
        'completion_pending_groups': completion_pending_groups,
        'accepted_count': accepted_count,
        'completion_count': completion_count,
        'reported_bookings': reported_bookings,
        'all_bookings': bookings,
        'booking_state_token': get_member_booking_state_token(request.user.member),
    })


# ─── ฝั่งติวเตอร์: รับงาน ────────────────────────────────────────────────────
@login_required
def booking_accept(request, bk_id):
    if request.method != 'POST':
        return redirect('bookings:tutor_requests')

    try:
        tutor = request.user.member.tutor
    except Exception:
        messages.error(request, 'ไม่มีสิทธิ์')
        return redirect('home')

    process_overdue_pending_bookings()

    changed_meeting = False
    previously_accepted = []
    booking_preview = Booking.objects.only('bk_id', 'ts_id').filter(
        bk_id=bk_id,
        tutc_id__tut_id=tutor,
        bk_status=0,
    ).first()
    if not booking_preview:
        messages.warning(request, 'คำขอนี้ไม่ได้อยู่ในสถานะรอตอบรับหรือเลยกำหนดแล้ว')
        return redirect('/bookings/tutor/?tab=pending')
    with transaction.atomic():
        slot = None
        if booking_preview.ts_id_id:
            slot = TimeSlot.objects.select_for_update().select_related(
                'sd_id', 'sd_id__tutc_id'
            ).get(pk=booking_preview.ts_id_id)
        bk = get_object_or_404(
            Booking.objects.select_for_update().select_related('tutc_id', 'ts_id'),
            bk_id=bk_id,
            tutc_id__tut_id=tutor,
            bk_status=0,
        )
        if slot:
            if slot.ts_status == 2 or timezone.now() > get_tutor_response_deadline_at(slot):
                messages.error(request, 'เลยกำหนดเวลาตอบรับการจองรอบนี้แล้ว')
                return redirect('/bookings/tutor/?tab=pending')

            meeting_detail = request.POST.get('meeting_detail', '').strip()
            meeting_confirmed = request.POST.get('meeting_confirmed') == '1'
            if not meeting_confirmed or not meeting_detail:
                messages.error(request, 'กรุณาตรวจสอบและยืนยันรายละเอียดนัดหมายให้ชัดเจนก่อนรับงาน')
                return redirect('/bookings/tutor/?tab=pending')

            old_detail = (slot.ts_meeting_detail or '').strip()
            changed_meeting = bool(old_detail and old_detail != meeting_detail)
            if changed_meeting:
                previously_accepted = list(
                    Booking.objects.filter(ts_id=slot, bk_status=1)
                    .select_related('member')
                )
            slot.ts_meeting_detail = meeting_detail
            slot.save(update_fields=['ts_meeting_detail'])

        bk.bk_status = 1
        bk.bk_accepted_date = timezone.now()
        bk.save(update_fields=['bk_status', 'bk_accepted_date'])

    if changed_meeting:
        for accepted_booking in previously_accepted:
            _notify_member(
                accepted_booking.member,
                'booking_accepted',
                f'รายละเอียดนัดหมายรอบ BK{accepted_booking.bk_id:05d} มีการเปลี่ยนแปลง โปรดตรวจสอบอีกครั้ง',
                '/bookings/my/?tab=1',
            )

    messages.success(request, f'รับงาน BK{bk.bk_id:05d} เรียบร้อย')
    return redirect('/bookings/tutor/?tab=accepted')


@login_required
def booking_accept_all(request, ts_id):
    """รับเฉพาะรายการที่ยังรอยืนยันในรอบ ณ เวลาที่กด"""
    if request.method != 'POST':
        return redirect('bookings:tutor_requests')

    try:
        tutor = request.user.member.tutor
    except Exception:
        messages.error(request, 'ไม่มีสิทธิ์')
        return redirect('home')

    process_overdue_pending_bookings()

    changed_meeting = False
    previously_accepted = []
    close_slot = request.POST.get('close_slot') == '1'
    with transaction.atomic():
        slot = get_object_or_404(
            TimeSlot.objects.select_for_update().select_related(
                'sd_id', 'sd_id__tutc_id'
            ),
            pk=ts_id,
            sd_id__tutc_id__tut_id=tutor,
        )
        if slot.ts_status == 2 or timezone.now() > get_tutor_response_deadline_at(slot):
            messages.error(request, 'เลยกำหนดเวลาตอบรับการจองรอบนี้แล้ว')
            return redirect('/bookings/tutor/?tab=pending')

        meeting_detail = request.POST.get('meeting_detail', '').strip()
        meeting_confirmed = request.POST.get('meeting_confirmed') == '1'
        if not meeting_confirmed or not meeting_detail:
            messages.error(request, 'กรุณาตรวจสอบและยืนยันรายละเอียดนัดหมายให้ชัดเจนก่อนรับงาน')
            return redirect('/bookings/tutor/?tab=pending')

        pending = list(
            Booking.objects.select_for_update()
            .filter(ts_id=slot, tutc_id__tut_id=tutor, bk_status=0)
            .select_related('member')
            .order_by('bk_date', 'bk_id')
        )
        if not pending:
            messages.info(request, 'ไม่มีรายการรอยืนยันในรอบนี้แล้ว')
            return redirect('/bookings/tutor/?tab=pending')

        old_detail = (slot.ts_meeting_detail or '').strip()
        changed_meeting = bool(old_detail and old_detail != meeting_detail)
        if changed_meeting:
            previously_accepted = list(
                Booking.objects.filter(ts_id=slot, bk_status=1).select_related('member')
            )
        slot.ts_meeting_detail = meeting_detail
        slot.save(update_fields=['ts_meeting_detail'])

        accepted_at = timezone.now()
        for booking in pending:
            booking.bk_status = 1
            booking.bk_accepted_date = accepted_at
            booking.save(update_fields=['bk_status', 'bk_accepted_date'])

        if close_slot:
            slot.ts_status = 2
            slot.save(update_fields=['ts_status'])

    if changed_meeting:
        for accepted_booking in previously_accepted:
            _notify_member(
                accepted_booking.member,
                'booking_accepted',
                f'รายละเอียดนัดหมายรอบ BK{accepted_booking.bk_id:05d} มีการเปลี่ยนแปลง โปรดตรวจสอบอีกครั้ง',
                '/bookings/my/?tab=1',
            )

    if close_slot:
        messages.success(request, f'รับการจอง {len(pending)} รายการและปิดรับรอบนี้แล้ว')
    else:
        messages.success(request, f'รับการจองรอบนี้แล้ว {len(pending)} รายการ โดยรอบยังเปิดรับเพิ่ม')
    return redirect('/bookings/tutor/?tab=accepted')


# ─── ฝั่งติวเตอร์: ปฏิเสธงาน ────────────────────────────────────────────────
@login_required
def booking_reject(request, bk_id):
    if request.method != 'POST':
        return redirect('bookings:tutor_requests')

    reject_reason = request.POST.get('reject_reason', '').strip()
    if not reject_reason:
        messages.error(request, 'กรุณาระบุเหตุผลที่ปฏิเสธงาน')
        return redirect('/bookings/tutor/?tab=pending')

    try:
        tutor = request.user.member.tutor
    except Exception:
        messages.error(request, 'ไม่มีสิทธิ์')
        return redirect('home')

    process_overdue_pending_bookings()
    if not Booking.objects.filter(
        bk_id=bk_id,
        tutc_id__tut_id=tutor,
        bk_status=0,
    ).exists():
        messages.warning(request, 'คำขอนี้ไม่ได้อยู่ในสถานะรอตอบรับหรือเลยกำหนดแล้ว')
        return redirect('/bookings/tutor/?tab=pending')

    try:
        with transaction.atomic():
            bk = get_object_or_404(
                Booking.objects.select_for_update(),
                bk_id=bk_id,
                tutc_id__tut_id=tutor,
                bk_status=0,
            )
            total_credit = bk.bk_rate_per_person * bk.bk_stu_count

            # คืนเครดิตที่ล็อกไว้ให้ผู้เรียน
            student = Member.objects.select_for_update().get(pk=bk.member_id)
            student.mb_locked_crd = max(0, student.mb_locked_crd - total_credit)
            student.save(update_fields=['mb_locked_crd'])

            bk.bk_status = 6
            bk.bk_cmt = append_booking_closed_comment(bk.bk_cmt, reject_reason)
            bk.save(update_fields=['bk_status', 'bk_cmt'])

        _notify_member(
            student,
            'booking_rejected',
            f'ติวเตอร์ปฏิเสธการจอง BK{bk.bk_id:05d} ของคุณ',
            '/bookings/my/?tab=6',
        )
        messages.error(request, f'ปฏิเสธคำขอจอง BK{bk.bk_id:05d} และคืนเครดิตให้ผู้เรียนแล้ว')
    except Http404:
        raise
    except Exception:
        messages.error(request, 'เกิดข้อผิดพลาด กรุณาลองใหม่')

    return redirect('/bookings/tutor/?tab=rejected')


# ─── ฝั่งติวเตอร์: เสร็จสิ้นการสอน (1→2) ───────────────────────────────────
@login_required
def mark_studying(request, bk_id):
    """ติวเตอร์กด 'เสร็จสิ้นการสอน' → status 1→2"""
    if request.method != 'POST':
        return redirect('bookings:tutor_requests')

    try:
        tutor = request.user.member.tutor
    except Exception:
        messages.error(request, 'ไม่มีสิทธิ์')
        return redirect('home')

    bk = get_object_or_404(
        Booking.objects.select_related('ts_id'),
        bk_id=bk_id,
        tutc_id__tut_id=tutor,
        bk_status=1,
    )

    if not bk.ts_id or not bk.ts_id.ts_end_time:
        messages.error(request, 'ไม่พบข้อมูลเวลาสิ้นสุดการสอน')
        return redirect('/bookings/tutor/?tab=accepted')

    local_start = timezone.localtime(bk.bk_stu_datetime)

    lesson_end = timezone.datetime.combine(
        local_start.date(),
        bk.ts_id.ts_end_time,
    )
    lesson_end = timezone.make_aware(
        lesson_end,
        timezone.get_current_timezone(),
    )

    if timezone.now() < lesson_end:
        lesson_end_local = timezone.localtime(lesson_end)

        messages.warning(
            request,
            f'กดเสร็จสิ้นการสอนได้หลังเวลาสิ้นสุดการสอนแล้วเท่านั้น  '
            f'นับตั้งแต่ '
            f'{lesson_end_local.strftime("%d/%m/%Y เวลา %H:%M น.")}'
        )
        return redirect('/bookings/tutor/?tab=accepted')

    bk.bk_status = 2
    bk.save(update_fields=['bk_status'])

    messages.success(request, f'บันทึกเสร็จสิ้นการสอน BK{bk.bk_id:05d} แล้ว')

    # ถ้ามี next ให้ redirect ไปหน้านั้น (เช่น tutoring_activity)
    next_url = request.POST.get('next', '')
    if next_url and next_url.startswith('/'):
        return redirect(next_url)
    return redirect('/bookings/tutor/?tab=completion')


# ─── ฝั่งนักเรียน: ประวัติการจอง ────────────────────────────────────────────
@login_required
def student_bookings(request):
    try:
        mb = request.user.member
    except Exception:
        return redirect('home')

    # ตรวจทุกกำหนดเวลาก่อนอ่านข้อมูล เพื่อไม่แสดงสถานะเก่าบนหน้าเว็บ
    process_time_based_bookings()
    mb.refresh_from_db(fields=['mb_deposit_crd', 'mb_income_crd', 'mb_locked_crd'])
    _auto_close_free_reports()

    bookings = list(
        Booking.objects
        .filter(member=mb)
        .select_related(
            'tutc_id', 'tutc_id__crs_id',
            'tutc_id__tut_id', 'tutc_id__tut_id__tut_id',
            'ts_id', 'ts_id__sd_id', 'jobcompletion', 'review',
        )
        .prefetch_related('report_statements', 'report_statements__member')
        .order_by('-bk_date')
    )
    _decorate_cancel_flags(bookings)

    return render(request, 'bookings/student_bookings.html', {
        'bookings':   bookings,
        'mb_credit':  mb.mb_deposit_crd + mb.mb_income_crd,
        'booking_state_token': get_member_booking_state_token(mb),
    })


# ═══════════════════════════════════════════════════════════════
# P13 — กิจกรรมการติว (ติวเตอร์อัปโหลดรูป + สรุปเนื้อหา)
# ═══════════════════════════════════════════════════════════════
@login_required
def tutoring_activity(request, bk_id):
    """ติวเตอร์อัปโหลดหลักฐานการสอนและสรุปเนื้อหา — รับเฉพาะ status=2"""
    try:
        tutor = request.user.member.tutor
    except Exception:
        messages.error(request, 'ไม่มีสิทธิ์เข้าถึงหน้านี้')
        return redirect('home')

    bk = get_object_or_404(Booking, bk_id=bk_id, tutc_id__tut_id=tutor, bk_status=2)

    try:
        activity = bk.tutoringactivity
    except TutoringActivity.DoesNotExist:
        activity = None

    if request.method == 'POST':
        action = request.POST.get('action', 'save')
        desc   = request.POST.get('ta_desc', '').strip()

        # บันทึกรูปที่อัปโหลดใหม่ลง DB ก่อนเสมอ
        with transaction.atomic():
            if activity is None:
                activity = TutoringActivity(bk_id=bk)
            import os
            for field, key in [('ta_img1', 'ta_img1'), ('ta_img2', 'ta_img2'), ('ta_img3', 'ta_img3')]:
                if request.FILES.get(key):
                    img = request.FILES[key]
                    ext = os.path.splitext(img.name)[1].lower() or '.jpg'
                    img.name = f'activity_bk_id={bk.bk_id}_{field}{ext}'
                    setattr(activity, field, img)
            if desc:
                activity.ta_desc = desc
            activity.save()

        if action == 'save':
            messages.success(request, 'บันทึกความคืบหน้าแล้ว')
            return redirect('/bookings/tutor/?tab=completion')

        else:
            # submit — validate ครบก่อนส่ง
            errors = []
            has_img = activity.ta_img1 or activity.ta_img2 or activity.ta_img3
            if not has_img:
                errors.append('กรุณาอัปโหลดรูปภาพหลักฐานการสอนอย่างน้อย 1 รูป')
            if not desc:
                errors.append('กรุณาเขียนสรุปเนื้อหาการสอน')

            if errors:
                for e in errors:
                    messages.error(request, e)
                form = TutoringActivityForm(instance=activity)
            else:
                with transaction.atomic():
                    activity.ta_desc = desc
                    activity.save()
                    bk.bk_status = 3
                    bk.save()
                    JobCompletion.objects.update_or_create(
                        bk_id=bk,
                        defaults={'jc_complete_date': timezone.now(), 'jc_confirm_date': None},
                    )
                messages.success(request, 'ส่งคำขอเสร็จสิ้นงานเรียบร้อย กำลังรอผู้เรียนยืนยัน')
                return redirect('/bookings/tutor/?tab=completion')
    else:
        form = TutoringActivityForm(instance=activity)

    return render(request, 'bookings/tutoring_activity.html', {
        'bk':       bk,
        'form':     form,
        'activity': activity,
    })


@login_required
def tutoring_activity_group(request, ts_id):
    """บันทึกผลเข้าเรียนและหลักฐานร่วมของผู้เรียนที่ติวเตอร์รับในรอบเดียวกัน"""
    try:
        tutor = request.user.member.tutor
    except Exception:
        messages.error(request, 'ไม่มีสิทธิ์เข้าถึงหน้านี้')
        return redirect('home')

    slot = get_object_or_404(
        TimeSlot.objects.select_related('sd_id', 'sd_id__tutc_id'),
        pk=ts_id,
        sd_id__tutc_id__tut_id=tutor,
    )
    lesson_end = timezone.make_aware(
        timezone.datetime.combine(slot.sd_id.sd_date, slot.ts_end_time),
        timezone.get_current_timezone(),
    )
    if timezone.now() < lesson_end:
        messages.warning(request, 'บันทึกผลการสอนได้หลังสิ้นสุดเวลาเรียนของรอบนี้')
        return redirect('/bookings/tutor/?tab=accepted')

    if request.method == 'POST' and request.POST.get('action') == 'start_completion':
        with transaction.atomic():
            bookings_to_finish = list(
                Booking.objects.select_for_update().filter(
                    ts_id=slot,
                    tutc_id__tut_id=tutor,
                    bk_status=1,
                    bk_report_date__isnull=True,
                )
            )
            for booking in bookings_to_finish:
                booking.bk_status = 2
                booking.save(update_fields=['bk_status'])

        if not bookings_to_finish:
            messages.info(request, 'รอบนี้ไม่มีรายการที่รอยืนยันเสร็จสิ้นการสอน')
            return redirect('/bookings/tutor/?tab=completion')
        return redirect('bookings:tutoring_activity_group', ts_id=slot.pk)

    bookings = list(
        Booking.objects.filter(ts_id=slot, tutc_id__tut_id=tutor, bk_status=2)
        .select_related('member', 'tutc_id')
        .order_by('bk_date', 'bk_id')
    )
    if not bookings:
        messages.info(request, 'รอบนี้ไม่มีรายการที่รอบันทึกกิจกรรมการสอน')
        return redirect('/bookings/tutor/?tab=completion')

    if request.method == 'POST':
        attendance = {
            booking.pk: request.POST.get(f'attendance_{booking.pk}', '')
            for booking in bookings
        }
        invalid = [value for value in attendance.values() if value not in {'attended', 'absent'}]
        attended = [booking for booking in bookings if attendance[booking.pk] == 'attended']
        absent = [booking for booking in bookings if attendance[booking.pk] == 'absent']
        desc = request.POST.get('ta_desc', '').strip()
        absent_desc = request.POST.get('absent_desc', '').strip()
        uploads = [
            request.FILES.get('ta_img1'),
            request.FILES.get('ta_img2'),
            request.FILES.get('ta_img3'),
        ]

        errors = []
        if invalid:
            errors.append('กรุณาระบุการเข้าเรียนของผู้เรียนให้ครบทุกรายการ')
        if attended and not desc:
            errors.append('กรุณากรอกสรุปเนื้อหาการสอน')
        if attended and not any(uploads):
            errors.append('กรุณาอัปโหลดหลักฐานการสอนอย่างน้อย 1 รูป')
        if absent and not absent_desc:
            errors.append('กรุณาระบุรายละเอียดกรณีผู้เรียนไม่เข้าเรียน')
        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            import os
            with transaction.atomic():
                shared_image_names = [None, None, None]
                for index, booking in enumerate(attended):
                    activity = TutoringActivity(bk_id=booking, ta_desc=desc)
                    if index == 0:
                        for image_index, upload in enumerate(uploads, start=1):
                            if upload:
                                extension = os.path.splitext(upload.name)[1].lower() or '.jpg'
                                upload.name = f'activity_ts_id={slot.ts_id}_img{image_index}{extension}'
                                setattr(activity, f'ta_img{image_index}', upload)
                        activity.save()
                        shared_image_names = [
                            activity.ta_img1.name if activity.ta_img1 else None,
                            activity.ta_img2.name if activity.ta_img2 else None,
                            activity.ta_img3.name if activity.ta_img3 else None,
                        ]
                    else:
                        activity.ta_img1 = shared_image_names[0]
                        activity.ta_img2 = shared_image_names[1]
                        activity.ta_img3 = shared_image_names[2]
                        activity.save()

                    booking.bk_status = 3
                    booking.save(update_fields=['bk_status'])
                    JobCompletion.objects.update_or_create(
                        bk_id=booking,
                        defaults={
                            'jc_complete_date': timezone.now(),
                            'jc_confirm_date': None,
                        },
                    )

                for booking in absent:
                    # รายการไม่เข้าเรียนกลับเข้าสถานะรอพิจารณาปัญหา
                    booking.bk_status = 1
                    booking.bk_report_reason = '5'
                    booking.bk_report_desc = absent_desc
                    booking.bk_report_date = timezone.now()
                    booking.bk_cmt = f'{TUTOR_PROBLEM_REPORT_MARKER} ผู้เรียนไม่เข้าเรียน'
                    booking.save(update_fields=[
                        'bk_status', 'bk_report_reason', 'bk_report_desc',
                        'bk_report_date', 'bk_cmt'
                    ])
                    _create_report_statement(
                        booking,
                        request.user.member,
                        'tutor',
                        absent_desc,
                    )

            for booking in absent:
                _notify_member(
                    booking.member,
                    'booking_reported',
                    f'ติวเตอร์บันทึกว่าผู้เรียนไม่เข้าเรียนใน BK{booking.bk_id:05d} ระบบจะเก็บเครดิตไว้ระหว่างพิจารณา',
                    '/bookings/my/?tab=reported',
                )
            messages.success(
                request,
                f'แจ้งจบงานเสร็จสิ้น กรุณารอการยืนยันจากผู้เรียน (BK{", BK".join(str(b.bk_id) for b in bookings)})'
            )
            return redirect('/bookings/tutor/?tab=completion')

    return render(request, 'bookings/tutoring_activity_group.html', {
        'slot': slot,
        'bookings': bookings,
        'lesson_end': lesson_end,
    })


# ═══════════════════════════════════════════════════════════════
# P15 — ยืนยันการจบงาน (POST-only จาก modal ใน student_bookings)
# ═══════════════════════════════════════════════════════════════
@login_required
def confirm_completion(request, bk_id):
    """ผู้เรียนยืนยันจบงานจาก modal — POST เท่านั้น ไม่มีหน้า render"""
    if request.method != 'POST':
        return redirect('bookings:student_bookings')

    try:
        mb = request.user.member
    except Exception:
        return redirect('home')

    try:
        with transaction.atomic():
            bk = get_object_or_404(
                Booking.objects.select_for_update(),
                bk_id=bk_id,
                member=mb,
                bk_status=3,
            )
            jc = get_object_or_404(
                JobCompletion.objects.select_for_update(),
                bk_id=bk,
            )
            student = Member.objects.select_for_update().get(pk=bk.member_id)
            tutor_member_id = bk.tutc_id.tut_id.tut_id_id
            tutor_member = Member.objects.select_for_update().get(pk=tutor_member_id)
            total_credit = bk.bk_rate_per_person * bk.bk_stu_count
            _pay_tutor(student, tutor_member, total_credit)

            jc.jc_confirm_date = timezone.now()
            jc.save()

            bk.bk_status = 4
            bk.save()

        messages.success(request, 'ยืนยันการจบงานเรียบร้อยแล้ว')
    except Http404:
        raise
    except Exception:
        messages.error(request, 'เกิดข้อผิดพลาด กรุณาลองใหม่')

    return redirect('bookings:review', bk_id=bk_id)


# ═══════════════════════════════════════════════════════════════
# P16 — การรีวิว (ผู้เรียนให้คะแนน ไม่บังคับทันที)
# ═══════════════════════════════════════════════════════════════
@login_required
def review(request, bk_id):
    """ผู้เรียนรีวิวติวเตอร์ — รับ status=4 เท่านั้น"""
    try:
        mb = request.user.member
    except Exception:
        return redirect('home')

    bk = get_object_or_404(Booking, bk_id=bk_id, member=mb, bk_status=4)
    tutor = bk.tutc_id.tut_id

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    rv                  = form.save(commit=False)
                    rv.bk_id            = bk
                    rv.rv_date          = timezone.now()
                    rv.rv_quality       = int(form.cleaned_data['rv_quality'])
                    rv.rv_knowledge     = int(form.cleaned_data['rv_knowledge'])
                    rv.rv_communication = int(form.cleaned_data['rv_communication'])
                    rv.rv_punctuality   = int(form.cleaned_data['rv_punctuality'])
                    rv.rv_satisfaction  = int(form.cleaned_data['rv_satisfaction'])
                    rv.save()

                    bk.bk_status = 5
                    bk.save()

                messages.success(request, 'ขอบคุณสำหรับการรีวิว!')
                return redirect('/bookings/my/?tab=45')

            except Exception:
                messages.error(request, 'เกิดข้อผิดพลาด กรุณาลองใหม่')
        else:
            messages.error(request, 'กรุณาให้คะแนนครบทุกด้าน')
    else:
        form = ReviewForm()

    return render(request, 'bookings/review.html', {
        'bk':    bk,
        'form':  form,
        'tutor': tutor,
    })


# ═══════════════════════════════════════════════════════════════
# รายงานปัญหา — ผู้เรียนรายงานปัญหาเกี่ยวกับกิจกรรมการติว
# ═══════════════════════════════════════════════════════════════
@login_required
def report_problem(request, bk_id):
    """ผู้เรียนรายงานปัญหา — POST only"""
    if request.method != 'POST':
        return redirect('bookings:student_bookings')

    try:
        mb = request.user.member
    except Exception:
        return redirect('home')

    bk        = get_object_or_404(Booking, bk_id=bk_id, member=mb)
    rp_reason = _normalize_report_reason(request.POST.get('rp_reason', ''))
    rp_desc   = request.POST.get('rp_desc', '').strip()

    if bk.bk_report_date:
        messages.warning(request, 'รายการนี้มีการรายงานปัญหาแล้ว ไม่สามารถส่งรายงานซ้ำได้')
        return redirect('/bookings/my/?tab=reported')

    if not _can_report_problem(bk):
        messages.error(request, 'รายงานปัญหาได้เฉพาะรายการที่รับงานแล้วและสิ้นสุดเวลาเรียนแล้ว')
        return redirect('bookings:student_bookings')

    if not rp_reason:
        messages.error(request, 'กรุณาเลือกสาเหตุของปัญหา')
        return redirect('bookings:student_bookings')

    student_reason_codes = (
        STUDENT_COMPLETION_REPORT_CODES
        if bk.bk_status == 3
        else STUDENT_ACTIVE_REPORT_CODES
    )
    if rp_reason not in student_reason_codes:
        messages.error(request, 'สาเหตุการรายงานไม่ถูกต้อง')
        return redirect('bookings:student_bookings')

    if rp_reason == '8' and not rp_desc:
        messages.error(request, 'กรุณาระบุรายละเอียดเมื่อเลือก "อื่น ๆ"')
        return redirect('bookings:student_bookings')

    bk.bk_report_reason = rp_reason
    bk.bk_report_desc   = rp_desc or None
    bk.bk_report_date   = timezone.now()
    bk.save(update_fields=['bk_report_reason', 'bk_report_desc', 'bk_report_date'])
    _create_report_statement(bk, mb, 'student', rp_desc or 'ผู้เรียนรายงานปัญหา')

    _notify_member(
        bk.tutc_id.tut_id.tut_id,
        'booking_reported',
        f'ผู้เรียนรายงานปัญหา BK{bk.bk_id:05d} โปรดเลือกรับทราบหรือเพิ่มคำชี้แจงภายใน 24 ชั่วโมง',
        '/bookings/tutor/?tab=reported',
    )

    return redirect('/bookings/my/?tab=reported&reported=1')


@login_required
def submit_report_statement(request, bk_id):
    """ผู้ถูกรายงานเลือกรับทราบหรือเพิ่มคำชี้แจงได้เพียงหนึ่งอย่าง"""
    if request.method != 'POST':
        return redirect('home')

    try:
        mb = request.user.member
    except Exception:
        return redirect('home')

    bk = get_object_or_404(
        Booking.objects.select_related(
            'member', 'tutc_id', 'tutc_id__tut_id', 'tutc_id__tut_id__tut_id'
        ),
        bk_id=bk_id,
        bk_report_date__isnull=False,
    )
    role, redirect_to = _get_report_statement_role(bk, mb)
    if not role:
        messages.error(request, 'คุณไม่มีสิทธิ์ตอบกลับรายงานสำหรับรายการนี้')
        return redirect('home')
    if role == 'student':
        redirect_to = '/bookings/my/?tab=reported'
    if role == 'tutor':
        redirect_to = '/bookings/tutor/?tab=reported'

    response_action = request.POST.get('response_action', '').strip()
    detail = request.POST.get('statement_desc', '').strip()
    if response_action not in {'acknowledge', 'dispute'}:
        messages.error(request, 'กรุณาเลือกว่าจะรับทราบหรือเพิ่มคำชี้แจง')
        return redirect(redirect_to)
    if response_action == 'acknowledge':
        detail = REPORT_ACKNOWLEDGEMENT_TEXT
    elif not detail:
        messages.error(request, 'กรุณาระบุคำชี้แจงก่อนส่ง')
        return redirect(redirect_to)

    with transaction.atomic():
        bk = get_object_or_404(
            Booking.objects.select_for_update().select_related(
                'member', 'tutc_id', 'tutc_id__tut_id', 'tutc_id__tut_id__tut_id'
            ),
            bk_id=bk_id,
            bk_report_date__isnull=False,
        )
        if bk.bk_report_resolved_date:
            messages.warning(request, 'รายงานนี้พิจารณาเสร็จสิ้นแล้ว')
            return redirect(redirect_to)
        if bk.report_statements.filter(brs_role=role).exists():
            messages.warning(request, 'คุณตอบกลับรายงานนี้แล้ว และเลือกตอบได้เพียง 1 อย่าง')
            return redirect(redirect_to)

        _create_report_statement(bk, mb, role, detail)

    if role == 'student':
        notification_text = (
            f'ผู้เรียนรับทราบรายงาน BK{bk.bk_id:05d} ยอมรับผิดและไม่มีข้อโต้แย้ง'
            if response_action == 'acknowledge'
            else f'ผู้เรียนเพิ่มคำชี้แจงในรายงาน BK{bk.bk_id:05d}'
        )
        _notify_member(
            bk.tutc_id.tut_id.tut_id,
            'booking_report_statement',
            notification_text,
            '/bookings/tutor/?tab=reported',
        )
    else:
        notification_text = (
            f'ติวเตอร์รับทราบรายงาน BK{bk.bk_id:05d} ยอมรับผิดและไม่มีข้อโต้แย้ง'
            if response_action == 'acknowledge'
            else f'ติวเตอร์เพิ่มคำชี้แจงในรายงาน BK{bk.bk_id:05d}'
        )
        _notify_member(
            bk.member,
            'booking_report_statement',
            notification_text,
            '/bookings/my/?tab=reported',
        )

    success_message = (
        'บันทึกการรับทราบรายงานแล้ว'
        if response_action == 'acknowledge'
        else 'เพิ่มคำชี้แจงแล้ว'
    )
    messages.success(request, success_message)
    return redirect(redirect_to)


@login_required
def student_request_cancel_booking(request, bk_id):
    """ผู้เรียนยกเลิกรายการที่รับงานแล้วได้เองเมื่อเหลือมากกว่า 24 ชั่วโมง"""
    if request.method != 'POST':
        return redirect('bookings:student_bookings')

    try:
        mb = request.user.member
    except Exception:
        return redirect('home')

    process_time_based_bookings()

    with transaction.atomic():
        bk = get_object_or_404(
            Booking.objects.select_for_update(),
            bk_id=bk_id,
            member=mb,
            bk_status=1,
        )
        now = timezone.now()
        direct_cancel_before = bk.bk_stu_datetime - timezone.timedelta(hours=24)
        if now >= direct_cancel_before:
            messages.error(request, 'เหลือเวลาไม่เกิน 24 ชั่วโมงก่อนเรียน กรุณาแชทแจ้งเหตุผลให้ติวเตอร์ทราบและขอให้ติวเตอร์ดำเนินการยกเลิก')
            return redirect('bookings:student_bookings')

        cancel_reason = (request.POST.get('cancel_reason') or '').strip()
        if not cancel_reason:
            messages.error(request, 'กรุณาระบุเหตุผลในการยกเลิกการเรียน')
            return redirect('bookings:student_bookings')
        if len(cancel_reason) > 1000:
            messages.error(request, 'เหตุผลในการยกเลิกต้องไม่เกิน 1,000 ตัวอักษร')
            return redirect('bookings:student_bookings')

        tutor_member = bk.tutc_id.tut_id.tut_id
        total_credit = _refund_locked_credit_to_student(bk)
        bk.bk_status = 6
        bk.bk_cmt = append_booking_closed_comment(
            bk.bk_cmt,
            'ผู้เรียนยกเลิกการเรียน ก่อนถึงเวลาเริ่มเรียนมากกว่า 24 ชั่วโมง\n'
            f'{STUDENT_CANCEL_REASON_MARKER}\n{cancel_reason}',
        )
        bk.save(update_fields=['bk_status', 'bk_cmt'])

    _notify_member(
        tutor_member,
        'booking_cancelled',
        f'ผู้เรียนยกเลิกการจอง BK{bk.bk_id:05d} ของคุณ',
        '/bookings/tutor/?tab=rejected',
    )
    messages.success(request, f'ยกเลิกการเรียนแล้ว เครดิต {total_credit} เครดิตได้รับการปลดล็อกแล้ว')
    return redirect('/bookings/my/?tab=6')


@login_required
def tutor_approve_cancel_booking(request, bk_id):
    """คง URL เดิมไว้สำหรับความเข้ากันได้ แต่ระบบไม่มีขั้นตอนอนุมัติคำขอยกเลิกแล้ว"""
    messages.warning(request, 'ระบบยกเลิกขั้นตอนอนุมัติคำขอยกเลิกแล้ว')
    return redirect('bookings:tutor_requests')


@login_required
def tutor_reject_cancel_booking(request, bk_id):
    """คง URL เดิมไว้สำหรับความเข้ากันได้ แต่ระบบไม่มีขั้นตอนปฏิเสธคำขอยกเลิกแล้ว"""
    messages.warning(request, 'ระบบยกเลิกขั้นตอนพิจารณาคำขอยกเลิกแล้ว')
    return redirect('bookings:tutor_requests')


@login_required
def tutor_cancel_for_student_booking(request, bk_id):
    """ติวเตอร์ยกเลิกงานที่รับแล้วก่อนเส้นตาย ปลดล็อกเครดิตและคืนจำนวนที่นั่ง"""
    if request.method != 'POST':
        return redirect('bookings:tutor_requests')

    try:
        tutor = request.user.member.tutor
    except Exception:
        messages.error(request, 'ไม่มีสิทธิ์')
        return redirect('home')

    process_time_based_bookings()

    with transaction.atomic():
        bk = get_object_or_404(
            Booking.objects.select_for_update(),
            bk_id=bk_id,
            tutc_id__tut_id=tutor,
            bk_status=1,
        )
        _decorate_cancel_flags([bk])

        if not bk.tutor_cancel_for_student_available:
            messages.warning(
                request,
                'ไม่สามารถยกเลิกการเรียนรายการนี้ได้'
            )
            return redirect('bookings:tutor_requests')

        total_credit = _refund_locked_credit_to_student(bk)
        bk.bk_status = 6
        bk.bk_cmt = append_booking_closed_comment(
            bk.bk_cmt,
            'ติวเตอร์ยกเลิกการเรียน',
        )
        bk.save(update_fields=['bk_status', 'bk_cmt'])

    _notify_member(
        bk.member,
        'booking_cancelled',
        f'ติวเตอร์ยกเลิกการเรียน BK{bk.bk_id:05d} เครดิต {total_credit} เครดิตได้รับคืนเข้าบัญชีแล้ว',
        '/bookings/my/?tab=6',
    )
    messages.success(request, f'ยกเลิกการเรียน BK{bk.bk_id:05d} และคืนเครดิตให้ผู้เรียนแล้ว')
    return redirect('/bookings/tutor/?tab=rejected')


@login_required
def tutor_escalate_cancel_dispute(request, bk_id):
    """ติวเตอร์รายงานปัญหาหลังสิ้นสุดเวลาเรียนแล้ว"""
    if request.method != 'POST':
        return redirect('bookings:tutor_requests')

    try:
        tutor = request.user.member.tutor
    except Exception:
        messages.error(request, 'ไม่มีสิทธิ์')
        return redirect('home')

    bk = get_object_or_404(
        Booking.objects.select_related('member', 'tutc_id', 'ts_id'),
        bk_id=bk_id,
        tutc_id__tut_id=tutor,
        bk_status__in=(1, 2),
    )
    _decorate_cancel_flags([bk])
    now = timezone.now()

    if not _can_report_problem(bk, now):
        messages.warning(request, 'รายงานปัญหาได้เฉพาะรายการที่รับงานแล้ว สิ้นสุดเวลาเรียนแล้ว และยังไม่เคยมีรายงาน')
        return redirect('bookings:tutor_requests')

    rp_reason = _normalize_report_reason(request.POST.get('rp_reason', ''))
    detail = request.POST.get('dispute_desc', '').strip()
    if not rp_reason:
        messages.error(request, 'กรุณาเลือกสาเหตุของปัญหา')
        return redirect('bookings:tutor_requests')

    if rp_reason not in TUTOR_REPORT_CODES:
        messages.error(request, 'สาเหตุการรายงานไม่ถูกต้อง')
        return redirect('bookings:tutor_requests')

    if rp_reason == '8' and not detail:
        messages.error(request, 'กรุณาระบุรายละเอียดเมื่อเลือก "อื่น ๆ"')
        return redirect('bookings:tutor_requests')

    bk.bk_report_reason = rp_reason
    bk.bk_report_desc = detail or None
    bk.bk_report_date = timezone.now()
    # เก็บรายงานไว้ในช่องรายงานโดยเฉพาะ
    bk.save(update_fields=['bk_report_reason', 'bk_report_desc', 'bk_report_date'])
    _create_report_statement(bk, request.user.member, 'tutor', detail or 'ติวเตอร์รายงานปัญหา')

    _notify_member(
        bk.member,
        'booking_reported',
        f'ติวเตอร์รายงานปัญหา BK{bk.bk_id:05d} โปรดเลือกรับทราบหรือเพิ่มคำชี้แจงภายใน 24 ชั่วโมง',
        '/bookings/my/?tab=reported',
    )
    messages.success(request, f'ส่งรายงานปัญหา BK{bk.bk_id:05d} แล้ว')
    return redirect('/bookings/tutor/?tab=reported')

# ═══════════════════════════════════════════════════════════════
# ผู้เรียนยกเลิกการจอง — ผู้เรียนยกเลิกการจองเมื่อสถานะยังเป็น 0 (รอติวเตอร์รับ)
# ═══════════════════════════════════════════════════════════════

@login_required
def student_cancel_booking(request, bk_id):
    """ผู้เรียนยกเลิกการจองเมื่อสถานะยังเป็น 0 (รอติวเตอร์รับ)"""
    if request.method == 'POST':
        process_overdue_pending_bookings()
        if not Booking.objects.filter(
            bk_id=bk_id,
            member=request.user.member,
            bk_status=0,
        ).exists():
            messages.warning(request, 'คำขอนี้ไม่ได้อยู่ในสถานะรอตอบรับหรือถูกยกเลิกแล้ว')
            return redirect('bookings:student_bookings')

        with transaction.atomic():
            booking = get_object_or_404(
                Booking.objects.select_for_update(),
                bk_id=bk_id,
                member=request.user.member,
            )

            # ตรวจสถานะอีกครั้งหลังได้ row lock แล้ว
            if booking.bk_status != 0:
                messages.error(request, 'ไม่สามารถยกเลิกการจองในสถานะนี้ได้')
                return redirect('bookings:student_bookings')

            member = Member.objects.select_for_update().get(pk=booking.member_id)
            total = booking.total_credit

            # เปลี่ยนสถานะและบันทึกหมายเหตุ
            booking.bk_status = 6
            booking.bk_cmt = append_booking_closed_comment(
                booking.bk_cmt,
                'ผู้เรียนยกเลิกการจอง',
            )
            booking.save(update_fields=['bk_status', 'bk_cmt'])
            tutor_member = booking.tutc_id.tut_id.tut_id

            # ปลดล็อกเครดิต โดยไม่เพิ่มยอดนำฝากซ้ำเพราะยอดต้นทางยังไม่ถูกหัก
            member.mb_locked_crd = max(0, member.mb_locked_crd - total)
            member.save(update_fields=['mb_locked_crd'])

        _notify_member(
            tutor_member,
            'booking_cancelled',
            f'ผู้เรียนยกเลิกการจอง BK{booking.bk_id:05d} ของคุณ',
            '/bookings/tutor/?tab=rejected',
        )
        messages.success(request, f'ยกเลิกการจอง BK{bk_id:05d} เรียบร้อยแล้ว เครดิต {total} เครดิต ได้รับคืนแล้ว')
        return redirect('/bookings/my/?tab=6')

    booking = get_object_or_404(Booking, bk_id=bk_id, member=request.user.member)
    if booking.bk_status != 0:
        messages.error(request, 'ไม่สามารถยกเลิกการจองในสถานะนี้ได้')

    return redirect('bookings:student_bookings')


# ─── helper: โอนเครดิตจากผู้เรียนไปให้ติวเตอร์ ──────────────────────────────
def _pay_tutor(student, tutor_member, total_credit):
    """
    หักเครดิตผู้เรียนตามลำดับ: deposit ก่อน → income ถ้าไม่พอ
    ลด mb_locked_crd และโอนให้ tutor เป็น mb_income_crd
    ต้องเรียกภายใน transaction.atomic()
    """
    deposit_deduct = min(student.mb_deposit_crd, total_credit)
    income_deduct  = total_credit - deposit_deduct

    student.mb_deposit_crd = max(0, student.mb_deposit_crd - deposit_deduct)
    student.mb_income_crd  = max(0, student.mb_income_crd  - income_deduct)
    student.mb_locked_crd  = max(0, student.mb_locked_crd  - total_credit)
    student.save(update_fields=['mb_deposit_crd', 'mb_income_crd', 'mb_locked_crd'])

    tutor_member.mb_income_crd += total_credit
    tutor_member.save(update_fields=['mb_income_crd'])


