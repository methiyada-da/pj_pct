# รายงานสำรวจ Django Models

## โครงการ

**การพัฒนาระบบเว็บแอปพลิเคชันเพื่อนช่วยติว**  
**DEVELOPMENT OF WEB APPLICATION SYSTEM FOR “PUEAN CHUAY TU”**

## ขอบเขตและวิธีนับ

- สำรวจ `apps/**/models.py`, `apps/**/models/*.py`, import ของ Model, abstract/proxy/custom user และการอ้างอิง Django User
- พบ Model ที่โครงการประกาศเอง **21 Model** รวม **153 field** โดยนับ primary key `id` ที่ Django สร้างอัตโนมัติ
- ไม่พบ `apps/**/models/*.py`, abstract model, proxy model หรือ custom user model
- โครงการอ้างอิง `django.contrib.auth.models.User` โดยตรง แต่ไม่นับเป็น Model ที่โครงการประกาศเองและไม่นับ field ของแพ็กเกจ Django ในยอด 153 field
- `config/settings.py` ไม่ได้กำหนด `AUTH_USER_MODEL`; จึงใช้ค่าเริ่มต้น `auth.User`
- ค่า `db_column` ที่ระบุว่า “อัตโนมัติ” คือชื่อคอลัมน์ที่ Django คำนวณให้: field ปกติใช้ชื่อ Python field และ relation ใช้ `<field>_id`
- `null`, `blank`, `primary_key`, `unique`, `db_index` ที่ไม่ได้ประกาศใช้ค่าเริ่มต้น `False`; ForeignKey มีดัชนีโดยปริยาย และ OneToOneField มี unique โดยปริยาย
- “validators: ไม่มี” หมายถึงไม่มี custom validator ที่ประกาศด้วย `validators=`; validator ภายในของชนิด field ยังทำงานตาม Django

## สรุป Model

| App | Model | Source | db_table | Primary key | จำนวน field |
|---|---|---|---|---|---:|
| admin_panel | System | `apps/admin_panel/models.py:7` | `system` | `id` (Django สร้าง) | 12 |
| courses | Faculty | `apps/courses/models.py:6` | `faculty` | `fac_id` | 2 |
| courses | Major | `apps/courses/models.py:19` | `major` | `mj_id` | 5 |
| courses | CourseGroup | `apps/courses/models.py:40` | `course_group` | `cg_id` | 3 |
| courses | Course | `apps/courses/models.py:54` | `course` | `crs_id` | 4 |
| accounts | Member | `apps/accounts/models.py:8` | `member` | `id` (Django สร้าง) | 10 |
| accounts | Tutor | `apps/accounts/models.py:40` | `tutor` | `tut_id` | 15 |
| tutoring | TutorCourse | `apps/tutoring/models.py:8` | `tutor_course` | `tutc_id` | 9 |
| tutoring | TutorRate | `apps/tutoring/models.py:43` | `tutor_rate` | `tut_rate_id` | 4 |
| tutoring | ScheduleDate | `apps/tutoring/models.py:63` | `schedule_date` | `sd_id` | 3 |
| tutoring | TimeSlot | `apps/tutoring/models.py:85` | `time_slot` | `ts_id` | 5 |
| bookings | Booking | `apps/bookings/models.py:8` | `booking` | `bk_id` | 16 |
| bookings | BookingReportStatement | `apps/bookings/models.py:71` | `booking_report_statement` | `brs_id` | 6 |
| bookings | TutoringActivity | `apps/bookings/models.py:105` | `tutoring_activity` | `bk_id` | 5 |
| bookings | JobCompletion | `apps/bookings/models.py:127` | `job_completion` | `bk_id` | 3 |
| bookings | Review | `apps/bookings/models.py:147` | `review` | `bk_id` | 8 |
| messaging | Inbox | `apps/messaging/models.py:7` | `inbox` | `ib_id` | 3 |
| messaging | Message | `apps/messaging/models.py:44` | `message` | `msg_id` | 7 |
| credits | Refill | `apps/credits/models.py:7` | `refill` | `rf_id` | 10 |
| credits | Withdrawals | `apps/credits/models.py:38` | `withdrawals` | `wd_id` | 15 |
| notifications | Notification | `apps/notifications/models.py:7` | `notification` | `id` (Django สร้าง) | 8 |

## รายละเอียด Model และ field

ในคอลัมน์ “คุณสมบัติ” ใช้รูปแบบ `max_length / max_digits,decimal_places; null; blank; default; PK; unique; index` และแสดงเฉพาะค่าขนาดที่ชนิด field รองรับ

### admin_panel.System

- Source: `apps/admin_panel/models.py:7`
- Meta: `db_table='system'`; ไม่มี `constraints`, `indexes`, `unique_together`

