# tutoring/views.py - views รวมทั้งหมดของติวเตอร์ (search, detail, profile, manage)
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.core.files.base import ContentFile
from django.core.paginator import Paginator
from django.utils import timezone
from django.db import transaction
from django.db.models import Avg, Count, Q, OuterRef, Subquery

from apps.accounts.models import Tutor, Member, TutorExperienceImage
from apps.courses.models import CourseGroup, Course
from apps.bookings.models import Booking, Review
from apps.bookings.services import (
    get_booking_close_at,
    get_fixed_rate,
    get_remaining_seats,
    has_active_course_bookings,
    process_time_based_bookings,
)
from .forms import ExperienceImagesField, TutorRegisterForm
from .models import TutorCourse, TutorRate, ScheduleDate, TimeSlot
import re
import os


BAYESIAN_MIN_REVIEWS = 5


def _is_future_schedule_start(slot_date, start_time, local_now):
    """ตรวจว่าเวลาเริ่มเรียนยังเหลือเวลารับจองตามค่ากลางของระบบ"""
    try:
        start = timezone.datetime.strptime(
            f'{slot_date.isoformat()} {start_time}',
            '%Y-%m-%d %H:%M',
        )
    except (TypeError, ValueError):
        return False
    start = timezone.make_aware(start, timezone.get_current_timezone())
    return start >= local_now + timezone.timedelta(hours=settings.BOOKING_CLOSE_HOURS)


def calculate_bayesian_rating(raw_rating, review_count, global_average, minimum_reviews=BAYESIAN_MIN_REVIEWS):
    """คำนวณคะแนน Bayesian Weighted Rating ของคอร์ส"""
    if review_count <= 0 or global_average <= 0:
        return 0.0
    return round(
        ((review_count / (review_count + minimum_reviews)) * float(raw_rating))
        + ((minimum_reviews / (review_count + minimum_reviews)) * global_average),
        2,
    )


def _get_course_rating_stats():
    """ดึงค่าเฉลี่ยรวมของระบบและสถิติรีวิวรายคอร์ส"""
    global_values = Review.objects.aggregate(
        quality=Avg('rv_quality'),
        knowledge=Avg('rv_knowledge'),
        communication=Avg('rv_communication'),
        punctuality=Avg('rv_punctuality'),
        satisfaction=Avg('rv_satisfaction'),
    )
    global_average = round(
        sum(float(value or 0) for value in global_values.values()) / 5,
        4,
    )

    rows = (
        Review.objects
        .values('bk_id__tutc_id')
        .annotate(
            review_count=Count('pk'),
            quality=Avg('rv_quality'),
            knowledge=Avg('rv_knowledge'),
            communication=Avg('rv_communication'),
            punctuality=Avg('rv_punctuality'),
            satisfaction=Avg('rv_satisfaction'),
        )
    )
    course_stats = {}
    for row in rows:
        raw_rating = round(
            sum(float(row[field] or 0) for field in (
                'quality', 'knowledge', 'communication',
                'punctuality', 'satisfaction',
            )) / 5,
            2,
        )
        course_stats[row['bk_id__tutc_id']] = {
            'raw_rating': raw_rating,
            'review_count': row['review_count'],
        }
    return global_average, course_stats


def _attach_bayesian_rating(course, global_average, course_stats):
    """แนบคะแนน Bayesian และจำนวนรีวิวให้ออบเจ็กต์คอร์สชั่วคราว"""
    stats = course_stats.get(course.tutc_id, {})
    course.review_count = stats.get('review_count', 0)
    course.bayesian_rating = calculate_bayesian_rating(
        stats.get('raw_rating', 0),
        course.review_count,
        global_average,
    )
    return course


# ============================================================
# SEARCH VIEWS - ค้นหาติวเตอร์
# ============================================================

def search_tutors(request):
    """
    หน้าค้นหาติวเตอร์และรายวิชา
    URL: /tutoring/search/
    """
    q          = request.GET.get('q', '').strip()
    cg_id      = request.GET.get('cg_id', '')
    crs_id     = request.GET.get('crs_id', '')
    min_price  = request.GET.get('min_price', '')
    max_price  = request.GET.get('max_price', '')
    min_rating = request.GET.get('min_rating', '')

    # ── Subquery: ราคาต่ำสุดของแต่ละ TutorCourse ──
    # วิธีนี้ไม่ต้องพึ่ง related_name เลย — query TutorRate โดยตรง
    min_rate_subquery = (
        TutorRate.objects
        .filter(tutc_id=OuterRef('tutc_id'))
        .order_by('tut_rate_per_person')
        .values('tut_rate_per_person')[:1]
    )

    # ── base queryset ──
    tutorcourses = (
        TutorCourse.objects
        .filter(tutc_status=1, tut_id__tut_status=1)
        .select_related(
            'tut_id',           # Tutor
            'tut_id__tut_id',   # Member (Tutor.tut_id คือ OneToOne → Member)
            'crs_id',           # Course
            'crs_id__cg_id',    # CourseGroup
        )
        .annotate(
            lowest_price=Subquery(min_rate_subquery),
            rate_count=Count('tutorrate'),
        )
        .filter(rate_count=1)
    )

    # ── Full-text search ──
    if q:
        tutorcourses = tutorcourses.filter(
            Q(tutc_name__icontains=q) |
            Q(crs_id__crs_name__icontains=q) |
            Q(crs_id__cg_id__cg_name__icontains=q) |
            Q(tut_id__tut_id__mb_full_name__icontains=q)
        )

    # ── Filter: กลุ่มวิชา ──
    if cg_id:
        tutorcourses = tutorcourses.filter(crs_id__cg_id__cg_id=cg_id)

    # ── Filter: รายวิชา ──
    if crs_id:
        tutorcourses = tutorcourses.filter(crs_id__crs_id=crs_id)

    # ── Filter: ช่วงราคา ──
    if min_price:
        tutorcourses = tutorcourses.filter(lowest_price__gte=int(min_price))
    if max_price:
        tutorcourses = tutorcourses.filter(lowest_price__lte=int(max_price))

    # ── คำนวณ กรอง และเรียงด้วย Bayesian Rating ──
    global_average, course_stats = _get_course_rating_stats()
    tutorcourses = [
        _attach_bayesian_rating(course, global_average, course_stats)
        for course in tutorcourses
    ]
    if min_rating:
        try:
            minimum_rating = float(min_rating)
            tutorcourses = [
                course for course in tutorcourses
                if course.review_count > 0
                and round(course.bayesian_rating, 1) >= minimum_rating
            ]
        except ValueError:
            min_rating = ''

    tutorcourses.sort(key=lambda course: (
        course.review_count == 0,
        -course.bayesian_rating,
        -course.review_count,
        course.tutc_name.casefold(),
    ))

    # แบ่งหน้าเมื่อมีคอร์สจำนวนมาก โดยคงลำดับ Bayesian เดิมไว้
    result_count = len(tutorcourses)
    paginator = Paginator(tutorcourses, 12)
    page_obj = paginator.get_page(request.GET.get('page'))
    tutorcourses = page_obj.object_list

    pagination_params = request.GET.copy()
    pagination_params.pop('page', None)
    pagination_query = pagination_params.urlencode()

    # ── Dropdown data ──
    course_groups = CourseGroup.objects.all().order_by('cg_name')

    courses = []
    if cg_id:
        courses = Course.objects.filter(cg_id__cg_id=cg_id).order_by('crs_name')

    # ── เครดิตคงเหลือ ──
    user_credit = None
    if request.user.is_authenticated:
        try:
            member = request.user.member
            user_credit = member.mb_deposit_crd + member.mb_income_crd - member.mb_locked_crd
        except Exception:
            user_credit = 0

    context = {
        'tutorcourses':  tutorcourses,
        'course_groups': course_groups,
        'courses':       courses,
        'result_count':  result_count,
        'page_obj':      page_obj,
        'pagination_query': pagination_query,
        'q':             q,
        'selected_cg':   cg_id,
        'selected_crs':  crs_id,
        'min_price':     min_price,
        'max_price':     max_price,
        'min_rating':    min_rating,
        'user_credit':   user_credit,
    }
    return render(request, 'tutoring/search.html', context)


