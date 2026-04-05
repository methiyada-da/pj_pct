from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import MemberRegisterForm
from apps.courses.models import Major


# ─────────────────────────────────────────────
#  หน้าแรก  (home)
# ─────────────────────────────────────────────
def home_view(request):
    """หน้าแรกของเว็บไซต์"""
    return render(request, 'main/home.html')


# ─────────────────────────────────────────────
#  เข้าสู่ระบบ
# ─────────────────────────────────────────────
def login_view(request):
    """หน้าเข้าสู่ระบบ — ใช้ email เป็น username"""

    # ถ้า login แล้ว → redirect ไปหน้าแรก
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        email    = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        next_url = request.POST.get('next', '')

        # Django default auth ใช้ username; เราเก็บ email ใน User.email ด้วย
        # ดังนั้นลอง lookup user จาก email ก่อน แล้วค่อย authenticate
        from django.contrib.auth.models import User as AuthUser
        try:
            user_obj = AuthUser.objects.get(email=email)
            username = user_obj.username
        except AuthUser.DoesNotExist:
            username = email   # fallback: ใส่ตรงๆ

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f'ยินดีต้อนรับกลับ, {user.first_name or user.username}!')
            if user.is_staff:
                return redirect('admin_panel:dashboard')
            return redirect(next_url or 'home')
        else:
            login_error = 'อีเมลหรือรหัสผ่านไม่ถูกต้อง กรุณาลองใหม่อีกครั้ง'

    from django import forms as dj_forms

    class _LoginForm:
        """ตัวช่วยส่ง error context ไปที่ template"""
        non_field_errors = []
        class _F:
            errors = []
            value = ''
        username = _F()
        password = _F()

    context = {
        'active_tab': 'login',
        'next': request.GET.get('next', ''),
        'login_error': login_error if 'login_error' in locals() else '',
    }
    return render(request, 'accounts/login.html', context)


# ─────────────────────────────────────────────
#  สมัครสมาชิก
# ─────────────────────────────────────────────
def register_view(request):
    """หน้าสมัครสมาชิก"""

    if request.user.is_authenticated:
        return redirect('home')

    # ดึงข้อมูลคณะสำหรับ dropdown filter
    try:
        from apps.courses.models import Faculty
        faculties = Faculty.objects.all().order_by('fac_name')
    except Exception:
        faculties = []

    if request.method == 'POST':
        # แปลง email prefix → full email ก่อนส่งเข้า form
        post_data = request.POST.copy()
        mb_email  = request.POST.get('mb_email', '').strip()
        if mb_email and not mb_email.endswith('@rmuti.ac.th'):
            mb_email = mb_email + '@rmuti.ac.th'
            post_data['mb_email'] = mb_email

        form = MemberRegisterForm(post_data, request.FILES)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'สมัครสมาชิกสำเร็จ!')
            return redirect('home')
    else:
        form = MemberRegisterForm()

    context = {
        'active_tab': 'register',
        'form': form,
        'faculties': faculties,
    }
    return render(request, 'accounts/register.html', context)


# ─────────────────────────────────────────────
#  ออกจากระบบ
# ─────────────────────────────────────────────
def logout_view(request):
    """ออกจากระบบ — POST only"""
    if request.method == 'POST':
        logout(request)
        messages.info(request, 'ออกจากระบบแล้ว')
    return redirect('home')


# ─────────────────────────────────────────────
#  จัดการโปรไฟล์
# ─────────────────────────────────────────────
@login_required
def profile_view(request):
    member = request.user.member
    password_error = None

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'photo':
            # อัปเดตเฉพาะรูปโปรไฟล์ — ไม่แตะรหัสผ่านหรือข้อมูลอื่น
            if 'mb_img' in request.FILES:
                member.mb_img = request.FILES['mb_img']
                member.save(update_fields=['mb_img'])
                messages.success(request, 'เปลี่ยนรูปโปรไฟล์เรียบร้อยแล้ว')
            return redirect('accounts:profile')

        elif action == 'password':
            # เปลี่ยนเฉพาะรหัสผ่าน — ไม่แตะรูปหรือข้อมูลอื่น
            from django.contrib.auth import update_session_auth_hash
            old_pw  = request.POST.get('old_password', '')
            new_pw1 = request.POST.get('new_password1', '')
            new_pw2 = request.POST.get('new_password2', '')

            if not request.user.check_password(old_pw):
                password_error = 'รหัสผ่านปัจจุบันไม่ถูกต้อง'
            elif len(new_pw1) < 8:
                password_error = 'รหัสผ่านใหม่ต้องมีอย่างน้อย 8 ตัวอักษร'
            elif new_pw1 != new_pw2:
                password_error = 'รหัสผ่านใหม่ทั้งสองช่องไม่ตรงกัน'
            else:
                request.user.set_password(new_pw1)
                request.user.save()
                update_session_auth_hash(request, request.user)
                messages.success(request, 'เปลี่ยนรหัสผ่านเรียบร้อยแล้ว')
                return redirect('accounts:profile')

    from apps.accounts.models import Tutor
    tutor = Tutor.objects.filter(tut_id=member).first()

    return render(request, 'accounts/profile.html', {
        'member'        : member,
        'faculty_name'  : member.mj_id.fac_id.fac_name if member.mj_id else '—',
        'major_name'    : member.mj_id.mj_name          if member.mj_id else '—',
        'password_error': password_error,
        'tutor_status'  : tutor.tut_status if tutor else None,
    })


# ─────────────────────────────────────────────
#  รีเซ็ตรหัสผ่าน (placeholder)
# ─────────────────────────────────────────────
def password_reset_view(request):
    """หน้ารีเซ็ตรหัสผ่าน (placeholder)"""
    return render(request, 'accounts/password_reset.html')