| Python field (บรรทัด) | db_column | Django field type | คุณสมบัติ | Relation | validators |
|---|---|---|---|---|---|
| id (implicit) | id | AutoField | null=F; blank=F; default=ไม่มี; PK=T; unique=T; index=T | - | ไม่มี |
| admin (8) | admin_id (อัตโนมัติ) | OneToOneField | null=T; blank=T; default=ไม่มี; PK=F; unique=T; index=T | `auth.User`; `SET_NULL`; related_name=`system` | ไม่มี |
| uni_name (16) | uni_name | CharField | max_length=100; null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| bank_name (17) | bank_name | CharField | max_length=100; null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| email_domain (18) | email_domain | CharField | max_length=100; null=F; blank=F; default=`'rmuti.ac.th'`; PK=F; unique=F; index=F | - | ไม่มี |
| acc_name (19) | acc_name | CharField | max_length=100; null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| acc_no (20) | acc_no | CharField | max_length=20; null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| promptpay_id (21) | promptpay_id | CharField | max_length=20; null=F; blank=T; default=`''`; PK=F; unique=F; index=F | - | ไม่มี |
| crd_val (22) | crd_val | DecimalField | max_digits=5, decimal_places=2; null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| deposit_withdraw_fee_pct (23) | deposit_withdraw_fee_pct | DecimalField | max_digits=5, decimal_places=2; null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| income_withdraw_fee_pct (24) | income_withdraw_fee_pct | DecimalField | max_digits=5, decimal_places=2; null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| total_accumulated_fee (25) | total_accumulated_fee | DecimalField | max_digits=10, decimal_places=2; null=F; blank=F; default=`0.00`; PK=F; unique=F; index=F | - | ไม่มี |

### courses.Faculty

- Source: `apps/courses/models.py:6`
- Meta: `db_table='faculty'`; ไม่มี constraints

| Python field (บรรทัด) | db_column | Django field type | คุณสมบัติ | Relation | validators |
|---|---|---|---|---|---|
| fac_id (7) | fac_id | AutoField | null=F; blank=F; default=ไม่มี; PK=T; unique=T; index=T | - | ไม่มี |
| fac_name (8) | fac_name | CharField | max_length=100; null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |

### courses.Major

- Source: `apps/courses/models.py:19`; Meta: `db_table='major'`; ไม่มี constraints

| Python field (บรรทัด) | db_column | Django field type | คุณสมบัติ | Relation | validators |
|---|---|---|---|---|---|
| mj_id (20) | mj_id | AutoField | null=F; blank=F; default=ไม่มี; PK=T; unique=T; index=T | - | ไม่มี |
| mj_name (21) | mj_name | CharField | max_length=100; null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| mj_abbr (22) | mj_abbr | CharField | max_length=10; null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| mj_desc (23) | mj_desc | TextField | null=T; blank=T; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| fac_id (24) | fac_id | ForeignKey | null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=T | `courses.Faculty`; `CASCADE`; related_name=ไม่มี | ไม่มี |

### courses.CourseGroup

- Source: `apps/courses/models.py:40`; Meta: `db_table='course_group'`; ไม่มี constraints

| Python field (บรรทัด) | db_column | Django field type | คุณสมบัติ | Relation | validators |
|---|---|---|---|---|---|
| cg_id (41) | cg_id | AutoField | null=F; blank=F; default=ไม่มี; PK=T; unique=T; index=T | - | ไม่มี |
| cg_name (42) | cg_name | CharField | max_length=100; null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| cg_desc (43) | cg_desc | TextField | null=T; blank=T; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |

### courses.Course

- Source: `apps/courses/models.py:54`; Meta: `db_table='course'`; ไม่มี constraints

| Python field (บรรทัด) | db_column | Django field type | คุณสมบัติ | Relation | validators |
|---|---|---|---|---|---|
| crs_id (55) | crs_id | CharField | max_length=13; null=F; blank=F; default=ไม่มี; PK=T; unique=T; index=T | - | ไม่มี |
| crs_name (56) | crs_name | CharField | max_length=150; null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| crs_desc (57) | crs_desc | TextField | null=T; blank=T; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| cg_id (58) | cg_id | ForeignKey | null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=T | `courses.CourseGroup`; `CASCADE`; related_name=ไม่มี | ไม่มี |

### accounts.Member

- Source: `apps/accounts/models.py:8`; Meta: `db_table='member'`; ไม่มี constraints

| Python field (บรรทัด) | db_column | Django field type | คุณสมบัติ | Relation | validators |
|---|---|---|---|---|---|
| id (implicit) | id | AutoField | null=F; blank=F; default=ไม่มี; PK=T; unique=T; index=T | - | ไม่มี |
| user (15) | user_id (อัตโนมัติ) | OneToOneField | null=F; blank=F; default=ไม่มี; PK=F; unique=T; index=T | `auth.User`; `CASCADE`; related_name=`member` | ไม่มี |
| mb_full_name (16) | mb_full_name | CharField | max_length=100; null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| mb_email (17) | mb_email | CharField | max_length=50; null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| mb_img (18) | mb_img | ImageField | max_length=100 (Django default); null=T; blank=T; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| mb_deposit_crd (19) | mb_deposit_crd | IntegerField | null=F; blank=F; default=0; PK=F; unique=F; index=F | - | ไม่มี |
| mb_income_crd (20) | mb_income_crd | IntegerField | null=F; blank=F; default=0; PK=F; unique=F; index=F | - | ไม่มี |
| mb_status (21) | mb_status | IntegerField | null=F; blank=F; default=1; PK=F; unique=F; index=F; choices=`STATUS_CHOICES` | - | ไม่มี |
| mb_locked_crd (22) | mb_locked_crd | IntegerField | null=F; blank=F; default=0; PK=F; unique=F; index=F | - | ไม่มี |
| mj_id (23) | mj_id | ForeignKey | null=T; blank=F; default=ไม่มี; PK=F; unique=F; index=T | `courses.Major`; `SET_NULL`; related_name=ไม่มี | ไม่มี |

### accounts.Tutor

- Source: `apps/accounts/models.py:40`; Meta: `db_table='tutor'`; ไม่มี constraints

