# admin_panel/views.py - views สำหรับผู้ดูแลระบบ
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.db import transaction
from django.urls import reverse

from django.utils import timezone
from django.db.models import Sum, Count, Avg

from .models import System
from .forms  import SystemForm, AdminUserForm
from apps.accounts.models import Tutor, Member
from apps.credits.models  import Refill, Withdrawals
from apps.courses.models  import Faculty, Major

# นำเข้าฟังก์ชันสร้าง QR Code จากแอป credits
from apps.credits.views import _generate_promptpay_qr


def is_admin(user):
    # ตรวจว่าเป็น staff และต้องเป็น admin ที่ผูกกับ System เท่านั้น
    # ป้องกัน superuser เข้า admin panel
    if not user.is_authenticated or not user.is_staff:
        return False
    return System.objects.filter(admin=user).exists()


def member_user_queryset():
    return Member.objects.filter(user__is_staff=False, user__is_superuser=False)


# ─── Dashboard ───────────────────────────────────────────────────────────────

@login_required
@user_passes_test(is_admin)
def dashboard(request):
    from apps.courses.models import Faculty, Major, CourseGroup, Course
    from apps.bookings.models import Booking, JobCompletion, Review
    import json
    from datetime import datetime, date, time, timedelta

    # ── Summary stats ──
    member_users = member_user_queryset()
    total_members   = member_users.count()
    active_members  = member_users.filter(mb_status=1).count()
    total_tutors    = Tutor.objects.filter(tut_id__user__is_staff=False, tut_id__user__is_superuser=False, tut_status=1).count()
    pending_tutors  = Tutor.objects.filter(tut_id__user__is_staff=False, tut_id__user__is_superuser=False, tut_status=0).count()

    approved_refills = Refill.objects.filter(rf_status=1)
    total_topup_money = approved_refills.aggregate(t=Sum('rf_money'))['t'] or 0
    pending_refills   = Refill.objects.filter(rf_status=0).count()
    pending_withdraw  = Withdrawals.objects.filter(wd_status=0).count()
    pending_reports   = Booking.objects.filter(bk_report_date__isnull=False, bk_report_resolved_date__isnull=True).count()

    total_faculties   = Faculty.objects.count()
    total_majors      = Major.objects.count()
    total_courses     = Course.objects.count()
    total_bookings    = Booking.objects.count()
    active_bookings   = Booking.objects.filter(bk_status__in=[0, 1, 2, 3]).count()
    completed_bookings = Booking.objects.filter(bk_status__in=[4, 5]).count()
    pending_completions = JobCompletion.objects.filter(jc_confirm_date__isnull=True).count()
    average_review = Review.objects.aggregate(avg=Avg('rv_satisfaction'))['avg'] or 0
    
    # System revenue (fees)
    system = System.objects.first()
    total_fees = system.total_accumulated_fee if system else 0

    # ── Monthly new members (last 7 months) ──
    today = timezone.now()
    chart_metric = request.GET.get('chart_metric', 'members')
    chart_range = request.GET.get('chart_range', '6m')
    metric_config = {
        'members': ('สมาชิกใหม่', Member, 'user__date_joined', 'count'),
        'bookings': ('การสมัครเรียน', Booking, 'bk_date', 'count'),
        'topups': ('ยอดเติมเครดิต', Refill, 'rf_date', 'sum'),
        'reviews': ('รีวิวที่ได้รับ', Review, 'rv_date', 'count'),
    }
    if chart_metric not in metric_config:
        chart_metric = 'members'
    if chart_range not in {'7d', '30d', '6m', 'year'}:
        chart_range = '6m'
    metric_label, metric_model, metric_field, metric_operation = metric_config[chart_metric]
    chart_labels, chart_data, periods = [], [], []
    if chart_range in {'7d', '30d'}:
        day_count = 7 if chart_range == '7d' else 30
        first_day = today.date() - timedelta(days=day_count - 1)
        for offset in range(day_count):
            current_day = first_day + timedelta(days=offset)
            periods.append((current_day, current_day + timedelta(days=1)))
            chart_labels.append(current_day.strftime('%d/%m'))
    else:
        month_count = 6 if chart_range == '6m' else 12
        for offset in range(month_count - 1, -1, -1):
            year = today.year
            month = today.month - offset
            while month <= 0:
                month += 12
                year -= 1
            current_month = date(year, month, 1)
            next_month = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
            periods.append((current_month, next_month))
            chart_labels.append(f'{month:02d}/{str(year)[-2:]}')
    for period_start, period_end in periods:
        start_datetime = timezone.make_aware(datetime.combine(period_start, time.min), timezone.get_current_timezone())
        end_datetime = timezone.make_aware(datetime.combine(period_end, time.min), timezone.get_current_timezone())
        period_qs = metric_model.objects.filter(**{f'{metric_field}__gte': start_datetime, f'{metric_field}__lt': end_datetime})
        if metric_operation == 'sum':
            value = period_qs.filter(rf_status=1).aggregate(total=Sum('rf_money'))['total'] or 0
            chart_data.append(float(value))
        else:
            chart_data.append(period_qs.count())
    MONTH_TH = ['', 'ม.ค.', 'ก.พ.', 'มี.ค.', 'เม.ย.', 'พ.ค.', 'มิ.ย.',
                'ก.ค.', 'ส.ค.', 'ก.ย.', 'ต.ค.', 'พ.ย.', 'ธ.ค.']
    for i in range(6, -1, -1):
        year = today.year
        month = today.month - i
        while month <= 0:
            month += 12
            year -= 1

        # กรองช่วงวันเวลาโดยตรง เพื่อไม่พึ่ง CONVERT_TZ ของ MySQL
        # ซึ่งอาจคืนค่า NULL หากฐานข้อมูลไม่มีตาราง Time Zone
        month_start = timezone.make_aware(datetime(year, month, 1), timezone.get_current_timezone())
        if month == 12:
            next_month_start = timezone.make_aware(datetime(year + 1, 1, 1), timezone.get_current_timezone())
        else:
            next_month_start = timezone.make_aware(datetime(year, month + 1, 1), timezone.get_current_timezone())

        # การนับสมาชิกถูกย้ายไปใช้ชุดข้อมูลกราฟที่เลือกด้านบนแล้ว

    # ── Top course groups by course count ──
    top_groups = (CourseGroup.objects
                  .annotate(crs_count=Count('course'))
                  .order_by('-crs_count')[:5])
    max_crs = top_groups[0].crs_count if top_groups else 1

    # ── Recent activity ──
    recent_members  = member_users.select_related('user').order_by('-user__date_joined')[:5]
    recent_refills  = Refill.objects.select_related('member').order_by('-rf_date')[:5]
    recent_withdraw = Withdrawals.objects.select_related('member').order_by('-wd_req_date')[:3]
    recent_bookings = (Booking.objects
                       .select_related('member', 'tutc_id__tut_id__tut_id')
                       .order_by('-bk_date')[:5])
    recent_completions = (JobCompletion.objects
                          .select_related('bk_id__member', 'bk_id__tutc_id__tut_id__tut_id')
                          .order_by('-jc_complete_date')[:5])

    return render(request, 'admin_panel/dashboard.html', {
        'active_menu'       : 'dashboard',
        'topbar_breadcrumb' : 'ภาพรวมแดชบอร์ด',
        # stats
        'total_members'     : total_members,
        'active_members'    : active_members,
        'total_tutors'      : total_tutors,
        'pending_tutors'    : pending_tutors,
        'total_topup_money' : total_topup_money,
        'pending_refills'   : pending_refills,
        'pending_withdraw'  : pending_withdraw,
        'pending_reports'   : pending_reports,
        'total_faculties'   : total_faculties,
        'total_majors'      : total_majors,
        'total_courses'     : total_courses,
        'total_bookings'    : total_bookings,
        'active_bookings'   : active_bookings,
        'completed_bookings': completed_bookings,
        'pending_completions': pending_completions,
        'average_review'    : average_review,
        'total_fees'        : total_fees,
        # chart
        'chart_labels'      : json.dumps(chart_labels, ensure_ascii=False),
        'chart_data'        : json.dumps(chart_data),
        'chart_metric'      : chart_metric,
        'chart_range'       : chart_range,
        'chart_metric_label': metric_label,
        # top groups
        'top_groups'        : top_groups,
        'max_crs'           : max_crs,
        # recent activity
        'recent_members'    : recent_members,
        'recent_refills'    : recent_refills,
        'recent_withdraw'   : recent_withdraw,
        'recent_bookings'   : recent_bookings,
        'recent_completions': recent_completions,
    })


