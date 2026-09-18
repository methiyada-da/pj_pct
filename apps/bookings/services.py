import hashlib
import logging

from django.conf import settings
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.tutoring.models import TutorRate


logger = logging.getLogger(__name__)


# สถานะ 6 คือรายการที่ปฏิเสธหรือยกเลิกแล้ว จึงไม่ใช้ที่นั่ง
INACTIVE_BOOKING_STATUS = 6
COURSE_EDIT_BLOCKING_STATUSES = (0, 1)
BOOKING_CLOSED_AT_MARKER = '[วันเวลาที่ปฏิเสธหรือยกเลิก]'


def append_booking_closed_comment(comment, note='', *, closed_at=None):
    """ต่อหมายเหตุและวันเวลาปิดรายการ โดยไม่เขียนทับข้อความเดิม"""
    parts = []
    current_comment = (comment or '').strip()
    new_note = (note or '').strip()
    if current_comment:
        parts.append(current_comment)
    if new_note and new_note != current_comment:
        parts.append(new_note)

    occurred_at = timezone.localtime(closed_at or timezone.now())
    parts.append(f'{BOOKING_CLOSED_AT_MARKER} {occurred_at.isoformat(timespec="seconds")}')
    return '\n'.join(parts)


def get_booking_closed_at(comment):
    """อ่านวันเวลาที่ปฏิเสธหรือยกเลิกจาก bk_cmt"""
    for line in reversed((comment or '').splitlines()):
        if not line.startswith(BOOKING_CLOSED_AT_MARKER):
            continue
        value = line[len(BOOKING_CLOSED_AT_MARKER):].strip()
        parsed = parse_datetime(value)
        if parsed and timezone.is_naive(parsed):
            parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
        return parsed
    return None


def strip_booking_closed_at(comment):
    """ซ่อนบรรทัดวันเวลาภายในเมื่อแสดงหมายเหตุให้ผู้ใช้"""
    return '\n'.join(
        line for line in (comment or '').splitlines()
        if not line.startswith(BOOKING_CLOSED_AT_MARKER)
    ).strip()


def get_slot_start(slot):
    """คืนวันเวลาเริ่มเรียนแบบ timezone-aware"""
    start = timezone.datetime.combine(
        slot.sd_id.sd_date,
        slot.ts_start_time,
    )
    return timezone.make_aware(start, timezone.get_current_timezone())


def get_booking_close_at(slot):
    return get_slot_start(slot) - timezone.timedelta(
        hours=settings.BOOKING_CLOSE_HOURS,
    )


def get_tutor_response_deadline_at(slot):
    return get_slot_start(slot) - timezone.timedelta(
        hours=settings.TUTOR_RESPONSE_DEADLINE_HOURS,
    )


def get_slot_end(slot):
    """คืนวันเวลาสิ้นสุดของช่วงเรียนแบบ timezone-aware"""
    end = timezone.datetime.combine(
        slot.sd_id.sd_date,
        slot.ts_end_time,
    )
    return timezone.make_aware(end, timezone.get_current_timezone())


def _notify_member(member, notif_type, message, url):
    """การประมวลผลสถานะต้องสำเร็จได้ แม้ส่วนแจ้งเตือนขัดข้อง"""
    try:
        from apps.notifications.signals import _notif_member
        _notif_member(member, notif_type, message, url)
    except Exception:
        logger.exception(
            'สร้าง Notification ไม่สำเร็จ: type=%s member=%s',
            notif_type,
            member.pk,
        )


def process_overdue_pending_bookings(*, now=None):
    """ยกเลิกคำขอที่ติวเตอร์ไม่ตอบรับภายในกำหนดและปลดล็อกเครดิต"""
    from apps.accounts.models import Member
    from .models import Booking

    now = now or timezone.now()
    booking_ids = []
    pending = (
        Booking.objects
        .filter(bk_status=0, ts_id__isnull=False)
        .select_related('ts_id__sd_id')
    )
    for booking in pending:
        if now > get_tutor_response_deadline_at(booking.ts_id):
            booking_ids.append(booking.pk)

    processed = 0
    for booking_id in booking_ids:
        student = None
        tutor_member = None
        booking = None
        with transaction.atomic():
            booking = (
                Booking.objects.select_for_update()
                .select_related(
                    'member', 'ts_id__sd_id',
                    'tutc_id__tut_id__tut_id',
                )
                .filter(pk=booking_id, bk_status=0)
                .first()
            )
            if not booking or now <= get_tutor_response_deadline_at(booking.ts_id):
                continue

            student = Member.objects.select_for_update().get(pk=booking.member_id)
            student.mb_locked_crd = max(
                0,
                student.mb_locked_crd - booking.total_credit,
            )
            student.save(update_fields=['mb_locked_crd'])

            booking.bk_status = INACTIVE_BOOKING_STATUS
            booking.bk_cmt = append_booking_closed_comment(
                booking.bk_cmt,
                '[เลยกำหนดตอบรับ] ระบบยกเลิกการจองอัตโนมัติ',
                closed_at=now,
            )
            booking.save(update_fields=['bk_status', 'bk_cmt'])
            tutor_member = booking.tutc_id.tut_id.tut_id

        _notify_member(
            student,
            'booking_rejected',
            f'การจอง BK{booking.bk_id:05d} เลยกำหนดตอบรับ เครดิตได้รับการปลดล็อกแล้ว',
            '/bookings/my/?tab=6',
        )
        _notify_member(
            tutor_member,
            'booking_cancelled',
            f'ระบบยกเลิกคำขอ BK{booking.bk_id:05d} เนื่องจากเลยกำหนดตอบรับ',
            '/bookings/tutor/?tab=rejected',
        )
        processed += 1

    return processed