def get_courses_by_group(request):
    """
    AJAX endpoint: คืน <option> tags ของรายวิชาตามกลุ่มที่เลือก
    URL: /tutoring/courses-by-group/?cg_id=<id>
    """
    cg_id = request.GET.get('cg_id', '')
    courses = []
    if cg_id:
        courses = Course.objects.filter(cg_id__cg_id=cg_id).order_by('crs_name')

    return render(request, 'tutoring/_course_options.html', {'courses': courses})


# ============================================================
# DETAIL VIEWS - รายละเอียดติวเตอร์
# ============================================================

def course_detail(request, tutc_id):
    # คืนที่นั่งจากคำขอที่หมดเวลาก่อนคำนวณรอบว่าง
    process_time_based_bookings()
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

    # นับรีวิวรวมของติวเตอร์และรีวิวเฉพาะคอร์สที่กำลังแสดง
    tutor_reviews = Review.objects.filter(bk_id__tutc_id__tut_id=tutor)
    tutor_review_count = tutor_reviews.count()
    course_review_count = tutor_reviews.filter(bk_id__tutc_id=tutcourse).count()
    global_average, course_stats = _get_course_rating_stats()
    _attach_bayesian_rating(tutcourse, global_average, course_stats)

    fixed_rate = get_fixed_rate(tutcourse)

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

    # กรองรอบที่ยังไม่ปิดรับและยังมีที่นั่งเหลือ
    now = timezone.now()

    available_dates = []
    for sd in schedule_qs:
        available_slots = []
        for slot in sd.time_slots.all():
            if slot.ts_status == 2:
                continue
            slot.booking_close_at = get_booking_close_at(slot)
            if now > slot.booking_close_at:
                continue
            slot.remaining_seats = get_remaining_seats(slot)
            if slot.remaining_seats <= 0:
                continue
            available_slots.append(slot)

        sd.available_slots = available_slots
        if available_slots:
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
        'fixed_rate':      fixed_rate,
        'available_dates': available_dates,
        'user_credit':     user_credit,
        'tutor_review_count': tutor_review_count,
        'course_review_count': course_review_count,
    }
    return render(request, 'tutoring/detail.html', context)


