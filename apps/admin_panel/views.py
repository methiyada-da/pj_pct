# admin_panel/views.py - views สำหรับผู้ดูแลระบบ
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.conf import settings
from django.contrib.staticfiles import finders
from django.core.paginator import Paginator
from django.db.models import (
    Avg, Case, Count, ExpressionWrapper, F, FloatField, IntegerField,
    Q, Sum, Value, When,
)
from django.db import transaction
from django.http import HttpResponse, HttpResponseForbidden
from django.template.loader import render_to_string
from django.urls import reverse

from django.utils import timezone
from django.utils.crypto import constant_time_compare
from django.utils.dateparse import parse_date

from decimal import Decimal, InvalidOperation
from pathlib import Path
import os
import shutil
import subprocess
import tempfile

from .models import System
from .forms  import SystemForm, AdminUserForm
from apps.accounts.models import Tutor, Member
from apps.credits.models  import Refill, Withdrawals
from apps.courses.models  import Faculty, Major
from apps.bookings.services import append_booking_closed_comment

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


def _find_chromium_browser():
    """ค้นหาเบราว์เซอร์ Chromium ที่ใช้สร้าง PDF บน Windows"""
    executable = shutil.which('msedge') or shutil.which('chrome')
    if executable:
        return executable

    candidates = (
        Path(os.environ.get('PROGRAMFILES(X86)', r'C:\Program Files (x86)'))
        / 'Microsoft/Edge/Application/msedge.exe',
        Path(os.environ.get('PROGRAMFILES', r'C:\Program Files'))
        / 'Microsoft/Edge/Application/msedge.exe',
        Path(os.environ.get('PROGRAMFILES', r'C:\Program Files'))
        / 'Google/Chrome/Application/chrome.exe',
        Path(os.environ.get('PROGRAMFILES(X86)', r'C:\Program Files (x86)'))
        / 'Google/Chrome/Application/chrome.exe',
    )
    return next((str(path) for path in candidates if path.is_file()), None)


def _html_to_pdf(html_string):
    """สร้าง PDF โดยใช้ Chromium บน Windows และใช้ WeasyPrint บนระบบอื่น"""
    if os.name != 'nt':
        from weasyprint import HTML

        return HTML(string=html_string).write_pdf()

    browser = _find_chromium_browser()
    if not browser:
        raise RuntimeError(
            'ไม่พบ Microsoft Edge หรือ Google Chrome สำหรับสร้างไฟล์ PDF'
        )

    # แยก user data ชั่วคราวเพื่อไม่ชนกับเบราว์เซอร์ที่ผู้ดูแลระบบเปิดอยู่
    with tempfile.TemporaryDirectory(prefix='pct-report-') as temp_dir:
        temp_path = Path(temp_dir)
        html_path = temp_path / 'report.html'
        pdf_path = temp_path / 'report.pdf'
        profile_path = temp_path / 'browser-profile'
        html_path.write_text(html_string, encoding='utf-8')

        command = [
            browser,
            '--headless=new',
            '--disable-gpu',
            '--no-pdf-header-footer',
            f'--user-data-dir={profile_path}',
            f'--print-to-pdf={pdf_path}',
            html_path.resolve().as_uri(),
        ]
        completed = subprocess.run(
            command,
            capture_output=True,
            timeout=60,
            check=False,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        )
        if completed.returncode != 0 or not pdf_path.is_file():
            error_message = completed.stderr.decode('utf-8', errors='replace').strip()
            raise RuntimeError(
                f'ไม่สามารถสร้างไฟล์ PDF ได้: {error_message or "เบราว์เซอร์ไม่สร้างไฟล์ผลลัพธ์"}'
            )
        return pdf_path.read_bytes()


# ─── Dashboard ───────────────────────────────────────────────────────────────

