from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages

from .models import System
from .forms  import SystemForm, AdminUserForm


def is_admin(user):
    return user.is_authenticated and user.is_staff


# ─── Dashboard ───────────────────────────────────────────────────────────────

@login_required
@user_passes_test(is_admin)
def dashboard(request):
    """หน้าภาพรวมแดชบอร์ด — เพิ่ม context ตามต้องการในภายหลัง"""
    return render(request, 'admin_panel/dashboard.html', {
        'active_menu': 'dashboard',
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
        'system'     : system,
        'sys_form'   : sys_form,
        'user_form'  : user_form,
        'active_menu': 'system',
    })
