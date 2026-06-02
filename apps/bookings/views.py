# bookings/views.py - views จัดการการจอง และกิจกรรมติว
from urllib import request

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.db.models import Avg

from apps import bookings

from .models import Booking, TutoringActivity, JobCompletion, Review
from .forms import TutoringActivityForm, ReviewForm


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

    pending   = [b for b in bookings if b.bk_status == 0]   # รอยืนยัน
    accepted  = [b for b in bookings if b.bk_status == 1]   # รับงานแล้ว
    studying  = [b for b in bookings if b.bk_status == 2]   # รอแจ้งจบงาน (เรียนแล้ว)
    notified  = [b for b in bookings if b.bk_status == 3]   # แจ้งจบงานแล้ว
    done      = [b for b in bookings if b.bk_status in (4, 5)]  # เสร็จสิ้น + รีวิวแล้ว
    rejected  = [b for b in bookings if b.bk_status == 6]

    return render(request, 'bookings/tutor_requests.html', {
        'pending':      pending,
        'accepted':     accepted,
        'studying':     studying,
        'notified':     notified,
        'done':         done,
        'rejected':     rejected,
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

    return redirect('bookings:tutor_requests')


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
    return redirect('bookings:tutor_requests')


# ─── ฝั่งนักเรียน: ประวัติการจอง ────────────────────────────────────────────
@login_required
def student_bookings(request):
    try:
        mb = request.user.member
    except Exception:
        return redirect('home')

    # ── lazy check: ยืนยันจบงานอัตโนมัติถ้าเกิน 24 ชม. ──
    _auto_confirm_overdue(mb)

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
            return redirect('bookings:tutor_requests')

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
                return redirect('bookings:tutor_requests')
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
                return redirect('bookings:student_bookings')

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
    rp_reason = request.POST.get('rp_reason', '').strip()
    rp_desc   = request.POST.get('rp_desc', '').strip()

    if not rp_reason:
        messages.error(request, 'กรุณาเลือกสาเหตุของปัญหา')
        return redirect('bookings:student_bookings')

    # บันทึก report ลงใน Booking field (รายงานไปยังแอดมินเสมอ)
    bk.bk_report_reason = rp_reason
    bk.bk_report_desc   = rp_desc or None
    bk.bk_report_date   = timezone.now()
    bk.save(update_fields=['bk_report_reason', 'bk_report_desc', 'bk_report_date'])

    return redirect('/bookings/my/?reported=1')

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
        return redirect('bookings:student_bookings')

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