@login_required
@user_passes_test(is_admin)
def dashboard(request):
    from apps.courses.models import Faculty, Major, CourseGroup, Course
    from apps.bookings.models import Booking, JobCompletion, Review
    import json
    from datetime import datetime, date, time, timedelta
    successful_booking_statuses = [4, 5]

    # ── Summary stats ──
    member_users = member_user_queryset()
    total_members   = member_users.count()
    active_members  = member_users.filter(mb_status=1).count()
    total_tutors    = Tutor.objects.filter(tut_id__user__is_staff=False, tut_id__user__is_superuser=False, tut_status=1).count()
    pending_tutors  = Tutor.objects.filter(tut_id__user__is_staff=False, tut_id__user__is_superuser=False, tut_status=0).count()

    pending_refills   = Refill.objects.filter(rf_status=0).count()
    pending_withdraw  = Withdrawals.objects.filter(wd_status=0).count()
    pending_reports   = Booking.objects.filter(
        bk_status__in=successful_booking_statuses,
        bk_report_date__isnull=False,
        bk_report_resolved_date__isnull=True,
    ).count()

    total_faculties   = Faculty.objects.count()
    total_majors      = Major.objects.count()
    total_courses     = Course.objects.count()
    total_bookings    = Booking.objects.filter(bk_status__in=successful_booking_statuses).count()
    active_bookings   = Booking.objects.filter(bk_status__in=[0, 1, 2, 3]).count()
    completed_bookings = Booking.objects.filter(bk_status__in=[4, 5]).count()
    pending_completions = JobCompletion.objects.filter(jc_confirm_date__isnull=True).count()
    completed_reviews = Review.objects.filter(
        bk_id__bk_status__in=successful_booking_statuses,
    )
    review_averages = completed_reviews.aggregate(
        quality=Avg('rv_quality'),
        knowledge=Avg('rv_knowledge'),
        communication=Avg('rv_communication'),
        punctuality=Avg('rv_punctuality'),
        satisfaction=Avg('rv_satisfaction'),
    )
    available_review_averages = [
        float(value) for value in review_averages.values() if value is not None
    ]
    average_review = (
        sum(available_review_averages) / len(available_review_averages)
        if available_review_averages else 0
    )
    
    # System revenue (fees)
    system = System.objects.first()
    total_fees = system.total_accumulated_fee if system else 0

    # ── กราฟแนวโน้ม ──
    from collections import defaultdict

    today = timezone.localdate()
    chart_metric = request.GET.get('chart_metric', 'members')
    chart_range = request.GET.get('chart_range', '6m')
    metric_config = {
        'members': {
            'label': 'สมาชิกใหม่',
            'unit': 'คน',
            'type': 'line',
            'border_color': '#2563EB',
            'background_color': 'rgba(37, 99, 235, 0.12)',
        },
        'bookings': {
            'label': 'การจองเรียน',
            'unit': 'รายการ',
            'type': 'line',
            'border_color': '#0F9F8F',
            'background_color': 'rgba(15, 159, 143, 0.12)',
        },
        'topups': {
            'label': 'ยอดเติมเครดิต',
            'unit': 'บาท',
            'type': 'bar',
            'border_color': '#D97706',
            'background_color': 'rgba(245, 158, 11, 0.55)',
        },
        'reviews': {
            'label': 'รีวิวที่ได้รับ',
            'unit': 'รีวิว',
            'type': 'line',
            'border_color': '#7C3AED',
            'background_color': 'rgba(124, 58, 237, 0.12)',
        },
    }
    if chart_metric not in metric_config:
        chart_metric = 'members'
    if chart_range not in {'7d', '30d', '6m', 'year'}:
        chart_range = '6m'
    metric_options = metric_config[chart_metric]

    def shift_month(source_date, month_offset):
        # เลื่อนเดือนโดยไม่พึ่งแพ็กเกจภายนอก
        month_index = source_date.year * 12 + source_date.month - 1 + month_offset
        return date(month_index // 12, month_index % 12 + 1, 1)

    month_labels = [
        '', 'ม.ค.', 'ก.พ.', 'มี.ค.', 'เม.ย.', 'พ.ค.', 'มิ.ย.',
        'ก.ค.', 'ส.ค.', 'ก.ย.', 'ต.ค.', 'พ.ย.', 'ธ.ค.',
    ]
    chart_keys = []
    if chart_range in {'7d', '30d'}:
        day_count = 7 if chart_range == '7d' else 30
        first_period = today - timedelta(days=day_count - 1)
        period_end = today + timedelta(days=1)
        chart_keys = [first_period + timedelta(days=offset) for offset in range(day_count)]
        chart_labels = [item.strftime('%d/%m') for item in chart_keys]
        chart_range_label = f'{day_count} วันล่าสุด'
        group_by_day = True
    else:
        if chart_range == 'year':
            first_period = date(today.year, 1, 1)
            month_count = today.month
            chart_range_label = f'ปี {today.year + 543}'
        else:
            first_period = shift_month(today, -5)
            month_count = 6
            chart_range_label = '6 เดือนล่าสุด'
        month_starts = [shift_month(first_period, offset) for offset in range(month_count)]
        chart_keys = [(item.year, item.month) for item in month_starts]
        chart_labels = [f'{month_labels[item.month]} {str(item.year + 543)[-2:]}' for item in month_starts]
        period_end = shift_month(month_starts[-1], 1)
        group_by_day = False

    current_timezone = timezone.get_current_timezone()
    start_datetime = timezone.make_aware(
        datetime.combine(first_period, time.min), current_timezone
    )
    end_datetime = timezone.make_aware(
        datetime.combine(period_end, time.min), current_timezone
    )

    # ดึงข้อมูลทั้งช่วงเพียงครั้งเดียว แล้วจัดกลุ่มใน Python เพื่อเลี่ยง CONVERT_TZ ของ MySQL
    if chart_metric == 'members':
        chart_rows = member_user_queryset().filter(
            user__date_joined__gte=start_datetime,
            user__date_joined__lt=end_datetime,
        ).values_list('user__date_joined', flat=True)
    elif chart_metric == 'bookings':
        chart_rows = Booking.objects.filter(
            bk_status__in=successful_booking_statuses,
            bk_date__gte=start_datetime,
            bk_date__lt=end_datetime,
        ).values_list('bk_date', flat=True)
    elif chart_metric == 'reviews':
        chart_rows = Review.objects.filter(
            bk_id__bk_status__in=successful_booking_statuses,
            rv_date__gte=start_datetime,
            rv_date__lt=end_datetime,
        ).values_list('rv_date', flat=True)
    else:
        chart_rows = Refill.objects.filter(
            rf_status=1,
            rf_date__gte=start_datetime,
            rf_date__lt=end_datetime,
        ).values_list('rf_date', 'rf_money')

    grouped_values = defaultdict(float)
    for row in chart_rows:
        occurred_at, amount = row if chart_metric == 'topups' else (row, 1)
        local_occurred_at = timezone.localtime(occurred_at)
        key = (
            local_occurred_at.date()
            if group_by_day
            else (local_occurred_at.year, local_occurred_at.month)
        )
        grouped_values[key] += float(amount)

    chart_data = [grouped_values[key] for key in chart_keys]
    if chart_metric != 'topups':
        chart_data = [int(value) for value in chart_data]
    chart_total = sum(chart_data)
    chart_total_display = (
        f'฿{chart_total:,.2f}'
        if chart_metric == 'topups'
        else f'{int(chart_total):,} {metric_options["unit"]}'
    )
    chart_has_data = any(value > 0 for value in chart_data)

    # ── Top course groups by course count ──
    top_groups = (CourseGroup.objects
                  .annotate(crs_count=Count('course'))
                  .order_by('-crs_count')[:5])
    max_crs = top_groups[0].crs_count if top_groups else 1

    # ── Recent activity ──
    recent_members  = member_users.select_related('user').order_by('-user__date_joined')[:5]
    recent_refills  = Refill.objects.filter(
        rf_status=1,
    ).select_related('member').order_by('-rf_date')[:5]
    recent_bookings = (Booking.objects
                       .filter(bk_status__in=successful_booking_statuses)
                       .select_related('member', 'tutc_id__tut_id__tut_id')
                       .order_by('-bk_date')[:5])
    recent_completions = (JobCompletion.objects
                          .filter(bk_id__bk_status__in=successful_booking_statuses)
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
        'chart_metric_label': metric_options['label'],
        'chart_range_label': chart_range_label,
        'chart_unit'        : metric_options['unit'],
        'chart_type'        : metric_options['type'],
        'chart_border_color': metric_options['border_color'],
        'chart_background_color': metric_options['background_color'],
        'chart_total_display': chart_total_display,
        'chart_has_data'    : chart_has_data,
        # top groups
        'top_groups'        : top_groups,
        'max_crs'           : max_crs,
        # recent activity
        'recent_members'    : recent_members,
        'recent_refills'    : recent_refills,
        'recent_bookings'   : recent_bookings,
        'recent_completions': recent_completions,
    })