| Python field (บรรทัด) | db_column | Django field type | คุณสมบัติ | Relation | validators |
|---|---|---|---|---|---|
| tut_id (52) | tut_id | OneToOneField | null=F; blank=F; default=ไม่มี; PK=T; unique=T; index=T | `accounts.Member`; `CASCADE`; related_name=ไม่มี | ไม่มี |
| tut_desc (59) | tut_desc | TextField | null=T; blank=T; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| tut_skill (60) | tut_skill | TextField | null=T; blank=T; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| tut_gpax (61) | tut_gpax | DecimalField | max_digits=3, decimal_places=2; null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| tut_has_exp (62) | tut_has_exp | IntegerField | null=F; blank=F; default=0; PK=F; unique=F; index=F; choices=`EXP_CHOICES` | - | ไม่มี |
| tut_exp_desc (63) | tut_exp_desc | TextField | null=T; blank=T; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| tut_rating (66) | tut_rating | DecimalField | max_digits=3, decimal_places=2; null=F; blank=F; default=0; PK=F; unique=F; index=F | - | ไม่มี |
| tut_rating_quality (69) | tut_rating_quality | DecimalField | max_digits=3, decimal_places=2; null=F; blank=F; default=0; PK=F; unique=F; index=F | - | ไม่มี |
| tut_rating_knowledge (70) | tut_rating_knowledge | DecimalField | max_digits=3, decimal_places=2; null=F; blank=F; default=0; PK=F; unique=F; index=F | - | ไม่มี |
| tut_rating_communication (71) | tut_rating_communication | DecimalField | max_digits=3, decimal_places=2; null=F; blank=F; default=0; PK=F; unique=F; index=F | - | ไม่มี |
| tut_rating_punctuality (72) | tut_rating_punctuality | DecimalField | max_digits=3, decimal_places=2; null=F; blank=F; default=0; PK=F; unique=F; index=F | - | ไม่มี |
| tut_rating_satisfaction (73) | tut_rating_satisfaction | DecimalField | max_digits=3, decimal_places=2; null=F; blank=F; default=0; PK=F; unique=F; index=F | - | ไม่มี |
| tut_status (75) | tut_status | IntegerField | null=F; blank=F; default=0; PK=F; unique=F; index=F; choices=`STATUS_CHOICES` | - | ไม่มี |
| tut_student_card (78) | tut_student_card | ImageField | max_length=100 (Django default); null=T; blank=T; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| tut_reject_note (85) | tut_reject_note | TextField | null=T; blank=T; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |

### tutoring.TutorCourse

- Source: `apps/tutoring/models.py:8`; Meta: `db_table='tutor_course'`; ไม่มี constraints

| Python field (บรรทัด) | db_column | Django field type | คุณสมบัติ | Relation | validators |
|---|---|---|---|---|---|
| tutc_id (14) | tutc_id | CharField | max_length=13; null=F; blank=F; default=ไม่มี; PK=T; unique=T; index=T | - | ไม่มี |
| tutc_name (15) | tutc_name | CharField | max_length=150; null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| tutc_desc (16) | tutc_desc | TextField | null=T; blank=T; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| tutc_img (17) | tutc_img | ImageField | max_length=100 (Django default); null=T; blank=T; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| tutc_max_stu (18) | tutc_max_stu | IntegerField | null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| tutc_status (19) | tutc_status | IntegerField | null=F; blank=F; default=1; PK=F; unique=F; index=F; choices=`STATUS_CHOICES` | - | ไม่มี |
| tutc_rating (20) | tutc_rating | DecimalField | max_digits=3, decimal_places=2; null=F; blank=F; default=0; PK=F; unique=F; index=F | - | ไม่มี |
| crs_id (21) | crs_id | ForeignKey | null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=T | `courses.Course`; `CASCADE`; related_name=ไม่มี | ไม่มี |
| tut_id (27) | tut_id | ForeignKey | null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=T | `accounts.Tutor`; `CASCADE`; related_name=ไม่มี | ไม่มี |

### tutoring.TutorRate

- Source: `apps/tutoring/models.py:43`; Meta: `db_table='tutor_rate'`; ไม่มี constraints

| Python field (บรรทัด) | db_column | Django field type | คุณสมบัติ | Relation | validators |
|---|---|---|---|---|---|
| tut_rate_id (44) | tut_rate_id | AutoField | null=F; blank=F; default=ไม่มี; PK=T; unique=T; index=T | - | ไม่มี |
| tut_rate_per_person (45) | tut_rate_per_person | IntegerField | null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| tut_rate_stu_count (46) | tut_rate_stu_count | IntegerField | null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| tutc_id (47) | tutc_id | ForeignKey | null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=T | `tutoring.TutorCourse`; `CASCADE`; related_name=ไม่มี | ไม่มี |

### tutoring.ScheduleDate

- Source: `apps/tutoring/models.py:63`; Meta: `db_table='schedule_date'`; ไม่มี constraints

| Python field (บรรทัด) | db_column | Django field type | คุณสมบัติ | Relation | validators |
|---|---|---|---|---|---|
| sd_id (64) | sd_id | AutoField | null=F; blank=F; default=ไม่มี; PK=T; unique=T; index=T | - | ไม่มี |
| sd_date (65) | sd_date | DateField | null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| tutc_id (66) | tutc_id | ForeignKey | null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=T | `tutoring.TutorCourse`; `CASCADE`; related_name=`schedule_dates` | ไม่มี |

