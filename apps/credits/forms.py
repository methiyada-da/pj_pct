# credits/forms.py - forms สำหรับเติมและถอนเครดิต
from django import forms
from .models import Refill, Withdrawals


class RefillForm(forms.ModelForm):
    """ฟอร์มแจ้งเติมเครดิต — สมาชิกกรอก"""
    class Meta:
        model = Refill
        # rf_id, rf_date, rf_credit, rf_confirm_date, rf_status, member กำหนดจาก view
        fields = ['rf_money', 'rf_slip']
        widgets = {
            'rf_money': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'placeholder': 'จำนวนเงินที่โอน'}),
            'rf_slip' : forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'rf_money': 'จำนวนเงิน (บาท)',
            'rf_slip' : 'สลิปการโอนเงิน',
        }


class RefillAdminForm(forms.ModelForm):
    """ฟอร์มสำหรับ admin ตรวจสอบการเติมเครดิต"""
    class Meta:
        model = Refill
        fields = ['rf_status', 'rf_cmt']
        widgets = {
            'rf_status': forms.Select(attrs={'class': 'form-select'}),
            'rf_cmt'   : forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'หมายเหตุ (ถ้ามี)'}),
        }
        labels = {
            'rf_status': 'ผลการตรวจสอบ',
            'rf_cmt'   : 'หมายเหตุ',
        }


class WithdrawalsForm(forms.ModelForm):
    """ฟอร์มขอถอนเครดิต — ติวเตอร์กรอก"""
    class Meta:
        model = Withdrawals
        # wd_req_date, wd_cash, wd_fee, wd_status, member คำนวณ/กำหนดจาก view
        fields = ['wd_credit', 'wd_bank_name', 'wd_acc_name', 'wd_acc_no']
        widgets = {
            'wd_credit'   : forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'placeholder': 'จำนวนเครดิตที่ต้องการถอน'}),
            'wd_bank_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'เช่น กสิกรไทย'}),
            'wd_acc_name' : forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ชื่อบัญชี'}),
            'wd_acc_no'   : forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'เลขที่บัญชี'}),
        }
        labels = {
            'wd_credit'   : 'จำนวนเครดิตที่ถอน',
            'wd_bank_name': 'ธนาคาร',
            'wd_acc_name' : 'ชื่อบัญชี',
            'wd_acc_no'   : 'เลขที่บัญชี',
        }


class WithdrawalsAdminForm(forms.ModelForm):
    """ฟอร์มสำหรับ admin อนุมัติการถอนเครดิต"""
    class Meta:
        model = Withdrawals
        fields = ['wd_status', 'wd_cmt']
        widgets = {
            'wd_status': forms.Select(attrs={'class': 'form-select'}),
            'wd_cmt'   : forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'หมายเหตุ (ถ้ามี)'}),
        }
        labels = {
            'wd_status': 'สถานะการจ่าย',
            'wd_cmt'   : 'หมายเหตุ',
        }