@login_required
def booking_create(request, tutc_id):
    if request.method != 'POST':
        return redirect('tutoring:course_detail', tutc_id=tutc_id)

    # ป้องกันคำขอหมดเวลากินที่นั่งค้างก่อนเริ่ม transaction การจองใหม่
    process_time_based_bookings()

    tutcourse    = get_object_or_404(TutorCourse, tutc_id=tutc_id)
    tutor_member = tutcourse.tut_id.tut_id

    ts_id     = request.POST.get('ts_id', '').strip()
    # หนึ่งบัญชีจองได้หนึ่งที่นั่งต่อหนึ่งช่วงเวลาเท่านั้น
    stu_count = 1
    bk_desc   = request.POST.get('bk_desc', '').strip()

    errors = []

    if not ts_id:
        errors.append('กรุณาเลือกช่วงเวลา')

    if tutcourse.tutc_status != 1:
        errors.append('คอร์สนี้ปิดรับการจองแล้ว')

    if not get_fixed_rate(tutcourse):
        errors.append('ไม่พบอัตราค่าบริการ')

    if errors:
        for e in errors:
            messages.error(request, e)
        return redirect('tutoring:course_detail', tutc_id=tutc_id)

    if request.user.member == tutor_member:
        messages.error(request, 'ไม่สามารถจองคอร์สของตัวเองได้')
        return redirect('tutoring:course_detail', tutc_id=tutc_id)

    try:
        with transaction.atomic():
            slot = get_object_or_404(
                TimeSlot.objects.select_for_update().select_related('sd_id__tutc_id'),
                ts_id=ts_id,
                sd_id__tutc_id=tutcourse,
            )
            if slot.ts_status == 2 or timezone.now() > get_booking_close_at(slot):
                messages.error(request, 'ช่วงเวลานี้ปิดรับการจองแล้ว')
                return redirect('tutoring:course_detail', tutc_id=tutc_id)

            if Booking.objects.filter(
                ts_id=slot,
                member=request.user.member,
            ).exclude(bk_status=6).exists():
                messages.error(request, 'คุณมีรายการจองช่วงเวลานี้แล้ว หนึ่งบัญชีจองได้หนึ่งที่นั่งต่อรอบเรียน')
                return redirect('tutoring:course_detail', tutc_id=tutc_id)

            remaining_seats = get_remaining_seats(slot)
            if remaining_seats < 1:
                messages.error(request, 'ช่วงเวลานี้เต็มแล้ว กรุณาเลือกช่วงเวลาอื่น')
                return redirect('tutoring:course_detail', tutc_id=tutc_id)

            rate_obj = get_fixed_rate(tutcourse, for_update=True)
            if not rate_obj:
                messages.error(request, 'ไม่พบอัตราค่าบริการ')
                return redirect('tutoring:course_detail', tutc_id=tutc_id)

            rate_per_person = rate_obj.tut_rate_per_person
            total_credit = rate_per_person * stu_count
            mb = Member.objects.select_for_update().get(pk=request.user.member.pk)
            available_credit = mb.mb_deposit_crd + mb.mb_income_crd - mb.mb_locked_crd
            if available_credit < total_credit:
                messages.error(request, f'เครดิตไม่เพียงพอ (ต้องการ {total_credit} เครดิต)')
                return redirect('tutoring:course_detail', tutc_id=tutc_id)

            if total_credit > 0:
                mb.mb_locked_crd += total_credit
                mb.save(update_fields=['mb_locked_crd'])

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

        if total_credit > 0:
            success_message = f'จองสำเร็จและล็อกเครดิตไว้ {total_credit} เครดิต กรุณารอผู้สอนตอบรับการจองเรียน'
        else:
            success_message = 'จองสำเร็จ รายการนี้ไม่มีใช้เครดิต(ฟรี) กรุณารอผู้สอนตอบรับ'
        messages.success(request, success_message)
        return redirect('bookings:student_bookings')
    except Exception:
        messages.error(request, 'เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง')

    return redirect('tutoring:course_detail', tutc_id=tutc_id)


# ============================================================
# PROFILE VIEWS - โปรไฟล์ติวเตอร์
# ============================================================

# ─────────────────────────────────────────────
#  หน้าโปรไฟล์ติวเตอร์ (ดูได้ทุกคน)
#  URL: /tutoring/profile/<tut_id>/
# ─────────────────────────────────────────────
def tutor_profile_view(request, tut_id):
    """
    แสดงหน้าโปรไฟล์สาธารณะของติวเตอร์
    """
    member = get_object_or_404(Member, pk=tut_id)
    tutor  = get_object_or_404(Tutor, tut_id=member)

    # คอร์สที่เปิดสอน (สถานะ = 1)
    courses = (
        TutorCourse.objects
        .filter(tut_id=tutor, tutc_status=1)
        .annotate(rate_count=Count('tutorrate'))
        .filter(rate_count=1)
        .select_related('crs_id')
        .prefetch_related('tutorrate_set')
    )

    # ราคาต่ำสุดต่อคอร์ส
    courses_with_min_rate = []
    for c in courses:
        rates    = c.tutorrate_set.all()
        min_rate = min((r.tut_rate_per_person for r in rates), default=None)
        courses_with_min_rate.append({'course': c, 'min_rate': min_rate})

    # ดึงรีวิว + รูปกิจกรรมจาก bookings (ถ้าโมดูล bookings พร้อมแล้ว)
    reviews         = []
    review_count    = 0
    activity_images = []   # list ของ URL รูปภาพ (str)
    try:
        from apps.bookings.models import Review, TutoringActivity
        # รีวิวล่าสุด 5 รายการ
        reviews_qs = (
            Review.objects
            .filter(bk_id__tutc_id__tut_id=tutor)
            .select_related('bk_id__member')
            .order_by('-rv_date')[:5]
        )
        # แนบค่าเฉลี่ยรวม 5 ด้านให้แต่ละ review
        reviews = []
        for rv in reviews_qs:
            avg = (rv.rv_quality + rv.rv_knowledge + rv.rv_communication +
                   rv.rv_punctuality + rv.rv_satisfaction) / 5
            rv.rv_avg = round(avg, 2)
            reviews.append(rv)
        review_count = Review.objects.filter(bk_id__tutc_id__tut_id=tutor).count()

        # รูปกิจกรรมทั้งหมด (ไม่จำกัดจำนวน)
        activities_all = (
            TutoringActivity.objects
            .filter(bk_id__tutc_id__tut_id=tutor)
            .order_by('-bk_id__bk_date')
        )
        all_images = []
        for act in activities_all:
            for field in ['ta_img1', 'ta_img2', 'ta_img3']:
                img = getattr(act, field)
                if img:
                    all_images.append(img.url)
        # แสดง 5 รูปแรกใน gallery, ทั้งหมดใน modal
        activity_images = all_images[:5]
    except Exception:
        pass   # bookings ยังไม่พร้อม — ไม่แสดงรีวิว/รูป

    # เจ้าของหรือไม่
    is_owner = (
        request.user.is_authenticated and
        hasattr(request.user, 'member') and
        request.user.member == member
    )

    # แยกทักษะ
    skills = [s.strip() for s in (tutor.tut_skill or '').split(',') if s.strip()]

    # สร้าง rating_rows สำหรับแสดงดาวแยกด้าน
    def make_row(label, val):
        v    = float(val or 0)
        full = int(v)
        half = (full + 1) if (v - full) >= 0.5 else 0
        return {'label': label, 'val': f"{v:.2f}", 'full': full, 'half': half}

    rating_rows = [
        make_row('คุณภาพการสอน',     tutor.tut_rating_quality),
        make_row('ความรู้ความสามารถ', tutor.tut_rating_knowledge),
        make_row('การสื่อสาร',        tutor.tut_rating_communication),
        make_row('ความตรงต่อเวลา',    tutor.tut_rating_punctuality),
        make_row('ความพึงพอใจ',       tutor.tut_rating_satisfaction),
    ]

    return render(request, 'tutoring/tutor_profile.html', {
        'tutor'                : tutor,
        'member'               : member,
        'courses_with_min_rate': courses_with_min_rate,
        'is_owner'             : is_owner,
        'skills'               : skills,
        'tutor_mb_id'          : member.pk,
        'faculty_name'         : member.mj_id.fac_id.fac_name if member.mj_id else '—',
        'major_name'           : member.mj_id.mj_name          if member.mj_id else '—',
        'reviews'              : reviews,
        'review_count'         : review_count,
        'activity_images'      : activity_images,
        'rating_rows'          : rating_rows,
        'experience_images'    : tutor.experience_images.all(),
    })


