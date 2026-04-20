from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from apps.accounts.models import Tutor, Member
from .models import TutorCourse, TutorRate


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
        from apps.bookings.models import Review, TutoringActivity, Booking
        # รีวิวล่าสุด 5 รายการ
        reviews = (
            Review.objects
            .filter(bk_id__tutc_id__tut_id=tutor)
            .select_related('bk_id__member')
            .order_by('-rv_date')[:5]
        )
        review_count = Review.objects.filter(bk_id__tutc_id__tut_id=tutor).count()

        # รูปกิจกรรมล่าสุด (สูงสุด 5 รูป)
        activities = (
            TutoringActivity.objects
            .filter(bk_id__tutc_id__tut_id=tutor)
            .order_by('-bk_id__bk_date')[:3]
        )
        for act in activities:
            for field in ['ta_img1', 'ta_img2', 'ta_img3']:
                img = getattr(act, field)
                if img:
                    activity_images.append(img.url)
                    if len(activity_images) >= 5:
                        break
            if len(activity_images) >= 5:
                break
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
        # อัปเดตรูปโปรไฟล์
        if 'mb_img' in request.FILES:
            member.mb_img = request.FILES['mb_img']
            member.save(update_fields=['mb_img'])

        # อัปเดตข้อมูลติวเตอร์
        tutor.tut_desc     = request.POST.get('tut_desc', '').strip()
        tutor.tut_skill    = request.POST.get('tut_skill', '').strip()
        tutor.tut_has_exp  = int(request.POST.get('tut_has_exp', 0))
        tutor.tut_exp_desc = request.POST.get('tut_exp_desc', '').strip()
        tutor.save(update_fields=['tut_desc', 'tut_skill', 'tut_has_exp', 'tut_exp_desc'])

        messages.success(request, 'บันทึกโปรไฟล์เรียบร้อยแล้ว')
        return redirect('tutoring:tutor_profile', tut_id=member.pk)

    return render(request, 'tutoring/tutor_profile_edit.html', {
        'tutor'       : tutor,
        'member'      : member,
        'skills'      : skills,
        'faculty_name': member.mj_id.fac_id.fac_name if member.mj_id else '—',
        'major_name'  : member.mj_id.mj_name          if member.mj_id else '—',
    })