# tutoring/forms.py - forms สำหรับติวเตอร์
from django import forms
from config.validators import validate_uploaded_image
from .models import TutorCourse, TutorRate, ScheduleDate, TimeSlot


class MultipleImageInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class ExperienceImagesField(forms.ImageField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('required', False)
        kwargs.setdefault('widget', MultipleImageInput(attrs={'accept': 'image/*'}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        images = data if isinstance(data, (list, tuple)) else ([data] if data else [])
        if len(images) > 5:
            raise forms.ValidationError('อัปโหลดรูปประสบการณ์ได้ไม่เกิน 5 รูปต่อครั้ง')
        cleaned_images = []
        for image in images:
            validate_uploaded_image(image)
            cleaned_images.append(super().clean(image))
        return cleaned_images


class TutorRegisterForm(forms.Form):
    """ฟอร์มขั้นตอนที่ 2 — ข้อมูลวิชาการและประสบการณ์"""
    student_card = forms.ImageField(
        label='รูปบัตรนักศึกษา',
        required=False,
        validators=[validate_uploaded_image],
        widget=forms.ClearableFileInput(attrs={'accept': 'image/*'}),
    )
    gpa = forms.DecimalField(
        label='เกรดเฉลี่ยสะสม',
        max_digits=3, decimal_places=2, min_value=0, max_value=4,
        widget=forms.NumberInput(attrs={'placeholder': '0.00', 'step': '0.01'}),
    )
    teaching_skills = forms.CharField(
        label='ทักษะการสอน',
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'ระบุสาขาวิชาที่คุณเชี่ยวชาญ...'}),
    )
    has_experience = forms.ChoiceField(
        label='ประสบการณ์การสอน',
        choices=[('0', 'ไม่มีประสบการณ์'), ('1', 'มีประสบการณ์')],
        widget=forms.RadioSelect,
    )
    experience_detail = forms.CharField(
        label='รายละเอียดประสบการณ์',
        required=False,
        widget=forms.Textarea(attrs={'rows': 4, 'placeholder': 'ช่วยเล่าเพิ่มเติมเกี่ยวกับประสบการณ์ของคุณในฐานะติวเตอร์หน่อย...'}),
    )
    experience_images = ExperienceImagesField(label='รูปประสบการณ์การสอน')


class TutorCourseForm(forms.ModelForm):
    """ฟอร์มสร้าง/แก้ไขรายวิชาที่รับสอน"""
    tutc_meeting_detail = forms.CharField(
        label='รายละเอียดนัดหมายเริ่มต้น',
        required=True,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'เช่น เรียนภายในมหาวิทยาลัย รายละเอียดห้องเรียนจะแจ้งตอนตอบรับการจอง',
        }),
    )
    class Meta:
        model = TutorCourse
        # tutc_id และ tut_id กำหนดจาก view
        fields = [
            'tutc_name', 'tutc_desc', 'tutc_meeting_detail', 'tutc_img',
            'tutc_max_stu', 'tutc_status', 'crs_id',
        ]
        widgets = {
            'tutc_name'   : forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ชื่อรายวิชาที่ประกาศสอน'}),
            'tutc_desc'   : forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'tutc_img'    : forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'tutc_max_stu': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'tutc_status' : forms.Select(attrs={'class': 'form-select'}),
            'crs_id'      : forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'tutc_name'   : 'ชื่อรายวิชาที่ประกาศสอน',
            'tutc_desc'   : 'รายละเอียดเนื้อหา',
            'tutc_meeting_detail': 'รายละเอียดนัดหมายเริ่มต้น',
            'tutc_img'    : 'รูปปก',
            'tutc_max_stu': 'จำนวนรับสูงสุด (คน/ครั้ง)',
            'tutc_status' : 'สถานะการเปิดสอน',
            'crs_id'      : 'รายวิชา',
        }

    def clean_tutc_img(self):
        image = self.cleaned_data.get('tutc_img')
        validate_uploaded_image(image)
        return image


class TutorRateForm(forms.ModelForm):
    """ฟอร์มกำหนดราคาเดียวต่อที่นั่ง"""
    class Meta:
        model = TutorRate
        # tutc_id กำหนดจาก view
        fields = ['tut_rate_stu_count', 'tut_rate_per_person']
        widgets = {
            'tut_rate_stu_count' : forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'tut_rate_per_person': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
        }
        labels = {
            'tut_rate_stu_count' : 'จำนวนคน',
            'tut_rate_per_person': 'ราคาต่อที่นั่ง (เครดิต)',
        }


class ScheduleDateForm(forms.ModelForm):
    """ฟอร์มกำหนดวันที่เปิดสอน"""
    class Meta:
        model = ScheduleDate
        # tutc_id กำหนดจาก view
        fields = ['sd_date']
        widgets = {
            'sd_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
        labels = {
            'sd_date': 'วันที่เปิดสอน',
        }


class TimeSlotForm(forms.ModelForm):
    """ฟอร์มกำหนดช่วงเวลาที่เปิดสอน"""
    class Meta:
        model = TimeSlot
        # sd_id กำหนดจาก view
        fields = ['ts_start_time', 'ts_end_time']
        widgets = {
            'ts_start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'ts_end_time'  : forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
        }
        labels = {
            'ts_start_time': 'เวลาเริ่ม',
            'ts_end_time'  : 'เวลาจบ',
        }

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('ts_start_time')
        end   = cleaned_data.get('ts_end_time')
        if start and end and end <= start:
            raise forms.ValidationError('เวลาจบต้องมากกว่าเวลาเริ่ม')
        return cleaned_data
