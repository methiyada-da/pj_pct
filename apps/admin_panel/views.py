# admin_panel/views.py - views สำหรับผู้ดูแลระบบ
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.db import transaction
from django.urls import reverse

from django.utils import timezone
from django.db.models import Sum, Count

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
    from apps.bookings.models import Booking
    import json

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
    
    # System revenue (fees)
    system = System.objects.first()
    total_fees = system.total_accumulated_fee if system else 0

    # ── Monthly new members (last 7 months) ──
    today = timezone.now()
    months_labels = []
    months_data   = []
    MONTH_TH = ['', 'ม.ค.', 'ก.พ.', 'มี.ค.', 'เม.ย.', 'พ.ค.', 'มิ.ย.',
                'ก.ค.', 'ส.ค.', 'ก.ย.', 'ต.ค.', 'พ.ย.', 'ธ.ค.']
    for i in range(6, -1, -1):
        # Calculate first day of the month i months ago
        d = today.replace(day=1) - timezone.timedelta(days=i * 30) # approximation
        # More accurate month calculation:
        year = today.year
        month = today.month - i
        while month <= 0:
            month += 12
            year -= 1
        
        cnt = member_users.filter(user__date_joined__year=year, user__date_joined__month=month).count()
        months_labels.append(MONTH_TH[month])
        months_data.append(cnt)

    # ── Top course groups by course count ──
    top_groups = (CourseGroup.objects
                  .annotate(crs_count=Count('course'))
                  .order_by('-crs_count')[:5])
    max_crs = top_groups[0].crs_count if top_groups else 1

    # ── Recent activity ──
    recent_members  = member_users.select_related('user').order_by('-user__date_joined')[:5]
    recent_refills  = Refill.objects.select_related('member').order_by('-rf_date')[:5]
    recent_withdraw = Withdrawals.objects.select_related('member').order_by('-wd_req_date')[:3]

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
        'total_fees'        : total_fees,
        # chart
        'chart_labels'      : json.dumps(months_labels, ensure_ascii=False),
        'chart_data'        : json.dumps(months_data),
        # top groups
        'top_groups'        : top_groups,
        'max_crs'           : max_crs,
        # recent activity
        'recent_members'    : recent_members,
        'recent_refills'    : recent_refills,
        'recent_withdraw'   : recent_withdraw,
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
            # แจ้งเตือนติวเตอร์
            from apps.notifications.signals import _notif_member
            _notif_member(
                tutor.tut_id,
                'tutor_approved',
                'บัญชีติวเตอร์ของคุณได้รับการปลดระงับแล้ว คุณสามารถกลับมาสอนได้ตามปกติ',
                '/tutoring/manage/',
            )
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
            refill.rf_status = 2
            orig = (refill.rf_cmt or '').split('| หมายเหตุ:')[0].rstrip()
            refill.rf_cmt = (orig + f' | หมายเหตุ: {note}') if note else (orig or None)
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

    # แยก bank name และ admin note ออกจาก rf_cmt สำหรับแต่ละรายการ
    for rf in page.object_list:
        rf.extracted_bank = ''
        rf.admin_note = ''
        if rf.rf_cmt and rf.rf_cmt.startswith('โอนจาก:'):
            parts = rf.rf_cmt.split('|')
            rf.extracted_bank = parts[0].replace('โอนจาก:', '').strip()
            for p in parts[2:]:
                p = p.strip()
                if p.startswith('หมายเหตุ:'):
                    rf.admin_note = p.replace('หมายเหตุ:', '', 1).strip()
        elif rf.rf_cmt:
            # rf_cmt เก่าที่ยังไม่มีรูปแบบ โอนจาก: ให้ใส่เป็น admin_note
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
                    total_credit = bk.bk_rate_per_person * bk.bk_stu_count
                    bk.member.mb_locked_crd = max(0, bk.member.mb_locked_crd - total_credit)
                    bk.member.save(update_fields=['mb_locked_crd'])
                    tutor_member = bk.tutc_id.tut_id.tut_id
                    tutor_member.mb_income_crd += total_credit
                    tutor_member.save(update_fields=['mb_income_crd'])
                    from apps.bookings.models import JobCompletion
                    JobCompletion.objects.filter(bk_id=bk).update(jc_confirm_date=timezone.now())
                    bk.bk_status                = 4
                    bk.bk_cmt                   = f'[แอดมิน] พิจารณาไม่คืนเครดิต: {note}'
                    bk.bk_report_resolved_date  = timezone.now()
                    bk.save(update_fields=['bk_status', 'bk_cmt', 'bk_report_resolved_date'])
                    from apps.notifications.signals import _notif_member
                    _notif_member(bk.member, 'booking_rejected',
                        f'แจ้งผลการพิจารณารายงาน BK{bk.bk_id:05d}: พิจารณาไม่คืนเครดิต', '/bookings/my/')
                    _notif_member(tutor_member, 'booking_credited',
                        f'แจ้งผลการพิจารณารายงาน BK{bk.bk_id:05d}: เครดิต {total_credit} เครดิตจากการจองนี้โอนเข้าบัญชีของคุณแล้ว', '/bookings/tutor/')
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
                    total_credit = bk.bk_rate_per_person * bk.bk_stu_count
                    bk.member.mb_locked_crd  = max(0, bk.member.mb_locked_crd - total_credit)
                    bk.member.mb_deposit_crd += total_credit
                    bk.member.save(update_fields=['mb_locked_crd', 'mb_deposit_crd'])
                    tutor_member = bk.tutc_id.tut_id.tut_id
                    bk.bk_status                = 6
                    bk.bk_cmt                   = f'[แอดมิน] พิจารณาให้คืนเครดิต: {note}'
                    bk.bk_report_resolved_date  = timezone.now()
                    bk.save(update_fields=['bk_status', 'bk_cmt', 'bk_report_resolved_date'])
                    from apps.notifications.signals import _notif_member
                    _notif_member(bk.member, 'booking_rejected',
                        f'แจ้งผลการพิจารณารายงาน BK{bk.bk_id:05d}: พิจารณาให้คืนเครดิต — เครดิต {total_credit} เครดิตได้รับคืนเข้าบัญชีแล้ว', '/bookings/my/')
                    _notif_member(tutor_member, 'booking_rejected',
                        f'แจ้งผลการพิจารณารายงาน BK{bk.bk_id:05d}: พิจารณาให้คืนเครดิตแก่ผู้เรียน', '/bookings/tutor/')
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

    paginator = Paginator(qs, 15)
    page      = paginator.get_page(request.GET.get('page', 1))

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