### tutoring.TimeSlot

- Source: `apps/tutoring/models.py:85`; Meta: `db_table='time_slot'`; ไม่มี constraints

| Python field (บรรทัด) | db_column | Django field type | คุณสมบัติ | Relation | validators |
|---|---|---|---|---|---|
| ts_id (91) | ts_id | AutoField | null=F; blank=F; default=ไม่มี; PK=T; unique=T; index=T | - | ไม่มี |
| ts_start_time (92) | ts_start_time | TimeField | null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| ts_end_time (93) | ts_end_time | TimeField | null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| ts_status (94) | ts_status | IntegerField | null=F; blank=F; default=0; PK=F; unique=F; index=F; choices=`STATUS_CHOICES` | - | ไม่มี |
| sd_id (99) | sd_id | ForeignKey | null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=T | `tutoring.ScheduleDate`; `CASCADE`; related_name=`time_slots` | ไม่มี |

### bookings.Booking

- Source: `apps/bookings/models.py:8`; Meta: `db_table='booking'`; ไม่มี constraints

| Python field (บรรทัด) | db_column | Django field type | คุณสมบัติ | Relation | validators |
|---|---|---|---|---|---|
| bk_id (19) | bk_id | AutoField | null=F; blank=F; default=ไม่มี; PK=T; unique=T; index=T | - | ไม่มี |
| bk_desc (20) | bk_desc | TextField | null=T; blank=T; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| bk_stu_datetime (21) | bk_stu_datetime | DateTimeField | null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| bk_stu_count (22) | bk_stu_count | IntegerField | null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| bk_rate_per_person (23) | bk_rate_per_person | IntegerField | null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| bk_date (24) | bk_date | DateTimeField | null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| bk_accepted_date (25) | bk_accepted_date | DateTimeField | null=T; blank=T; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| bk_status (26) | bk_status | IntegerField | null=F; blank=F; default=0; PK=F; unique=F; index=F; choices=`STATUS_CHOICES` | - | ไม่มี |
| bk_cmt (27) | bk_cmt | TextField | null=T; blank=T; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| bk_report_reason (35) | bk_report_reason | CharField | max_length=10; null=T; blank=T; default=ไม่มี; PK=F; unique=F; index=F; choices=`REPORT_REASON_CHOICES` | - | ไม่มี |
| bk_report_desc (36) | bk_report_desc | TextField | null=T; blank=T; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| bk_report_date (37) | bk_report_date | DateTimeField | null=T; blank=T; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| bk_report_resolved_date (38) | bk_report_resolved_date | DateTimeField | null=T; blank=T; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| member (39) | member_id (อัตโนมัติ) | ForeignKey | null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=T | `accounts.Member`; `CASCADE`; related_name=ไม่มี | ไม่มี |
| tutc_id (44) | tutc_id | ForeignKey | null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=T | `tutoring.TutorCourse`; `CASCADE`; related_name=ไม่มี | ไม่มี |
| ts_id (50) | ts_id | ForeignKey | null=T; blank=T; default=ไม่มี; PK=F; unique=F; index=T | `tutoring.TimeSlot`; `SET_NULL`; related_name=ไม่มี | ไม่มี |

### bookings.BookingReportStatement

- Source: `apps/bookings/models.py:71`; Meta: `db_table='booking_report_statement'`, ordering=`['brs_date', 'brs_id']`; ไม่มี constraints

| Python field (บรรทัด) | db_column | Django field type | คุณสมบัติ | Relation | validators |
|---|---|---|---|---|---|
| brs_id (77) | brs_id | AutoField | null=F; blank=F; default=ไม่มี; PK=T; unique=T; index=T | - | ไม่มี |
| bk_id (78) | bk_id | ForeignKey | null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=T | `bookings.Booking`; `CASCADE`; related_name=`report_statements` | ไม่มี |
| member (85) | member_id | ForeignKey | null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=T | `accounts.Member`; `CASCADE`; related_name=ไม่มี | ไม่มี |
| brs_role (91) | brs_role | CharField | max_length=10; null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=F; choices=`ROLE_CHOICES` | - | ไม่มี |
| brs_desc (92) | brs_desc | TextField | null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| brs_date (93) | brs_date | DateTimeField | null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |

### bookings.TutoringActivity

- Source: `apps/bookings/models.py:105`; Meta: `db_table='tutoring_activity'`; ไม่มี constraints

| Python field (บรรทัด) | db_column | Django field type | คุณสมบัติ | Relation | validators |
|---|---|---|---|---|---|
| bk_id (106) | bk_id | OneToOneField | null=F; blank=F; default=ไม่มี; PK=T; unique=T; index=T | `bookings.Booking`; `CASCADE`; related_name=ไม่มี | ไม่มี |
| ta_img1 (113) | ta_img1 | ImageField | max_length=100 (Django default); null=T; blank=T; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| ta_img2 (114) | ta_img2 | ImageField | max_length=100 (Django default); null=T; blank=T; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| ta_img3 (115) | ta_img3 | ImageField | max_length=100 (Django default); null=T; blank=T; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| ta_desc (116) | ta_desc | TextField | null=T; blank=T; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |

### bookings.JobCompletion

- Source: `apps/bookings/models.py:127`; Meta: `db_table='job_completion'`; ไม่มี constraints

