from django.conf import settings
from django.db.models import Sum
from django.utils import timezone

from apps.tutoring.models import TutorRate


# สถานะ 6 คือรายการที่ปฏิเสธหรือยกเลิกแล้ว จึงไม่ใช้ที่นั่ง
INACTIVE_BOOKING_STATUS = 6
COURSE_EDIT_BLOCKING_STATUSES = (0, 1)


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
        and now < get_booking_close_at(slot)
        and get_remaining_seats(slot) > 0
    )