# ─────────────────────────────────────────────
#  หน้าแก้ไขโปรไฟล์ติวเตอร์ (เจ้าของเท่านั้น)
#  URL: /tutoring/profile/edit/
# ─────────────────────────────────────────────
@login_required
def tutor_profile_edit(request):
    """
    แก้ไขโปรไฟล์ติวเตอร์ของตัวเอง
    """
    member = request.user.member
    tutor  = get_object_or_404(Tutor, tut_id=member)

    skills = [s.strip() for s in (tutor.tut_skill or '').split(',') if s.strip()]

    if request.method == 'POST':
        try:
            experience_images = ExperienceImagesField().clean(request.FILES.getlist('experience_images'))
        except ValidationError as error:
            messages.error(request, ' '.join(error.messages))
            return redirect('tutoring:tutor_profile_edit')

        # อัปเดตรูปโปรไฟล์
        if 'mb_img' in request.FILES:
            member.mb_img = request.FILES['mb_img']
            member.save(update_fields=['mb_img'])

        # อัปเดตข้อมูลติวเตอร์
        tutor.tut_desc     = request.POST.get('tut_desc', '').strip()
        tutor.tut_skill    = request.POST.get('tut_skill', '').strip()
        tutor.tut_has_exp  = int(request.POST.get('tut_has_exp') == '1')
        tutor.tut_exp_desc = request.POST.get('tut_exp_desc', '').strip()
        tutor.save(update_fields=['tut_desc', 'tut_skill', 'tut_has_exp', 'tut_exp_desc'])
        if tutor.tut_has_exp:
            for image in experience_images:
                TutorExperienceImage.objects.create(tutor=tutor, image=image)

        messages.success(request, 'บันทึกโปรไฟล์เรียบร้อยแล้ว')
        return redirect('tutoring:tutor_profile', tut_id=member.pk)

    return render(request, 'tutoring/tutor_profile_edit.html', {
        'tutor'       : tutor,
        'member'      : member,
        'skills'      : skills,
        'faculty_name': member.mj_id.fac_id.fac_name if member.mj_id else '—',
        'major_name'  : member.mj_id.mj_name          if member.mj_id else '—',
        'experience_images': tutor.experience_images.all(),
    })


# ============================================================
# GENERAL VIEWS - ทั่วไป (จาก views.py เดิม)
# ============================================================

def _member_context(member):
    return {
        'member'      : member,
        'faculty_name': member.mj_id.fac_id.fac_name if member.mj_id else '',
        'major_name'  : member.mj_id.mj_name          if member.mj_id else '',
    }


def _rename_student_card(file, tut_pk):
    """เปลี่ยนชื่อไฟล์บัตรนักศึกษาเป็น tut_id{pk}.ext"""
    ext  = os.path.splitext(file.name)[1].lower() or '.jpg'
    file.name = f'tut_stu_card_id={tut_pk}{ext}'
    return file


# ─── สมัครเป็นติวเตอร์ ────────────────────────────────────────────────────────

@login_required
def register_tutor(request):
    member = request.user.member

    # ── ตรวจสอบรูปโปรไฟล์ก่อนเข้าหน้าสมัครติวเตอร์ ──
    if not member.mb_img:
        messages.warning(
            request,
            'คุณยังไม่มีรูปโปรไฟล์ กรุณาอัปโหลดรูปโปรไฟล์ก่อนสมัครเป็นติวเตอร์ เพื่อความน่าเชื่อถือของคุณ'
        )
        return redirect('accounts:profile')

    tutor  = Tutor.objects.filter(tut_id=member).first()

    initial = {}
    if tutor:
        initial = {
            'gpa'              : tutor.tut_gpax,
            'teaching_skills'  : tutor.tut_skill,
            'has_experience'   : str(tutor.tut_has_exp),
            'experience_detail': tutor.tut_exp_desc,
        }

    form = TutorRegisterForm(request.POST or None, request.FILES or None, initial=initial)

    if request.method == 'POST' and tutor and tutor.tut_status in (0, 3):
        messages.warning(request, 'ไม่สามารถแก้ไขข้อมูลระหว่างรอตรวจสอบหรือถูกระงับการสอนได้')
        return redirect('tutoring:register_tutor')

    if request.method == 'POST' and form.is_valid():
        if tutor:
            old_status         = tutor.tut_status
            tutor.tut_gpax     = form.cleaned_data['gpa']
            tutor.tut_skill    = form.cleaned_data['teaching_skills']
            tutor.tut_has_exp  = int(form.cleaned_data['has_experience'])
            tutor.tut_exp_desc = form.cleaned_data['experience_detail'] or ''
            # อัพโหลดบัตรนักศึกษาถ้ามีการส่งมา
            if form.cleaned_data.get('student_card'):
                card = _rename_student_card(form.cleaned_data['student_card'], member.pk)
                tutor.tut_student_card = card
            if old_status == 2:
                tutor.tut_status      = 0
                tutor.tut_reject_note = None  # ล้างหมายเหตุเก่าเมื่อส่งใหม่
                tutor.save()
                messages.success(request, 'ส่งคำขอใหม่เรียบร้อยแล้ว Admin จะตรวจสอบและแจ้งผลภายใน 1-3 วันทำการ')
            else:
                tutor.save()
                messages.success(request, 'อัปเดตข้อมูลติวเตอร์เรียบร้อยแล้ว')
        else:
            card = None
            if form.cleaned_data.get('student_card'):
                card = _rename_student_card(form.cleaned_data['student_card'], member.pk)
            tutor = Tutor.objects.create(
                tut_id           = member,
                tut_gpax         = form.cleaned_data['gpa'],
                tut_skill        = form.cleaned_data['teaching_skills'],
                tut_has_exp      = int(form.cleaned_data['has_experience']),
                tut_exp_desc     = form.cleaned_data['experience_detail'] or '',
                tut_student_card = card,
                tut_status       = 0,
            )
            messages.success(
                request,
                'ส่งคำขอสมัครเป็นติวเตอร์เรียบร้อยแล้ว Adminจะตรวจสอบและแจ้งผลภายใน 1-3 วันทำการ'
            )
        if tutor.tut_has_exp:
            for image in form.cleaned_data['experience_images']:
                TutorExperienceImage.objects.create(tutor=tutor, image=image)
        return redirect('tutoring:register_tutor')

    return render(request, 'tutoring/register_tutor.html', {
        **_member_context(member),
        'form'        : form,
        'tutor'       : tutor,
        'is_view_only': tutor is not None and tutor.tut_status in (0, 3),
        'reject_note' : tutor.tut_reject_note if tutor else None,
        'experience_images': tutor.experience_images.all() if tutor else [],
    })


