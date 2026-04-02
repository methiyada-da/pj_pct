from django import forms
from .models import Inbox, Message


class InboxForm(forms.ModelForm):
    """ฟอร์มสร้างกล่องข้อความระหว่างสมาชิก 2 คน"""
    class Meta:
        model = Inbox
        fields = ['member1', 'member2']
        widgets = {
            'member1': forms.Select(attrs={'class': 'form-select'}),
            'member2': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'member1': 'สมาชิกคนที่ 1',
            'member2': 'สมาชิกคนที่ 2',
        }


class MessageForm(forms.ModelForm):
    """ฟอร์มส่งข้อความ"""
    class Meta:
        model = Message
        # msg_sent_time, sender, กำหนดจาก view
        fields = ['msg', 'inbox']
        widgets = {
            'msg'  : forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'พิมพ์ข้อความ...'}),
            'inbox': forms.HiddenInput(),
        }
        labels = {
            'msg': 'ข้อความ',
        }