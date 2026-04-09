from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.urls import reverse

from django.utils import timezone
from django.db.models import Sum, Count

from .models import System
from .forms  import SystemForm, AdminUserForm
from apps.accounts.models import Tutor, Member
from apps.credits.models  import Refill


def is_admin(user):
    return user.is_authenticated and user.is_staff


# ─── Dashboard ───────────────────────────────────────────────────────────────

@login_required
@user_passes_test(is_admin)
def dashboard(request):
    """หน้าภาพรวมแดชบอร์ด — เพิ่ม context ตามต้องการในภายหลัง"""
    return render(request, 'admin_panel/dashboard.html', {
        'active_menu'       : 'dashboard',
        'topbar_breadcrumb' : 'ภาพรวมแดชบอร์ด',
    })


# ─── System Settings ─────────────────────────────────────────────────────────

@login_required
@user_passes_test(is_admin)
def system_settings(request):
    """หน้าตั้งค่าระบบ (System + Admin User)"""
    system    = System.objects.select_related('admin').first()
    admin_user = system.admin if system else None

    sys_form  = SystemForm(instance=system)
    user_form = AdminUserForm(instance=admin_user)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'system':
            sys_form = SystemForm(request.POST, instance=system)
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
            tutor.tut_status = 2
            tutor.save()
            messages.success(request, f'ปฏิเสธคำขอของ {tutor.tut_id.mb_full_name} เรียบร้อยแล้ว')
            return redirect('admin_panel:tutor_mgmt_detail', pk=pk)
        elif action == 'suspend':
            tutor.tut_status = 3
            tutor.save()
            messages.success(request, f'ระงับการสอนของ {tutor.tut_id.mb_full_name} เรียบร้อยแล้ว')
            return redirect('admin_panel:tutor_mgmt_detail', pk=pk)
        elif action == 'unsuspend':
            tutor.tut_status = 1
            tutor.save()
            messages.success(request, f'ปลดระงับการสอนของ {tutor.tut_id.mb_full_name} เรียบร้อยแล้ว')
            return redirect('admin_panel:tutor_mgmt_detail', pk=pk)

    member   = tutor.tut_id
    year     = member.user.date_joined.year
    tutor_id = f"TR-{year}-{tutor.pk:04d}"
    skills   = [s.strip() for s in (tutor.tut_skill or '').split(',') if s.strip()]

    return render(request, 'admin_panel/tutor_mgmt_detail.html', {
        'tutor'             : tutor,
        'member'            : member,
        'tutor_id'          : tutor_id,
        'skills'            : skills,
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
    status_filter = request.GET.get("status", "")

    qs = Member.objects.select_related("user", "mj_id", "mj_id__fac_id").order_by("-user__date_joined")

    if q:
        qs = qs.filter(
            Q(mb_full_name__icontains=q) |
            Q(mb_email__icontains=q)     |
            Q(mj_id__mj_name__icontains=q)
        )
    if status_filter != "": 
        qs = qs.filter(mb_status=status_filter)

    total_count  = Member.objects.count()
    active_count = Member.objects.filter(mb_status=1).count()
    tutor_count  = Member.objects.filter(tutor__tut_status=1).count()

    paginator = Paginator(qs, 15)
    page      = paginator.get_page(request.GET.get("page", 1))

    return render(request, "admin_panel/member_mgmt.html", {
        "page"          : page,
        "q"             : q,
        "status_filter" : status_filter,
        "total_count"   : total_count,
        "active_count"  : active_count,
        "tutor_count"   : tutor_count,
        "active_menu"   : "member_mgmt",
        "topbar_breadcrumb": "จัดการสมาชิก",
    })
