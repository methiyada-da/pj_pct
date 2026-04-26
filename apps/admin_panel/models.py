# admin_panel/models.py - models ของ system config และ reports
from django.db import models
from django.contrib.auth.models import User


# 4.3.1.1 ตารางข้อมูลระบบ
class System(models.Model):
    admin = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='system',
        verbose_name="ผู้ดูแลระบบ"
    )
    uni_name                 = models.CharField(max_length=100, verbose_name="ชื่อมหาวิทยาลัย")
    bank_name                = models.CharField(max_length=100, verbose_name="ชื่อธนาคาร")
    acc_name                 = models.CharField(max_length=100, verbose_name="ชื่อบัญชี")
    acc_no                   = models.CharField(max_length=20,  verbose_name="เลขที่บัญชีธนาคาร")
    promptpay_id             = models.CharField(max_length=20, blank=True, default='', verbose_name="หมายเลขพร้อมเพย์ (เบอร์โทร/เลขบัตรประชาชน)")
    crd_val                  = models.DecimalField(max_digits=5,  decimal_places=2, verbose_name="มูลค่าเครดิต")
    deposit_withdraw_fee_pct = models.DecimalField(max_digits=5,  decimal_places=2, verbose_name="อัตราร้อยละค่าธรรมเนียมการถอนยอดเครดิตนำฝาก")
    income_withdraw_fee_pct  = models.DecimalField(max_digits=5,  decimal_places=2, verbose_name="อัตราร้อยละค่าธรรมเนียมการถอนยอดเครดิตรายได้")

    class Meta:
        db_table     = 'system'
        verbose_name = "ข้อมูลระบบ"

    def __str__(self):
        return self.uni_name

    @property
    def admin_email(self):
        return self.admin.email if self.admin else None

    @property
    def admin_name(self):
        return self.admin.get_full_name() if self.admin else None