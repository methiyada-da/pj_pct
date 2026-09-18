# accounts/models.py - models ของ Member และ Tutor
from django.db import models
from django.contrib.auth.models import User
from apps.courses.models import Major


# 4.3.1.6 ตารางข้อมูลสมาชิก
class Member(models.Model):
    STATUS_CHOICES = [
        (0, 'ปิดการใช้งาน'),
        (1, 'ใช้งานปกติ'),
        (2, 'ระงับชั่วคราว'),
    ]

    user           = models.OneToOneField(User, on_delete=models.CASCADE, related_name='member')
    mb_full_name   = models.CharField(max_length=100, verbose_name="ชื่อและนามสกุล")
    mb_email       = models.CharField(max_length=50,  verbose_name="อีเมลมหาวิทยาลัย")
    mb_img         = models.ImageField(upload_to='accounts/member_profile/', blank=True, null=True, verbose_name="รูปโปรไฟล์")
    mb_deposit_crd = models.IntegerField(default=0, verbose_name="เครดิตนำฝาก")
    mb_income_crd  = models.IntegerField(default=0, verbose_name="เครดิตรายได้")
    mb_status      = models.IntegerField(choices=STATUS_CHOICES, default=1, verbose_name="สถานะ")
    mb_locked_crd  = models.IntegerField(default=0, verbose_name="เครดิตที่ล็อกไว้")
    mj_id          = models.ForeignKey(
        Major,
        on_delete=models.SET_NULL,
        null=True,
        db_column='mj_id',
        verbose_name="รหัสสาขา"
    )

    class Meta:
        db_table     = 'member'
        verbose_name = "ข้อมูลสมาชิก"

    def __str__(self):
        return self.mb_full_name


# 4.3.1.7 ตารางข้อมูลติวเตอร์
class Tutor(models.Model):
    STATUS_CHOICES = [
        (0, 'รอการตรวจสอบ'),
        (1, 'อนุมัติแล้ว'),
        (2, 'ปฏิเสธ'),
        (3, 'ระงับการสอน'),
    ]
    EXP_CHOICES = [
        (0, 'ไม่เคยสอน'),
        (1, 'เคยสอน'),
    ]

    tut_id       = models.OneToOneField(
        Member,
        on_delete=models.CASCADE,
        primary_key=True,
        db_column='tut_id',
        verbose_name="รหัสติวเตอร์"
    )
    tut_desc     = models.TextField(blank=True, null=True, verbose_name="ข้อมูลแนะนำตัว")
    tut_skill    = models.TextField(blank=True, null=True, verbose_name="ความถนัด")
    tut_gpax     = models.DecimalField(max_digits=3, decimal_places=2, verbose_name="เกรดเฉลี่ย")
    tut_has_exp  = models.IntegerField(choices=EXP_CHOICES, default=0, verbose_name="ประสบการณ์สอน")
    tut_exp_desc = models.TextField(blank=True, null=True, verbose_name="รายละเอียดประสบการณ์สอน")

    # คะแนนรีวิวเฉลี่ยรวม (ใช้สำหรับ sort/rank ในหน้าค้นหา)
    tut_rating   = models.DecimalField(max_digits=3, decimal_places=2, default=0, verbose_name="คะแนนรีวิวเฉลี่ย")

    # คะแนนรีวิวแยก 5 ด้าน (cache จาก Review — อัพเดตทุกครั้งที่มีรีวิวใหม่)
    tut_rating_quality       = models.DecimalField(max_digits=3, decimal_places=2, default=0, verbose_name="เฉลี่ยคุณภาพการสอน")
    tut_rating_knowledge     = models.DecimalField(max_digits=3, decimal_places=2, default=0, verbose_name="เฉลี่ยความรู้ความสามารถ")
    tut_rating_communication = models.DecimalField(max_digits=3, decimal_places=2, default=0, verbose_name="เฉลี่ยการสื่อสารและการอธิบาย")
    tut_rating_punctuality   = models.DecimalField(max_digits=3, decimal_places=2, default=0, verbose_name="เฉลี่ยความตรงต่อเวลา")
    tut_rating_satisfaction  = models.DecimalField(max_digits=3, decimal_places=2, default=0, verbose_name="เฉลี่ยความพึงพอใจ")

    tut_status   = models.IntegerField(choices=STATUS_CHOICES, default=0, verbose_name="สถานะ")

    # [เพิ่มใหม่] รูปบัตรนักศึกษาสำหรับยืนยันตัวตน
    tut_student_card = models.ImageField(
        upload_to='tutoring/tutor_student_cards/',
        blank=True, null=True,
        verbose_name="รูปบัตรนักศึกษา"
    )

    # [เพิ่มใหม่] หมายเหตุจาก Admin เมื่อปฏิเสธหรือระงับการสอน
    tut_reject_note = models.TextField(
        blank=True, null=True,
        verbose_name="หมายเหตุการปฏิเสธ/ระงับ"
    )

    class Meta:
        db_table     = 'tutor'
        verbose_name = "ข้อมูลติวเตอร์"

    def __str__(self):
        return f"Tutor: {self.tut_id}"


class TutorExperienceImage(models.Model):
    tutor = models.ForeignKey(
        Tutor, on_delete=models.CASCADE, related_name='experience_images',
        verbose_name="ติวเตอร์",
    )
    image = models.ImageField(
        upload_to='tutoring/experience/', verbose_name="รูปประสบการณ์การสอน",
    )

    class Meta:
        db_table = 'tutor_experience_image'
        verbose_name = "รูปประสบการณ์การสอน"
        verbose_name_plural = "รูปประสบการณ์การสอน"
