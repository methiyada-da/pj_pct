# messaging/forms.py - forms สำหรับส่งข้อความ
from django import forms
from .models import Message


class MessageForm(forms.ModelForm):
    """ฟอร์มส่งข้อความ รองรับข้อความ + รูปภาพ"""

    class Meta:
        model  = Message
        fields = ['msg', 'msg_img']
        widgets = {
            'msg': forms.Textarea(attrs={
                'class':       'msg-input',
                'rows':        1,
                'placeholder': 'พิมพ์ข้อความ...',
                'id':          'msg-textarea',
            }),
            'msg_img': forms.FileInput(attrs={
                'class':  'd-none',
                'id':     'msg-img-input',
                'accept': 'image/*',
            }),
        }

    def clean(self):
        cleaned = super().clean()
        msg     = cleaned.get('msg', '').strip()
        img     = cleaned.get('msg_img')
        # ต้องมีอย่างใดอย่างหนึ่ง
        if not msg and not img:
            raise forms.ValidationError('กรุณาพิมพ์ข้อความหรือแนบรูปภาพ')
        return cleaned

    def clean_msg_img(self):
        img = self.cleaned_data.get('msg_img')
        if img:
            # จำกัดขนาด 5 MB
            if img.size > 5 * 1024 * 1024:
                raise forms.ValidationError('ขนาดรูปภาพต้องไม่เกิน 5 MB')
        return img