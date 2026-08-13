# courses/models.py - models ของ Faculty, Major, CourseGroup, Course
from django.db import models


# 4.3.1.2 ตารางข้อมูลคณะ
class Faculty(models.Model):
    fac_id   = models.AutoField(primary_key=True, verbose_name="รหัสคณะ")
    fac_name = models.CharField(max_length=100, verbose_name="ชื่อคณะ")

    class Meta:
        db_table     = 'faculty'
        verbose_name = "ข้อมูลคณะ"

    def __str__(self):
        return self.fac_name


# 4.3.1.3 ตารางข้อมูลสาขา
class Major(models.Model):
    mj_id   = models.AutoField(primary_key=True, verbose_name="รหัสสาขา")
    mj_name = models.CharField(max_length=100, verbose_name="ชื่อสาขา")
    mj_desc = models.TextField(blank=True, null=True, verbose_name="รายละเอียด")
    fac_id  = models.ForeignKey(
        Faculty,
        on_delete=models.CASCADE,
        db_column='fac_id',
        verbose_name="รหัสคณะ"
    )

    class Meta:
        db_table     = 'major'
        verbose_name = "ข้อมูลสาขา"

    def __str__(self):
        return self.mj_name


# 4.3.1.4 ตารางข้อมูลกลุ่มรายวิชา
class CourseGroup(models.Model):
    cg_id   = models.AutoField(primary_key=True, verbose_name="รหัสกลุ่มรายวิชา")
    cg_name = models.CharField(max_length=100, verbose_name="ชื่อกลุ่มรายวิชา")
    cg_desc = models.TextField(blank=True, null=True, verbose_name="รายละเอียด")

    class Meta:
        db_table     = 'course_group'
        verbose_name = "ข้อมูลกลุ่มรายวิชา"

    def __str__(self):
        return self.cg_name


# 4.3.1.5 ตารางข้อมูลรายวิชา
class Course(models.Model):
    crs_id   = models.CharField(max_length=13, primary_key=True, verbose_name="รหัสรายวิชา")
    crs_name = models.CharField(max_length=150, verbose_name="ชื่อรายวิชา")
    crs_desc = models.TextField(blank=True, null=True, verbose_name="รายละเอียด")
    cg_id    = models.ForeignKey(
        CourseGroup,
        on_delete=models.CASCADE,
        db_column='cg_id',
        verbose_name="รหัสกลุ่มรายวิชา"
    )

    class Meta:
        db_table     = 'course'
        verbose_name = "ข้อมูลรายวิชา"

    def __str__(self):
        return self.crs_name
    
    @classmethod
    def generate_id(cls):
        last = cls.objects.order_by('-crs_id').first()
        if last:
            num = int(last.crs_id[3:]) + 1
        else:
            num = 1
        return f'CRS{num:04d}'
