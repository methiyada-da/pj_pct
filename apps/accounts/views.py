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
            if request.POST.get('remember_me'):
                request.session.set_expiry(60 * 60 * 24 * 7)  # 30 วัน
            else:
                request.session.set_expiry(0)  # หมดอายุเมื่อปิด browser
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
        'email_value': email if 'email' in locals() else '',
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
    tutor        = Tutor.objects.filter(tut_id=member).first()
    faculty_name = member.mj_id.fac_id.fac_name if member.mj_id else '—'
    major_name   = member.mj_id.mj_name          if member.mj_id else '—'

    info_rows = [
        ('คณะ',          faculty_name),
        ('สาขาวิชา',     major_name),
        ('ชื่อ-นามสกุล', member.mb_full_name),
        ('อีเมล',        member.mb_email),
    ]

    return render(request, 'accounts/profile.html', {
        'member'        : member,
        'faculty_name'  : faculty_name,
        'major_name'    : major_name,
        'info_rows'     : info_rows,
        'password_error': password_error,
        'tutor_status'  : tutor.tut_status if tutor else None,
    })


# ─────────────────────────────────────────────
#  รีเซ็ตรหัสผ่าน
# ─────────────────────────────────────────────
def password_reset_view(request):
    """ขอ reset — กรอก email แล้วส่งลิงก์"""
    if request.method == 'POST':
        from django.contrib.auth.models import User as AuthUser
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        from django.core.mail import send_mail
        from django.conf import settings as conf_settings

        email = request.POST.get('email', '').strip().lower()
        try:
            user = AuthUser.objects.get(email__iexact=email)
            uid   = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_url = request.build_absolute_uri(
                f'/accounts/password-reset/confirm/{uid}/{token}/'
            )
            send_mail(
                subject='[Puean Chuay Tu] รีเซ็ตรหัสผ่าน',
                message=(
                    f'สวัสดี {user.first_name or user.username},\n\n'
                    f'คลิกลิงก์ด้านล่างเพื่อตั้งรหัสผ่านใหม่:\n{reset_url}\n\n'
                    f'ลิงก์นี้จะหมดอายุใน 24 ชั่วโมง\n'
                    f'หากคุณไม่ได้ขอรีเซ็ต กรุณาเพิกเฉยต่ออีเมลนี้'
                ),
                from_email=conf_settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
        except AuthUser.DoesNotExist:
            pass  # ไม่บอกว่า email ไม่มีในระบบ (ป้องกัน user enumeration)
        except Exception:
            messages.error(request, 'ส่งอีเมลไม่สำเร็จ กรุณาติดต่อผู้ดูแลระบบ')
            return render(request, 'accounts/password_reset.html')

        return redirect('accounts:password_reset_done')

    return render(request, 'accounts/password_reset.html')


def password_reset_done_view(request):
    """แจ้งว่าส่งอีเมลแล้ว"""
    return render(request, 'accounts/password_reset_done.html')


def password_reset_confirm_view(request, uidb64, token):
    """หน้าตั้งรหัสผ่านใหม่ — ตรวจ token ก่อน"""
    from django.contrib.auth.models import User as AuthUser
    from django.contrib.auth.tokens import default_token_generator
    from django.utils.http import urlsafe_base64_decode
    from django.utils.encoding import force_str

    try:
        uid  = force_str(urlsafe_base64_decode(uidb64))
        user = AuthUser.objects.get(pk=uid)
    except Exception:
        user = None

    valid = user is not None and default_token_generator.check_token(user, token)

    if request.method == 'POST' and valid:
        pw1 = request.POST.get('password1', '')
        pw2 = request.POST.get('password2', '')
        if len(pw1) < 8:
            messages.error(request, 'รหัสผ่านต้องมีอย่างน้อย 8 ตัวอักษร')
        elif pw1 != pw2:
            messages.error(request, 'รหัสผ่านไม่ตรงกัน')
        else:
            user.set_password(pw1)
            user.save()
            return redirect('accounts:password_reset_complete')

    return render(request, 'accounts/password_reset_confirm.html', {
        'valid': valid,
        'uidb64': uidb64,
        'token': token,
    })


def password_reset_complete_view(request):
    """รีเซ็ตสำเร็จ"""
    return render(request, 'accounts/password_reset_complete.html')