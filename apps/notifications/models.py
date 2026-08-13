# notifications/models.py - models ของ Notification
from django.db import models
from django.contrib.auth.models import User
from apps.accounts.models import Member


class Notification(models.Model):
    notif_id = models.BigAutoField(primary_key=True, verbose_name="รหัสการแจ้งเตือน")

    # ประเภทการแจ้งเตือน
    TYPE_CHOICES = [
        ('booking_new',       'มีการจองติวใหม่'),
        ('booking_accepted',  'การจองได้รับการยืนยัน'),
        ('booking_rejected',  'การจองถูกปฏิเสธ'),
        ('booking_completed', 'มีการแจ้งจบงานที่ต้องยืนยัน'),
        ('booking_credited',  'งานเสร็จสิ้น ได้รับเครดิตแล้ว'),
        ('booking_reviewed',  'มีรีวิวใหม่'),
        ('booking_reported',  'มีการรายงานปัญหา'),
        ('booking_cancel_requested', 'มีคำขอยกเลิกการเรียน'),
        ('booking_cancel_rejected',  'คำขอยกเลิกไม่ได้รับการอนุมัติ'),
        ('booking_cancelled',        'การจองหรือการเรียนถูกยกเลิก'),
        ('booking_report_statement', 'มีคำชี้แจงเพิ่มเติมในรายงาน'),
        ('booking_report_resolved',  'รายงานได้รับการพิจารณาแล้ว'),
        ('tutor_approved',    'ติวเตอร์ได้รับการอนุมัติ'),
        ('tutor_rejected',    'ติวเตอร์ถูกปฏิเสธ'),
        ('tutor_suspended',   'บัญชีติวเตอร์ถูกระงับ'),
        ('refill_approved',   'เติมเครดิตผ่านการตรวจสอบ'),
        ('refill_rejected',   'เติมเครดิตไม่ผ่านการตรวจสอบ'),
        ('withdraw_paid',     'ถอนเงินเข้าบัญชีเรียบร้อย'),
        ('admin_refill',      'มีคำขอเติมเครดิต'),
        ('admin_withdraw',    'มีคนขอถอนเครดิต'),
        ('admin_tutor_new',   'มีติวเตอร์สมัครใหม่รอ approve'),
        ('admin_reported',    'มีการรายงานปัญหา'),
    ]

    # ผู้รับแจ้งเตือน: Member ทั่วไป (null ถ้าเป็น admin)
    recipient        = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='notifications',
        verbose_name="ผู้รับ (Member)"
    )
    # ผู้รับแจ้งเตือน: Admin Django User (null ถ้าเป็น member)
    admin_recipient  = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='notifications',
        verbose_name="ผู้รับ (Admin)"
    )
    notif_type       = models.CharField(max_length=30, choices=TYPE_CHOICES, verbose_name="ประเภท")
    notif_text       = models.CharField(max_length=255, verbose_name="ข้อความแจ้งเตือน")
    notif_url        = models.CharField(max_length=255, blank=True, default='', verbose_name="ลิงก์ปลายทาง")
    notif_is_read    = models.BooleanField(default=False, verbose_name="อ่านแล้ว")
    notif_created_at = models.DateTimeField(auto_now_add=True, verbose_name="วันเวลาที่สร้าง")

    class Meta:
        db_table     = 'notification'
        verbose_name = "การแจ้งเตือน"
        ordering     = ['-notif_created_at']

    def __str__(self):
        target = self.recipient or self.admin_recipient
        return f"[{self.notif_type}] → {target}"