# ─── หน้าเมนูหลัก จัดการข้อมูลติวเตอร์ ──────────────────────────────────────

@login_required
def tutor_manage(request):
    member = request.user.member
    tutor  = Tutor.objects.filter(tut_id=member).first()

    course_count         = 0
    pending_booking_count = 0
    total_student_count  = 0

    if tutor and tutor.tut_status == 1:
        courses = TutorCourse.objects.filter(tut_id=tutor)
        course_count = courses.count()
        pending_booking_count = Booking.objects.filter(
            tutc_id__tut_id=tutor, bk_status=0
        ).count()

    return render(request, 'tutoring/tutor_manage.html', {
        **_member_context(member),
        'tutor'               : tutor,
        'course_count'        : course_count,
        'pending_booking_count': pending_booking_count,
        'total_student_count' : total_student_count,
    })


# ─── รายการคอร์สของติวเตอร์ ──────────────────────────────────────────────────

@login_required
def tutor_course_list(request):
    member = request.user.member
    tutor  = get_object_or_404(Tutor, tut_id=member, tut_status=1)
    courses = TutorCourse.objects.filter(tut_id=tutor).select_related('crs_id', 'crs_id__cg_id').order_by('-tutc_id')

    return render(request, 'tutoring/tutor_course_list.html', {
        **_member_context(member),
        'tutor'  : tutor,
        'courses': courses,
    })


# ─── เพิ่ม / แก้ไขคอร์ส ──────────────────────────────────────────────────────