| Python field (บรรทัด) | db_column | Django field type | คุณสมบัติ | Relation | validators |
|---|---|---|---|---|---|
| bk_id (128) | bk_id | OneToOneField | null=F; blank=F; default=ไม่มี; PK=T; unique=T; index=T | `bookings.Booking`; `CASCADE`; related_name=ไม่มี | ไม่มี |
| jc_complete_date (135) | jc_complete_date | DateTimeField | null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| jc_confirm_date (136) | jc_confirm_date | DateTimeField | null=T; blank=T; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |

### bookings.Review

- Source: `apps/bookings/models.py:147`; Meta: `db_table='review'`; ไม่มี constraints

| Python field (บรรทัด) | db_column | Django field type | คุณสมบัติ | Relation | validators |
|---|---|---|---|---|---|
| bk_id (148) | bk_id | OneToOneField | null=F; blank=F; default=ไม่มี; PK=T; unique=T; index=T | `bookings.Booking`; `CASCADE`; related_name=ไม่มี | ไม่มี |
| rv_quality (155) | rv_quality | IntegerField | null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| rv_knowledge (156) | rv_knowledge | IntegerField | null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| rv_communication (157) | rv_communication | IntegerField | null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| rv_punctuality (158) | rv_punctuality | IntegerField | null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| rv_satisfaction (159) | rv_satisfaction | IntegerField | null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| rv_cmt (160) | rv_cmt | TextField | null=T; blank=T; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| rv_date (161) | rv_date | DateTimeField | null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |

### messaging.Inbox

- Source: `apps/messaging/models.py:7`; Meta: `db_table='inbox'`
- Constraint: `unique_together=[['member1', 'member2']]` ที่ `apps/messaging/models.py:25`; ไม่มี `Meta.constraints` หรือ `Meta.indexes`

| Python field (บรรทัด) | db_column | Django field type | คุณสมบัติ | Relation | validators |
|---|---|---|---|---|---|
| ib_id (8) | ib_id | AutoField | null=F; blank=F; default=ไม่มี; PK=T; unique=T; index=T | - | ไม่มี |
| member1 (9) | member1_id (อัตโนมัติ) | ForeignKey | null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=T | `accounts.Member`; `CASCADE`; related_name=`inbox_as_member1` | ไม่มี |
| member2 (15) | member2_id (อัตโนมัติ) | ForeignKey | null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=T | `accounts.Member`; `CASCADE`; related_name=`inbox_as_member2` | ไม่มี |

### messaging.Message

- Source: `apps/messaging/models.py:44`; Meta: `db_table='message'`, ordering=`['msg_sent_time']`; ไม่มี constraints

| Python field (บรรทัด) | db_column | Django field type | คุณสมบัติ | Relation | validators |
|---|---|---|---|---|---|
| msg_id (45) | msg_id | AutoField | null=F; blank=F; default=ไม่มี; PK=T; unique=T; index=T | - | ไม่มี |
| msg_sent_time (46) | msg_sent_time | DateTimeField | auto_now_add=T; null=F; blank=T (กำหนดภายใน Django); default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| msg (47) | msg | TextField | null=F; blank=T; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| msg_img (48) | msg_img | ImageField | max_length=100 (Django default); null=T; blank=T; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| msg_is_read (54) | msg_is_read | IntegerField | null=F; blank=F; default=0; PK=F; unique=F; index=F | - | ไม่มี |
| sender (55) | sender_id (อัตโนมัติ) | ForeignKey | null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=T | `accounts.Member`; `CASCADE`; related_name=ไม่มี | ไม่มี |
| inbox (60) | inbox_id (อัตโนมัติ) | ForeignKey | null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=T | `messaging.Inbox`; `CASCADE`; related_name=ไม่มี | ไม่มี |

### credits.Refill

- Source: `apps/credits/models.py:7`; Meta: `db_table='refill'`; ไม่มี constraints

| Python field (บรรทัด) | db_column | Django field type | คุณสมบัติ | Relation | validators |
|---|---|---|---|---|---|
| rf_id (14) | rf_id | AutoField | null=F; blank=F; default=ไม่มี; PK=T; unique=T; index=T | - | ไม่มี |
| rf_date (15) | rf_date | DateTimeField | null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| rf_money (16) | rf_money | DecimalField | max_digits=7, decimal_places=2; null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| rf_credit (17) | rf_credit | IntegerField | null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| rf_slip (18) | rf_slip | ImageField | max_length=100 (Django default); null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| rf_qr_payload (19) | rf_qr_payload | CharField | max_length=255; null=T; blank=T; default=ไม่มี; PK=F; unique=T; index=T | - | ไม่มี |
| rf_confirm_date (20) | rf_confirm_date | DateTimeField | null=T; blank=T; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| rf_status (21) | rf_status | IntegerField | null=F; blank=F; default=0; PK=F; unique=F; index=F; choices=`STATUS_CHOICES` | - | ไม่มี |
| rf_cmt (22) | rf_cmt | TextField | null=T; blank=T; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| member (23) | member_id (อัตโนมัติ) | ForeignKey | null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=T | `accounts.Member`; `CASCADE`; related_name=ไม่มี | ไม่มี |

### credits.Withdrawals

- Source: `apps/credits/models.py:38`; Meta: `db_table='withdrawals'`; ไม่มี constraints