def process_overdue_completions(*, now=None):
    """ยืนยันจบงานและโอนเครดิตเมื่อผู้เรียนไม่ดำเนินการภายในกำหนด"""
    from apps.accounts.models import Member
    from .models import Booking, JobCompletion

    now = now or timezone.now()
    cutoff = now - timezone.timedelta(
        hours=settings.COMPLETION_AUTO_CONFIRM_HOURS,
    )
    booking_ids = list(
        Booking.objects.filter(
            bk_status=3,
            jobcompletion__jc_complete_date__lte=cutoff,
        ).values_list('pk', flat=True)
    )

    processed = 0
    for booking_id in booking_ids:
        with transaction.atomic():
            booking = (
                Booking.objects.select_for_update()
                .select_related('tutc_id__tut_id__tut_id')
                .filter(pk=booking_id, bk_status=3)
                .first()
            )
            if not booking:
                continue

            completion = (
                JobCompletion.objects.select_for_update()
                .filter(bk_id=booking)
                .first()
            )
            if not completion or completion.jc_complete_date > cutoff:
                continue

            student = Member.objects.select_for_update().get(pk=booking.member_id)
            tutor_member = Member.objects.select_for_update().get(
                pk=booking.tutc_id.tut_id.tut_id_id,
            )
            total_credit = booking.total_credit
            deposit_deduct = min(student.mb_deposit_crd, total_credit)
            income_deduct = total_credit - deposit_deduct
            student.mb_deposit_crd = max(0, student.mb_deposit_crd - deposit_deduct)
            student.mb_income_crd = max(0, student.mb_income_crd - income_deduct)
            student.mb_locked_crd = max(0, student.mb_locked_crd - total_credit)
            student.save(
                update_fields=['mb_deposit_crd', 'mb_income_crd', 'mb_locked_crd'],
            )
            tutor_member.mb_income_crd += total_credit
            tutor_member.save(update_fields=['mb_income_crd'])

            completion.jc_confirm_date = now
            completion.save(update_fields=['jc_confirm_date'])
            booking.bk_status = 4
            booking.save(update_fields=['bk_status'])
            processed += 1

    return processed


def process_time_based_bookings(*, now=None):
    """ประมวลผลสถานะที่ครบกำหนดทั้งหมดจากเวลาเดียวกัน"""
    now = now or timezone.now()
    return {
        'timed_out': process_overdue_pending_bookings(now=now),
        'completed': process_overdue_completions(now=now),
    }


def get_member_booking_state_token(member, *, now=None):
    """สร้าง token ที่เปลี่ยนเมื่อสถานะหรือสิทธิ์ตามเวลาของสมาชิกเปลี่ยน"""
    from .models import Booking

    now = now or timezone.now()
    bookings = (
        Booking.objects
        .filter(
            Q(member=member)
            | Q(tutc_id__tut_id__tut_id=member),
        )
        .select_related('ts_id__sd_id')
        .order_by('bk_id')
    )

    states = []
    for booking in bookings:
        phase = ''
        if booking.bk_status == 1 and booking.bk_stu_datetime:
            if booking.ts_id_id and booking.ts_id.ts_end_time:
                lesson_end = get_slot_end(booking.ts_id)
            else:
                lesson_end = booking.bk_stu_datetime

            if now >= lesson_end:
                phase = 'finished'
            elif now >= booking.bk_stu_datetime:
                phase = 'studying'
            elif now >= booking.bk_stu_datetime - timezone.timedelta(hours=24):
                phase = 'within_cancel_window'
            else:
                phase = 'direct_cancel'

        states.append((
            booking.bk_id,
            booking.bk_status,
            phase,
            booking.bk_report_date.isoformat() if booking.bk_report_date else '',
            booking.bk_report_resolved_date.isoformat()
            if booking.bk_report_resolved_date else '',
        ))

    return hashlib.sha256(repr(states).encode('utf-8')).hexdigest()


def get_reserved_seats(slot):
    """รวมที่นั่งของรายการที่ยังไม่ถูกปฏิเสธหรือยกเลิก"""
    from .models import Booking

    result = (
        Booking.objects
        .filter(ts_id=slot)
        .exclude(bk_status=INACTIVE_BOOKING_STATUS)
        .aggregate(total=Sum('bk_stu_count'))
    )
    return result['total'] or 0


def get_remaining_seats(slot):
    capacity = slot.sd_id.tutc_id.tutc_max_stu
    return max(0, capacity - get_reserved_seats(slot))


def get_fixed_rate(tutor_course, *, for_update=False):
    """คืนราคาเมื่อคอร์สมีเรทเดียวเท่านั้น คอร์สหลายเรทเดิมต้องให้ติวเตอร์ตั้งใหม่"""
    queryset = TutorRate.objects.filter(tutc_id=tutor_course)
    if for_update:
        queryset = queryset.select_for_update()
    rates = list(queryset.order_by('tut_rate_stu_count', 'tut_rate_id')[:2])
    return rates[0] if len(rates) == 1 else None


def has_active_course_bookings(tutor_course):
    """ราคาและจำนวนรับแก้ไม่ได้ขณะมีรายการรอรับหรือรอเรียน"""
    from .models import Booking

    return Booking.objects.filter(
        tutc_id=tutor_course,
        bk_status__in=COURSE_EDIT_BLOCKING_STATUSES,
    ).exists()


def slot_is_bookable(slot, *, now=None):
    now = now or timezone.now()
    return (
        slot.ts_status != 2
        and slot.sd_id.tutc_id.tutc_status == 1
        and now <= get_booking_close_at(slot)
        and get_remaining_seats(slot) > 0
    )
