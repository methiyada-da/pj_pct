# admin_panel/forms.py - forms สำหรับ admin panel
from django import forms
from django.contrib.auth.models import User
from .models import System


BANK_CHOICES = [
    ('',                        '— เลือกธนาคาร —'),
    ('ธนาคารกรุงเทพ',           'ธนาคารกรุงเทพ'),
    ('ธนาคารกสิกรไทย',          'ธนาคารกสิกรไทย'),
    ('ธนาคารไทยพาณิชย์',        'ธนาคารไทยพาณิชย์'),
    ('ธนาคารกรุงไทย',           'ธนาคารกรุงไทย'),
    ('ธนาคารกรุงศรีอยุธยา',     'ธนาคารกรุงศรีอยุธยา'),
    ('ธนาคารทหารไทยธนชาต',      'ธนาคารทหารไทยธนชาต'),
    ('ธนาคารออมสิน',             'ธนาคารออมสิน'),
    ('ธนาคารเพื่อการเกษตรฯ',    'ธนาคารเพื่อการเกษตรฯ'),
    ('ธนาคารอาคารสงเคราะห์',    'ธนาคารอาคารสงเคราะห์'),
    ('ธนาคารซีไอเอ็มบี ไทย',   'ธนาคารซีไอเอ็มบี ไทย'),
    ('ธนาคารแลนด์ แอนด์ เฮ้าส์', 'ธนาคารแลนด์ แอนด์ เฮ้าส์'),
    ('ธนาคารยูโอบี',             'ธนาคารยูโอบี'),
]


class SystemForm(forms.ModelForm):
    """ฟอร์มแก้ไขข้อมูลระบบ"""

    bank_name = forms.ChoiceField(
        choices=BANK_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='ชื่อธนาคาร',
    )

    class Meta:
        model = System
        fields = [
            'uni_name', 'bank_name', 'acc_name', 'acc_no', 'promptpay_id',
            'crd_val', 'deposit_withdraw_fee_pct', 'income_withdraw_fee_pct',
        ]
        widgets = {
            'uni_name'                : forms.TextInput(attrs={'class': 'form-control'}),
            'acc_name'                : forms.TextInput(attrs={'class': 'form-control'}),
            'acc_no'                  : forms.TextInput(attrs={'class': 'form-control'}),
            'promptpay_id'            : forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'เช่น 0812345678 หรือ 1234567890123'}),
            'crd_val'                 : forms.NumberInput(attrs={'class': 'form-control'}),
            'deposit_withdraw_fee_pct': forms.NumberInput(attrs={'class': 'form-control'}),
            'income_withdraw_fee_pct' : forms.NumberInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'uni_name'                : 'ชื่อมหาวิทยาลัย',
            'bank_name'               : 'ชื่อธนาคาร',
            'acc_name'                : 'ชื่อบัญชี',
            'acc_no'                  : 'เลขที่บัญชี',
            'promptpay_id'            : 'หมายเลขพร้อมเพย์',
            'crd_val'                 : 'มูลค่าเครดิต',
            'deposit_withdraw_fee_pct': 'ค่าธรรมเนียมถอนนำฝาก (%)',
            'income_withdraw_fee_pct' : 'ค่าธรรมเนียมถอนรายได้ (%)',
        }


class AdminUserForm(forms.ModelForm):
    """ฟอร์มแก้ไข/สร้างข้อมูล Admin (Django User) ที่ผูกกับ System แบบ OneToOne"""

    # username — แสดงเฉพาะตอนสร้างใหม่ (ซ่อนผ่าน __init__ เมื่อแก้ไข)
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='ชื่อผู้ใช้ (Username)',
        required=False,
        help_text='ใช้สำหรับเข้าสู่ระบบ',
    )

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label='รหัสผ่าน',
        required=False,
        help_text='อย่างน้อย 8 ตัวอักษร ประกอบด้วยตัวอักษรและตัวเลข',
    )

    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label='ยืนยันรหัสผ่าน',
        required=False,
    )

    class Meta:
        model  = User
        fields = ['username', 'first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name' : forms.TextInput(attrs={'class': 'form-control'}),
            'email'     : forms.EmailInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'first_name': 'ชื่อ',
            'last_name' : 'นามสกุล',
            'email'     : 'อีเมลผู้ดูแลระบบ',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # กรณีสร้างใหม่ — username และ password บังคับกรอก
        if not self.instance or not self.instance.pk:
            self.fields['username'].required  = True
            self.fields['password'].required  = True
            self.fields['password2'].required = True
        else:
            # กรณีแก้ไข — ซ่อน username (เปลี่ยนไม่ได้)
            self.fields['username'].widget   = forms.HiddenInput()
            self.fields['username'].required = False

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        # ตรวจซ้ำเฉพาะตอนสร้างใหม่
        if not self.instance or not self.instance.pk:
            if User.objects.filter(username=username).exists():
                raise forms.ValidationError('ชื่อผู้ใช้นี้มีในระบบแล้ว กรุณาใช้ชื่ออื่น')
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        # ตรวจอีเมลซ้ำกับ User อื่นในระบบ (ยกเว้น instance ตัวเอง)
        qs = User.objects.filter(email=email)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('อีเมลนี้มีในระบบแล้ว กรุณาใช้อีเมลอื่น')
        return email

    def clean(self):
        cleaned_data = super().clean()
        pw1 = cleaned_data.get('password')
        pw2 = cleaned_data.get('password2')
        # ตรวจรหัสผ่านตรงกันเฉพาะเมื่อกรอก pw1 มา
        if pw1 and pw1 != pw2:
            self.add_error('password2', 'รหัสผ่านไม่ตรงกัน กรุณากรอกใหม่อีกครั้ง')
        return cleaned_data

    def save(self, commit=True):
        user     = super().save(commit=False)
        password = self.cleaned_data.get('password')
        # ตั้งค่าให้เป็น staff เสมอ ไม่ใช่ superuser
        user.is_staff     = True
        user.is_superuser = False
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user