| Python field (บรรทัด) | db_column | Django field type | คุณสมบัติ | Relation | validators |
|---|---|---|---|---|---|
| wd_id (52) | wd_id | AutoField | null=F; blank=F; default=ไม่มี; PK=T; unique=T; index=T | - | ไม่มี |
| wd_req_date (53) | wd_req_date | DateTimeField | null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| wd_type (55) | wd_type | IntegerField | null=F; blank=F; default=0; PK=F; unique=F; index=F; choices=`TYPE_CHOICES` | - | ไม่มี |
| wd_credit (56) | wd_credit | IntegerField | null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| wd_cash (57) | wd_cash | DecimalField | max_digits=7, decimal_places=2; null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| wd_bank_name (58) | wd_bank_name | CharField | max_length=100; null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| wd_acc_name (59) | wd_acc_name | CharField | max_length=100; null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| wd_acc_no (60) | wd_acc_no | CharField | max_length=20; null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| wd_promptpay_no (61) | wd_promptpay_no | CharField | max_length=20; null=T; blank=T; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| wd_fee (62) | wd_fee | DecimalField | max_digits=7, decimal_places=2; null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| wd_net_cash (64) | wd_net_cash | DecimalField | max_digits=7, decimal_places=2; null=F; blank=F; default=0; PK=F; unique=F; index=F | - | ไม่มี |
| wd_paid_date (65) | wd_paid_date | DateTimeField | null=T; blank=T; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| wd_status (66) | wd_status | IntegerField | null=F; blank=F; default=0; PK=F; unique=F; index=F; choices=`STATUS_CHOICES` | - | ไม่มี |
| wd_cmt (67) | wd_cmt | TextField | null=T; blank=T; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| member (68) | member_id (อัตโนมัติ) | ForeignKey | null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=T | `accounts.Member`; `CASCADE`; related_name=ไม่มี | ไม่มี |

### notifications.Notification

- Source: `apps/notifications/models.py:7`; Meta: `db_table='notification'`, ordering=`['-notif_created_at']`; ไม่มี constraints
- `apps/notifications/apps.py:5` กำหนด implicit PK เป็น `BigAutoField`

| Python field (บรรทัด) | db_column | Django field type | คุณสมบัติ | Relation | validators |
|---|---|---|---|---|---|
| id (implicit) | id | BigAutoField | null=F; blank=F; default=ไม่มี; PK=T; unique=T; index=T | - | ไม่มี |
| recipient (30) | recipient_id (อัตโนมัติ) | ForeignKey | null=T; blank=T; default=ไม่มี; PK=F; unique=F; index=T | `accounts.Member`; `CASCADE`; related_name=`notifications` | ไม่มี |
| admin_recipient (38) | admin_recipient_id (อัตโนมัติ) | ForeignKey | null=T; blank=T; default=ไม่มี; PK=F; unique=F; index=T | `auth.User`; `CASCADE`; related_name=`notifications` | ไม่มี |
| notif_type (45) | notif_type | CharField | max_length=30; null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=F; choices=`TYPE_CHOICES` | - | ไม่มี |
| notif_text (46) | notif_text | CharField | max_length=255; null=F; blank=F; default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |
| notif_url (47) | notif_url | CharField | max_length=255; null=F; blank=T; default=`''`; PK=F; unique=F; index=F | - | ไม่มี |
| notif_is_read (48) | notif_is_read | BooleanField | null=F; blank=F; default=False; PK=F; unique=F; index=F | - | ไม่มี |
| notif_created_at (49) | notif_created_at | DateTimeField | auto_now_add=T; null=F; blank=T (กำหนดภายใน Django); default=ไม่มี; PK=F; unique=F; index=F | - | ไม่มี |

## Django User ที่ระบบอ้างอิง

- Model: `django.contrib.auth.models.User` (concrete class ที่สืบทอด `AbstractUser`)
- Meta.db_table: `auth_user`
- Primary key: `id`
- ระบบไม่ได้กำหนด `AUTH_USER_MODEL` และไม่มี custom user model
- อ้างอิงจาก `accounts.Member.user` (`apps/accounts/models.py:15`), `admin_panel.System.admin` (`apps/admin_panel/models.py:8`) และ `notifications.Notification.admin_recipient` (`apps/notifications/models.py:38`)
- ความสัมพันธ์ที่ใช้: OneToOneField/CASCADE, OneToOneField/SET_NULL และ ForeignKey/CASCADE ตามลำดับ

## Field ที่มี choices และการใช้งานในระบบ

### 1. `Member.mb_status`

นิยามที่ `apps/accounts/models.py:9-12,21`:

- 0 = ปิดการใช้งาน
- 1 = ใช้งานปกติ
- 2 = ระงับชั่วคราว

การใช้: forms ใช้ Model choices (`apps/accounts/forms.py:120-138`); views กรอง 1 เป็นสมาชิกใช้งาน (`apps/admin_panel/views.py:47,420-425`, `apps/messaging/views.py:46`); templates แสดง 0/1/2 ตามความหมาย (`templates/accounts/profile.html:34-44`, `templates/admin_panel/member_mgmt.html:168-175`) จึงสอดคล้องภายในระบบ

### 2. `Tutor.tut_has_exp`

นิยามที่ `apps/accounts/models.py:47-50,62`:

- 0 = ไม่เคยสอน
- 1 = เคยสอน

การใช้: forms ใช้ Model choices (`apps/accounts/forms.py:165-177`); views รับค่า 0/1 (`apps/tutoring/views.py:454,521,543`); templates ใช้ radio 0/1 และแสดงมี/ไม่มีประสบการณ์ (`templates/tutoring/tutor_profile_edit.html:153-165`, `templates/tutoring/tutor_manage.html:183`) จึงสอดคล้อง

### 3. `Tutor.tut_status`

