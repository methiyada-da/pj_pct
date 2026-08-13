# bookings/models.py - models ของ Booking, TutoringActivity, Review
from django.db import models
from apps.accounts.models import Member
from apps.tutoring.models import TutorCourse, TimeSlot


# 4.3.1.13 ตารางข้อมูลการจองเรียน
class Booking(models.Model):
    STATUS_CHOICES = [
        (0, 'จอง'),
        (1, 'รับงานแล้ว'),
        (2, 'เรียนแล้ว'),
        (3, 'แจ้งจบงาน'),
        (4, 'ยืนยันการจบงาน'),
        (5, 'รีวิวแล้ว'),
        (6, 'ปฏิเสธ'),
    ]

    bk_id              = models.AutoField(primary_key=True, verbose_name="รหัสการจองเรียน")
    bk_desc            = models.TextField(blank=True, null=True, verbose_name="รายละเอียด")
    bk_stu_datetime    = models.DateTimeField(verbose_name="วันเวลาที่นัดเรียน")
    bk_stu_count       = models.IntegerField(verbose_name="จำนวนผู้เรียน")
    bk_rate_per_person = models.IntegerField(verbose_name="อัตราค่าติว (เครดิต) ต่อคน")
    bk_date            = models.DateTimeField(verbose_name="วันเวลาที่จอง")
    bk_accepted_date   = models.DateTimeField(blank=True, null=True, verbose_name="วันเวลาที่รับงาน")
    bk_status          = models.IntegerField(choices=STATUS_CHOICES, default=0, verbose_name="สถานะ")
    bk_cmt             = models.TextField(blank=True, null=True, verbose_name="หมายเหตุ")
    REPORT_REASON_CHOICES = [
        ('1', 'หลักฐานการสอนไม่ตรงความจริง'),
        ('2', 'ติวเตอร์ไม่เข้าสอน'),
        ('3', 'เนื้อหาไม่ตรงที่ตกลงไว้'),
        ('5', 'ผู้เรียนไม่เข้าเรียน'),
        ('6', 'ติดต่ออีกฝ่ายไม่ได้'),
        ('7', 'ไม่สามารถตกลงกันได้'),
        ('8', 'อื่น ๆ'),
    ]
    bk_report_reason   = models.CharField(max_length=10, blank=True, null=True, choices=REPORT_REASON_CHOICES, verbose_name="สาเหตุการรายงานปัญหา")
    bk_report_desc     = models.TextField(blank=True, null=True, verbose_name="รายละเอียดการรายงานปัญหา")
    bk_report_date          = models.DateTimeField(blank=True, null=True, verbose_name="วันเวลาที่รายงาน")
    bk_report_resolved_date = models.DateTimeField(blank=True, null=True, verbose_name="วันเวลาที่จัดการรายงาน")
    member             = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
        verbose_name="รหัสสมาชิก"
    )
    tutc_id            = models.ForeignKey(
        TutorCourse,
        on_delete=models.CASCADE,
        db_column='tutc_id',
        verbose_name="รหัสรายวิชาที่รับสอน"
    )
    ts_id              = models.ForeignKey(
        TimeSlot,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='ts_id',
        verbose_name="รหัสช่วงเวลา"
    )

    class Meta:
        db_table     = 'booking'
        verbose_name = "ข้อมูลการจองเรียน"

    @property
    def total_credit(self):
        return self.bk_rate_per_person * self.bk_stu_count

    def __str__(self):
        return f"BK{self.bk_id:05d} | {self.member.mb_full_name}"


class BookingReportStatement(models.Model):
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('tutor', 'Tutor'),
    ]

    brs_id = models.AutoField(primary_key=True, verbose_name="Report statement ID")
    bk_id = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name='report_statements',
        db_column='bk_id',
        verbose_name="Booking",
    )
    member = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
        db_column='member_id',
        verbose_name="Statement owner",
    )
    brs_role = models.CharField(max_length=10, choices=ROLE_CHOICES, verbose_name="Role")
    brs_desc = models.TextField(verbose_name="Statement detail")
    brs_date = models.DateTimeField(verbose_name="Statement date")

    class Meta:
        db_table = 'booking_report_statement'
        verbose_name = "Booking report statement"
        ordering = ['brs_date', 'brs_id']

    def __str__(self):
        return f"Statement | BK{self.bk_id_id:05d} | {self.brs_role}"


# 4.3.1.16 ตารางข้อมูลกิจกรรมการติว
class TutoringActivity(models.Model):
    bk_id   = models.OneToOneField(
        Booking,
        on_delete=models.CASCADE,
        primary_key=True,
        db_column='bk_id',
        verbose_name="รหัสการจองเรียน"
    )
    ta_img1 = models.ImageField(upload_to='tutoring/activity/', blank=True, null=True, verbose_name="รูปภาพการสอน 1")
    ta_img2 = models.ImageField(upload_to='tutoring/activity/', blank=True, null=True, verbose_name="รูปภาพการสอน 2")
    ta_img3 = models.ImageField(upload_to='tutoring/activity/', blank=True, null=True, verbose_name="รูปภาพการสอน 3")
    ta_desc = models.TextField(blank=True, null=True, verbose_name="รายละเอียดเพิ่มเติม")

    class Meta:
        db_table     = 'tutoring_activity'
        verbose_name = "ข้อมูลกิจกรรมการติว"

    def __str__(self):
        return f"Activity | BK{self.bk_id.bk_id:05d}"


# 4.3.1.17 ตารางข้อมูลการแจ้งจบงาน
class JobCompletion(models.Model):
    bk_id            = models.OneToOneField(
        Booking,
        on_delete=models.CASCADE,
        primary_key=True,
        db_column='bk_id',
        verbose_name="รหัสการจองเรียน"
    )
    jc_complete_date = models.DateTimeField(verbose_name="วันเวลาที่แจ้งจบงาน")
    jc_confirm_date  = models.DateTimeField(blank=True, null=True, verbose_name="วันเวลาที่ยืนยัน")

    class Meta:
        db_table     = 'job_completion'
        verbose_name = "ข้อมูลการแจ้งจบงาน"

    def __str__(self):
        return f"JobComplete | BK{self.bk_id.bk_id:05d}"


# 4.3.1.18 ตารางข้อมูลการรีวิว
class Review(models.Model):
    bk_id            = models.OneToOneField(
        Booking,
        on_delete=models.CASCADE,
        primary_key=True,
        db_column='bk_id',
        verbose_name="รหัสการจองเรียน"
    )
    rv_quality       = models.IntegerField(verbose_name="คะแนนคุณภาพการสอน")
    rv_knowledge     = models.IntegerField(verbose_name="คะแนนความรู้ความสามารถ")
    rv_communication = models.IntegerField(verbose_name="คะแนนการสื่อสารและการอธิบาย")
    rv_punctuality   = models.IntegerField(verbose_name="คะแนนความตรงต่อเวลา")
    rv_satisfaction  = models.IntegerField(verbose_name="คะแนนความพึงพอใจ")
    rv_cmt           = models.TextField(blank=True, null=True, verbose_name="ข้อความรีวิว")
    rv_date          = models.DateTimeField(verbose_name="วันเวลาที่บันทึก")

    class Meta:
        db_table     = 'review'
        verbose_name = "ข้อมูลการรีวิว"

    def __str__(self):
        return f"Review | BK{self.bk_id.bk_id:05d}"
