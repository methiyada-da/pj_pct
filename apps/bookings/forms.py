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
    """ฟอร์มอัปโหลดรูปกิจกรรมการติว — บังคับอย่างน้อย 1 รูป และต้องเขียนสรุป"""
    class Meta:
        model = TutoringActivity
        # bk_id กำหนดจาก view
        fields = ['ta_img1', 'ta_img2', 'ta_img3', 'ta_desc']
        widgets = {
            'ta_img1': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'ta_img2': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'ta_img3': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'ta_desc': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'สรุปหัวข้อหลักที่เรียนและพัฒนาการของนักเรียน...',
                'maxlength': '1000',
            }),
        }
        labels = {
            'ta_img1': 'รูปภาพการสอน 1',
            'ta_img2': 'รูปภาพการสอน 2',
            'ta_img3': 'รูปภาพการสอน 3',
            'ta_desc': 'สรุปเนื้อหาการสอน',
        }

    def clean(self):
        cleaned_data = super().clean()
        img1 = cleaned_data.get('ta_img1')
        img2 = cleaned_data.get('ta_img2')
        img3 = cleaned_data.get('ta_img3')
        desc = cleaned_data.get('ta_desc', '').strip()

        # บังคับอัปโหลดอย่างน้อย 1 รูป
        if not img1 and not img2 and not img3:
            raise forms.ValidationError('กรุณาอัปโหลดรูปภาพหลักฐานการสอนอย่างน้อย 1 รูป')

        # บังคับเขียนสรุป
        if not desc:
            self.add_error('ta_desc', 'กรุณาเขียนสรุปเนื้อหาการสอน')

        return cleaned_data


class JobCompletionForm(forms.ModelForm):
    """ฟอร์มแจ้งจบงาน — ติวเตอร์กด (ไม่มี field ให้กรอก กด submit เพื่อยืนยัน)"""
    class Meta:
        model = JobCompletion
        fields = []


SCORE_CHOICES = [(i, str(i)) for i in range(1, 6)]  # 1-5 ดาว


class ReviewForm(forms.ModelForm):
    """ฟอร์มรีวิวหลังเรียนจบ — ผู้เรียนกรอก บังคับให้คะแนนทุกด้าน"""
    rv_quality       = forms.ChoiceField(choices=SCORE_CHOICES, widget=forms.HiddenInput, label='คุณภาพการสอน')
    rv_knowledge     = forms.ChoiceField(choices=SCORE_CHOICES, widget=forms.HiddenInput, label='ความรู้ความสามารถ')
    rv_communication = forms.ChoiceField(choices=SCORE_CHOICES, widget=forms.HiddenInput, label='การสื่อสารและการอธิบาย')
    rv_punctuality   = forms.ChoiceField(choices=SCORE_CHOICES, widget=forms.HiddenInput, label='ความตรงต่อเวลา')
    rv_satisfaction  = forms.ChoiceField(choices=SCORE_CHOICES, widget=forms.HiddenInput, label='ความพึงพอใจโดยรวม')

    class Meta:
        model = Review
        # bk_id, rv_date กำหนดจาก view
        fields = [
            'rv_quality', 'rv_knowledge', 'rv_communication',
            'rv_punctuality', 'rv_satisfaction', 'rv_cmt',
        ]
        widgets = {
            'rv_cmt': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'แชร์ประสบการณ์การเรียนของคุณที่นี่...',
            }),
        }
        labels = {
            'rv_cmt': 'ข้อความรีวิวเพิ่มเติม (ไม่บังคับ)',
        }

    def clean(self):
        cleaned_data = super().clean()
        # ตรวจสอบว่ากดดาวครบทุกด้าน (ค่าต้องอยู่ใน 1-5)
        fields = ['rv_quality', 'rv_knowledge', 'rv_communication', 'rv_punctuality', 'rv_satisfaction']
        for f in fields:
            val = cleaned_data.get(f)
            if not val:
                raise forms.ValidationError('กรุณาให้คะแนนครบทุกด้าน')
        return cleaned_data