# bookings/views.py - views จัดการการจอง และกิจกรรมติว
from urllib import request

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.db.models import Avg

from apps import bookings

from .models import Booking, BookingReportStatement, TutoringActivity, JobCompletion, Review
from .forms import TutoringActivityForm, ReviewForm


STUDENT_CANCEL_MARKER = '[คำขอยกเลิกโดยผู้เรียน]'
TUTOR_CANCEL_REJECT_MARKER = '[ไม่อนุมัติการยกเลิก]'
TUTOR_CANCEL_DISPUTE_MARKER = '[ส่งแอดมินหลังไม่อนุมัติยกเลิก]'
TUTOR_CANCEL_DISPUTE_REASON = 'cancel'
TUTOR_PROBLEM_REPORT_MARKER = '[รายงานโดยติวเตอร์]'
FREE_REPORT_AUTO_CLOSE_NOTE = 'ระบบปิดคำจองรายงานปัญหาการสอนฟรีอัตโนมัติหลังครบ 24 ชั่วโมง'
REPORT_REASON_CODES = {
    '1',
    '2',
    '3',
    '4',
    '5',
    '6',
    '7',
    '8',
    'other',
    't_no_show',
    's_no_show',
    'contact',
    'cannot_contact',
    'agree',
    TUTOR_CANCEL_DISPUTE_REASON,
}
REPORT_REASON_NORMALIZE = {
    't_no_show': '2',
    's_no_show': '5',
    'contact': '6',
    'cannot_contact': '6',
    'agree': '7',
    'other': '8',
}


def _strip_marker(text, marker):
    text = text or ''
    if not text.startswith(marker):
        return ''
    return text[len(marker):].lstrip(' :-')


def _decorate_cancel_flags(bookings):
    now = timezone.now()

    for bk in bookings:
        cmt = bk.bk_cmt or ''

        bk.cancel_request_pending = (
            bk.bk_status == 1
            and cmt.startswith(STUDENT_CANCEL_MARKER)
        )

        bk.cancel_request_rejected = (
            bk.bk_status == 1
            and cmt.startswith(TUTOR_CANCEL_REJECT_MARKER)
        )

        bk.cancel_request_reason = (
            _strip_marker(cmt, STUDENT_CANCEL_MARKER)
            if bk.cancel_request_pending else ''
        )

        bk.cancel_reject_reason = (
            _strip_marker(cmt, TUTOR_CANCEL_REJECT_MARKER)
            if bk.cancel_request_rejected else ''
        )

        # ใช้สำหรับซ่อน/แสดงปุ่ม "ส่งให้แอดมินพิจารณา"
        # แสดงได้เฉพาะกรณีติวเตอร์ไม่อนุมัติการยกเลิก และถึงเวลาเรียนแล้ว
        bk.cancel_dispute_available = (
            bk.cancel_request_rejected
            and bk.bk_stu_datetime
            and now >= bk.bk_stu_datetime
        )

        bk.tutor_cancel_for_student_available = (
            bk.bk_status == 1
            and not bk.cancel_request_pending
            and bk.bk_stu_datetime
            and now >= bk.bk_stu_datetime - timezone.timedelta(hours=6)
            and not bk.bk_report_date
        )

        bk.tutor_can_escalate_after_start = (
            bk.bk_status == 1
            and bk.bk_stu_datetime
            and now >= bk.bk_stu_datetime
            and not bk.bk_report_date
        )

        bk.can_report_problem_after_start = _can_report_problem(bk, now)
        first_statement = None
        try:
            first_statement = next(iter(bk.report_statements.all()), None)
        except Exception:
            first_statement = None

        bk.report_by_tutor = (
            bk.bk_report_reason == TUTOR_CANCEL_DISPUTE_REASON
            or cmt.startswith(TUTOR_PROBLEM_REPORT_MARKER)
            or (first_statement and first_statement.brs_role == 'tutor')
        )

    return bookings


