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
    """ฟอร์มแก้ไขข้อมูล Admin (Django User) ที่ผูกกับ System แบบ OneToOne"""
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label='รหัสผ่านใหม่',
        required=False,
        help_text='เว้นว่างถ้าไม่ต้องการเปลี่ยนรหัสผ่าน'
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
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

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user