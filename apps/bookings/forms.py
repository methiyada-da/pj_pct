from django import forms
from .models import Booking, TutoringActivity, JobCompletion, Review


class BookingForm(forms.ModelForm):
    """ฟอร์มจองเรียน — ผู้เรียนกรอก"""
    class Meta:
        model = Booking
        # member, tutc_id, bk_date, bk_rate_per_person, bk_status กำหนดจาก view
        fields = ['bk_desc', 'bk_stu_datetime', 'bk_stu_count', 'ts_id']
        widgets = {
            'bk_desc'        : forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'รายละเอียดเพิ่มเติม'}),
            'bk_stu_datetime': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'bk_stu_count'   : forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'ts_id'          : forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'bk_desc'        : 'รายละเอียด',
            'bk_stu_datetime': 'วันเวลาที่นัดเรียน',
            'bk_stu_count'   : 'จำนวนผู้เรียน',
            'ts_id'          : 'ช่วงเวลา',
        }


class BookingStatusForm(forms.ModelForm):
    """ฟอร์มอัปเดตสถานะการจองสำหรับติวเตอร์"""
    class Meta:
        model = Booking
        fields = ['bk_status', 'bk_cmt']
        widgets = {
            'bk_status': forms.Select(attrs={'class': 'form-select'}),
            'bk_cmt'   : forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'bk_status': 'สถานะ',
            'bk_cmt'   : 'หมายเหตุ',
        }


class TutoringActivityForm(forms.ModelForm):
    """ฟอร์มอัปโหลดรูปกิจกรรมการติว"""
    class Meta:
        model = TutoringActivity
        # bk_id กำหนดจาก view
        fields = ['ta_img1', 'ta_img2', 'ta_img3', 'ta_desc']
        widgets = {
            'ta_img1': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'ta_img2': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'ta_img3': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'ta_desc': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'รายละเอียดเพิ่มเติม'}),
        }
        labels = {
            'ta_img1': 'รูปภาพการสอน 1',
            'ta_img2': 'รูปภาพการสอน 2',
            'ta_img3': 'รูปภาพการสอน 3',
            'ta_desc': 'รายละเอียด',
        }


class JobCompletionForm(forms.ModelForm):
    """ฟอร์มแจ้งจบงาน — ติวเตอร์กด (ไม่มี field ให้กรอก กด submit เพื่อยืนยัน)"""
    class Meta:
        model = JobCompletion
        fields = []


class JobCompletionConfirmForm(forms.ModelForm):
    """ฟอร์มสำหรับผู้เรียนยืนยันจบงาน"""
    class Meta:
        model = JobCompletion
        fields = ['jc_confirm_date']
        widgets = {
            'jc_confirm_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }
        labels = {
            'jc_confirm_date': 'วันเวลาที่ยืนยัน',
        }


SCORE_CHOICES = [(i, str(i)) for i in range(1, 6)]  # 1-5 ดาว


class ReviewForm(forms.ModelForm):
    """ฟอร์มรีวิวหลังเรียนจบ — ผู้เรียนกรอก"""
    rv_quality       = forms.ChoiceField(choices=SCORE_CHOICES, widget=forms.RadioSelect, label='คุณภาพการสอน')
    rv_knowledge     = forms.ChoiceField(choices=SCORE_CHOICES, widget=forms.RadioSelect, label='ความรู้ความสามารถ')
    rv_communication = forms.ChoiceField(choices=SCORE_CHOICES, widget=forms.RadioSelect, label='การสื่อสารและการอธิบาย')
    rv_punctuality   = forms.ChoiceField(choices=SCORE_CHOICES, widget=forms.RadioSelect, label='ความตรงต่อเวลา')
    rv_satisfaction  = forms.ChoiceField(choices=SCORE_CHOICES, widget=forms.RadioSelect, label='ความพึงพอใจโดยรวม')

    class Meta:
        model = Review
        # bk_id, rv_date กำหนดจาก view
        fields = [
            'rv_quality', 'rv_knowledge', 'rv_communication',
            'rv_punctuality', 'rv_satisfaction', 'rv_cmt',
        ]
        widgets = {
            'rv_cmt': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'ความคิดเห็นเพิ่มเติม...'}),
        }
        labels = {
            'rv_cmt': 'ความคิดเห็น',
        }