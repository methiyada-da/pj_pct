from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db import transaction

from .models import Booking


# ─── ฝั่งติวเตอร์: คำขอจองทั้งหมด ───────────────────────────────────────────
@login_required
def tutor_requests(request):
    try:
        tutor = request.user.member.tutor
    except Exception:
        messages.error(request, 'คุณไม่มีสิทธิ์เข้าถึงหน้านี้')
        return redirect('home')

    bookings = (
        Booking.objects
        .filter(tutc_id__tut_id=tutor)
        .select_related('member', 'tutc_id', 'tutc_id__crs_id', 'ts_id', 'ts_id__sd_id')
        .order_by('-bk_date')
    )

    pending  = [b for b in bookings if b.bk_status == 0]
    accepted = [b for b in bookings if b.bk_status == 1]
    others   = [b for b in bookings if b.bk_status not in (0, 1)]

    STATUS_LABELS = {
        0: ('รอยืนยัน',    'warning'),
        1: ('รับงานแล้ว',  'success'),
        2: ('เรียนแล้ว',   'info'),
        3: ('แจ้งจบงาน',   'primary'),
        4: ('ยืนยันจบงาน', 'success'),
        5: ('รีวิวแล้ว',   'secondary'),
        6: ('ปฏิเสธ',      'danger'),
    }

    return render(request, 'bookings/tutor_requests.html', {
        'pending':       pending,
        'accepted':      accepted,
        'others':        others,
        'status_labels': STATUS_LABELS,
        'all_bookings':  bookings,
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

    bk = get_object_or_404(
        Booking,
        bk_id=bk_id,
        tutc_id__tut_id=tutor,
        bk_status=0,
    )

    bk.bk_status       = 1
    bk.bk_accepted_date = timezone.now()
    bk.save()

    messages.success(request, f'รับงาน BK{bk.bk_id:05d} เรียบร้อย')
    return redirect('bookings:tutor_requests')


# ─── ฝั่งติวเตอร์: ปฏิเสธงาน ────────────────────────────────────────────────
@login_required
def booking_reject(request, bk_id):
    if request.method != 'POST':
        return redirect('bookings:tutor_requests')

    try:
        tutor = request.user.member.tutor
    except Exception:
        messages.error(request, 'ไม่มีสิทธิ์')
        return redirect('home')

    bk = get_object_or_404(
        Booking,
        bk_id=bk_id,
        tutc_id__tut_id=tutor,
        bk_status=0,
    )

    total_credit = bk.bk_rate_per_person * bk.bk_stu_count

    try:
        with transaction.atomic():
            # คืนเครดิตที่ล็อกไว้ให้นักเรียน
            student = bk.member
            student.mb_locked_crd = max(0, student.mb_locked_crd - total_credit)
            student.save()

            # ปลด lock slot
            if bk.ts_id:
                bk.ts_id.ts_status = 0
                bk.ts_id.save()

            bk.bk_status = 6
            bk.bk_cmt    = request.POST.get('reject_reason', '').strip() or None
            bk.save()

        messages.success(request, f'ปฏิเสธงาน BK{bk.bk_id:05d} และคืนเครดิตให้นักเรียนแล้ว')
    except Exception:
        messages.error(request, 'เกิดข้อผิดพลาด กรุณาลองใหม่')

    return redirect('bookings:tutor_requests')


# ─── ฝั่งนักเรียน: ประวัติการจอง ────────────────────────────────────────────
@login_required
def student_bookings(request):
    try:
        mb = request.user.member
    except Exception:
        return redirect('home')

    bookings = (
        Booking.objects
        .filter(member=mb)
        .select_related(
            'tutc_id', 'tutc_id__crs_id',
            'tutc_id__tut_id', 'tutc_id__tut_id__tut_id',
            'ts_id', 'ts_id__sd_id',
        )
        .order_by('-bk_date')
    )

    STATUS_LABELS = {
        0: ('รอยืนยัน',    'warning'),
        1: ('รับงานแล้ว',  'success'),
        2: ('เรียนแล้ว',   'info'),
        3: ('แจ้งจบงาน',   'primary'),
        4: ('ยืนยันจบงาน', 'success'),
        5: ('รีวิวแล้ว',   'secondary'),
        6: ('ปฏิเสธ',      'danger'),
    }

    return render(request, 'bookings/student_bookings.html', {
        'bookings':      bookings,
        'status_labels': STATUS_LABELS,
    })