# ─── ศูนย์ออกรายงาน ───────────────────────────────────────────────────────

REPORT_TITLES = {
    'members': 'รายงานสมาชิก',
    'tutors': 'รายงานติวเตอร์',
    'courses': 'รายงานรายวิชา',
    'bookings': 'รายงานการจองเรียน',
    'refills': 'รายงานการเติมเครดิต',
    'withdrawals': 'รายงานการถอนเครดิต',
    'reviews': 'รายงานการรีวิว',
}

REPORT_FILE_NAMES = {
    'members': 'member-report.pdf',
    'tutors': 'tutor-report.pdf',
    'courses': 'course-report.pdf',
    'bookings': 'booking-report.pdf',
    'refills': 'refill-report.pdf',
    'withdrawals': 'withdrawal-report.pdf',
    'reviews': 'review-report.pdf',
}


def _select_filter(name, label, value, options):
    normalized_options = []
    for option in options:
        option_value, option_label, *metadata = option
        normalized_options.append(
            (str(option_value), option_label, *metadata)
        )
    return {
        'type': 'select', 'name': name, 'label': label, 'value': value,
        'options': normalized_options,
    }


def _input_filter(name, label, value, input_type='date', **attrs):
    options = attrs.pop('options', [])
    return {
        'type': input_type, 'name': name, 'label': label, 'value': value,
        'options': options,
        **attrs,
    }


def _safe_choice(raw_value, valid_values, errors, label):
    if raw_value in {'', 'all', None}:
        return ''
    if raw_value not in valid_values:
        errors.append(f'ค่า{label}ไม่ถูกต้อง ระบบจึงไม่ใช้เงื่อนไขนี้')
        return ''
    return raw_value


def _safe_decimal(raw_value, errors, label):
    if not raw_value:
        return None
    try:
        return Decimal(raw_value)
    except (InvalidOperation, TypeError):
        errors.append(f'ค่า{label}ไม่ถูกต้อง ระบบจึงไม่ใช้เงื่อนไขนี้')
        return None


def _apply_date_range(queryset, field_name, start_raw, end_raw, errors, label):
    # ใช้ช่วงวันเวลาโดยตรงเพื่อไม่พึ่งตารางเขตเวลาของฐานข้อมูล MySQL
    from datetime import datetime, time

    try:
        start = parse_date(start_raw) if start_raw else None
    except ValueError:
        start = None
    try:
        end = parse_date(end_raw) if end_raw else None
    except ValueError:
        end = None
    if (start_raw and not start) or (end_raw and not end):
        errors.append(f'ช่วง{label}ไม่ถูกต้อง')
        return queryset.none()
    if start and end and start > end:
        errors.append(f'{label}เริ่มต้นต้องไม่มากกว่าวันสิ้นสุด')
        return queryset.none()
    timezone_info = timezone.get_current_timezone()
    if start:
        start_datetime = timezone.make_aware(datetime.combine(start, time.min), timezone_info)
        queryset = queryset.filter(**{f'{field_name}__gte': start_datetime})
    if end:
        end_datetime = timezone.make_aware(datetime.combine(end, time.max), timezone_info)
        queryset = queryset.filter(**{f'{field_name}__lte': end_datetime})
    return queryset


def _format_datetime(value):
    if not value:
        return '—'
    if timezone.is_aware(value):
        value = timezone.localtime(value)
    return value.strftime('%d/%m/%Y %H:%M')


def _format_date(value):
    return value.strftime('%d/%m/%Y') if value else '—'


def _format_number(value, decimals=0):
    if value is None:
        value = 0
    return f'{value:,.{decimals}f}'


def _group_report_rows(rows, group_indexes):
    """สร้าง rowspan เฉพาะค่าที่เรียงติดกัน และรองรับกลุ่มซ้อนหลายระดับ"""
    prepared = [{'cells': [{'value': value, 'rowspan': 1} for value in row]} for row in rows]
    for level, column_index in enumerate(group_indexes):
        row_index = 0
        while row_index < len(rows):
            signature = tuple(rows[row_index][index] for index in group_indexes[:level + 1])
            end_index = row_index + 1
            while end_index < len(rows):
                next_signature = tuple(rows[end_index][index] for index in group_indexes[:level + 1])
                if next_signature != signature:
                    break
                end_index += 1
            prepared[row_index]['cells'][column_index]['rowspan'] = end_index - row_index
            for hidden_index in range(row_index + 1, end_index):
                prepared[hidden_index]['cells'][column_index]['rowspan'] = 0
            row_index = end_index
    return prepared


def _selected_filter_summary(filter_fields):
    summary = []
    for field in filter_fields:
        value = field.get('value')
        if not value:
            continue
        display_value = value
        if field['type'] == 'select':
            display_value = next(
                (
                    option[1]
                    for option in field['options']
                    if option[0] == str(value)
                ),
                value,
            )
        summary.append((field['label'], display_value))
    return summary or [('เงื่อนไข', 'ทั้งหมด')]