@login_required
def manage_course(request, tutc_id=None):
    member = request.user.member
    tutor  = get_object_or_404(Tutor, tut_id=member, tut_status=1)

    tutc  = None
    rates = []
    fixed_rate = None
    course_edit_locked = False
    schedule_dates_with_slots = []

    if tutc_id:
        tutc  = get_object_or_404(TutorCourse, tutc_id=tutc_id, tut_id=tutor)
        rates = TutorRate.objects.filter(tutc_id=tutc).order_by('tut_rate_stu_count')
        fixed_rate = rates.first()
        course_edit_locked = has_active_course_bookings(tutc)
        _today    = timezone.localdate()
        _now_time = timezone.localtime(timezone.now()).time()
        _sds  = list(
            ScheduleDate.objects.filter(tutc_id=tutc, sd_date__gte=_today)
            .prefetch_related('time_slots')
            .order_by('sd_date')
        )
        # ลบวันที่ผ่านมาแล้วได้เฉพาะเมื่อไม่เคยมีรายการจองอ้างถึง
        ScheduleDate.objects.filter(tutc_id=tutc, sd_date__lt=_today).exclude(
            time_slots__booking__isnull=False
        ).delete()

        # แนบ weekday (0=จ … 6=อา) และแยกช่วงที่แก้ไขได้ออกจากช่วงที่มีประวัติการจอง
        for sd in _sds:
            sd.weekday = sd.sd_date.weekday()
            editable_slots = [
                ts for ts in sd.time_slots.all()
                if not ts.booking_set.exists() and ts.ts_status != 2
            ]
            if sd.sd_date == _today:
                sd.available_slots = [
                    ts for ts in editable_slots if ts.ts_start_time > _now_time
                ]
            else:
                sd.available_slots = editable_slots
            sd.booked_slot_count = sum(
                1 for ts in sd.time_slots.all() if ts.booking_set.exists()
            )

        # กรองออกวันที่ไม่มี available slot เลย (ทุก slot จองหมดแล้ว)
        schedule_dates_with_slots = [sd for sd in _sds if sd.available_slots]
        # จัดกลุ่มตาม weekday โดยใช้ dict (ไม่ขึ้นกับลำดับ)
        _wd_map = {}
        for sd in schedule_dates_with_slots:
            _wd_map.setdefault(sd.weekday, []).append(sd)
        # เรียงกลุ่มตามลำดับวันในสัปดาห์ (จ→อา)
        grouped_schedule = sorted(_wd_map.items(), key=lambda x: x[0])

    course_groups = CourseGroup.objects.all().order_by('cg_name')

    if request.method == 'POST':
        # ── ข้อมูลพื้นฐาน ──
        tutc_name    = request.POST.get('tutc_name', '').strip()
        tutc_desc    = request.POST.get('tutc_desc', '').strip()
        tutc_meeting_detail = request.POST.get('tutc_meeting_detail', '').strip()
        tutc_max_stu = request.POST.get('tutc_max_stu', '').strip()
        tutc_status  = 1 if request.POST.get('tutc_status') == '1' else 0
        crs_id_val   = request.POST.get('crs_id', '').strip()

        # ── ตรวจ new_dates + existing_sd ──
        # เก็บวันที่ที่ส่งมาทั้งหมดเพื่อตรวจย้อนหลังและแจ้งข้อผิดพลาดอย่างชัดเจน
        new_dates = [
            d for d in request.POST.getlist('new_date[]')
            if d.strip()
        ]
        existing_sd_ids  = [
            key.split('ts_start_')[1].rstrip('[]').split('[')[0]
            for key in request.POST
            if key.startswith('ts_start_') and not key.startswith('ts_start_new_')
        ]
        has_any_date = len(new_dates) > 0 or len(existing_sd_ids) > 0

        # ── ตรวจราคาเดียวต่อที่นั่ง ──
        rate_per_person_raw = request.POST.get('rate_per_person', '').strip()
        rate_per_person = None
        if rate_per_person_raw.isdigit():
            rate_per_person = int(rate_per_person_raw)

        # ── ตรวจ time slots อย่างน้อย 1 ช่วงในแต่ละวัน และทุก slot ต้องกรอกครบคู่ ──
        has_all_slots   = True
        slot_error_msg  = ''

        # ── compile regex เวลา HH:MM ครั้งเดียว ──
        time_re = re.compile(r'^([01][0-9]|2[0-3]):[0-5][0-9]$')

        # วันใหม่ — key รูปแบบ ts_start_new_XXXX[]
        seen_new_suffixes = set()
        for key in request.POST:
            if key.startswith('ts_start_new_'):
                suffix = key[len('ts_start_new_'):].rstrip('[]')
                if suffix in seen_new_suffixes:
                    continue
                seen_new_suffixes.add(suffix)

                starts = [s.strip() for s in request.POST.getlist(key)]
                ends   = [e.strip() for e in request.POST.getlist(f'ts_end_new_{suffix}[]')]

                if len(starts) == 0:
                    has_all_slots  = False
                    slot_error_msg = 'แต่ละวันต้องมีช่วงเวลาอย่างน้อย 1 ช่วง'
                    break
                if len(starts) != len(ends):
                    has_all_slots  = False
                    slot_error_msg = 'กรุณากรอกเวลาเริ่มและเวลาสิ้นสุดให้ครบทุกช่วง'
                    break
                # ตรวจ format HH:MM และ end > start
                for s, e in zip(starts, ends):
                    if not s or not e:
                        has_all_slots = False
                        slot_error_msg = 'กรุณากรอกเวลาเริ่มและเวลาสิ้นสุดให้ครบทุกช่วง'
                        break
                    if not time_re.match(s) or not time_re.match(e):
                        has_all_slots  = False
                        slot_error_msg = 'รูปแบบเวลาไม่ถูกต้อง กรุณาใช้รูปแบบ HH:MM (เช่น 09:00)'
                        break
                    if e <= s:
                        has_all_slots  = False
                        slot_error_msg = 'เวลาสิ้นสุดต้องมากกว่าเวลาเริ่มต้น'
                        break
                if not has_all_slots:
                    break

        # วันเก่า — key รูปแบบ ts_start_SDID[]
        if has_all_slots:
            for sd_id_str in existing_sd_ids:
                starts = [s.strip() for s in request.POST.getlist(f'ts_start_{sd_id_str}[]')]
                ends   = [e.strip() for e in request.POST.getlist(f'ts_end_{sd_id_str}[]')]

                if len(starts) == 0:
                    has_all_slots  = False
                    slot_error_msg = 'แต่ละวันต้องมีช่วงเวลาอย่างน้อย 1 ช่วง'
                    break
                if len(starts) != len(ends):
                    has_all_slots  = False
                    slot_error_msg = 'กรุณากรอกเวลาเริ่มและเวลาสิ้นสุดให้ครบทุกช่วง'
                    break
                for s, e in zip(starts, ends):
                    if not s or not e:
                        has_all_slots = False
                        slot_error_msg = 'กรุณากรอกเวลาเริ่มและเวลาสิ้นสุดให้ครบทุกช่วง'
                        break
                    if not time_re.match(s) or not time_re.match(e):
                        has_all_slots  = False
                        slot_error_msg = 'รูปแบบเวลาไม่ถูกต้อง กรุณาใช้รูปแบบ HH:MM (เช่น 09:00)'
                        break
                    if e <= s:
                        has_all_slots  = False
                        slot_error_msg = 'เวลาสิ้นสุดต้องมากกว่าเวลาเริ่มต้น'
                        break
                if not has_all_slots:
                    break

        # ตรวจวันและเวลาเริ่มก่อนแก้ข้อมูลใด ๆ เพื่อไม่ให้ส่งฟอร์มข้ามข้อจำกัดหน้าเว็บ
        if has_all_slots:
            local_now = timezone.localtime(timezone.now())
            today_date = local_now.date()
            posted_new_dates = request.POST.getlist('new_date[]')
            posted_new_suffixes = []
            for key in request.POST:
                if key.startswith('ts_start_new_'):
                    suffix = key[len('ts_start_new_'):].rstrip('[]')
                    if suffix not in posted_new_suffixes:
                        posted_new_suffixes.append(suffix)

            if len(posted_new_dates) != len(posted_new_suffixes):
                has_all_slots = False
                slot_error_msg = 'ข้อมูลวันที่และช่วงเวลาไม่ครบ กรุณาเพิ่มใหม่อีกครั้ง'
            else:
                for date_str, suffix in zip(posted_new_dates, posted_new_suffixes):
                    try:
                        slot_date = timezone.datetime.strptime(date_str, '%Y-%m-%d').date()
                    except ValueError:
                        has_all_slots = False
                        slot_error_msg = 'รูปแบบวันที่เปิดสอนไม่ถูกต้อง'
                        break
                    if slot_date < today_date:
                        has_all_slots = False
                        slot_error_msg = 'ไม่สามารถเพิ่มวันที่ผ่านมาแล้วได้'
                        break
                    starts = request.POST.getlist(f'ts_start_new_{suffix}[]')
                    if any(
                        not _is_future_schedule_start(slot_date, start.strip(), local_now)
                        for start in starts
                    ):
                        has_all_slots = False
                        slot_error_msg = f'ต้องกำหนดเวลาเริ่มเรียนล่วงหน้าอย่างน้อย {settings.BOOKING_CLOSE_HOURS} ชั่วโมง'
                        break

            if has_all_slots and existing_sd_ids:
                valid_sd_ids = [int(sd_id) for sd_id in existing_sd_ids if sd_id.isdigit()]
                schedule_dates = dict(
                    ScheduleDate.objects.filter(tutc_id=tutc, sd_id__in=valid_sd_ids)
                    .values_list('sd_id', 'sd_date')
                )
                for sd_id_str in existing_sd_ids:
                    slot_date = schedule_dates.get(int(sd_id_str)) if sd_id_str.isdigit() else None
                    if slot_date is None:
                        has_all_slots = False
                        slot_error_msg = 'ไม่พบวันที่เปิดสอนที่ต้องการแก้ไข'
                        break
                    if slot_date < today_date:
                        has_all_slots = False
                        slot_error_msg = 'ไม่สามารถบันทึกวันที่ผ่านมาแล้วได้'
                        break
                    starts = request.POST.getlist(f'ts_start_{sd_id_str}[]')
                    if any(
                        not _is_future_schedule_start(slot_date, start.strip(), local_now)
                        for start in starts
                    ):
                        has_all_slots = False
                        slot_error_msg = f'ต้องกำหนดเวลาเริ่มเรียนล่วงหน้าอย่างน้อย {settings.BOOKING_CLOSE_HOURS} ชั่วโมง'
                        break

        # ── รวม error ──
        errors = []
        if not tutc_name:
            errors.append('กรุณากรอกชื่อรายวิชา')
        if not tutc_meeting_detail:
            errors.append('กรุณาระบุรายละเอียดนัดหมายเริ่มต้น')
        if not crs_id_val:
            errors.append('กรุณาเลือกรายวิชา')
        if not tutc_max_stu or not tutc_max_stu.isdigit() or int(tutc_max_stu) < 1:
            errors.append('กรุณาระบุจำนวนรับสูงสุด')
        if not has_any_date:
            errors.append('กรุณาเพิ่มวันที่อย่างน้อย 1 วัน')
        elif not has_all_slots:
            errors.append(slot_error_msg or 'แต่ละวันต้องมีช่วงเวลาอย่างน้อย 1 ช่วง')
        if rate_per_person is None:
            errors.append('กรุณาระบุราคาต่อที่นั่งเป็นจำนวนเต็มตั้งแต่ 0 เครดิตขึ้นไป')

        # ราคาและจำนวนรับเปลี่ยนไม่ได้ขณะมีรายการรอรับหรือรอเรียน
        if tutc and has_active_course_bookings(tutc):
            current_rate = get_fixed_rate(tutc)
            current_price = current_rate.tut_rate_per_person if current_rate else None
            max_changed = tutc_max_stu.isdigit() and int(tutc_max_stu) != tutc.tutc_max_stu
            price_changed = rate_per_person is not None and rate_per_person != current_price
            if max_changed or price_changed:
                errors.append(
                    'ไม่สามารถแก้ราคาและจำนวนรับได้ '
                    'เนื่องจากมีรายการจองที่รอตอบรับหรือรอเรียนอยู่'
                )

        if errors:
            for err in errors:
                messages.error(request, err)
            return render(request, 'tutoring/manage_course.html', {
                **_member_context(member),
                'tutor'                    : tutor,
                'tutc'                     : tutc,
                'rates'                    : rates,
                'fixed_rate'               : fixed_rate,
                'course_edit_locked'       : course_edit_locked,
                'course_groups'            : course_groups,
                'schedule_dates_with_slots': schedule_dates_with_slots,
                'grouped_schedule'         : grouped_schedule if tutc_id else [],
                'weekday_labels'           : ['จ','อ','พ','พฤ','ศ','ส','อา'],
                'booking_close_hours'      : settings.BOOKING_CLOSE_HOURS,
            })

        course = get_object_or_404(Course, crs_id=crs_id_val)

        # ── สร้าง / อัปเดต TutorCourse ──
        if tutc:
            tutc.tutc_name    = tutc_name
            tutc.tutc_desc    = tutc_desc or None
            tutc.tutc_meeting_detail = tutc_meeting_detail or None
            tutc.tutc_max_stu = int(tutc_max_stu)
            tutc.tutc_status  = tutc_status
            tutc.crs_id       = course
            if 'tutc_img' in request.FILES:
                img_file = request.FILES['tutc_img']
                ext = os.path.splitext(img_file.name)[1].lower() or '.jpg'
                img_file.name = f'tutc_{tutc.tutc_id}{ext}'
                tutc.tutc_img = img_file
            tutc.save()
            messages.success(request, 'อัปเดตคอร์สเรียบร้อยแล้ว')
        else:
            # สร้าง tutc_id แบบ TUTC001, TUTC002, ...
            last = TutorCourse.objects.order_by('-tutc_id').first()
            if last and re.match(r'TUTC\d+', last.tutc_id):
                last_num = int(last.tutc_id[4:])
            else:
                last_num = 0
            new_id = f"TUTC{last_num + 1:03d}"
            img_file = request.FILES.get('tutc_img')
            if img_file:
                ext = os.path.splitext(img_file.name)[1].lower() or '.jpg'
                img_file.name = f'tutc_{new_id}{ext}'
            tutc = TutorCourse.objects.create(
                tutc_id      = new_id,
                tutc_name    = tutc_name,
                tutc_desc    = tutc_desc or None,
                tutc_meeting_detail = tutc_meeting_detail or None,
                tutc_max_stu = int(tutc_max_stu),
                tutc_status  = tutc_status,
                crs_id       = course,
                tut_id       = tutor,
                tutc_img     = img_file,
            )
            messages.success(request, 'เพิ่มคอร์สเรียบร้อยแล้ว')

        # ── อัปเดตราคาเดียวต่อที่นั่ง โดยคงตาราง TutorRate เดิมไว้ ──
        TutorRate.objects.filter(tutc_id=tutc).delete()
        TutorRate.objects.create(
            tutc_id=tutc,
            tut_rate_stu_count=1,
            tut_rate_per_person=rate_per_person,
        )

        # ── อัปเดต Schedule Dates + Time Slots ──
        # วันที่มีอยู่แล้ว (sd_id ที่ส่งมาจาก POST)
        existing_sd_ids = [
            key.split('ts_start_')[1].rstrip('[]').split('[')[0]
            for key in request.POST
            if key.startswith('ts_start_') and not key.startswith('ts_start_new_')
        ]
        # ลบ sd เก่าที่ไม่ได้ส่งมา (ผู้ใช้กดลบออก)
        # เฉพาะวันที่ไม่เคยมี Booking เพื่อไม่ทำให้ประวัติรายการจองเสียความสัมพันธ์
        ScheduleDate.objects.filter(tutc_id=tutc).exclude(sd_id__in=[
            int(i) for i in existing_sd_ids if i.isdigit()
        ]).exclude(time_slots__booking__isnull=False).delete()

        # ลบวันที่ผ่านมาแล้วที่ค้างในฐานข้อมูล (ไม่มี booking อยู่)
        _today_save = timezone.localdate()
        ScheduleDate.objects.filter(
            tutc_id=tutc, sd_date__lt=_today_save
        ).exclude(time_slots__booking__isnull=False).delete()

        # อัปเดต time slots ของวันที่มีอยู่
        for sd_id_str in existing_sd_ids:
            if not sd_id_str.isdigit():
                continue
            sd = ScheduleDate.objects.filter(sd_id=int(sd_id_str), tutc_id=tutc).first()
            if not sd:
                continue
            TimeSlot.objects.filter(sd_id=sd, booking__isnull=True).delete()
            starts = request.POST.getlist(f'ts_start_{sd_id_str}[]')
            ends   = request.POST.getlist(f'ts_end_{sd_id_str}[]')
            for s, e in zip(starts, ends):
                if s and e:
                    TimeSlot.objects.create(sd_id=sd, ts_start_time=s, ts_end_time=e)

        # วันที่ใหม่ — จับคู่ new_date[] กับ ts_start_new_XXXX[] ตามลำดับ
        new_dates = request.POST.getlist('new_date[]')

        # รวบรวม suffix ทั้งหมดของ new dates ตามลำดับจริงใน POST (ไม่ sort)
        # Django MultiValueDict เก็บลำดับ key ตามที่ browser ส่งมา
        new_suffixes = []
        seen_suffixes = set()
        for key in request.POST:
            if key.startswith('ts_start_new_'):
                suffix = key[len('ts_start_new_'):].rstrip('[]')
                if suffix not in seen_suffixes:
                    seen_suffixes.add(suffix)
                    new_suffixes.append(suffix)

        # จับคู่ new_date[i] กับ suffix[i]
        for i, date_str in enumerate(new_dates):
            if not date_str:
                continue
            sd = ScheduleDate.objects.create(sd_date=date_str, tutc_id=tutc)
            if i < len(new_suffixes):
                suffix = new_suffixes[i]
                starts = request.POST.getlist(f'ts_start_new_{suffix}[]')
                ends   = request.POST.getlist(f'ts_end_new_{suffix}[]')
                for s, e in zip(starts, ends):
                    if s and e:
                        TimeSlot.objects.create(sd_id=sd, ts_start_time=s, ts_end_time=e)

        return redirect('tutoring:tutor_course_list')

    return render(request, 'tutoring/manage_course.html', {
        **_member_context(member),
        'tutor'                   : tutor,
        'tutc'                    : tutc,
        'rates'                   : rates,
        'fixed_rate'              : fixed_rate,
        'course_edit_locked'      : course_edit_locked,
        'course_groups'           : course_groups,
        'schedule_dates_with_slots': schedule_dates_with_slots,
        'grouped_schedule'        : grouped_schedule if tutc_id else [],
        'weekday_labels'          : ['จ','อ','พ','พฤ','ศ','ส','อา'],
        'booking_close_hours'     : settings.BOOKING_CLOSE_HOURS,
    })