นิยามที่ `apps/accounts/models.py:41-46,75`:

- 0 = รอการตรวจสอบ
- 1 = อนุมัติแล้ว
- 2 = ปฏิเสธ
- 3 = ระงับการสอน

การใช้: forms ใช้ Model choices (`apps/accounts/forms.py:186-191`); admin เปลี่ยนค่า 1/2/3 และปลดระงับกลับ 1 (`apps/admin_panel/views.py:249-269`); views จำกัดผู้สอนที่อนุมัติด้วยค่า 1 และให้ 0/3 เป็น view-only (`apps/tutoring/views.py:558,574,595,610`); templates แสดงครบ 0-3 (`templates/tutoring/register_tutor.html:91-106`) จึงสอดคล้อง

### 4. `TutorCourse.tutc_status`

นิยามที่ `apps/tutoring/models.py:9-12,19`:

- 0 = ปิดรับสอน
- 1 = เปิดรับสอน

การใช้: forms ใช้ Model choices (`apps/tutoring/forms.py:39-53`); views และ templates ใช้ 0/1 ตามปิด/เปิด (`apps/tutoring/views.py:662,959-962`, `templates/tutoring/tutor_course_list.html:54-125`) จึงสอดคล้อง

### 5. `TimeSlot.ts_status`

นิยามที่ `apps/tutoring/models.py:86-89,94-98`:

- 0 = ว่าง
- 1 = ล็อกแล้ว

การใช้: views เลือกจองได้เมื่อ 0, เปลี่ยนเป็น 1 เมื่อล็อก และคืนเป็น 0 เมื่อปล่อย slot (`apps/tutoring/views.py:185-197,271,290`, `apps/bookings/views.py:173-174,199-200,317`) จึงสอดคล้อง

### 6. `Booking.bk_status`

นิยามที่ `apps/bookings/models.py:9-17,26`:

- 0 = จอง
- 1 = รับงานแล้ว
- 2 = เรียนแล้ว
- 3 = แจ้งจบงาน
- 4 = ยืนยันการจบงาน
- 5 = รีวิวแล้ว
- 6 = ปฏิเสธ

การใช้ workflow ใน views ครบ 0-6 (`apps/bookings/views.py:253-258,284-377,432-562`) และตรงตามลำดับสถานะ แต่ข้อความฝั่งผู้เรียนใช้ถ้อยคำตามบริบทต่างจาก label ของ Model: 0 “จองแล้ว”, 1 “อนุมัติแล้ว”, 3 “ยืนยันจบงาน”, 4 “เสร็จสิ้น”, 6 “ติวเตอร์ปฏิเสธ” (`templates/bookings/student_bookings.html:196-210`) ค่าตัวเลขยังสอดคล้อง แต่ label ไม่ตรงตัวอักษรทุกค่า

### 7. `Booking.bk_report_reason`

นิยามที่ `apps/bookings/models.py:28-35`:

- `'1'` = หลักฐานการสอนไม่ตรงความจริง
- `'2'` = ไม่ได้สอนเลยแต่แจ้งจบงาน
- `'3'` = เนื้อหาไม่ตรงที่ตกลงไว้
- `'4'` = ผู้เรียนกดยืนยันโดยไม่ตั้งใจ
- `'other'` = อื่นๆ

การใช้เพิ่มเติมใน `apps/bookings/views.py:19-45,186-188`: views ยอมรับ `'5'`, `'6'`, `'7'`, `'8'`, `'t_no_show'`, `'s_no_show'`, `'contact'`, `'cannot_contact'`, `'agree'`, `'cancel'` และ normalize alias บางค่าเป็น 2/5/6/7/8; templates ส่งค่า 5-8 (`templates/bookings/tutor_requests.html:1079-1091`) และ 2/6/7/8 (`templates/bookings/student_bookings.html:942-954`) รวมทั้งแสดงค่าพิเศษเหล่านี้ (`templates/admin_panel/report_mgmt.html:258-266`) จึง **ไม่สอดคล้องกับ choices ของ Model** เพราะมีค่าที่ระบบใช้งานแต่ไม่มีใน `REPORT_REASON_CHOICES`

### 8. `BookingReportStatement.brs_role`

นิยามที่ `apps/bookings/models.py:72-75,91`:

- `'student'` = Student
- `'tutor'` = Tutor

การใช้: views บันทึก role ลง field (`apps/bookings/views.py:224`); templates ตรวจ `'tutor'` และใช้อีกกรณีเป็นผู้เรียน (`templates/admin_panel/tutor_mgmt_detail.html:179`, `templates/bookings/tutor_requests.html:730`) จึงสอดคล้องด้านค่า แม้ label ใน Model เป็นภาษาอังกฤษและ UI แปลไทย

### 9. `Refill.rf_status`

นิยามที่ `apps/credits/models.py:8-12,21`:

- 0 = รอตรวจสอบ
- 1 = ผ่านการตรวจสอบ
- 2 = ไม่ผ่านการตรวจสอบ

การใช้: forms ใช้ Model choices (`apps/credits/forms.py:26-32`); admin เปลี่ยน 0→1/2 (`apps/admin_panel/views.py:327-363`); views/templates และ signals ใช้ความหมายเดียวกัน (`apps/credits/views.py:104-115`, `apps/notifications/signals.py:176-194`, `templates/admin_panel/dashboard.html:198-211`) จึงสอดคล้อง

### 10. `Withdrawals.wd_type`