@login_required
@user_passes_test(is_admin)
def report_center(request):
    """แสดงตัวอย่างและส่งออก PDF จากชุดข้อมูลและตัวกรองเดียวกัน"""
    from apps.bookings.models import Booking, BookingReportStatement, Review
    from apps.courses.models import Course, CourseGroup

    report_type = request.GET.get('report_type', '')
    if not report_type:
        return render(request, 'admin_panel/report_center.html', {
            'active_menu': 'dashboard',
            'topbar_breadcrumb': 'ออกรายงาน',
            'report_selected': False,
        })
    if report_type not in REPORT_TITLES:
        report_type = 'members'

    errors = []
    filters = {key: value.strip() for key, value in request.GET.items()}
    filter_fields = []
    headers = []
    group_indexes = ()
    summary_items = []

    faculties = Faculty.objects.order_by('fac_name')
    majors = Major.objects.select_related('fac_id').order_by('fac_id__fac_name', 'mj_name')
    major_options = [
        (item.pk, item.mj_name, item.fac_id_id)
        for item in majors
    ]
    courses = Course.objects.order_by('crs_id')
    course_options = [
        (item.pk, f'{item.pk} — {item.crs_name}', item.cg_id_id)
        for item in courses
    ]
    tutors = Tutor.objects.select_related('tut_id').order_by('tut_id__mb_full_name')
    members = member_user_queryset().order_by('mb_full_name')

    if report_type == 'members':
        faculty = filters.get('faculty', '')
        major = filters.get('major', '')
        status = _safe_choice(filters.get('status', ''), {'0', '1', '2'}, errors, 'สถานะสมาชิก')
        user_type = _safe_choice(
            filters.get('user_type', ''),
            {'tutor'},
            errors,
            'ประเภทผู้ใช้งาน',
        )
        queryset = member_user_queryset().select_related('mj_id__fac_id', 'tutor')
        if faculty.isdigit():
            queryset = queryset.filter(mj_id__fac_id_id=int(faculty))
        elif faculty:
            errors.append('ค่าคณะไม่ถูกต้อง ระบบจึงไม่ใช้เงื่อนไขนี้')
        if major.isdigit():
            queryset = queryset.filter(mj_id_id=int(major))
        elif major:
            errors.append('ค่าสาขาไม่ถูกต้อง ระบบจึงไม่ใช้เงื่อนไขนี้')
        if status:
            queryset = queryset.filter(mb_status=int(status))
        if user_type == 'tutor':
            queryset = queryset.filter(tutor__isnull=False)
        queryset = queryset.order_by('mj_id__fac_id__fac_name', 'mj_id__mj_name', 'mb_full_name', 'pk')
        totals = queryset.aggregate(
            total=Count('pk', distinct=True),
            active=Count('pk', filter=Q(mb_status=1), distinct=True),
            suspended=Count('pk', filter=Q(mb_status=2), distinct=True),
            disabled=Count('pk', filter=Q(mb_status=0), distinct=True),
        )
        headers = ['คณะ', 'สาขา', 'รหัสสมาชิก', 'ชื่อ-นามสกุล', 'ประเภทผู้ใช้งาน', 'สถานะสมาชิก']
        group_indexes = (0, 1)
        row_builder = lambda member: [
            member.mj_id.fac_id.fac_name if member.mj_id else 'ไม่ระบุคณะ',
            member.mj_id.mj_name if member.mj_id else 'ไม่ระบุสาขา',
            f'M{member.pk:03d}', member.mb_full_name,
            'ติวเตอร์' if hasattr(member, 'tutor') else '—',
            member.get_mb_status_display(),
        ]
        summary_items = [
            ('สมาชิกทั้งหมด', totals['total']), ('ใช้งานปกติ', totals['active']),
            ('ระงับชั่วคราว', totals['suspended']), ('ปิดการใช้งาน', totals['disabled']),
        ]
        filter_fields = [
            _select_filter('faculty', 'คณะ', faculty, [(item.pk, item.fac_name) for item in faculties]),
            _select_filter('major', 'สาขา', major, major_options),
            _select_filter(
                'user_type',
                'ประเภทผู้ใช้งาน',
                user_type,
                [('tutor', 'ติวเตอร์')],
            ),
            _select_filter('status', 'สถานะสมาชิก', status, Member.STATUS_CHOICES),
        ]

    elif report_type == 'tutors':
        faculty = filters.get('faculty', '')
        major = filters.get('major', '')
        status = _safe_choice(filters.get('status', ''), {'0', '1', '2', '3'}, errors, 'สถานะติวเตอร์')
        rating_min_raw = filters.get('rating_min', '')
        rating_max_raw = filters.get('rating_max', '')
        rating_min = _safe_decimal(rating_min_raw, errors, 'คะแนนต่ำสุด')
        rating_max = _safe_decimal(rating_max_raw, errors, 'คะแนนสูงสุด')
        queryset = Tutor.objects.select_related('tut_id__user', 'tut_id__mj_id__fac_id').filter(
            tut_id__user__is_staff=False,
            tut_id__user__is_superuser=False,
        )
        if faculty.isdigit():
            queryset = queryset.filter(tut_id__mj_id__fac_id_id=int(faculty))
        elif faculty:
            errors.append('ค่าคณะไม่ถูกต้อง ระบบจึงไม่ใช้เงื่อนไขนี้')
        if major.isdigit():
            queryset = queryset.filter(tut_id__mj_id_id=int(major))
        elif major:
            errors.append('ค่าสาขาไม่ถูกต้อง ระบบจึงไม่ใช้เงื่อนไขนี้')
        if status:
            queryset = queryset.filter(tut_status=int(status))
        if rating_min is not None:
            queryset = queryset.filter(tut_rating__gte=rating_min)
        if rating_max is not None:
            queryset = queryset.filter(tut_rating__lte=rating_max)
        if rating_min is not None and rating_max is not None and rating_min > rating_max:
            errors.append('คะแนนต่ำสุดต้องไม่มากกว่าคะแนนสูงสุด')
            queryset = queryset.none()
        queryset = queryset.order_by(
            'tut_id__mj_id__fac_id__fac_name', 'tut_id__mj_id__mj_name',
            'tut_id__mb_full_name', 'pk',
        )
        totals = queryset.aggregate(
            total=Count('pk', distinct=True), pending=Count('pk', filter=Q(tut_status=0), distinct=True),
            approved=Count('pk', filter=Q(tut_status=1), distinct=True),
            rejected=Count('pk', filter=Q(tut_status=2), distinct=True),
            suspended=Count('pk', filter=Q(tut_status=3), distinct=True),
            average=Avg('tut_rating'),
        )
        headers = ['คณะ', 'สาขา', 'รหัสติวเตอร์', 'ชื่อ-นามสกุล', 'ความถนัด', 'คะแนนรีวิวเฉลี่ย', 'สถานะ']
        group_indexes = (0, 1)
        row_builder = lambda tutor: [
            tutor.tut_id.mj_id.fac_id.fac_name if tutor.tut_id.mj_id else 'ไม่ระบุคณะ',
            tutor.tut_id.mj_id.mj_name if tutor.tut_id.mj_id else 'ไม่ระบุสาขา',
            f'TR-{tutor.tut_id.user.date_joined.year}-{tutor.pk:04d}',
            tutor.tut_id.mb_full_name, tutor.tut_skill or '—',
            _format_number(tutor.tut_rating, 2), tutor.get_tut_status_display(),
        ]
        summary_items = [
            ('ติวเตอร์ทั้งหมด', totals['total']), ('รอตรวจสอบ', totals['pending']),
            ('อนุมัติแล้ว', totals['approved']), ('ปฏิเสธ', totals['rejected']),
            ('ระงับการสอน', totals['suspended']),
            ('คะแนนรีวิวเฉลี่ย', _format_number(totals['average'], 2)),
        ]
        filter_fields = [
            _select_filter('faculty', 'คณะ', faculty, [(item.pk, item.fac_name) for item in faculties]),
            _select_filter('major', 'สาขา', major, major_options),
            _select_filter('status', 'สถานะติวเตอร์', status, Tutor.STATUS_CHOICES),
            _input_filter('rating_min', 'คะแนนรีวิวต่ำสุด', rating_min_raw, 'number', step='0.01', min='0', max='5'),
            _input_filter('rating_max', 'คะแนนรีวิวสูงสุด', rating_max_raw, 'number', step='0.01', min='0', max='5'),
        ]

    elif report_type == 'courses':
        course_group = filters.get('course_group', '')
        course = filters.get('course', '')
        has_tutor = _safe_choice(filters.get('has_tutor', ''), {'yes', 'no'}, errors, 'การเปิดสอน')
        queryset = Course.objects.select_related('cg_id').annotate(
            tutor_count=Count(
                'tutorcourse__tut_id',
                filter=Q(tutorcourse__tutc_status=1, tutorcourse__tut_id__tut_status=1),
                distinct=True,
            ),
        )
        if course_group.isdigit():
            queryset = queryset.filter(cg_id_id=int(course_group))
        elif course_group:
            errors.append('ค่ากลุ่มรายวิชาไม่ถูกต้อง ระบบจึงไม่ใช้เงื่อนไขนี้')
        if course:
            queryset = queryset.filter(crs_id=course)
        if has_tutor == 'yes':
            queryset = queryset.filter(tutor_count__gt=0)
        elif has_tutor == 'no':
            queryset = queryset.filter(tutor_count=0)
        queryset = queryset.order_by('cg_id__cg_name', 'crs_id')
        total_courses = queryset.count()
        headers = ['กลุ่มรายวิชา', 'รหัสรายวิชา', 'ชื่อรายวิชา', 'ติวเตอร์ที่เปิดสอน']
        group_indexes = (0,)
        row_builder = lambda item: [item.cg_id.cg_name, item.crs_id, item.crs_name, item.tutor_count]
        summary_items = [
            ('จำนวนกลุ่มรายวิชา', queryset.values('cg_id_id').distinct().count()),
            ('จำนวนรายวิชา', total_courses),
            ('มีติวเตอร์เปิดสอน', queryset.filter(tutor_count__gt=0).count()),
            ('ยังไม่มีติวเตอร์เปิดสอน', queryset.filter(tutor_count=0).count()),
        ]
        filter_fields = [
            _select_filter('course_group', 'กลุ่มรายวิชา', course_group, [
                (item.pk, item.cg_name) for item in CourseGroup.objects.order_by('cg_name')
            ]),
            _select_filter('course', 'รายวิชา', course, course_options),
            _select_filter('has_tutor', 'การเปิดสอน', has_tutor, [('yes', 'มีติวเตอร์เปิดสอน'), ('no', 'ไม่มีติวเตอร์เปิดสอน')]),
        ]

    elif report_type == 'bookings':
        date_from = filters.get('date_from', '')
        date_to = filters.get('date_to', '')
        course = filters.get('course', '')
        tutor = filters.get('tutor', '')
        queryset = Booking.objects.select_related(
            'member', 'tutc_id__crs_id', 'tutc_id__tut_id__tut_id', 'ts_id__sd_id',
        ).filter(bk_status=5)
        queryset = _apply_date_range(queryset, 'bk_date', date_from, date_to, errors, 'วันที่จอง')
        if course:
            queryset = queryset.filter(tutc_id__crs_id_id=course)
        if tutor:
            queryset = queryset.filter(
                tutc_id__tut_id__tut_id__mb_full_name__icontains=tutor,
            )
        queryset = queryset.order_by('-bk_date', '-bk_id')
        booking_value = ExpressionWrapper(
            F('bk_rate_per_person') * F('bk_stu_count'), output_field=IntegerField(),
        )
        totals = queryset.aggregate(
            total=Count('bk_id', distinct=True),
            total_value=Sum(booking_value),
        )
        headers = ['วันที่จอง', 'เลขที่การจอง', 'ผู้เรียน', 'รายวิชา', 'ติวเตอร์', 'ค่าติว', 'สถานะ']
        group_indexes = (0,)
        def row_builder(booking):
            booking_date = (
                timezone.localtime(booking.bk_date).date()
                if booking.bk_date else None
            )
            return [
                _format_date(booking_date), f'BK{booking.bk_id:05d}',
                booking.member.mb_full_name, booking.tutc_id.crs_id.crs_name,
                booking.tutc_id.tut_id.tut_id.mb_full_name,
                f'{booking.total_credit:,} เครดิต', booking.get_bk_status_display(),
            ]
        summary_items = [
            ('การจองทั้งหมด', totals['total']),
            ('มูลค่าการจองรวม', f'{_format_number(totals["total_value"])} เครดิต'),
        ]
        filter_fields = [
            _input_filter('date_from', 'วันที่จองเริ่มต้น', date_from),
            _input_filter('date_to', 'วันที่จองสิ้นสุด', date_to),
            _select_filter('course', 'รายวิชา', course, [(item.pk, f'{item.pk} — {item.crs_name}') for item in courses]),
            _input_filter(
                'tutor',
                'ค้นหาติวเตอร์',
                tutor,
                'search',
                options=[item.tut_id.mb_full_name for item in tutors],
            ),
        ]

    elif report_type == 'refills':
        date_from = filters.get('date_from', '')
        date_to = filters.get('date_to', '')
        member = filters.get('member', '')
        queryset = Refill.objects.filter(
            rf_status=1,
        ).select_related('member')
        queryset = _apply_date_range(queryset, 'rf_date', date_from, date_to, errors, 'วันที่แจ้งเติม')
        if member.isdigit():
            queryset = queryset.filter(member_id=int(member))
        elif member:
            queryset = queryset.filter(member__mb_full_name__icontains=member)
        queryset = queryset.order_by('-rf_date', '-rf_id')
        totals = queryset.aggregate(
            total=Count('rf_id', distinct=True),
            money=Sum('rf_money'),
            credits=Sum('rf_credit'),
        )
        headers = ['เลขที่รายการ', 'วันที่', 'สมาชิก', 'จำนวนเงิน', 'จำนวนเครดิต', 'สถานะ']
        row_builder = lambda refill: [
            f'RF{refill.rf_id:05d}', _format_datetime(refill.rf_date), refill.member.mb_full_name,
            f'{_format_number(refill.rf_money, 2)} บาท', f'{refill.rf_credit:,} เครดิต', refill.get_rf_status_display(),
        ]
        summary_items = [
            ('รายการเติมที่สำเร็จ', totals['total']),
            ('จำนวนเงินที่สำเร็จ', f'{_format_number(totals["money"], 2)} บาท'),
            ('เครดิตที่เติมสำเร็จ', f'{_format_number(totals["credits"])} เครดิต'),
        ]
        filter_fields = [
            _input_filter('date_from', 'วันที่แจ้งเติมเริ่มต้น', date_from),
            _input_filter('date_to', 'วันที่แจ้งเติมสิ้นสุด', date_to),
            _input_filter(
                'member',
                'ค้นหาสมาชิก',
                member,
                'search',
                options=[item.mb_full_name for item in members],
            ),
        ]

    elif report_type == 'withdrawals':
        date_from = filters.get('date_from', '')
        date_to = filters.get('date_to', '')
        withdrawal_type = _safe_choice(filters.get('withdrawal_type', ''), {str(value) for value, _ in Withdrawals.TYPE_CHOICES}, errors, 'ประเภทเครดิต')
        member = filters.get('member', '')
        queryset = Withdrawals.objects.filter(
            wd_status=1,
        ).select_related('member')
        queryset = _apply_date_range(queryset, 'wd_req_date', date_from, date_to, errors, 'วันที่ขอถอน')
        if withdrawal_type:
            queryset = queryset.filter(wd_type=int(withdrawal_type))
        if member.isdigit():
            queryset = queryset.filter(member_id=int(member))
        elif member:
            queryset = queryset.filter(member__mb_full_name__icontains=member)
        queryset = queryset.order_by('wd_type', '-wd_req_date', '-wd_id')
        totals = queryset.aggregate(
            total=Count('wd_id', distinct=True),
            credits=Sum('wd_credit'),
            net_cash=Sum('wd_net_cash'),
        )
        headers = ['ประเภทเครดิต', 'เลขที่รายการ', 'วันที่ขอถอน', 'สมาชิก', 'จำนวนเครดิต', 'ยอดสุทธิ', 'สถานะ']
        group_indexes = (0,)
        row_builder = lambda withdrawal: [
            'เครดิตนำฝาก' if withdrawal.wd_type == 0 else 'เครดิตรายได้',
            f'WD{withdrawal.wd_id:05d}',
            _format_datetime(withdrawal.wd_req_date), withdrawal.member.mb_full_name,
            f'{withdrawal.wd_credit:,} เครดิต', f'{_format_number(withdrawal.wd_net_cash, 2)} บาท',
            withdrawal.get_wd_status_display(),
        ]
        summary_items = [
            ('รายการถอนที่สำเร็จ', totals['total']),
            ('เครดิตที่จ่ายสำเร็จ', f'{_format_number(totals["credits"])} เครดิต'),
            ('ยอดสุทธิที่จ่ายจริง', f'{_format_number(totals["net_cash"], 2)} บาท'),
        ]
        filter_fields = [
            _input_filter('date_from', 'วันที่ขอถอนเริ่มต้น', date_from),
            _input_filter('date_to', 'วันที่ขอถอนสิ้นสุด', date_to),
            _select_filter('withdrawal_type', 'ประเภทเครดิต', withdrawal_type, Withdrawals.TYPE_CHOICES),
            _input_filter(
                'member',
                'ค้นหาสมาชิก',
                member,
                'search',
                options=[item.mb_full_name for item in members],
            ),
        ]

    elif report_type == 'reviews':
        date_from = filters.get('date_from', '')
        date_to = filters.get('date_to', '')
        tutor = filters.get('tutor', '')
        course = filters.get('course', '')
        rating_min_raw = filters.get('rating_min', '')
        rating_max_raw = filters.get('rating_max', '')
        rating_min = _safe_decimal(rating_min_raw, errors, 'คะแนนต่ำสุด')
        rating_max = _safe_decimal(rating_max_raw, errors, 'คะแนนสูงสุด')
        average_expression = ExpressionWrapper(
            (F('rv_quality') + F('rv_knowledge') + F('rv_communication') +
             F('rv_punctuality') + F('rv_satisfaction')) / Value(5.0),
            output_field=FloatField(),
        )
        queryset = Review.objects.select_related(
            'bk_id__member', 'bk_id__tutc_id__crs_id', 'bk_id__tutc_id__tut_id__tut_id',
        ).annotate(review_average=average_expression)
        queryset = _apply_date_range(queryset, 'rv_date', date_from, date_to, errors, 'วันที่รีวิว')
        if tutor.isdigit():
            queryset = queryset.filter(bk_id__tutc_id__tut_id_id=int(tutor))
        elif tutor:
            errors.append('ค่าติวเตอร์ไม่ถูกต้อง ระบบจึงไม่ใช้เงื่อนไขนี้')
        if course:
            queryset = queryset.filter(bk_id__tutc_id__crs_id_id=course)
        if rating_min is not None:
            queryset = queryset.filter(review_average__gte=rating_min)
        if rating_max is not None:
            queryset = queryset.filter(review_average__lte=rating_max)
        if rating_min is not None and rating_max is not None and rating_min > rating_max:
            errors.append('คะแนนต่ำสุดต้องไม่มากกว่าคะแนนสูงสุด')
            queryset = queryset.none()
        queryset = queryset.order_by(
            'bk_id__tutc_id__tut_id__tut_id__mb_full_name', '-rv_date', '-bk_id_id',
        )
        totals = queryset.aggregate(
            total=Count('bk_id', distinct=True), quality=Avg('rv_quality'), knowledge=Avg('rv_knowledge'),
            communication=Avg('rv_communication'), punctuality=Avg('rv_punctuality'),
            satisfaction=Avg('rv_satisfaction'), overall=Avg(average_expression),
        )
        headers = ['วันที่รีวิว', 'ติวเตอร์', 'รายวิชา', 'ผู้เรียน', 'คะแนนเฉลี่ย', 'ความคิดเห็น']
        group_indexes = (1,)
        row_builder = lambda review: [
            _format_datetime(review.rv_date), review.bk_id.tutc_id.tut_id.tut_id.mb_full_name,
            review.bk_id.tutc_id.crs_id.crs_name, review.bk_id.member.mb_full_name,
            _format_number(review.review_average, 2), review.rv_cmt or '—',
        ]
        summary_items = [
            ('จำนวนรีวิวทั้งหมด', totals['total']), ('คะแนนเฉลี่ยรวม', _format_number(totals['overall'], 2)),
            ('คุณภาพการสอน', _format_number(totals['quality'], 2)),
            ('ความรู้', _format_number(totals['knowledge'], 2)),
            ('การสื่อสาร', _format_number(totals['communication'], 2)),
            ('ความตรงต่อเวลา', _format_number(totals['punctuality'], 2)),
            ('ความพึงพอใจ', _format_number(totals['satisfaction'], 2)),
        ]
        filter_fields = [
            _input_filter('date_from', 'วันที่รีวิวเริ่มต้น', date_from),
            _input_filter('date_to', 'วันที่รีวิวสิ้นสุด', date_to),
            _select_filter('tutor', 'ติวเตอร์', tutor, [(item.pk, item.tut_id.mb_full_name) for item in tutors]),
            _select_filter('course', 'รายวิชา', course, [(item.pk, f'{item.pk} — {item.crs_name}') for item in courses]),
            _input_filter('rating_min', 'คะแนนต่ำสุด', rating_min_raw, 'number', step='0.01', min='0', max='5'),
            _input_filter('rating_max', 'คะแนนสูงสุด', rating_max_raw, 'number', step='0.01', min='0', max='5'),
        ]

    else:
        date_from = filters.get('date_from', '')
        date_to = filters.get('date_to', '')
        role = _safe_choice(filters.get('role', ''), {'student', 'tutor'}, errors, 'บทบาทผู้รายงาน')
        reason = _safe_choice(filters.get('reason', ''), {value for value, _ in Booking.REPORT_REASON_CHOICES}, errors, 'สาเหตุ')
        resolution = _safe_choice(filters.get('resolution', ''), {'waiting', 'resolved'}, errors, 'สถานะดำเนินการ')
        course = filters.get('course', '')
        tutor = filters.get('tutor', '')
        queryset = BookingReportStatement.objects.select_related(
            'member', 'bk_id__member', 'bk_id__tutc_id__crs_id',
            'bk_id__tutc_id__tut_id__tut_id',
        )
        queryset = _apply_date_range(queryset, 'brs_date', date_from, date_to, errors, 'วันที่รายงาน')
        if role:
            queryset = queryset.filter(brs_role=role)
        if reason:
            queryset = queryset.filter(bk_id__bk_report_reason=reason)
        if resolution == 'waiting':
            queryset = queryset.filter(bk_id__bk_report_resolved_date__isnull=True)
        elif resolution == 'resolved':
            queryset = queryset.filter(bk_id__bk_report_resolved_date__isnull=False)
        if course:
            queryset = queryset.filter(bk_id__tutc_id__crs_id_id=course)
        if tutor.isdigit():
            queryset = queryset.filter(bk_id__tutc_id__tut_id_id=int(tutor))
        elif tutor:
            errors.append('ค่าติวเตอร์ไม่ถูกต้อง ระบบจึงไม่ใช้เงื่อนไขนี้')
        queryset = queryset.annotate(
            resolution_order=Case(
                When(bk_id__bk_report_resolved_date__isnull=True, then=Value(0)),
                default=Value(1), output_field=IntegerField(),
            ),
        ).order_by('resolution_order', '-brs_date', '-brs_id')
        totals = queryset.aggregate(
            total=Count('brs_id', distinct=True),
            student=Count('brs_id', filter=Q(brs_role='student'), distinct=True),
            tutor=Count('brs_id', filter=Q(brs_role='tutor'), distinct=True),
            bookings=Count('bk_id', distinct=True),
            waiting=Count('brs_id', filter=Q(bk_id__bk_report_resolved_date__isnull=True), distinct=True),
            resolved=Count('brs_id', filter=Q(bk_id__bk_report_resolved_date__isnull=False), distinct=True),
        )
        headers = ['รหัสรายงาน', 'วันที่รายงาน', 'เลขที่การจอง', 'ผู้รายงาน', 'บทบาท', 'สาเหตุ', 'สถานะ']
        group_indexes = (6,)
        row_builder = lambda statement: [
            f'BRS{statement.brs_id:05d}', _format_datetime(statement.brs_date),
            f'BK{statement.bk_id_id:05d}', statement.member.mb_full_name,
            'ผู้เรียน' if statement.brs_role == 'student' else 'ติวเตอร์',
            statement.bk_id.get_bk_report_reason_display() or '—',
            'ยังไม่ดำเนินการ' if statement.bk_id.bk_report_resolved_date is None else 'ดำเนินการแล้ว',
        ]
        summary_items = [
            ('รายงานปัญหาทั้งหมด', totals['total']), ('ผู้เรียนเป็นผู้รายงาน', totals['student']),
            ('ติวเตอร์เป็นผู้รายงาน', totals['tutor']), ('Booking ที่มีปัญหา', totals['bookings']),
            ('ยังไม่ดำเนินการ', totals['waiting']), ('ดำเนินการแล้ว', totals['resolved']),
        ]
        filter_fields = [
            _input_filter('date_from', 'วันที่รายงานเริ่มต้น', date_from),
            _input_filter('date_to', 'วันที่รายงานสิ้นสุด', date_to),
            _select_filter('role', 'บทบาทผู้รายงาน', role, [('student', 'ผู้เรียน'), ('tutor', 'ติวเตอร์')]),
            _select_filter('reason', 'สาเหตุ', reason, Booking.REPORT_REASON_CHOICES),
            _select_filter('resolution', 'สถานะดำเนินการ', resolution, [('waiting', 'ยังไม่ดำเนินการ'), ('resolved', 'ดำเนินการแล้ว')]),
            _select_filter('course', 'รายวิชา', course, [(item.pk, f'{item.pk} — {item.crs_name}') for item in courses]),
            _select_filter('tutor', 'ติวเตอร์', tutor, [(item.pk, item.tut_id.mb_full_name) for item in tutors]),
        ]

    total_rows = queryset.count()
    is_pdf = request.GET.get('print') == '1'
    page_obj = None
    if is_pdf:
        page_items = queryset
    else:
        paginator = Paginator(queryset, 50)
        page_obj = paginator.get_page(request.GET.get('page'))
        page_items = page_obj.object_list
    plain_rows = [row_builder(item) for item in page_items]
    rows = _group_report_rows(plain_rows, group_indexes)

    query_parameters = request.GET.copy()
    query_parameters.pop('page', None)
    query_parameters.pop('print', None)
    base_query = query_parameters.urlencode()
    report_context = {
        'report_type': report_type,
        'report_title': REPORT_TITLES[report_type],
        'headers': headers,
        'rows': rows,
        'total_rows': total_rows,
        'summary_items': summary_items,
        'generated_at': timezone.now(),
        'reporter_name': request.user.get_full_name() or request.user.username,
        'report_selected': True,
        'filter_fields': filter_fields,
        'filter_summary': _selected_filter_summary(filter_fields),
        'filter_errors': errors,
        'page_obj': page_obj,
        'row_start': page_obj.start_index() if page_obj and total_rows else 1,
        'base_query': base_query,
        'export_url': f'?{base_query}&print=1' if base_query else '?print=1',
        'page_orientation': 'landscape' if len(headers) + 1 > 6 else 'portrait',
    }
    if is_pdf:
        logo_path = finders.find('images/report-logo.png')
        report_context['logo_uri'] = Path(logo_path).resolve().as_uri() if logo_path else ''
        html_string = render_to_string('admin_panel/report_pdf.html', report_context, request=request)
        pdf = _html_to_pdf(html_string)
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{REPORT_FILE_NAMES[report_type]}"'
        return response

    return render(request, 'admin_panel/report_center.html', {
        'active_menu': 'dashboard',
        'topbar_breadcrumb': 'ออกรายงาน',
        **report_context,
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
        ).prefetch_related('experience_images'),
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
        'experience_images' : tutor.experience_images.all(),
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
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "update_status":
            member = get_object_or_404(
                member_user_queryset(),
                pk=request.POST.get("member_id"),
            )
            status_value = request.POST.get("member_status", "")
            valid_statuses = {str(value) for value, _ in Member.STATUS_CHOICES}
            if status_value not in valid_statuses:
                messages.error(request, "สถานะสมาชิกไม่ถูกต้อง")
            elif member.mb_status == int(status_value):
                messages.info(request, "สมาชิกอยู่ในสถานะที่เลือกอยู่แล้ว")
            else:
                member.mb_status = int(status_value)
                member.save(update_fields=["mb_status"])
                messages.success(
                    request,
                    f"เปลี่ยนสถานะสมาชิก {member.mb_full_name} เป็น {member.get_mb_status_display()} เรียบร้อยแล้ว",
                )
            return redirect("admin_panel:member_mgmt")

    q             = request.GET.get("q", "").strip()
    fac_filter    = request.GET.get("fac", "")
    mj_filter     = request.GET.get("mj", "")
    status_filter = request.GET.get("status", "")

    qs = member_user_queryset().select_related(
        "user", "mj_id", "mj_id__fac_id", "tutor",
    ).order_by("-user__date_joined")

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
        wd = get_object_or_404(Withdrawals, pk=wd_id)

        if action == 'pay' and wd.wd_status == 0:
            with transaction.atomic():
                wd = Withdrawals.objects.select_for_update().get(pk=wd.pk)
                if wd.wd_status != 0:
                    messages.info(request, f'รายการ WD{wd.wd_id:05d} ดำเนินการไปแล้ว')
                else:
                    member = Member.objects.select_for_update().get(pk=wd.member_id)
                    source_balance = (
                        member.mb_income_crd
                        if wd.wd_type == 1
                        else member.mb_deposit_crd
                    )
                    if source_balance < wd.wd_credit:
                        messages.error(
                            request,
                            f'ไม่สามารถจ่าย WD{wd.wd_id:05d} ได้ เนื่องจากเครดิตต้นทางไม่เพียงพอ',
                        )
                    else:
                        wd.wd_status    = 1
                        wd.wd_paid_date = timezone.now()
                        wd.wd_cmt       = note or None
                        member.mb_locked_crd -= wd.wd_credit
                        if wd.wd_type == 1:
                            member.mb_income_crd -= wd.wd_credit
                        else:
                            member.mb_deposit_crd -= wd.wd_credit
                        member.save(update_fields=[
                            'mb_locked_crd', 'mb_income_crd', 'mb_deposit_crd',
                        ])
                        wd.save(update_fields=[
                            'wd_status', 'wd_paid_date', 'wd_cmt',
                        ])

                        locked_system = System.objects.select_for_update().first()
                        if locked_system:
                            locked_system.total_accumulated_fee += wd.wd_fee
                            locked_system.save(update_fields=['total_accumulated_fee'])

                        messages.success(
                            request,
                            f'บันทึกการจ่าย WD{wd.wd_id:05d} เรียบร้อยแล้ว (เครดิตถูกหักออกจากบัญชีแล้ว)',
                        )

        elif action == 'reject' and wd.wd_status == 0:
            with transaction.atomic():
                wd = Withdrawals.objects.select_for_update().get(pk=wd.pk)
                if wd.wd_status == 0:
                    member = Member.objects.select_for_update().get(pk=wd.member_id)
                    wd.wd_status = 2
                    wd.wd_cmt    = note or None
                    wd.save(update_fields=['wd_status', 'wd_cmt'])
                    member.mb_locked_crd = max(
                        0,
                        member.mb_locked_crd - wd.wd_credit,
                    )
                    member.save(update_fields=['mb_locked_crd'])
                    messages.error(
                        request,
                        f'ปฏิเสธการถอน WD{wd.wd_id:05d} — เครดิตที่ล็อกไว้ถูกปลดล็อกคืนให้สมาชิกแล้ว',
                    )

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
                    bk.bk_cmt = f'[แอดมิน] พิจารณาไม่คืนเครดิต: {note}'
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
                    bk.bk_status = 6
                    bk.bk_cmt = append_booking_closed_comment(
                        bk.bk_cmt,
                        f'[แอดมิน] พิจารณาให้คืนเครดิต: {note}',
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

    setup_token = request.POST.get('setup_token', '') or request.GET.get('token', '')
    expected_token = settings.ADMIN_SETUP_TOKEN
    if not expected_token or not setup_token or not constant_time_compare(setup_token, expected_token):
        return HttpResponseForbidden('ไม่อนุญาตให้ตั้งค่าผู้ดูแลระบบ กรุณาตรวจสอบ setup token')

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

    return render(request, 'admin_panel/admin_setup.html', {
        'form': form,
        'setup_token': setup_token,
    })