# ─── เปิด / ปิด รับนักเรียน ──────────────────────────────────────────────────

@login_required
def toggle_course_status(request, tutc_id):
    if request.method != 'POST':
        return redirect('tutoring:tutor_course_list')

    member = request.user.member
    tutor  = get_object_or_404(Tutor, tut_id=member, tut_status=1)
    tutc   = get_object_or_404(TutorCourse, tutc_id=tutc_id, tut_id=tutor)

    tutc.tutc_status = 0 if tutc.tutc_status == 1 else 1
    tutc.save()

    label = 'เปิดรับสอน' if tutc.tutc_status == 1 else 'ปิดรับสอน'
    messages.success(request, f'เปลี่ยนสถานะคอร์ส "{tutc.tutc_name}" เป็น {label} แล้ว')
    return redirect('tutoring:tutor_course_list')


# ─── ลบคอร์ส ─────────────────────────────────────────────────────────────────

@login_required
def delete_course(request, tutc_id):
    if request.method != 'POST':
        return redirect('tutoring:tutor_course_list')

    member = request.user.member
    tutor  = get_object_or_404(Tutor, tut_id=member, tut_status=1)
    tutc   = get_object_or_404(TutorCourse, tutc_id=tutc_id, tut_id=tutor)

    # ✅ เช็ค Booking ที่ยังดำเนินอยู่ (จอง / รับงาน / เรียนอยู่ / แจ้งจบงานแล้วแต่ยังไม่ยืนยัน)
    ACTIVE_STATUSES = [0, 1, 2, 3]  # จอง, รับงานแล้ว, เรียนแล้ว, แจ้งจบงาน
    has_active = Booking.objects.filter(
        tutc_id=tutc,
        bk_status__in=ACTIVE_STATUSES
    ).exists()

    if has_active:
        messages.error(
            request,
            f'ไม่สามารถลบคอร์ส "{tutc.tutc_name}" ได้ '
            f'เนื่องจากมีนักเรียนที่จองหรือกำลังเรียนอยู่'
        )
        return redirect('tutoring:tutor_course_list')

    name = tutc.tutc_name
    tutc.delete()
    messages.error(request, f'ลบคอร์ส "{name}" เรียบร้อยแล้ว')
    return redirect('tutoring:tutor_course_list')