def _can_report_problem(booking, now=None):
    now = now or timezone.now()
    return (
        booking.bk_status == 1
        and booking.bk_stu_datetime
        and now >= booking.bk_stu_datetime
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
        if bk.ts_id:
            bk.ts_id.ts_status = 0
            bk.ts_id.save(update_fields=['ts_status'])
        bk.save(update_fields=update_fields)


def _notify_member(member, notif_type, message, url):
    try:
        from apps.notifications.signals import _notif_member
        _notif_member(member, notif_type, message, url)
    except Exception:
        pass


def _normalize_report_reason(reason):
    reason = (reason or '').strip()
    return REPORT_REASON_NORMALIZE.get(reason, reason)


def _refund_locked_credit_to_student(booking):
    total_credit = booking.total_credit
    student = booking.member
    student.mb_locked_crd = max(0, student.mb_locked_crd - total_credit)
    student.mb_deposit_crd += total_credit
    student.save(update_fields=['mb_locked_crd', 'mb_deposit_crd'])

    if booking.ts_id:
        booking.ts_id.ts_status = 0
        booking.ts_id.save(update_fields=['ts_status'])

    return total_credit


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

    _auto_close_free_reports()

    bookings = list(
        Booking.objects
        .filter(tutc_id__tut_id=tutor)
        .select_related('member', 'tutc_id', 'tutc_id__crs_id', 'ts_id', 'ts_id__sd_id')
        .prefetch_related('report_statements', 'report_statements__member')
        .order_by('-bk_date')
    )
    _decorate_cancel_flags(bookings)

    reported_bookings = [b for b in bookings if b.bk_report_date]
    normal_bookings   = [b for b in bookings if not b.bk_report_date]

    pending   = [b for b in normal_bookings if b.bk_status == 0]   # รอยืนยัน
    accepted  = [b for b in normal_bookings if b.bk_status == 1]   # รับงานแล้ว
    studying  = [b for b in normal_bookings if b.bk_status == 2]   # รอแจ้งจบงาน (เรียนแล้ว)
    notified  = [b for b in normal_bookings if b.bk_status == 3]   # แจ้งจบงานแล้ว
    done      = [b for b in normal_bookings if b.bk_status in (4, 5)]  # เสร็จสิ้น + รีวิวแล้ว
    rejected  = [b for b in normal_bookings if b.bk_status == 6]

    return render(request, 'bookings/tutor_requests.html', {
        'pending':      pending,
        'accepted':     accepted,
        'studying':     studying,
        'notified':     notified,
        'done':         done,
        'rejected':     rejected,
        'reported_bookings': reported_bookings,
        'all_bookings': bookings,
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

    bk = get_object_or_404(Booking, bk_id=bk_id, tutc_id__tut_id=tutor, bk_status=0)
    bk.bk_status        = 1
    bk.bk_accepted_date = timezone.now()
    bk.save()

    messages.success(request, f'รับงาน BK{bk.bk_id:05d} เรียบร้อย')
    return redirect('/bookings/tutor/?tab=accepted')


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

    bk = get_object_or_404(Booking, bk_id=bk_id, tutc_id__tut_id=tutor, bk_status=0)
    total_credit = bk.bk_rate_per_person * bk.bk_stu_count

    try:
        with transaction.atomic():
            # คืนเครดิตที่ล็อกไว้ให้ผู้เรียน
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

        messages.error(request, f'ปฏิเสธคำขอจอง BK{bk.bk_id:05d} และคืนเครดิตให้ผู้เรียนแล้ว')
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

    bk = get_object_or_404(Booking, bk_id=bk_id, tutc_id__tut_id=tutor, bk_status=1)
    bk.bk_status = 2
    bk.save()

    messages.success(request, f'บันทึกเสร็จสิ้นการสอน BK{bk.bk_id:05d} แล้ว')
    # ถ้ามี next ให้ redirect ไปหน้านั้น (เช่น tutoring_activity)
    next_url = request.POST.get('next', '')
    if next_url and next_url.startswith('/'):
        return redirect(next_url)
    return redirect('/bookings/tutor/?tab=studying')


# ─── ฝั่งนักเรียน: ประวัติการจอง ────────────────────────────────────────────
@login_required
def student_bookings(request):
    try:
        mb = request.user.member
    except Exception:
        return redirect('home')

    # ── lazy check: ยืนยันจบงานอัตโนมัติถ้าเกิน 24 ชม. ──
    _auto_confirm_overdue(mb)
    _auto_close_free_reports()

    bookings = list(
        Booking.objects
        .filter(member=mb)
        .select_related(
            'tutc_id', 'tutc_id__crs_id',
            'tutc_id__tut_id', 'tutc_id__tut_id__tut_id',
            'ts_id', 'ts_id__sd_id',
        )
        .prefetch_related('report_statements', 'report_statements__member')
        .order_by('-bk_date')
    )
    _decorate_cancel_flags(bookings)

    return render(request, 'bookings/student_bookings.html', {
        'bookings':   bookings,
        'mb_credit':  mb.mb_deposit_crd + mb.mb_income_crd,
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
            return redirect('/bookings/tutor/?tab=studying')

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
                return redirect('/bookings/tutor/?tab=notified')
    else:
        form = TutoringActivityForm(instance=activity)

    return render(request, 'bookings/tutoring_activity.html', {
        'bk':       bk,
        'form':     form,
        'activity': activity,
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

    bk = get_object_or_404(Booking, bk_id=bk_id, member=mb, bk_status=3)
    jc = get_object_or_404(JobCompletion, bk_id=bk)
    total_credit = bk.bk_rate_per_person * bk.bk_stu_count

    try:
        with transaction.atomic():
            tutor_member = bk.tutc_id.tut_id.tut_id
            _pay_tutor(mb, tutor_member, total_credit)

            jc.jc_confirm_date = timezone.now()
            jc.save()

            bk.bk_status = 4
            bk.save()

        messages.success(request, 'ยืนยันการจบงานเรียบร้อยแล้ว')
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

                    _update_tutor_ratings(tutor)

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
        messages.error(request, 'รายงานปัญหาได้เฉพาะรายการที่รับงานแล้วและถึงเวลาเรียนแล้ว')
        return redirect('bookings:student_bookings')

    if not rp_reason:
        messages.error(request, 'กรุณาเลือกสาเหตุของปัญหา')
        return redirect('bookings:student_bookings')

    if rp_reason not in REPORT_REASON_CODES:
        messages.error(request, 'สาเหตุการรายงานไม่ถูกต้อง')
        return redirect('bookings:student_bookings')

    bk.bk_report_reason = rp_reason
    bk.bk_report_desc   = rp_desc or None
    bk.bk_report_date   = timezone.now()
    bk.save(update_fields=['bk_report_reason', 'bk_report_desc', 'bk_report_date'])
    _create_report_statement(bk, mb, 'student', rp_desc or 'ผู้เรียนรายงานปัญหา')

    _notify_member(
        bk.tutc_id.tut_id.tut_id,
        'booking_reported',
        f'ผู้เรียนรายงานปัญหา BK{bk.bk_id:05d} โปรดส่งคำชี้แจงภายใน 24 ชั่วโมงหากต้องการให้ข้อมูลเพิ่มเติม',
        '/bookings/tutor/?tab=reported',
    )

    return redirect('/bookings/my/?tab=reported&reported=1')


@login_required
def submit_report_statement(request, bk_id):
    """ผู้เรียน/ติวเตอร์ส่งคำชี้แจงเพิ่มเติมในเคสรายงานที่ยังรอจัดการ"""
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
        messages.error(request, 'คุณไม่มีสิทธิ์ส่งคำชี้แจงสำหรับรายการนี้')
        return redirect('home')
    if role == 'student':
        redirect_to = '/bookings/my/?tab=reported'
    if role == 'tutor':
        redirect_to = '/bookings/tutor/?tab=reported'

    if bk.bk_report_resolved_date:
        messages.warning(request, 'รายงานนี้พิจารณาเสร็จสิ้นแล้ว')
        return redirect(redirect_to)

    detail = request.POST.get('statement_desc', '').strip()
    if not detail:
        messages.error(request, 'กรุณาระบุคำชี้แจงก่อนส่ง')
        return redirect(redirect_to)

    _create_report_statement(bk, mb, role, detail)

    if role == 'student':
        _notify_member(
            bk.tutc_id.tut_id.tut_id,
            'booking_reported',
            f'ผู้เรียนส่งคำชี้แจงเพิ่มเติมในรายงาน BK{bk.bk_id:05d}',
            '/bookings/tutor/?tab=reported',
        )
    else:
        _notify_member(
            bk.member,
            'booking_reported',
            f'ติวเตอร์ส่งคำชี้แจงเพิ่มเติมในรายงาน BK{bk.bk_id:05d}',
            '/bookings/my/?tab=reported',
        )

    messages.success(request, 'ส่งคำชี้แจงเพิ่มเติมแล้ว')
    return redirect(redirect_to)


@login_required
def student_request_cancel_booking(request, bk_id):
    """ผู้เรียนส่งคำขอยกเลิกหลังติวเตอร์รับงานแล้ว โดยต้องแจ้งล่วงหน้าอย่างน้อย 6 ชั่วโมง"""
    if request.method != 'POST':
        return redirect('bookings:student_bookings')

    try:
        mb = request.user.member
    except Exception:
        return redirect('home')

    bk = get_object_or_404(
        Booking.objects.select_related('tutc_id', 'tutc_id__tut_id', 'tutc_id__tut_id__tut_id'),
        bk_id=bk_id,
        member=mb,
        bk_status=1,
    )
    _decorate_cancel_flags([bk])

    if bk.cancel_request_pending:
        messages.info(request, 'คุณได้ส่งคำขอยกเลิกการเรียนแล้ว กำลังรอการพิจารณาจากติวเตอร์')
        return redirect('bookings:student_bookings')

    if bk.cancel_request_rejected:
        messages.warning(request, 'ติวเตอร์ไม่อนุมัติคำขอยกเลิกก่อนหน้านี้ กรุณาดูรายละเอียดการจอง')
        return redirect('bookings:student_bookings')

    if bk.bk_stu_datetime and timezone.now() > bk.bk_stu_datetime - timezone.timedelta(hours=6):
        messages.error(request, 'การยกเลิกการเรียนต้องแจ้งล่วงหน้าอย่างน้อย 6 ชั่วโมงก่อนเวลาเรียน')
        return redirect('bookings:student_bookings')

    reason = request.POST.get('cancel_reason', '').strip()
    if not reason:
        messages.error(request, 'กรุณาระบุเหตุผลในการขอยกเลิกการเรียน')
        return redirect('bookings:student_bookings')

    bk.bk_cmt = f'{STUDENT_CANCEL_MARKER} {reason}'
    bk.save(update_fields=['bk_cmt'])

    tutor_member = bk.tutc_id.tut_id.tut_id
    _notify_member(
        tutor_member,
        'booking_completed',
        f'ผู้เรียนส่งคำขอยกเลิกการเรียน BK{bk.bk_id:05d} โปรดพิจารณา',
        '/bookings/tutor/?tab=accepted',
    )
    messages.success(request, 'ส่งคำขอยกเลิกการเรียนแล้ว กำลังรอการพิจารณาจากติวเตอร์')
    return redirect('/bookings/my/?tab=1')


@login_required
def tutor_approve_cancel_booking(request, bk_id):
    """ติวเตอร์อนุมัติคำขอยกเลิกจากผู้เรียน คืนเครดิตและเปิดช่วงเวลาเรียน"""
    if request.method != 'POST':
        return redirect('bookings:tutor_requests')

    try:
        tutor = request.user.member.tutor
    except Exception:
        messages.error(request, 'ไม่มีสิทธิ์')
        return redirect('home')

    bk = get_object_or_404(
        Booking.objects.select_related('member', 'tutc_id', 'tutc_id__tut_id', 'tutc_id__tut_id__tut_id', 'ts_id'),
        bk_id=bk_id,
        tutc_id__tut_id=tutor,
        bk_status=1,
    )
    _decorate_cancel_flags([bk])
    if not bk.cancel_request_pending:
        messages.warning(request, 'ไม่พบคำขอยกเลิกที่รอพิจารณา')
        return redirect('bookings:tutor_requests')

    with transaction.atomic():
        total_credit = _refund_locked_credit_to_student(bk)
        bk.bk_status = 6
        bk.bk_cmt = 'ติวเตอร์อนุมัติการยกเลิกตามคำขอผู้เรียน'
        bk.save(update_fields=['bk_status', 'bk_cmt'])

    _notify_member(
        bk.member,
        'booking_rejected',
        f'ติวเตอร์อนุมัติการยกเลิก BK{bk.bk_id:05d} เครดิต {total_credit} เครดิตได้รับคืนเข้าบัญชีแล้ว',
        '/bookings/my/?tab=6',
    )
    messages.success(request, f'อนุมัติการยกเลิก BK{bk.bk_id:05d} และคืนเครดิตให้ผู้เรียนแล้ว')
    return redirect('/bookings/tutor/?tab=rejected')


@login_required
def tutor_reject_cancel_booking(request, bk_id):
    """ติวเตอร์ไม่อนุมัติคำขอยกเลิก สถานะยังคงเป็นรับงานแล้ว"""
    if request.method != 'POST':
        return redirect('bookings:tutor_requests')

    try:
        tutor = request.user.member.tutor
    except Exception:
        messages.error(request, 'ไม่มีสิทธิ์')
        return redirect('home')

    bk = get_object_or_404(
        Booking.objects.select_related('member', 'tutc_id'),
        bk_id=bk_id,
        tutc_id__tut_id=tutor,
        bk_status=1,
    )
    _decorate_cancel_flags([bk])
    if not bk.cancel_request_pending:
        messages.warning(request, 'ไม่พบคำขอยกเลิกที่รอพิจารณา')
        return redirect('bookings:tutor_requests')

    reason = request.POST.get('reject_reason', '').strip()
    if not reason:
        messages.error(request, 'กรุณาระบุเหตุผลที่ไม่อนุมัติการยกเลิก')
        return redirect('bookings:tutor_requests')

    bk.bk_cmt = f'{TUTOR_CANCEL_REJECT_MARKER} {reason}'
    bk.save(update_fields=['bk_cmt'])

    _notify_member(
        bk.member,
        'booking_completed',
        f'ติวเตอร์ไม่อนุมัติการยกเลิก BK{bk.bk_id:05d} โปรดดูรายละเอียดการจอง',
        '/bookings/my/?tab=1',
    )
    messages.info(request, f'บันทึกผลไม่อนุมัติการยกเลิก BK{bk.bk_id:05d} แล้ว')
    return redirect('/bookings/tutor/?tab=accepted')


@login_required
def tutor_cancel_for_student_booking(request, bk_id):
    """ติวเตอร์ยกเลิกให้ผู้เรียนหลังพูดคุยกันแล้ว คืนเครดิตและเปิดช่วงเวลาเรียน"""
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
        bk_status=1,
    )
    _decorate_cancel_flags([bk])

    if not bk.tutor_cancel_for_student_available:
        messages.warning(
            request,
            'ติวเตอร์ยกเลิกให้ผู้เรียนได้เฉพาะช่วงที่ผู้เรียนส่งคำขอยกเลิกเองไม่ได้แล้ว หรือเมื่อมีการตกลงกันหลังใกล้เวลาเรียน'
        )
        return redirect('bookings:tutor_requests')

    with transaction.atomic():
        total_credit = _refund_locked_credit_to_student(bk)
        bk.bk_status = 6
        bk.bk_cmt = 'ติวเตอร์ยกเลิกการเรียนตามคำขอผู้เรียน'
        bk.save(update_fields=['bk_status', 'bk_cmt'])

    _notify_member(
        bk.member,
        'booking_rejected',
        f'ติวเตอร์ยกเลิกการเรียนตามคำขอ BK{bk.bk_id:05d} เครดิต {total_credit} เครดิตได้รับคืนเข้าบัญชีแล้ว',
        '/bookings/my/?tab=6',
    )
    messages.success(request, f'ยกเลิกการเรียน BK{bk.bk_id:05d} และคืนเครดิตให้ผู้เรียนแล้ว')
    return redirect('/bookings/tutor/?tab=rejected')


@login_required
def tutor_escalate_cancel_dispute(request, bk_id):
    """ติวเตอร์รายงานปัญหาหลังถึงเวลาเรียนแล้ว"""
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
        bk_status=1,
    )
    _decorate_cancel_flags([bk])
    now = timezone.now()

    if not _can_report_problem(bk, now):
        messages.warning(request, 'รายงานปัญหาได้เฉพาะรายการที่รับงานแล้ว ถึงเวลาเรียนแล้ว และยังไม่เคยมีรายงาน')
        return redirect('bookings:tutor_requests')

    rp_reason = _normalize_report_reason(request.POST.get('rp_reason', ''))
    detail = request.POST.get('dispute_desc', '').strip()
    if not rp_reason:
        messages.error(request, 'กรุณาเลือกสาเหตุของปัญหา')
        return redirect('bookings:tutor_requests')

    if rp_reason not in REPORT_REASON_CODES:
        messages.error(request, 'สาเหตุการรายงานไม่ถูกต้อง')
        return redirect('bookings:tutor_requests')

    bk.bk_report_reason = rp_reason
    bk.bk_report_desc = detail or None
    bk.bk_report_date = timezone.now()
    bk.bk_cmt = f'{TUTOR_PROBLEM_REPORT_MARKER} {detail}'.strip()
    bk.save(update_fields=['bk_report_reason', 'bk_report_desc', 'bk_report_date', 'bk_cmt'])
    _create_report_statement(bk, request.user.member, 'tutor', detail or 'ติวเตอร์รายงานปัญหา')

    _notify_member(
        bk.member,
        'booking_reported',
        f'ติวเตอร์รายงานปัญหา BK{bk.bk_id:05d} โปรดส่งคำชี้แจงภายใน 24 ชั่วโมงหากต้องการให้ข้อมูลเพิ่มเติม',
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
    from django.utils import timezone

    booking = get_object_or_404(Booking, bk_id=bk_id, member=request.user.member)

    # ยกเลิกได้เฉพาะสถานะ 0 เท่านั้น
    if booking.bk_status != 0:
        messages.error(request, 'ไม่สามารถยกเลิกการจองในสถานะนี้ได้')
        return redirect('bookings:student_bookings')

    if request.method == 'POST':
        member = request.user.member
        total  = booking.total_credit

        with transaction.atomic():
            # คืน slot ให้ว่างอีกครั้ง
            if booking.ts_id:
                booking.ts_id.ts_status = 0
                booking.ts_id.save()

            # เปลี่ยนสถานะและบันทึกหมายเหตุ
            booking.bk_status = 6
            booking.bk_cmt    = 'ผู้เรียนยกเลิกการจอง'
            booking.save(update_fields=['bk_status', 'bk_cmt'])

            # คืนเครดิตที่ล็อกไว้กลับเข้า deposit
            member.mb_locked_crd  = max(0, member.mb_locked_crd - total)
            member.mb_deposit_crd = member.mb_deposit_crd + total
            member.save(update_fields=['mb_locked_crd', 'mb_deposit_crd'])

        messages.success(request, f'ยกเลิกการจอง BK{bk_id:05d} เรียบร้อยแล้ว เครดิต {total} เครดิต ได้รับคืนแล้ว')
        return redirect('/bookings/my/?tab=6')

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


# ─── helper: ยืนยันจบงานอัตโนมัติถ้าเกิน 24 ชม. ──────────────────────────────
def _auto_confirm_overdue(mb):
    """
    ตรวจ booking ของ mb ที่ status=3 และ jc_complete_date เกิน 24 ชม.
    ถ้าพบให้ยืนยันอัตโนมัติ (โอนเครดิตให้ติวเตอร์)
    """
    from datetime import timedelta
    cutoff = timezone.now() - timedelta(hours=24) 
    # ── cutoff = timezone.now() - timedelta(minutes=1) ──สำหรับทดสอบเวลาให้เร็วขึ้น

    overdue = (
        Booking.objects
        .filter(member=mb, bk_status=3)
        .select_related('tutc_id__tut_id__tut_id')
        .prefetch_related('jobcompletion')
    )

    for bk in overdue:
        try:
            jc = bk.jobcompletion
            if jc.jc_complete_date and jc.jc_complete_date <= cutoff:
                total_credit = bk.bk_rate_per_person * bk.bk_stu_count
                with transaction.atomic():
                    tutor_member = bk.tutc_id.tut_id.tut_id
                    _pay_tutor(mb, tutor_member, total_credit)

                    jc.jc_confirm_date = timezone.now()
                    jc.save()

                    bk.bk_status = 4
                    bk.save()
        except Exception:
            pass  # ถ้าไม่มี jobcompletion หรือ error ข้ามไป


# ─── helper: คำนวณและอัพเดต tut_rating ทุกด้าน ──────────────────────────────
def _update_tutor_ratings(tutor):
    from apps.bookings.models import Review as ReviewModel

    reviews = ReviewModel.objects.filter(bk_id__tutc_id__tut_id=tutor)
    if not reviews.exists():
        return

    agg = reviews.aggregate(
        avg_quality       = Avg('rv_quality'),
        avg_knowledge     = Avg('rv_knowledge'),
        avg_communication = Avg('rv_communication'),
        avg_punctuality   = Avg('rv_punctuality'),
        avg_satisfaction  = Avg('rv_satisfaction'),
    )

    q = round(agg['avg_quality']       or 0, 2)
    k = round(agg['avg_knowledge']     or 0, 2)
    c = round(agg['avg_communication'] or 0, 2)
    p = round(agg['avg_punctuality']   or 0, 2)
    s = round(agg['avg_satisfaction']  or 0, 2)

    tutor.tut_rating_quality       = q
    tutor.tut_rating_knowledge     = k
    tutor.tut_rating_communication = c
    tutor.tut_rating_punctuality   = p
    tutor.tut_rating_satisfaction  = s
    tutor.tut_rating               = round((q + k + c + p + s) / 5, 2)
    tutor.save()