# ─── ศูนย์ออกรายงาน ───────────────────────────────────────────────────────

@login_required
@user_passes_test(is_admin)
def report_center(request):
    """แสดงตัวอย่างรายงานตามประเภทและตัวกรองที่ผู้ดูแลเลือก"""
    from apps.bookings.models import Booking, Review
    from apps.courses.models import Course, CourseGroup

    report_type = request.GET.get('report_type', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    status = request.GET.get('status', 'all')
    order = request.GET.get('order', 'latest')
    course_group = request.GET.get('course_group', '')

    report_titles = {
        'members': 'รายงานสมาชิก', 'tutors': 'รายงานติวเตอร์',
        'courses': 'รายงานรายวิชา', 'bookings': 'รายงานการสมัครเรียน',
        'tutor_income': 'รายงานรายได้ติวเตอร์', 'refills': 'รายงานการเติมเครดิต',
        'summary': 'รายงานสรุปภาพรวมระบบ',
    }
    if not report_type:
        return render(request, 'admin_panel/report_center.html', {
            'active_menu': 'dashboard', 'topbar_breadcrumb': 'ออกรายงาน',
            'report_selected': False,
        })
    if report_type not in report_titles:
        report_type = 'members'

    filter_configs = {
        'members': {
            'date_label': 'วันที่สมัครสมาชิก',
            'status_label': 'สถานะบัญชี',
            'status_options': [('all', 'ทั้งหมด'), ('0', 'ปิดการใช้งาน'), ('1', 'ใช้งานปกติ'), ('2', 'ระงับชั่วคราว')],
        },
        'tutors': {
            'date_label': 'วันที่สมัครเป็นติวเตอร์',
            'status_label': 'สถานะติวเตอร์',
            'status_options': [('all', 'ทั้งหมด'), ('0', 'รอการตรวจสอบ'), ('1', 'อนุมัติแล้ว'), ('2', 'ปฏิเสธ'), ('3', 'ระงับการสอน')],
        },
        'courses': {
            'date_label': '', 'status_label': '', 'status_options': [],
        },
        'bookings': {
            'date_label': 'วันที่สมัครเรียน',
            'status_label': 'สถานะการสมัครเรียน',
            'status_options': [('all', 'ทั้งหมด'), ('0', 'จอง'), ('1', 'รับงานแล้ว'), ('2', 'เรียนแล้ว'), ('3', 'แจ้งจบงาน'), ('4', 'ยืนยันการจบงาน'), ('5', 'รีวิวแล้ว'), ('6', 'ปฏิเสธ')],
        },
        'tutor_income': {
            'date_label': 'วันที่รับงาน',
            'status_label': 'สถานะงาน',
            'status_options': [('all', 'ทั้งหมด'), ('0', 'จอง'), ('1', 'รับงานแล้ว'), ('2', 'เรียนแล้ว'), ('3', 'แจ้งจบงาน'), ('4', 'ยืนยันการจบงาน'), ('5', 'รีวิวแล้ว'), ('6', 'ปฏิเสธ')],
        },
        'refills': {
            'date_label': 'วันที่เติมเครดิต',
            'status_label': 'สถานะการเติมเครดิต',
            'status_options': [('all', 'ทั้งหมด'), ('0', 'รอตรวจสอบ'), ('1', 'ผ่านการตรวจสอบ'), ('2', 'ไม่ผ่านการตรวจสอบ')],
        },
        'summary': {
            'date_label': '', 'status_label': '', 'status_options': [],
        },
    }
    filter_config = filter_configs[report_type]
    if report_type == 'courses':
        filter_config['course_groups'] = CourseGroup.objects.order_by('cg_name')

    def apply_date_filter(queryset, field_name):
        # เปรียบเทียบช่วงวันเวลาโดยตรง เพราะฐานข้อมูล MySQL อาจไม่มีตาราง Time Zone
        # ซึ่งทำให้การใช้ lookup __date คืนค่า NULL และกรองข้อมูลไม่พบ
        from datetime import datetime, time
        from django.utils.dateparse import parse_date

        start = parse_date(start_date) if start_date else None
        end = parse_date(end_date) if end_date else None
        timezone_info = timezone.get_current_timezone()
        if start:
            start_datetime = timezone.make_aware(datetime.combine(start, time.min), timezone_info)
            queryset = queryset.filter(**{f'{field_name}__gte': start_datetime})
        if end:
            end_datetime = timezone.make_aware(datetime.combine(end, time.max), timezone_info)
            queryset = queryset.filter(**{f'{field_name}__lte': end_datetime})
        return queryset

    headers, rows, summary_items = [], [], []
    if report_type == 'members':
        queryset = apply_date_filter(member_user_queryset().select_related('user'), 'user__date_joined')
        if status != 'all' and status in {'0', '1', '2'}:
            queryset = queryset.filter(mb_status=int(status))
        queryset = queryset.order_by('user__date_joined' if order == 'oldest' else '-user__date_joined')
        headers = ['ชื่อสมาชิก', 'ประเภท', 'วันที่สมัคร', 'สถานะ', 'เครดิตคงเหลือ']
        tutor_member_ids = set(Tutor.objects.values_list('tut_id_id', flat=True))
        rows = [[m.mb_full_name, 'ติวเตอร์' if m.pk in tutor_member_ids else 'ผู้เรียน', m.user.date_joined, m.get_mb_status_display(), m.mb_deposit_crd + m.mb_income_crd] for m in queryset]
        summary_items = [('สมาชิกทั้งหมด', len(rows)), ('ติวเตอร์', sum(1 for row in rows if row[1] == 'ติวเตอร์')), ('ผู้เรียน', sum(1 for row in rows if row[1] == 'ผู้เรียน'))]
    elif report_type == 'tutors':
        queryset = apply_date_filter(Tutor.objects.select_related('tut_id__user').annotate(course_count=Count('tutorcourse')), 'tut_id__user__date_joined')
        if status != 'all' and status in {'0', '1', '2', '3'}:
            queryset = queryset.filter(tut_status=int(status))
        queryset = queryset.order_by('tut_id__user__date_joined' if order == 'oldest' else '-tut_id__user__date_joined')
        headers = ['ชื่อติวเตอร์', 'รายวิชาที่เปิดสอน', 'คะแนนรีวิว', 'สถานะ', 'วันที่สมัคร']
        rows = [[t.tut_id.mb_full_name, t.course_count, t.tut_rating, t.get_tut_status_display(), t.tut_id.user.date_joined] for t in queryset]
        summary_items = [('ติวเตอร์ทั้งหมด', len(rows)), ('คะแนนรีวิวเฉลี่ย', round(sum(float(row[2]) for row in rows) / len(rows), 2) if rows else 0), ('รายวิชาที่เปิดสอนรวม', sum(row[1] for row in rows))]
    elif report_type == 'courses':
        queryset = Course.objects.select_related('cg_id').annotate(tutor_count=Count('tutorcourse'))
        if course_group:
            queryset = queryset.filter(cg_id_id=course_group)
        # Course ไม่มีวันที่สร้าง จึงใช้รหัสรายวิชาแทนลำดับล่าสุด/เก่าสุด
        queryset = queryset.order_by('crs_id' if order == 'oldest' else '-crs_id')
        headers = ['รหัสรายวิชา', 'ชื่อรายวิชา', 'กลุ่มรายวิชา', 'ติวเตอร์ที่เปิดสอน']
        rows = [[c.crs_id, c.crs_name, c.cg_id.cg_name, c.tutor_count] for c in queryset]
        summary_items = [('รายวิชาทั้งหมด', len(rows)), ('ติวเตอร์ที่เปิดสอนรวม', sum(row[3] for row in rows))]
    elif report_type in {'bookings', 'tutor_income'}:
        queryset = apply_date_filter(Booking.objects.select_related('member', 'tutc_id__tut_id__tut_id'), 'bk_date')
        if status != 'all' and status in {'0', '1', '2', '3', '4', '5', '6'}:
            queryset = queryset.filter(bk_status=int(status))
        queryset = queryset.order_by('bk_date' if order == 'oldest' else '-bk_date')
        if report_type == 'bookings':
            headers = ['รหัสการจอง', 'ผู้เรียน', 'ติวเตอร์', 'รายวิชา', 'วันที่สมัครเรียน', 'สถานะ']
            rows = [[f'BK{b.bk_id:05d}', b.member.mb_full_name, b.tutc_id.tut_id.tut_id.mb_full_name, b.tutc_id.tutc_name, b.bk_date, b.get_bk_status_display()] for b in queryset]
            summary_items = [('การสมัครเรียนทั้งหมด', len(rows)), ('เรียนสำเร็จ', sum(1 for row in rows if row[5] in {'ยืนยันการจบงาน', 'รีวิวแล้ว'}))]
        else:
            headers = ['ติวเตอร์', 'รหัสการจอง', 'รายวิชา', 'เครดิตที่ได้รับ', 'สถานะ', 'วันที่สมัครเรียน']
            rows = [[b.tutc_id.tut_id.tut_id.mb_full_name, f'BK{b.bk_id:05d}', b.tutc_id.tutc_name, b.total_credit, b.get_bk_status_display(), b.bk_date] for b in queryset]
            summary_items = [('งานที่รับทั้งหมด', len(rows)), ('เครดิตค่าติวรวม', sum(row[3] for row in rows))]
    elif report_type == 'refills':
        queryset = apply_date_filter(Refill.objects.select_related('member'), 'rf_date')
        if status != 'all' and status in {'0', '1', '2'}:
            queryset = queryset.filter(rf_status=int(status))
        queryset = queryset.order_by('rf_date' if order == 'oldest' else '-rf_date')
        headers = ['รหัสรายการ', 'สมาชิก', 'จำนวนเงิน', 'เครดิต', 'วันที่แจ้งเติม', 'สถานะ']
        rows = [[f'RF{r.rf_id:05d}', r.member.mb_full_name, r.rf_money, r.rf_credit, r.rf_date, r.get_rf_status_display()] for r in queryset]
        summary_items = [('รายการเติมเครดิต', len(rows)), ('ยอดเงินรวม', sum(row[2] for row in rows)), ('เครดิตรวม', sum(row[3] for row in rows))]
    else:
        members = member_user_queryset()
        total_credit = members.aggregate(total=Sum('mb_deposit_crd') + Sum('mb_income_crd'))['total'] or 0
        average_rating = Review.objects.aggregate(avg=Avg('rv_satisfaction'))['avg'] or 0
        system = System.objects.first()
        headers = ['จำนวนสมาชิก', 'ผู้เรียน', 'ติวเตอร์', 'รายวิชา', 'การสมัครเรียน', 'รายได้ระบบ', 'เครดิตคงเหลือ', 'คะแนนรีวิวเฉลี่ย']
        rows = [[members.count(), members.exclude(tutor__isnull=False).count(), Tutor.objects.filter(tut_status=1).count(), Course.objects.count(), Booking.objects.count(), system.total_accumulated_fee if system else 0, total_credit, average_rating]]
        summary_items = list(zip(headers, rows[0]))

    total_rows = len(rows)
    report_context = {
        'report_type': report_type, 'report_title': report_titles[report_type],
        'headers': headers, 'rows': rows, 'total_rows': total_rows,
        'start_date': start_date, 'end_date': end_date, 'status': status, 'order': order, 'course_group': course_group,
        'summary_items': summary_items, 'generated_at': timezone.now(),
        'reporter_name': request.user.get_full_name() or request.user.username,
        'report_selected': True, 'filter_config': filter_config,
    }
    if request.GET.get('print') == '1':
        return render(request, 'admin_panel/report_pdf.html', report_context)

    return render(request, 'admin_panel/report_center.html', {
        'active_menu': 'dashboard', 'topbar_breadcrumb': 'ออกรายงาน',
        **report_context, 'rows': rows[:200],
    })


# ─── System Settings ─────────────────────────────────────────────────────────

@login_required
@user_passes_test(is_admin)
def system_settings(request):
    """หน้าตั้งค่าระบบ (System + Admin User)"""
    system    = System.objects.select_related('admin').first()
    admin_user = system.admin if system else None
    member_exists = member_user_queryset().exists()
    credit_value_locked = member_exists
    email_domain_locked = member_exists

    sys_form  = SystemForm(instance=system)
    user_form = AdminUserForm(instance=admin_user)
    if credit_value_locked:
        sys_form.fields['crd_val'].disabled = True
        sys_form.fields['crd_val'].help_text = 'มูลค่าเครดิตถูกล็อกแล้ว ไม่สามารถแก้ไขได้'
    if email_domain_locked:
        sys_form.fields['email_domain'].disabled = True
        sys_form.fields['email_domain'].help_text = 'โดเมนอีเมลถูกล็อกแล้ว หากจำเป็นต้องเปลี่ยนให้ใช้คำสั่งดูแลระบบ'

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'system':
            post_data = request.POST.copy()
            if credit_value_locked:
                post_data['crd_val'] = str(system.crd_val)

            if email_domain_locked:
                post_data['email_domain'] = system.email_domain

            sys_form = SystemForm(post_data, instance=system)
            if credit_value_locked:
                sys_form.fields['crd_val'].disabled = True
                sys_form.fields['crd_val'].help_text = 'มูลค่าเครดิตถูกล็อกแล้ว ไม่สามารถแก้ไขได้'
            if email_domain_locked:
                sys_form.fields['email_domain'].disabled = True
                sys_form.fields['email_domain'].help_text = 'โดเมนอีเมลถูกล็อกแล้ว หากจำเป็นต้องเปลี่ยนให้ใช้คำสั่งดูแลระบบ'
            if sys_form.is_valid():
                sys_form.save()
                messages.success(request, 'บันทึกข้อมูลระบบเรียบร้อยแล้ว')
                return redirect('admin_panel:system_settings')
            else:
                messages.error(request, 'ข้อมูลไม่ถูกต้อง กรุณาตรวจสอบอีกครั้ง')

        elif action == 'admin_user' and admin_user:
            user_form = AdminUserForm(request.POST, instance=admin_user)
            if user_form.is_valid():
                user_form.save()
                messages.success(request, 'บันทึกข้อมูลผู้ดูแลระบบเรียบร้อยแล้ว')
                return redirect('admin_panel:system_settings')
            else:
                messages.error(request, 'ข้อมูลไม่ถูกต้อง กรุณาตรวจสอบอีกครั้ง')

    return render(request, 'admin_panel/system_settings.html', {
        'system'            : system,
        'sys_form'          : sys_form,
        'user_form'         : user_form,
        'credit_value_locked': credit_value_locked,
        'email_domain_locked': email_domain_locked,
        'active_menu'       : 'system',
        'topbar_breadcrumb' : 'ตั้งค่าระบบ',
    })


# ─── Tutor Management — List ──────────────────────────────────────────────────

@login_required
@user_passes_test(is_admin)
def tutor_mgmt_list(request):
    qs = Tutor.objects.select_related(
        'tut_id', 'tut_id__mj_id', 'tut_id__mj_id__fac_id', 'tut_id__user'
    ).order_by('tut_id')

    q             = request.GET.get('q',      '').strip()
    status_filter = request.GET.get('status', '')

    if q:
        qs = qs.filter(
            Q(tut_id__mb_full_name__icontains=q) |
            Q(tut_id__mb_email__icontains=q)     |
            Q(tut_id__mj_id__fac_id__fac_name__icontains=q)
        )
    if status_filter == 'pending':
        qs = qs.filter(tut_status=0)
    elif status_filter == 'approved':
        qs = qs.filter(tut_status=1)

    paginator = Paginator(qs, 10)
    page      = paginator.get_page(request.GET.get('page', 1))

    all_tutors     = Tutor.objects.all()
    total          = all_tutors.count()
    pending_count  = all_tutors.filter(tut_status=0).count()
    approved_count = all_tutors.filter(tut_status=1).count()

    return render(request, 'admin_panel/tutor_mgmt_list.html', {
        'page_obj'      : page,
        'q'             : q,
        'status_filter' : status_filter,
        'total'         : total,
        'pending_count' : pending_count,
        'approved_count': approved_count,
        'active_menu'   : 'tutor_mgmt',
        'topbar_breadcrumb': 'การอนุมัติติวเตอร์',
    })


# ─── Tutor Management — Detail ───────────────────────────────────────────────

@login_required
@user_passes_test(is_admin)
def tutor_mgmt_detail(request, pk):
    tutor = get_object_or_404(
        Tutor.objects.select_related(
            'tut_id', 'tut_id__mj_id', 'tut_id__mj_id__fac_id', 'tut_id__user'
        ),
        pk=pk
    )

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'approve':
            tutor.tut_status = 1
            tutor.save()
            messages.success(request, f'อนุมัติติวเตอร์ {tutor.tut_id.mb_full_name} เรียบร้อยแล้ว')
            return redirect('admin_panel:tutor_mgmt_detail', pk=pk)
        elif action == 'reject':
            note = request.POST.get('reject_note', '').strip()
            tutor.tut_status      = 2
            tutor.tut_reject_note = note or None  # บันทึกลง DB โดยตรง
            tutor.save()
            messages.error(request, f'ปฏิเสธคำขอเป็นติวเตอร์ของ {tutor.tut_id.mb_full_name} เรียบร้อยแล้ว')
            return redirect('admin_panel:tutor_mgmt_detail', pk=pk)
        elif action == 'suspend':
            note = request.POST.get('reject_note', '').strip()
            tutor.tut_status      = 3
            tutor.tut_reject_note = note or None  # บันทึกเหตุผลการระงับ
            tutor.save()
            messages.error(request, f'ระงับการสอนของ {tutor.tut_id.mb_full_name} เรียบร้อยแล้ว')
            return redirect('admin_panel:tutor_mgmt_detail', pk=pk)
        elif action == 'unsuspend':
            tutor.tut_status = 1
            tutor.save(update_fields=['tut_status'])
            messages.success(request, f'ปลดระงับการสอนของ {tutor.tut_id.mb_full_name} เรียบร้อยแล้ว')
            return redirect('admin_panel:tutor_mgmt_detail', pk=pk)

    member   = tutor.tut_id
    year     = member.user.date_joined.year
    tutor_id = f"TR-{year}-{tutor.pk:04d}"
    skills   = [s.strip() for s in (tutor.tut_skill or '').split(',') if s.strip()]
    from apps.bookings.models import Booking
    report_history = (
        Booking.objects
        .filter(tutc_id__tut_id=tutor, bk_report_date__isnull=False)
        .select_related('member', 'tutc_id')
        .prefetch_related('report_statements', 'report_statements__member')
        .order_by('-bk_report_date')
    )

    return render(request, 'admin_panel/tutor_mgmt_detail.html', {
        'tutor'             : tutor,
        'member'            : member,
        'tutor_id'          : tutor_id,
        'skills'            : skills,
        'report_history'    : report_history,
        'faculty_name'      : member.mj_id.fac_id.fac_name if member.mj_id else '—',
        'major_name'        : member.mj_id.mj_name          if member.mj_id else '—',
        'active_menu'       : 'tutor_mgmt',
        'topbar_breadcrumb' : (
            f'<a href="{reverse("admin_panel:tutor_mgmt_list")}" style="color:var(--text-muted);text-decoration:none;">'
            f'การอนุมัติติวเตอร์</a>'
            f'<span style="color:#D1D5DB;margin:0 6px;">›</span>'
            f'<span style="color:var(--text-main);font-weight:500;">รายละเอียด</span>'
        ),
    })


# ─────────────────────────────────────────────
#  การเติมเครดิต (admin)
# ─────────────────────────────────────────────
@login_required
@user_passes_test(is_admin)
def refill_mgmt(request):
    """รายการคำขอเติมเครดิตทั้งหมด"""

    # handle approve / reject
    if request.method == 'POST':
        rf_id  = request.POST.get('rf_id')
        action = request.POST.get('action')
        note   = request.POST.get('note', '').strip()
        refill = get_object_or_404(Refill.objects.select_related('member'), pk=rf_id)

        if action == 'approve' and refill.rf_status == 0:
            refill.rf_status       = 1
            refill.rf_confirm_date = timezone.now()
            # preserve original bank/date info; append admin note as 3rd pipe-segment
            orig = (refill.rf_cmt or '').split('| หมายเหตุ:')[0].rstrip()
            refill.rf_cmt = (orig + f' | หมายเหตุ: {note}') if note else (orig or None)
            refill.save()
            # เพิ่มเครดิตให้ member
            member = refill.member
            member.mb_deposit_crd += refill.rf_credit
            member.save(update_fields=['mb_deposit_crd'])
            messages.success(request, f'อนุมัติการเติมเครดิต RF{refill.rf_id:05d} เรียบร้อย (+{refill.rf_credit} เครดิต)')

        elif action == 'reject' and refill.rf_status == 0:
            if not note:
                messages.error(request, 'กรุณาระบุเหตุผลที่ไม่อนุมัติรายการเติมเครดิต')
                return redirect('admin_panel:refill_mgmt')
            refill.rf_status       = 2
            refill.rf_confirm_date = timezone.now()
            orig = (refill.rf_cmt or '').split('| หมายเหตุ:')[0].rstrip()
            refill.rf_cmt = orig + f' | หมายเหตุ: {note}'
            refill.save()
            messages.error(request, f'ปฏิเสธการเติมเครดิต RF{refill.rf_id:05d} เรียบร้อย')

        return redirect('admin_panel:refill_mgmt')

    # ── filters ──
    status_filter = request.GET.get('status', '')
    date_filter   = request.GET.get('date',   '')

    qs = Refill.objects.select_related('member').order_by('-rf_date')
    if status_filter != '':
        qs = qs.filter(rf_status=status_filter)
    if date_filter:
        qs = qs.filter(rf_date__date=date_filter)

    # ── summary stats ──
    all_refills = Refill.objects.all()
    pending_count  = all_refills.filter(rf_status=0).count()
    approved_count = all_refills.filter(rf_status=1).count()
    total_money    = all_refills.filter(rf_status=1).aggregate(t=Sum('rf_money'))['t'] or 0

    paginator = Paginator(qs, 15)
    page      = paginator.get_page(request.GET.get('page', 1))

    # เตรียมธนาคารต้นทางและหมายเหตุสำหรับแสดงผล พร้อมรองรับข้อมูลเก่า
    for rf in page.object_list:
        rf.extracted_bank = rf.rf_bank_from or ''
        rf.transfer_datetime = ''
        rf.admin_note = ''
        if rf.rf_cmt:
            parts = rf.rf_cmt.split('|')
            if not rf.extracted_bank and rf.rf_cmt.startswith('โอนจาก:'):
                rf.extracted_bank = parts[0].replace('โอนจาก:', '').strip()
            for p in parts:
                p = p.strip()
                if p.startswith('วันที่:'):
                    rf.transfer_datetime = p.replace('วันที่:', '', 1).strip()
                if p.startswith('หมายเหตุ:'):
                    rf.admin_note = p.replace('หมายเหตุ:', '', 1).strip()
            if not rf.admin_note and not (
                rf.rf_cmt.startswith('โอนจาก:') or rf.rf_cmt.startswith('วันที่:')
            ):
                rf.admin_note = rf.rf_cmt

    return render(request, 'admin_panel/refill_mgmt.html', {
        'page'           : page,
        'pending_count'  : pending_count,
        'approved_count' : approved_count,
        'total_money'    : total_money,
        'status_filter'  : status_filter,
        'date_filter'    : date_filter,
        'active_menu'    : 'refill_mgmt',
        'topbar_breadcrumb': 'การเติมเครดิต',
    })



# ─────────────────────────────────────────────
#  จัดการสมาชิก (admin)
# ─────────────────────────────────────────────
@login_required
@user_passes_test(is_admin)
def member_mgmt(request):
    q             = request.GET.get("q", "").strip()
    fac_filter    = request.GET.get("fac", "")
    mj_filter     = request.GET.get("mj", "")
    status_filter = request.GET.get("status", "")

    qs = member_user_queryset().select_related("user", "mj_id", "mj_id__fac_id").order_by("-user__date_joined")

    if q:
        qs = qs.filter(
            Q(mb_full_name__icontains=q) |
            Q(mb_email__icontains=q)     |
            Q(mj_id__mj_name__icontains=q)
        )
    if fac_filter:
        qs = qs.filter(mj_id__fac_id=fac_filter)
    if mj_filter:
        qs = qs.filter(mj_id=mj_filter)
    if status_filter != "":
        qs = qs.filter(mb_status=status_filter)

    base_members = member_user_queryset()
    total_count  = base_members.count()
    active_count = base_members.filter(mb_status=1).count()
    tutor_count  = base_members.filter(tutor__tut_status=1).count()

    faculties = Faculty.objects.order_by("fac_name")
    majors    = Major.objects.select_related("fac_id").order_by("fac_id", "mj_name")

    paginator = Paginator(qs, 15)
    page      = paginator.get_page(request.GET.get("page", 1))

    return render(request, "admin_panel/member_mgmt.html", {
        "page"          : page,
        "q"             : q,
        "fac_filter"    : fac_filter,
        "mj_filter"     : mj_filter,
        "status_filter" : status_filter,
        "faculties"     : faculties,
        "majors"        : majors,
        "total_count"   : total_count,
        "active_count"  : active_count,
        "tutor_count"   : tutor_count,
        "active_menu"   : "member_mgmt",
        "topbar_breadcrumb": "จัดการสมาชิก",
    })


# ─────────────────────────────────────────────
#  การชำระเงิน / ถอนเครดิต (admin)
# ─────────────────────────────────────────────
@login_required
@user_passes_test(is_admin)
def payment_mgmt(request):
    """รายการคำขอถอนเครดิตทั้งหมด"""
    
    system = System.objects.first()

    if request.method == 'POST':
        wd_id  = request.POST.get('wd_id')
        action = request.POST.get('action')
        note   = request.POST.get('note', '').strip()
        wd = get_object_or_404(Withdrawals.objects.select_related('member'), pk=wd_id)

        if action == 'pay' and wd.wd_status == 0:
            wd.wd_status    = 1
            wd.wd_paid_date = timezone.now()
            wd.wd_cmt       = note or None
            wd.save()
            
            # หักเครดิตออกจากระบบถาวร (หักจาก locked และยอดหลัก)
            member = wd.member
            member.mb_locked_crd = max(0, member.mb_locked_crd - wd.wd_credit)
            if wd.wd_type == 1:
                member.mb_income_crd = max(0, member.mb_income_crd - wd.wd_credit)
            else:
                member.mb_deposit_crd = max(0, member.mb_deposit_crd - wd.wd_credit)
            member.save(update_fields=['mb_locked_crd', 'mb_income_crd', 'mb_deposit_crd'])

            # สะสมค่าธรรมเนียมเมื่อทำรายการสำเร็จ
            if system:
                system.total_accumulated_fee += wd.wd_fee
                system.save(update_fields=['total_accumulated_fee'])
                
            messages.success(request, f'บันทึกการจ่าย WD{wd.wd_id:05d} เรียบร้อยแล้ว (เครดิตถูกหักออกจากบัญชีแล้ว)')

        elif action == 'reject' and wd.wd_status == 0:
            wd.wd_status = 2
            wd.wd_cmt    = note or None
            wd.save()
            # คืนเครดิตที่ล็อกไว้ให้ member เมื่อปฏิเสธ (ลดเฉพาะ locked_crd)
            member = wd.member
            member.mb_locked_crd = max(0, member.mb_locked_crd - wd.wd_credit)
            member.save(update_fields=['mb_locked_crd'])
            messages.error(request, f'ปฏิเสธการถอน WD{wd.wd_id:05d} — เครดิตที่ล็อกไว้ถูกปลดล็อกคืนให้สมาชิกแล้ว')

        return redirect('admin_panel:payment_mgmt')

    status_filter = request.GET.get('status', '')
    qs = Withdrawals.objects.select_related('member').order_by('-wd_req_date')
    if status_filter != '':
        qs = qs.filter(wd_status=status_filter)

    all_wd         = Withdrawals.objects.all()
    
    # นับจำนวนรายการ
    pending_count  = all_wd.filter(wd_status=0).count()
    paid_count     = all_wd.filter(wd_status=1).count()
    rejected_count = all_wd.filter(wd_status=2).count()
    
    # ยอดจ่ายแล้วทั้งหมด
    paid_cash      = all_wd.filter(wd_status=1).aggregate(t=Sum('wd_net_cash'))['t'] or 0

    paginator = Paginator(qs, 15)
    page      = paginator.get_page(request.GET.get('page', 1))

    # สร้าง QR สำหรับรายการที่เป็นพร้อมเพย์
    for wd in page.object_list:
        wd.qr_code = None
        if hasattr(wd, 'wd_promptpay_no') and wd.wd_promptpay_no and wd.wd_promptpay_no != '-':
            try:
                wd.qr_code = _generate_promptpay_qr(wd.wd_promptpay_no, amount=float(wd.wd_net_cash))
            except Exception:
                pass

    return render(request, 'admin_panel/payment_mgmt.html', {
        'page'                  : page,
        'pending_count'         : pending_count,
        'paid_count'            : paid_count,
        'paid_cash'             : paid_cash,
        'rejected_count'        : rejected_count,
        'status_filter'         : status_filter,
        'accumulated_fee'       : system.total_accumulated_fee if system else 0,
        'active_menu'           : 'payment',
        'topbar_breadcrumb'     : 'การชำระเงิน',
    })


# ─────────────────────────────────────────────
#  รายงานปัญหา (admin)
# ─────────────────────────────────────────────
@login_required
@user_passes_test(is_admin)
def report_mgmt(request):
    """รายการรายงานปัญหาจากผู้เรียน"""
    from apps.bookings.models import Booking

    if request.method == 'POST':
        bk_id  = request.POST.get('bk_id')
        action = request.POST.get('action')
        bk = get_object_or_404(
            Booking.objects.select_related(
                'member', 'tutc_id', 'tutc_id__tut_id', 'tutc_id__tut_id__tut_id'
            ), pk=bk_id
        )

        if bk.bk_report_resolved_date:
            messages.warning(request, f'รายงาน BK{bk.bk_id:05d} ถูกจัดการแล้ว')
            return redirect('admin_panel:report_mgmt')

        if action == 'no_refund':
            note = request.POST.get('note', '').strip()
            if not note:
                messages.error(request, 'กรุณาระบุหมายเหตุผลการพิจารณาก่อนดำเนินการ')
                return redirect('admin_panel:report_mgmt')
            try:
                with transaction.atomic():
                    bk = Booking.objects.select_for_update().get(pk=bk_id)
                    if bk.bk_report_resolved_date:
                        messages.warning(request, f'รายงาน BK{bk.bk_id:05d} ถูกจัดการแล้ว')
                        return redirect('admin_panel:report_mgmt')
                    if bk.bk_status not in (1, 3):
                        messages.warning(
                            request,
                            'สถานะของรายการเปลี่ยนแปลงแล้ว ไม่สามารถบันทึกผลการพิจารณาได้',
                        )
                        return redirect('admin_panel:report_mgmt')

                    total_credit = bk.bk_rate_per_person * bk.bk_stu_count
                    student = Member.objects.select_for_update().get(pk=bk.member_id)
                    student.mb_locked_crd = max(0, student.mb_locked_crd - total_credit)
                    student.save(update_fields=['mb_locked_crd'])
                    tutor_member_id = bk.tutc_id.tut_id.tut_id_id
                    tutor_member = Member.objects.select_for_update().get(pk=tutor_member_id)
                    tutor_member.mb_income_crd += total_credit
                    tutor_member.save(update_fields=['mb_income_crd'])
                    from apps.bookings.models import JobCompletion
                    JobCompletion.objects.filter(bk_id=bk).update(jc_confirm_date=timezone.now())
                    bk.bk_status                = 4
                    admin_decision = f'[แอดมิน] พิจารณาไม่คืนเครดิต: {note}'
                    cancel_history = (bk.bk_cmt or '').strip()
                    bk.bk_cmt = (
                        f'{cancel_history}\n{admin_decision}'
                        if cancel_history.startswith('[ไม่อนุมัติการยกเลิก]')
                        else admin_decision
                    )
                    bk.bk_report_resolved_date  = timezone.now()
                    bk.save(update_fields=['bk_status', 'bk_cmt', 'bk_report_resolved_date'])
                    from apps.notifications.signals import _notif_member
                    _notif_member(student, 'booking_report_resolved',
                        f'ผลพิจารณารายงาน BK{bk.bk_id:05d}: ไม่คืนเครดิตแก่ผู้เรียน', '/bookings/my/?tab=reported')
                    _notif_member(tutor_member, 'booking_report_resolved',
                        f'ผลพิจารณารายงาน BK{bk.bk_id:05d}: เครดิต {total_credit} เครดิตโอนเข้าบัญชีของคุณแล้ว', '/bookings/tutor/?tab=reported')
                messages.success(request, f'บันทึกผลการพิจารณา BK{bk.bk_id:05d} แล้ว: ไม่คืนเครดิต')
            except Exception as e:
                messages.error(request, f'เกิดข้อผิดพลาด: {str(e)}')

        elif action == 'refund':
            note = request.POST.get('note', '').strip()
            if not note:
                messages.error(request, 'กรุณาระบุหมายเหตุผลการพิจารณาก่อนดำเนินการ')
                return redirect('admin_panel:report_mgmt')
            try:
                with transaction.atomic():
                    bk = Booking.objects.select_for_update().get(pk=bk_id)
                    if bk.bk_report_resolved_date:
                        messages.warning(request, f'รายงาน BK{bk.bk_id:05d} ถูกจัดการแล้ว')
                        return redirect('admin_panel:report_mgmt')
                    if bk.bk_status not in (1, 3):
                        messages.warning(
                            request,
                            'สถานะของรายการเปลี่ยนแปลงแล้ว ไม่สามารถบันทึกผลการพิจารณาได้',
                        )
                        return redirect('admin_panel:report_mgmt')

                    total_credit = bk.bk_rate_per_person * bk.bk_stu_count
                    # ปลดล็อกเครดิต โดยไม่เพิ่มยอดนำฝากซ้ำเพราะยอดต้นทางยังไม่ถูกหัก
                    student = Member.objects.select_for_update().get(pk=bk.member_id)
                    student.mb_locked_crd = max(0, student.mb_locked_crd - total_credit)
                    student.save(update_fields=['mb_locked_crd'])
                    tutor_member_id = bk.tutc_id.tut_id.tut_id_id
                    tutor_member = Member.objects.select_for_update().get(pk=tutor_member_id)
                    bk.bk_status                = 6
                    admin_decision = f'[แอดมิน] พิจารณาให้คืนเครดิต: {note}'
                    cancel_history = (bk.bk_cmt or '').strip()
                    bk.bk_cmt = (
                        f'{cancel_history}\n{admin_decision}'
                        if cancel_history.startswith('[ไม่อนุมัติการยกเลิก]')
                        else admin_decision
                    )
                    bk.bk_report_resolved_date  = timezone.now()
                    bk.save(update_fields=['bk_status', 'bk_cmt', 'bk_report_resolved_date'])
                    from apps.notifications.signals import _notif_member
                    _notif_member(student, 'booking_report_resolved',
                        f'ผลพิจารณารายงาน BK{bk.bk_id:05d}: คืนเครดิต {total_credit} เครดิตให้คุณแล้ว', '/bookings/my/?tab=reported')
                    _notif_member(tutor_member, 'booking_report_resolved',
                        f'ผลพิจารณารายงาน BK{bk.bk_id:05d}: คืนเครดิตให้ผู้เรียน', '/bookings/tutor/?tab=reported')
                messages.success(request, f'คืนเครดิต {total_credit} เครดิต และบันทึกผลการพิจารณา BK{bk.bk_id:05d} แล้ว')
            except Exception as e:
                messages.error(request, f'เกิดข้อผิดพลาด: {str(e)}')

        return redirect('admin_panel:report_mgmt')

    # ดึง booking ที่เคยรายงานปัญหา (มี bk_report_date) ทั้งรอพิจารณาและจัดการแล้ว
    qs = (
        Booking.objects
        .filter(bk_report_date__isnull=False)
        .select_related('member', 'tutc_id', 'tutc_id__tut_id__tut_id')
        .prefetch_related('tutoringactivity', 'report_statements', 'report_statements__member')
        .order_by('-bk_report_date')
    )

    all_count      = qs.count()
    waiting_count  = qs.filter(bk_report_resolved_date__isnull=True).count()
    resolved_count = qs.filter(bk_report_resolved_date__isnull=False).count()

    # filter สถานะ
    status_filter = request.GET.get('status', '')
    if status_filter == 'waiting':
        qs = qs.filter(bk_report_resolved_date__isnull=True)
    elif status_filter == 'resolved':
        qs = qs.filter(bk_report_resolved_date__isnull=False)

    raw_page = request.GET.get('page') or 1
    try:
        page_number = int(raw_page)
    except (TypeError, ValueError):
        page_number = 1
    if page_number < 1:
        page_number = 1

    paginator = Paginator(qs, 15)
    page      = paginator.get_page(page_number)

    # แยกเหตุผลการขอยกเลิกเพื่อแสดงเป็นประวัติประกอบการพิจารณา
    from apps.bookings.views import _parse_cancel_history
    for booking in page.object_list:
        booking.cancel_request_reason, booking.cancel_reject_reason = (
            _parse_cancel_history(booking.bk_cmt)
        )

    # Template เรียก previous_page_number/next_page_number แม้ปุ่ม disabled
    # จึงกันไม่ให้หน้าแรกสร้างเลข 0 หรือหน้าสุดท้ายสร้างเลขเกินจำนวนหน้า
    if not page.has_previous():
        page.previous_page_number = lambda: page.number
    if not page.has_next():
        page.next_page_number = lambda: page.number

    return render(request, 'admin_panel/report_mgmt.html', {
        'page'           : page,
        'all_count'      : all_count,
        'waiting_count'  : waiting_count,
        'resolved_count' : resolved_count,
        'status_filter'  : status_filter,
        'active_menu'    : 'report_mgmt',
        'topbar_breadcrumb': 'รายงานปัญหา',
    })
    
# ─── Admin Setup (ครั้งแรก) ──────────────────────────────────────────────────

def admin_setup(request):
    """หน้าลงทะเบียน admin ครั้งแรก — เข้าได้เฉพาะตอนยังไม่มี admin ในระบบ"""
    from django.contrib.auth import login as auth_login

    system = System.objects.first()

    # ถ้ามี admin แล้ว → เด้งไปหน้า home
    if system and system.admin is not None:
        return redirect('home')

    form = AdminUserForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            user = form.save(commit=False)
            user.is_staff     = True
            user.is_superuser = False
            user.save()

            # ถ้ายังไม่มี System → สร้างขึ้นมาก่อน
            if not system:
                system = System.objects.create(
                    admin                    = user,
                    uni_name                 = '',
                    email_domain             = 'rmuti.ac.th',
                    bank_name                = '',
                    acc_name                 = '',
                    acc_no                   = '',
                    crd_val                  = 0,
                    deposit_withdraw_fee_pct = 0,
                    income_withdraw_fee_pct  = 0,
                )
            else:
                system.admin = user
                system.save(update_fields=['admin'])

            # login อัตโนมัติหลังสร้าง admin สำเร็จ
            auth_login(request, user)
            messages.success(request, f'สร้างบัญชีผู้ดูแลระบบ "{user.username}" เรียบร้อยแล้ว')
            return redirect('admin_panel:system_settings')

    return render(request, 'admin_panel/admin_setup.html', {'form': form})
