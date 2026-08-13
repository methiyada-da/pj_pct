# courses/forms.py - forms สำหรับจัดการรายวิชา
from django import forms
from .models import Faculty, Major, CourseGroup, Course


class FacultyForm(forms.ModelForm):
    class Meta:
        model = Faculty
        fields = ['fac_name']
        widgets = {
            'fac_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ชื่อคณะ'}),
        }
        labels = {
            'fac_name': 'ชื่อคณะ',
        }


class MajorForm(forms.ModelForm):
    class Meta:
        model = Major
        fields = ['mj_name', 'mj_desc', 'fac_id']
        widgets = {
            'mj_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ชื่อสาขา'}),
            'mj_desc': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'fac_id' : forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'mj_name': 'ชื่อสาขา',
            'mj_desc': 'รายละเอียด',
            'fac_id' : 'คณะ',
        }


class CourseGroupForm(forms.ModelForm):
    class Meta:
        model = CourseGroup
        fields = ['cg_name', 'cg_desc']
        widgets = {
            'cg_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ชื่อกลุ่มรายวิชา'}),
            'cg_desc': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'cg_name': 'ชื่อกลุ่มรายวิชา',
            'cg_desc': 'รายละเอียด',
        }


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['crs_id', 'crs_name', 'crs_desc', 'cg_id']
        widgets = {
            'crs_id'  : forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'รหัสรายวิชา เช่น CRS0001'}),
            'crs_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ชื่อรายวิชา'}),
            'crs_desc': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'cg_id'   : forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'crs_id'  : 'รหัสรายวิชา',
            'crs_name': 'ชื่อรายวิชา',
            'crs_desc': 'รายละเอียด',
            'cg_id'   : 'กลุ่มรายวิชา',
        }
