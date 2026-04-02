from django.db import models
from apps.accounts.models import Member


# 4.3.1.12 ตารางข้อมูลการเติมเครดิต
class Refill(models.Model):
    STATUS_CHOICES = [
        (0, 'รอตรวจสอบ'),
        (1, 'ผ่านการตรวจสอบ'),
        (2, 'ไม่ผ่านการตรวจสอบ'),
    ]

    rf_id           = models.AutoField(primary_key=True, verbose_name="รหัสการเติมเครดิต")
    rf_date         = models.DateTimeField(verbose_name="วันเวลาที่แจ้งเติม")
    rf_money        = models.DecimalField(max_digits=7, decimal_places=2, verbose_name="จำนวนเงินที่เติม")
    rf_credit       = models.IntegerField(verbose_name="จำนวนเครดิตที่ได้รับ")
    rf_slip         = models.ImageField(upload_to='Refill/', verbose_name="สลิปการโอนเงิน")
    rf_confirm_date = models.DateTimeField(blank=True, null=True, verbose_name="วันเวลาที่ยืนยันการเติม")
    rf_status       = models.IntegerField(choices=STATUS_CHOICES, default=0, verbose_name="สถานะการตรวจสอบ")
    rf_cmt          = models.TextField(blank=True, null=True, verbose_name="หมายเหตุ")
    member          = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
        verbose_name="รหัสสมาชิก"
    )

    class Meta:
        db_table     = 'refill'
        verbose_name = "ข้อมูลการเติมเครดิต"

    def __str__(self):
        return f"RF{self.rf_id:05d} | {self.member.mb_full_name} | {self.rf_credit} เครดิต"


# 4.3.1.19 ตารางข้อมูลการขอถอนเครดิต
class Withdrawals(models.Model):
    STATUS_CHOICES = [
        (0, 'รอดำเนินการ'),
        (1, 'จ่ายแล้ว'),
        (2, 'ปฏิเสธการถอน'),
    ]

    wd_id        = models.AutoField(primary_key=True, verbose_name="รหัสการขอถอนเครดิต")
    wd_req_date  = models.DateTimeField(verbose_name="วันเวลาที่ขอถอนเครดิต")
    wd_credit    = models.IntegerField(verbose_name="จำนวนเครดิตที่ถอน")
    wd_cash      = models.DecimalField(max_digits=7, decimal_places=2, verbose_name="จำนวนเงิน (บาท)")
    wd_bank_name = models.CharField(max_length=100, verbose_name="ชื่อธนาคาร")
    wd_acc_name  = models.CharField(max_length=100, verbose_name="ชื่อบัญชี")
    wd_acc_no    = models.CharField(max_length=20,  verbose_name="เลขที่บัญชีธนาคาร")
    wd_fee       = models.DecimalField(max_digits=7, decimal_places=2, verbose_name="ค่าธรรมเนียมการถอน")
    wd_paid_date = models.DateTimeField(blank=True, null=True, verbose_name="วันเวลาที่จ่าย")
    wd_status    = models.IntegerField(choices=STATUS_CHOICES, default=0, verbose_name="สถานะการจ่าย")
    wd_cmt       = models.TextField(blank=True, null=True, verbose_name="หมายเหตุ")
    member       = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
        verbose_name="รหัสสมาชิก"
    )

    class Meta:
        db_table     = 'withdrawals'
        verbose_name = "ข้อมูลการขอถอนเครดิต"

    def __str__(self):
        return f"WD{self.wd_id:05d} | {self.member.mb_full_name} | {self.wd_credit} เครดิต"