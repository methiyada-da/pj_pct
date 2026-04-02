from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Member, Tutor
from apps.courses.models import Major


class MemberRegisterForm(UserCreationForm):
    """ฟอร์มสมัครสมาชิกใหม่ — สร้าง User + Member พร้อมกัน"""
    mb_email = forms.EmailField(
        label='อีเมลมหาวิทยาลัย (@rmuti.ac.th)',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'xxxxx@rmuti.ac.th'})
    )
    mj_id = forms.ModelChoiceField(
        queryset=Major.objects.all(),
        label='สาขา',
        widget=forms.Select(attrs={'class': 'form-select'})
    )


    class Meta(UserCreationForm.Meta):
        model = User
        fields = ['first_name', 'last_name', 'password1', 'password2']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name' : forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'first_name': 'ชื่อ',
            'last_name' : 'นามสกุล',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.pop('username', None)
        self.fields['first_name'].required = True   # ← เพิ่ม
        self.fields['last_name'].required = True    # ← เพิ่ม
        self.fields['mj_id'].required = True 
        for field in self.fields.values():
            if not isinstance(field.widget, (forms.CheckboxInput, forms.Select)):
                field.widget.attrs.setdefault('class', 'form-control')
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.setdefault('class', 'form-select')

    def clean_mb_email(self):
        email = self.cleaned_data.get('mb_email')
        if not email.endswith('@rmuti.ac.th'):
            raise forms.ValidationError('กรุณาใช้อีเมลมหาวิทยาลัย (@rmuti.ac.th) เท่านั้น')
        if Member.objects.filter(mb_email=email).exists():
            raise forms.ValidationError('อีเมลนี้ถูกใช้งานแล้ว')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['mb_email']
        # auto username จาก email prefix
        user.username = self.cleaned_data['mb_email'].split('@')[0]
        if commit:
            user.save()
            Member.objects.create(
                user         = user,
                mb_full_name = f"{user.first_name} {user.last_name}".strip(),
                mb_email     = self.cleaned_data['mb_email'],
                mb_img       = None,  # ← ไม่รับรูปตอนสมัคร
                mj_id        = self.cleaned_data['mj_id'],
            )
        return user


class MemberForm(forms.ModelForm):
    """ฟอร์มแก้ไขข้อมูลสมาชิก (admin)"""
    class Meta:
        model = Member
        fields = [
            'mb_full_name', 'mb_email', 'mb_img',
            'mb_deposit_crd', 'mb_income_crd',
            'mb_status', 'mb_locked_crd', 'mj_id',
        ]
        widgets = {
            'mb_full_name'  : forms.TextInput(attrs={'class': 'form-control'}),
            'mb_email'      : forms.EmailInput(attrs={'class': 'form-control'}),
            'mb_img'        : forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'mb_deposit_crd': forms.NumberInput(attrs={'class': 'form-control'}),
            'mb_income_crd' : forms.NumberInput(attrs={'class': 'form-control'}),
            'mb_status'     : forms.Select(attrs={'class': 'form-select'}),
            'mb_locked_crd' : forms.NumberInput(attrs={'class': 'form-control'}),
            'mj_id'         : forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'mb_full_name'  : 'ชื่อและนามสกุล',
            'mb_email'      : 'อีเมลมหาวิทยาลัย',
            'mb_img'        : 'รูปโปรไฟล์',
            'mb_deposit_crd': 'เครดิตนำฝาก',
            'mb_income_crd' : 'เครดิตรายได้',
            'mb_status'     : 'สถานะ',
            'mb_locked_crd' : 'เครดิตที่ล็อกไว้',
            'mj_id'         : 'สาขา',
        }


class MemberEditForm(forms.ModelForm):
    """ฟอร์มแก้ไขข้อมูลส่วนตัว (สมาชิกแก้ไขเอง)"""
    class Meta:
        model = Member
        fields = ['mb_full_name', 'mb_img', 'mj_id']
        widgets = {
            'mb_full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'mb_img'      : forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'mj_id'       : forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'mb_full_name': 'ชื่อและนามสกุล',
            'mb_img'      : 'รูปโปรไฟล์',
            'mj_id'       : 'สาขา',
        }


class TutorRegisterForm(forms.ModelForm):
    """ฟอร์มลงทะเบียนเป็นติวเตอร์"""
    class Meta:
        model = Tutor
        fields = ['tut_desc', 'tut_skill', 'tut_gpax', 'tut_has_exp', 'tut_exp_desc']
        widgets = {
            'tut_desc'    : forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'tut_skill'   : forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'tut_gpax'    : forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '4'}),
            'tut_has_exp' : forms.Select(attrs={'class': 'form-select'}),
            'tut_exp_desc': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'tut_desc'    : 'แนะนำตัว',
            'tut_skill'   : 'ความถนัด',
            'tut_gpax'    : 'เกรดเฉลี่ย (GPAX)',
            'tut_has_exp' : 'ประสบการณ์สอน',
            'tut_exp_desc': 'รายละเอียดประสบการณ์สอน',
        }


class TutorStatusForm(forms.ModelForm):
    """ฟอร์มสำหรับ admin อนุมัติ/ระงับติวเตอร์"""
    class Meta:
        model = Tutor
        fields = ['tut_status']
        widgets = {
            'tut_status': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'tut_status': 'สถานะ',
        }