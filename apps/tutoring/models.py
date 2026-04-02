from django.db import models
from apps.accounts.models import Tutor
from apps.courses.models import Course


# 4.3.1.8 ตารางข้อมูลรายวิชาที่รับสอน
class TutorCourse(models.Model):
    STATUS_CHOICES = [
        (0, 'ปิดรับสอน'),
        (1, 'เปิดรับสอน'),
    ]

    tutc_id      = models.CharField(max_length=13, primary_key=True, verbose_name="รหัสรายวิชาที่รับสอน")
    tutc_name    = models.CharField(max_length=150, verbose_name="ชื่อรายวิชาเพื่อโฆษณา")
    tutc_desc    = models.TextField(blank=True, null=True, verbose_name="รายละเอียดเนื้อหา")
    tutc_img     = models.ImageField(upload_to='tutor_course/', blank=True, null=True, verbose_name="รูปปก")
    tutc_max_stu = models.IntegerField(verbose_name="จำนวนรับสูงสุด (คน)")
    tutc_status  = models.IntegerField(choices=STATUS_CHOICES, default=1, verbose_name="สถานะการเปิดสอน")
    crs_id       = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        db_column='crs_id',
        verbose_name="รหัสรายวิชา"
    )
    tut_id       = models.ForeignKey(
        Tutor,
        on_delete=models.CASCADE,
        db_column='tut_id',
        verbose_name="รหัสติวเตอร์"
    )

    class Meta:
        db_table     = 'tutor_course'
        verbose_name = "ข้อมูลรายวิชาที่รับสอน"

    def __str__(self):
        return self.tutc_name


# 4.3.1.9 ตารางข้อมูลอัตราค่าติว
class TutorRate(models.Model):
    tut_rate_id         = models.AutoField(primary_key=True, verbose_name="รหัสค่าติว")
    tut_rate_per_person = models.IntegerField(verbose_name="อัตราค่าติว (เครดิต) ต่อคน")
    tut_rate_stu_count  = models.IntegerField(verbose_name="เรทตามจำนวนคน")
    tutc_id             = models.ForeignKey(
        TutorCourse,
        on_delete=models.CASCADE,
        db_column='tutc_id',
        verbose_name="รหัสรายวิชาที่รับสอน"
    )

    class Meta:
        db_table     = 'tutor_rate'
        verbose_name = "ข้อมูลอัตราค่าติว"

    def __str__(self):
        return f"{self.tutc_id} | {self.tut_rate_stu_count} คน = {self.tut_rate_per_person} เครดิต/คน"


# 4.3.1.10 ตารางข้อมูลวันที่เปิดสอน
class ScheduleDate(models.Model):
    sd_id   = models.AutoField(primary_key=True, verbose_name="รหัสวันที่เปิดสอน")
    sd_date = models.DateField(verbose_name="วันที่เปิดสอน")
    tutc_id = models.ForeignKey(
        TutorCourse,
        on_delete=models.CASCADE,
        db_column='tutc_id',
        related_name='schedule_dates',
        verbose_name="รหัสรายวิชาที่รับสอน"
    )

    class Meta:
        db_table     = 'schedule_date'
        verbose_name = "ข้อมูลวันที่เปิดสอน"

    def __str__(self):
        return f"{self.tutc_id} | {self.sd_date}"


# 4.3.1.11 ตารางข้อมูลช่วงเวลาที่เปิดสอน
class TimeSlot(models.Model):
    ts_id         = models.AutoField(primary_key=True, verbose_name="รหัสช่วงเวลา")
    ts_start_time = models.TimeField(verbose_name="เวลาเริ่ม")
    ts_end_time   = models.TimeField(verbose_name="เวลาจบ")
    sd_id         = models.ForeignKey(
        ScheduleDate,
        on_delete=models.CASCADE,
        db_column='sd_id',
        related_name='time_slots',
        verbose_name="รหัสวันที่เปิดสอน"
    )

    class Meta:
        db_table     = 'time_slot'
        verbose_name = "ข้อมูลช่วงเวลาที่เปิดสอน"

    def __str__(self):
        return f"{self.sd_id.sd_date} | {self.ts_start_time} - {self.ts_end_time}"