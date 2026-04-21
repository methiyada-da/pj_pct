from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db import transaction

from apps.tutoring.models import TutorCourse, TutorRate, ScheduleDate, TimeSlot
from apps.bookings.models import Booking


def course_detail(request, tutc_id):
    tutcourse = get_object_or_404(
        TutorCourse.objects.select_related(
            'tut_id',
            'tut_id__tut_id',
            'tut_id__tut_id__mj_id',
            'tut_id__tut_id__mj_id__fac_id',
            'crs_id',
            'crs_id__cg_id',
        ),
        tutc_id=tutc_id,
    )

    tutor  = tutcourse.tut_id
    member = tutor.tut_id

    rates_qs = list(TutorRate.objects.filter(tutc_id=tutcourse).order_by('tut_rate_stu_count'))

    # สร้าง rates_with_range: แต่ละ rate จะรู้ช่วงของตัวเอง
    # เช่น rate1(1คน, 10cr), rate2(3คน, 9cr), max=5
    # → ช่วง: 1–2 คน = 10cr, 3–5 คน = 9cr
    rates = []
    for i, r in enumerate(rates_qs):
        start = r.tut_rate_stu_count
        if i + 1 < len(rates_qs):
            end = rates_qs[i + 1].tut_rate_stu_count - 1
        else:
            end = tutcourse.tutc_max_stu
        rates.append({
            'start':       start,
            'end':         end,
            'price':       r.tut_rate_per_person,
            'is_single':   start == end,
        })

    # ── ดึง ScheduleDate เฉพาะวันนี้เป็นต้นไป ──
    schedule_qs = (
        ScheduleDate.objects
        .filter(
            tutc_id=tutcourse,
            sd_date__gte=timezone.localdate(),
        )
        .prefetch_related('time_slots')
        .order_by('sd_date')
    )

    # กรองเฉพาะวันที่ยังมี slot ว่าง (ts_status=0) และเวลายังไม่ผ่าน
    now_local = timezone.localtime(timezone.now())
    today     = now_local.date()
    now_time  = now_local.time()

    available_dates = []
    for sd in schedule_qs:
        if sd.sd_date == today:
            # วันนี้ — กรอง slot ที่เวลาเริ่มยังไม่ผ่าน
            has_slot = sd.time_slots.filter(ts_status=0, ts_start_time__gt=now_time).exists()
        else:
            # วันอื่น (อนาคต) — กรอง slot ว่างปกติ
            has_slot = sd.time_slots.filter(ts_status=0).exists()
        if has_slot:
            available_dates.append(sd)

    user_credit = None
    if request.user.is_authenticated:
        try:
            mb = request.user.member
            user_credit = mb.mb_deposit_crd + mb.mb_income_crd - mb.mb_locked_crd
        except Exception:
            user_credit = 0

    context = {
        'tc':              tutcourse,
        'tutor':           tutor,
        'member':          member,
        'rates':           rates,
        'available_dates': available_dates,
        'user_credit':     user_credit,
    }
    return render(request, 'tutoring/detail.html', context)


@login_required
def booking_create(request, tutc_id):
    if request.method != 'POST':
        return redirect('tutoring:course_detail', tutc_id=tutc_id)

    tutcourse    = get_object_or_404(TutorCourse, tutc_id=tutc_id)
    tutor_member = tutcourse.tut_id.tut_id

    ts_id     = request.POST.get('ts_id', '').strip()
    stu_count = request.POST.get('stu_count', '1')
    bk_desc   = request.POST.get('bk_desc', '').strip()

    errors = []

    if not ts_id:
        errors.append('กรุณาเลือกช่วงเวลา')

    try:
        stu_count = int(stu_count)
        if stu_count < 1:
            errors.append('จำนวนผู้เรียนต้องอย่างน้อย 1 คน')
        if stu_count > tutcourse.tutc_max_stu:
            errors.append(f'จำนวนผู้เรียนต้องไม่เกิน {tutcourse.tutc_max_stu} คน')
    except (ValueError, TypeError):
        errors.append('จำนวนผู้เรียนไม่ถูกต้อง')
        stu_count = 1

    rate_obj = (
        TutorRate.objects
        .filter(tutc_id=tutcourse, tut_rate_stu_count__gte=stu_count)
        .order_by('tut_rate_stu_count')
        .first()
    ) or TutorRate.objects.filter(tutc_id=tutcourse).order_by('-tut_rate_stu_count').first()

    if not rate_obj:
        errors.append('ไม่พบอัตราค่าบริการ')

    if errors:
        for e in errors:
            messages.error(request, e)
        return redirect('tutoring:course_detail', tutc_id=tutc_id)

    rate_per_person = rate_obj.tut_rate_per_person
    total_credit    = rate_per_person * stu_count

    try:
        slot = TimeSlot.objects.select_related('sd_id').get(
            ts_id=ts_id,
            sd_id__tutc_id=tutcourse,
            ts_status=0,
        )
    except TimeSlot.DoesNotExist:
        messages.error(request, 'ช่วงเวลาที่เลือกไม่พร้อมใช้งานแล้ว กรุณาเลือกใหม่')
        return redirect('tutoring:course_detail', tutc_id=tutc_id)

    mb = request.user.member
    available_credit = mb.mb_deposit_crd + mb.mb_income_crd - mb.mb_locked_crd

    if mb == tutor_member:
        messages.error(request, 'ไม่สามารถจองคอร์สของตัวเองได้')
        return redirect('tutoring:course_detail', tutc_id=tutc_id)

    if available_credit < total_credit:
        messages.error(request, f'เครดิตไม่เพียงพอ (มี {available_credit} ต้องการ {total_credit})')
        return redirect('tutoring:course_detail', tutc_id=tutc_id)

    try:
        with transaction.atomic():
            slot.ts_status = 1
            slot.save()

            mb.mb_locked_crd += total_credit
            mb.save()

            Booking.objects.create(
                bk_desc            = bk_desc or None,
                bk_stu_datetime    = timezone.make_aware(
                    timezone.datetime.combine(slot.sd_id.sd_date, slot.ts_start_time)
                ),
                bk_stu_count       = stu_count,
                bk_rate_per_person = rate_per_person,
                bk_date            = timezone.now(),
                bk_status          = 0,
                member             = mb,
                tutc_id            = tutcourse,
                ts_id              = slot,
            )

        messages.success(
            request,
            f'จองสำเร็จ! รอติวเตอร์ยืนยันภายใน 24 ชั่วโมง (ล็อกเครดิต {total_credit} เครดิต)'
        )
        return redirect('bookings:student_bookings')
    except Exception:
        messages.error(request, 'เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง')

    return redirect('tutoring:course_detail', tutc_id=tutc_id)