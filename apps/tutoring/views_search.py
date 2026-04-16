from django.shortcuts import render
from django.db.models import Q, OuterRef, Subquery
from apps.tutoring.models import TutorCourse, TutorRate
from apps.courses.models import CourseGroup, Course


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
        .annotate(lowest_price=Subquery(min_rate_subquery))
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

    # ── Filter: คะแนนรีวิว ──
    if min_rating:
        tutorcourses = tutorcourses.filter(tut_id__tut_rating__gte=float(min_rating))

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
        'result_count':  tutorcourses.count(),
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