นิยามที่ `apps/credits/models.py:40-43,55`:

- 0 = นำฝาก
- 1 = รายได้

การใช้: แบบฟอร์มหน้าเว็บส่ง 0/1 (`templates/credits/withdraw.html:192-209`); views เลือกยอดและค่าธรรมเนียมโดย 1=รายได้ มิฉะนั้น=นำฝาก (`apps/credits/views.py:406-451`); admin ใช้ 1 เพื่อคืน/หักเครดิตรายได้ (`apps/admin_panel/views.py:474`) จึงสอดคล้อง

### 11. `Withdrawals.wd_status`

นิยามที่ `apps/credits/models.py:45-50,66`:

- 0 = รอดำเนินการ
- 1 = จ่ายแล้ว
- 2 = ปฏิเสธการถอน
- 3 = ยกเลิกโดยผู้ใช้

การใช้: forms ใช้ Model choices (`apps/credits/forms.py:61-67`); admin เปลี่ยน 0→1/2 (`apps/admin_panel/views.py:465-509`); ผู้ใช้ยกเลิกได้เฉพาะ 0 และเปลี่ยนเป็น 3 (`apps/credits/views.py:214-220`); template แสดง 0/1/3 และ fallback ครอบคลุมค่า 2 (`templates/admin_panel/payment_mgmt.html:309-321`) จึงสอดคล้อง

### 12. `Notification.notif_type`

นิยามที่ `apps/notifications/models.py:9-27,45`:

- `'booking_new'` = มีการจองติวใหม่
- `'booking_accepted'` = การจองได้รับการยืนยัน
- `'booking_rejected'` = การจองถูกปฏิเสธ
- `'booking_completed'` = มีการแจ้งจบงานที่ต้องยืนยัน
- `'booking_credited'` = งานเสร็จสิ้น ได้รับเครดิตแล้ว
- `'booking_reviewed'` = มีรีวิวใหม่
- `'booking_reported'` = มีการรายงานปัญหา
- `'tutor_approved'` = ติวเตอร์ได้รับการอนุมัติ
- `'tutor_rejected'` = ติวเตอร์ถูกปฏิเสธ
- `'tutor_suspended'` = บัญชีติวเตอร์ถูกระงับ
- `'refill_approved'` = เติมเครดิตผ่านการตรวจสอบ
- `'refill_rejected'` = เติมเครดิตไม่ผ่านการตรวจสอบ
- `'withdraw_paid'` = ถอนเงินเข้าบัญชีเรียบร้อย
- `'admin_refill'` = มีคำขอเติมเครดิต
- `'admin_withdraw'` = มีคนขอถอนเครดิต
- `'admin_tutor_new'` = มีติวเตอร์สมัครใหม่รอ approve
- `'admin_reported'` = มีการรายงานปัญหา

การใช้: signals ใช้ค่าที่ประกาศส่วนใหญ่ (`apps/notifications/signals.py:76-121,145-159,182-194,217-230`) และ views ใช้ `booking_reported`, `booking_completed`, `booking_rejected`, `booking_credited`, `tutor_approved` ที่มีใน choices อย่างสอดคล้อง อย่างไรก็ตาม `apps/notifications/signals.py:108` สร้างค่า `'booking_cancelled'` = “ผู้เรียนยกเลิกการจองของคุณ” ซึ่ง **ไม่มีใน `TYPE_CHOICES`** จึงไม่สอดคล้องครบทุกค่าที่ใช้งาน

## Field สถานะที่ไม่ได้ประกาศ choices

- `messaging.Message.msg_is_read` (`apps/messaging/models.py:54`) เป็น IntegerField, default=0; verbose_name ระบุ 0=ยังไม่อ่าน, 1=อ่านแล้ว แต่ไม่ได้ผูก `choices`
- `notifications.Notification.notif_is_read` (`apps/notifications/models.py:48`) เป็น BooleanField, default=False; ใช้ False=ยังไม่อ่าน และ True=อ่านแล้วตามชนิด BooleanField แต่ไม่ได้ผูก `choices`

## Constraints และ validators รวม

- Custom validators (`validators=`): ไม่พบใน Model ทั้งหมด
- `Meta.constraints`: ไม่พบ
- `Meta.indexes`: ไม่พบ
- `unique_together`: พบเฉพาะ `messaging.Inbox(member1, member2)` ที่ `apps/messaging/models.py:25`
- Field-level `unique=True`: `credits.Refill.rf_qr_payload`
- Relation, primary key และ unique field มีดัชนีตามพฤติกรรมมาตรฐานของ Django ตามที่ระบุในแต่ละตาราง

## สรุปผลการสำรวจ

- Model ที่โครงการประกาศเอง: **21 Model**
- Model ภายนอกที่อ้างอิงโดยตรง: **1 Model (`auth.User`)**
- Field ของ Model ที่โครงการประกาศเอง: **153 field**
- Field ที่มี `choices`: **12 field**
- ความไม่สอดคล้องภายในระบบที่พบระหว่าง choices กับค่าที่ใช้งาน:
  - `Booking.bk_report_reason`: ระบบใช้งานค่ามากกว่าที่ประกาศใน Model choices
  - `Notification.notif_type`: มีการสร้างค่า `'booking_cancelled'` ซึ่งไม่มีใน Model choices
- รายงานนี้เป็น inventory ของโครงสร้าง Model และการใช้ choices เท่านั้น ยังไม่ได้เปรียบเทียบความตรงกันกับ Data Dictionary
