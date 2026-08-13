# รายงานเปรียบเทียบ Django Models กับ Data Dictionary แบบรายฟิลด์

## โครงการ

**การพัฒนาระบบเว็บแอปพลิเคชันเพื่อนช่วยติว**  
**DEVELOPMENT OF WEB APPLICATION SYSTEM FOR “PUEAN CHUAY TU”**

## 1. สรุปภาพรวม

### ขอบเขตและเกณฑ์

- ตรวจ Data Dictionary ต้นฉบับ PDF หน้า 1-14, Markdown ที่ถอดจาก PDF, Model จริงทั้ง 21 Model และการใช้ค่าใน forms, views, templates, JavaScript, signals, constants และ tests
- PDF ระบุข้อความว่า “ประกอบด้วย 19 ตาราง” (`docs/Data Dictionary เพื่อนช่วยติว0608.pdf` หน้า 2) แต่รายการจริงจับคู่กับ Django ได้ 21 ตาราง/Model (`docs/Data Dictionary เพื่อนช่วยติว0608.md:17-358`)
- เปรียบเทียบแบบเคร่งครัด: ชื่อ field, DB column, Type, Size, PK/FK/O2O, target, `on_delete`, `related_name`, choices และความหมายต้องสอดคล้อง ไม่ถือว่าตรงเพียงเพราะฐานข้อมูลพอเก็บค่าได้
- Data Dictionary ไม่กำหนด `null`, `blank`, `default`, `unique`, `db_index`, validators และ constraints เป็นส่วนใหญ่ จึงบันทึกค่าฝั่ง Django แต่ไม่ตัดสินว่าไม่ตรงจากการไม่ระบุเพียงอย่างเดียว
- สถานะ “ตรงทั้งหมด” หมายถึงทุก field ที่ Data Dictionary ระบุจับคู่ได้และคุณสมบัติที่ระบุตรงกัน; “ตรงบางส่วน” หมายถึงยังจับคู่ Model ได้แต่มีอย่างน้อยหนึ่ง field ไม่ตรง/ขาด/เกิน/กำกวม

### จำนวนผลลัพธ์

| รายการ | จำนวน |
|---|---:|
| ตารางที่ Data Dictionary กล่าวอ้างในเนื้อความ | 19 |
| ตาราง/หัวข้อที่ปรากฏจริงและจับคู่ Model ได้ | 21 |
| Model ที่จับคู่ได้ | 21 |
| ตารางที่ตรงทั้งหมด | 6 |
| ตารางที่ตรงบางส่วน | 15 |
| ตารางที่ไม่สามารถจับคู่ Model ได้ | 0 |
| Field ฝั่ง Data Dictionary | 153 |
| Field ฝั่ง Django | 153 |
| แถวเปรียบเทียบแบบ union | 157 |
| Field ตรง | 109 |
| Field ไม่ตรง | 36 |
| Field ที่ Data Dictionary ระบุแต่ไม่มีในระบบ | 4 |
| Field ที่มีใน Django แต่ไม่มีใน Data Dictionary | 4 |
| Field กำกวม | 4 |
| Field ตรวจไม่ได้ | 0 |
| Field ที่ประกาศ `choices` ใน Django | 12 |
| ปัญหา choices หลัก | 4 ประเภท: type ต่าง, label ต่าง, DD ไม่แจกแจง, runtime ใช้ค่านอก Model choices |
| ปัญหา Type/Size หลัก | `TINYINT(1)` เทียบ `IntegerField/BooleanField`, ImageField ความยาว 100 เทียบ VARCHAR(255), DECIMAL precision, FK อ้าง PK คนละชนิด, BigAutoField เทียบ INT |
| ปัญหา PK/FK หลัก | Member ID, Tutor PK/FK และ FK ที่อ้าง Member/Tutor ใช้ INT จริง แต่ DD ระบุ VARCHAR(13); Notification ใช้ BigAutoField แต่ DD ระบุ INT |

ตารางที่ตรงทั้งหมด: `Faculty`, `CourseGroup`, `Course`, `TutorRate`, `ScheduleDate`, `JobCompletion`  
ตารางที่ตรงบางส่วน: `System`, `Major`, `Member`, `Tutor`, `TutorCourse`, `TimeSlot`, `Refill`, `Booking`, `Inbox`, `Message`, `TutoringActivity`, `Review`, `Withdrawals`, `BookingReportStatement`, `Notification`

## 2. ตารางเปรียบเทียบรายฟิลด์

คำย่อในตาราง: `N`=`null`, `B`=`blank`, `D`=`default`, `U`=`unique`, `I`=`db_index`, `PK`=`primary_key`; `F`=False, `T`=True, `—`=ไม่ได้กำหนด/ไม่มี ค่า `I=T*` หมายถึงมี index โดยธรรมชาติของ PK/FK/unique แม้ไม่ได้เขียน `db_index=True` โดยตรง ทุก field ไม่มี custom `validators=` เว้นแต่ระบุ และทุก Model ไม่มี `Meta.constraints`/`Meta.indexes` เว้น `Inbox.unique_together` ที่ระบุในรายละเอียด

คำอ้างอิง `DD md:<บรรทัด>` ในตารางหมายถึง `docs/Data Dictionary เพื่อนช่วยติว0608.md:<บรรทัด>`; คำว่า `model:<บรรทัด>` หมายถึงไฟล์ Model ของ Model ในแถวนั้นตาม path ที่แสดงในส่วนรายงานแยกตาม Model

| ลำดับ | DD Table | Django Model | DD Field | Django Field | DB Column | DD Type/Size | Django Type/Options | DD Choices | Django Choices | Default | Key/Relation | สถานะ | รายละเอียดปัญหา | หลักฐานไฟล์และบรรทัด |
|---:|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | System | System | uni_name | uni_name | uni_name | VARCHAR(100) | CharField(max_length=100; N=F; B=F; U=F; I=F) | - | - | — | - | ตรง | ชื่อ/ชนิด/ขนาดตรง | DD md:27; `apps/admin_panel/models.py:16` |
| 2 | System | System | bank_name | bank_name | bank_name | VARCHAR(100) | CharField(max_length=100; N=F; B=F; U=F; I=F) | - | - | — | - | ตรง | ตรง | DD md:28; model:17 |
| 3 | System | System | acc_name | acc_name | acc_name | VARCHAR(100) | CharField(max_length=100; N=F; B=F; U=F; I=F) | - | - | — | - | ตรง | ตรง | DD md:29; model:19 |
| 4 | System | System | acc_no | acc_no | acc_no | VARCHAR(20) | CharField(max_length=20; N=F; B=F; U=F; I=F) | - | - | — | - | ตรง | ตรง | DD md:30; model:20 |
| 5 | System | System | promptpay_id | promptpay_id | promptpay_id | VARCHAR(20) | CharField(max_length=20; N=F; B=T; U=F; I=F) | - | - | `''` | - | ตรง | DD ทำเครื่องหมาย “เพิ่ม”; Type/Size ตรง | DD md:31; model:21 |
| 6 | System | System | crd_val | crd_val | crd_val | DECIMAL(5,2) | DecimalField(max_digits=5; decimal_places=2; N=F; B=F) | - | - | — | - | ตรง | precision/scale ตรง | DD md:32; model:22 |
| 7 | System | System | deposit_withdraw_fee_pct | deposit_withdraw_fee_pct | deposit_withdraw_fee_pct | DECIMAL(5,2) | DecimalField(5,2; N=F; B=F) | - | - | — | - | ตรง | ตรง | DD md:33; model:23 |
| 8 | System | System | income_withdraw_fee_pct | income_withdraw_fee_pct | income_withdraw_fee_pct | DECIMAL(5,2) | DecimalField(5,2; N=F; B=F) | - | - | — | - | ตรง | ตรง | DD md:34; model:24 |
| 9 | System | System | total_accumulated_fee | total_accumulated_fee | total_accumulated_fee | DECIMAL(5,2) | DecimalField(10,2; N=F; B=F) | - | - | 0.00 | - | ไม่ตรง | max_digits 5 กับ 10 ไม่ตรง | DD md:35; model:25 |
| 10 | System | System | admin_pwd | - | - | VARCHAR(255) | - | - | - | - | - | ไม่มีในระบบ | ไม่มี DB field ใน System; รหัสผ่านอยู่ใน `auth.User.password` ไม่ใช่ `admin_pwd` | DD md:36; `apps/admin_panel/models.py:8-14`; `django.contrib.auth.models.User` |
| 11 | System | System | admin_email | - | - | VARCHAR(255) | - | - | - | - | - | ไม่มีในระบบ | มีเพียง property `admin_email`; email จริงอยู่ `auth.User.email` และไม่ใช่ column ใน `system` | DD md:37; `apps/admin_panel/models.py:38-40` |
| 12 | System | System | email_domain | email_domain | email_domain | VARCHAR(100) | CharField(max_length=100; N=F; B=F) | - | - | `'rmuti.ac.th'` | - | ตรง | DD ไม่ระบุ default | DD md:38; model:18 |
| 13 | System | System | - | id | id | - | AutoField(N=F; PK=T; U=T; I=T*) | - | - | auto | PK | ไม่มีใน Data Dictionary | Django สร้าง PK อัตโนมัติ | `apps/admin_panel/models.py:7,27-29`; inventory:57-75 |
| 14 | System | System | - | admin | admin_id | - | OneToOneField(N=T; B=T; U=T; I=T*) | - | - | — | O2O→`auth.User`; SET_NULL; related_name=`system` | ไม่มีใน Data Dictionary | DD แยกรหัสผ่าน/อีเมล แต่ไม่ระบุ relation นี้ | `apps/admin_panel/models.py:8-14` |
| 15 | Faculty | Faculty | fac_id | fac_id | fac_id | INT | AutoField(PK=T; U=T; I=T*) | - | - | auto | PK | ตรง | INT PK สอดคล้องกับ AutoField | DD md:46; `apps/courses/models.py:7` |
| 16 | Faculty | Faculty | fac_name | fac_name | fac_name | VARCHAR(100) | CharField(max_length=100; N=F; B=F) | - | - | — | - | ตรง | ตรง | DD md:47; model:8 |
| 17 | Major | Major | mj_id | mj_id | mj_id | INT | AutoField(PK=T; U=T; I=T*) | - | - | auto | PK | ตรง | ตรง | DD md:57; `apps/courses/models.py:20` |
| 18 | Major | Major | mj_name | mj_name | mj_name | VARCHAR(100) | CharField(max_length=100) | - | - | — | - | ตรง | ตรง | DD md:58; model:21 |
| 19 | Major | Major | mj_abbr | mj_abbr | mj_abbr | VARCHAR(10) | CharField(max_length=10; N=F; B=F) | - | - | — | - | กำกวม | โครงสร้างตรง แต่ DD มีหมายเหตุสีแดง “ตัดออก” ขณะที่ field ยังอยู่จริง | DD md:59 (PDF หน้า 3); model:22 |
| 20 | Major | Major | mj_desc | mj_desc | mj_desc | TEXT | TextField(N=T; B=T) | - | - | — | - | ตรง | DD ไม่กำหนด null/blank | DD md:60; model:23 |
| 21 | Major | Major | fac_id | fac_id | fac_id | INT | ForeignKey(N=F; B=F; I=T*) | - | - | — | FK→Faculty; CASCADE; related_name=—; target PK=AutoField/INT | ตรง | ชนิด FK ตาม target PK ตรง | DD md:61; model:24-29 |
| 22 | Course Group | CourseGroup | cg_id | cg_id | cg_id | INT | AutoField(PK=T; U=T; I=T*) | - | - | auto | PK | ตรง | ตรง | DD md:69; `apps/courses/models.py:41` |
| 23 | Course Group | CourseGroup | cg_name | cg_name | cg_name | VARCHAR(100) | CharField(max_length=100) | - | - | — | - | ตรง | ตรง | DD md:70; model:42 |
| 24 | Course Group | CourseGroup | cg_desc | cg_desc | cg_desc | TEXT | TextField(N=T; B=T) | - | - | — | - | ตรง | ตรงตามคุณสมบัติที่ DD ระบุ | DD md:71; model:43 |
| 25 | Course | Course | crs_id | crs_id | crs_id | VARCHAR(13) | CharField(max_length=13; PK=T; U=T; I=T*) | - | - | — | PK | ตรง | ตรง | DD md:79; `apps/courses/models.py:55` |
| 26 | Course | Course | crs_name | crs_name | crs_name | VARCHAR(150) | CharField(max_length=150) | - | - | — | - | ตรง | ตรง | DD md:80; model:56 |
| 27 | Course | Course | crs_desc | crs_desc | crs_desc | TEXT | TextField(N=T; B=T) | - | - | — | - | ตรง | ตรง | DD md:81; model:57 |
| 28 | Course | Course | cg_id | cg_id | cg_id | INT | ForeignKey(N=F; I=T*) | - | - | — | FK→CourseGroup; CASCADE; related_name=—; target PK=INT | ตรง | ตรง | DD md:82; model:58-63 |
| 29 | Member | Member | mb_id | id | id | VARCHAR(13) | AutoField(PK=T; U=T; I=T*) | - | - | auto | PK | ไม่ตรง | ชื่อ, Type และ Size ไม่ตรง: DD เป็นรหัสข้อความ แต่ Django เป็นเลขอัตโนมัติ | DD md:92; `apps/accounts/models.py:8,31-33` |
| 30 | Member | Member | mb_full_name | mb_full_name | mb_full_name | VARCHAR(100) | CharField(max_length=100) | - | - | — | - | ตรง | ตรง | DD md:93; model:16 |
| 31 | Member | Member | mb_email | mb_email | mb_email | VARCHAR(50) | CharField(max_length=50; U=F) | - | - | — | - | ตรง | Type/Size ตรง; DD ไม่ระบุ unique | DD md:94; model:17 |
| 32 | Member | Member | mb_pwd | - | - | VARCHAR(255) | - | - | - | - | - | ไม่มีในระบบ | รหัสผ่านอยู่ `auth.User.password` ผ่าน relation `user`; ไม่ใช่ field ของ Member และขนาดมาตรฐานไม่ใช่ 255 | DD md:95; model:15 |
| 33 | Member | Member | mb_img | mb_img | mb_img | VARCHAR(100) | ImageField(max_length=100; N=T; B=T; DB เป็น VARCHAR) | - | - | — | - | ตรง | Django type เฉพาะไฟล์ แต่ DB column/ความยาวและความหมายชื่อไฟล์ตรง | DD md:96; model:18 |
| 34 | Member | Member | mb_deposit_crd | mb_deposit_crd | mb_deposit_crd | INT | IntegerField(N=F; B=F) | - | - | 0 | - | ตรง | DD ไม่ระบุ default | DD md:97; model:19 |
| 35 | Member | Member | mb_income_crd | mb_income_crd | mb_income_crd | INT | IntegerField(N=F; B=F) | - | - | 0 | - | ตรง | ตรง | DD md:98; model:20 |
| 36 | Member | Member | mb_status | mb_status | mb_status | TINYINT(1) | IntegerField(N=F; B=F) | 0=ปิดการใช้งาน<br>1=ใช้งานปกติ<br>2=ระงับชั่วคราว | 0=ปิดการใช้งาน<br>1=ใช้งานปกติ<br>2=ระงับชั่วคราว | 1 | - | ไม่ตรง | choices/ความหมายตรง แต่ field type เป็น IntegerField ไม่ใช่ TINYINT(1) | DD md:99; `apps/accounts/models.py:9-13,21`; usages `apps/admin_panel/views.py:47,420-425` |
| 37 | Member | Member | mb_locked_crd | mb_locked_crd | mb_locked_crd | INT | IntegerField(N=F; B=F) | - | - | 0 | - | ตรง | ตรง | DD md:100; model:22 |
| 38 | Member | Member | mj_id | mj_id | mj_id | INT | ForeignKey(N=T; B=F; I=T*) | - | - | — | FK→Major; SET_NULL; related_name=—; target PK=INT | ตรง | Relation/ชนิด target ตรง; DD ไม่ระบุ nullable | DD md:101; model:23-29 |
| 39 | Member | Member | - | user | user_id | - | OneToOneField(N=F; B=F; U=T; I=T*) | - | - | — | O2O→`auth.User`; CASCADE; related_name=`member` | ไม่มีใน Data Dictionary | เป็นโครงสร้างบัญชีผู้ใช้จริง | `apps/accounts/models.py:3,15` |
| 40 | Tutor | Tutor | tut_id | tut_id | tut_id | VARCHAR(13) | OneToOneField(PK=T; U=T; I=T*) | - | - | — | PK/O2O→Member; CASCADE; related_name=—; target PK=AutoField/INT | ไม่ตรง | Key relation ตรงแนวคิด แต่ชนิดจริงเป็น INT ตาม `Member.id`, ไม่ใช่ VARCHAR(13) | DD md:111; `apps/accounts/models.py:52-58`; Member model:8,31-33 |
| 41 | Tutor | Tutor | tut_desc | tut_desc | tut_desc | TEXT | TextField(N=T; B=T) | - | - | — | - | ตรง | ตรง | DD md:112; model:59 |
| 42 | Tutor | Tutor | tut_skill | tut_skill | tut_skill | TEXT | TextField(N=T; B=T) | - | - | — | - | ตรง | ตรง | DD md:113; model:60 |
| 43 | Tutor | Tutor | tut_gpax | tut_gpax | tut_gpax | DECIMAL(3,2) | DecimalField(3,2; N=F; B=F) | - | - | — | - | ตรง | ตรง | DD md:114; model:61 |
| 44 | Tutor | Tutor | tut_student_card | tut_student_card | tut_student_card | VARCHAR(100) | ImageField(max_length=100; N=T; B=T; DB เป็น VARCHAR) | - | - | — | - | ตรง | DD ทำเครื่องหมายเพิ่ม; DB Type/Size และความหมายตรง | DD md:115; model:78-82 |
| 45 | Tutor | Tutor | tut_has_exp | tut_has_exp | tut_has_exp | TINYINT(1) | IntegerField(N=F; B=F) | 0=ไม่เคยสอน<br>1=เคยสอน | 0=ไม่เคยสอน<br>1=เคยสอน | 0 | - | ไม่ตรง | choices ตรง แต่ Django type ไม่ใช่ TINYINT(1) | DD md:116; `apps/accounts/models.py:47-50,62`; `apps/tutoring/views.py:454,521` |
| 46 | Tutor | Tutor | tut_exp_desc | tut_exp_desc | tut_exp_desc | TEXT | TextField(N=T; B=T) | - | - | — | - | ตรง | ตรง | DD md:117; model:63 |
| 47 | Tutor | Tutor | tut_rating | tut_rating | tut_rating | DECIMAL(3,2) | DecimalField(3,2) | - | - | 0 | - | ตรง | ตรง | DD md:118; model:66 |
| 48 | Tutor | Tutor | tut_rating_quality | tut_rating_quality | tut_rating_quality | DECIMAL(3,2) | DecimalField(3,2) | - | - | 0 | - | ตรง | ตรง | DD md:119; model:69 |
| 49 | Tutor | Tutor | tut_rating_knowledge | tut_rating_knowledge | tut_rating_knowledge | DECIMAL(3,2) | DecimalField(3,2) | - | - | 0 | - | ตรง | ตรง | DD md:120; model:70 |
| 50 | Tutor | Tutor | tut_rating_communication | tut_rating_communication | tut_rating_communication | DECIMAL(3,2) | DecimalField(3,2) | - | - | 0 | - | ตรง | ตรง | DD md:121; model:71 |
| 51 | Tutor | Tutor | tut_rating_punctuality | tut_rating_punctuality | tut_rating_punctuality | DECIMAL(3,2) | DecimalField(3,2) | - | - | 0 | - | ตรง | ตรง | DD md:122; model:72 |
| 52 | Tutor | Tutor | tut_rating_satisfaction | tut_rating_satisfaction | tut_rating_satisfaction | DECIMAL(3,2) | DecimalField(3,2) | - | - | 0 | - | ตรง | ตรง | DD md:123; model:73 |
| 53 | Tutor | Tutor | tut_status | tut_status | tut_status | TINYINT(1) | IntegerField(N=F; B=F) | 0=ยังไม่อนุมัติ<br>1=อนุมัติแล้ว<br>2=ปฏิเสธ<br>3=ระงับการสอน | 0=รอการตรวจสอบ<br>1=อนุมัติแล้ว<br>2=ปฏิเสธ<br>3=ระงับการสอน | 0 | - | ไม่ตรง | ค่า 0 มีเจตนา workflow เดียวกัน (ก่อนอนุมัติ/รอตรวจ) แต่ข้อความไม่ตรง; Type ก็ไม่ตรง TINYINT | DD md:124; `apps/accounts/models.py:41-46,75`; `apps/admin_panel/views.py:210-269` |
| 54 | Tutor | Tutor | tut_reject_note | tut_reject_note | tut_reject_note | TEXT | TextField(N=T; B=T) | - | - | — | - | ตรง | DD ทำเครื่องหมายเพิ่ม; ตรง | DD md:125; model:85-88 |
| 55 | Tutor Course | TutorCourse | tutc_id | tutc_id | tutc_id | VARCHAR(13) | CharField(max_length=13; PK=T) | - | - | — | PK | ตรง | ตรง | DD md:135; `apps/tutoring/models.py:14` |
| 56 | Tutor Course | TutorCourse | tutc_name | tutc_name | tutc_name | VARCHAR(150) | CharField(max_length=150) | - | - | — | - | ตรง | ตรง | DD md:136; model:15 |
| 57 | Tutor Course | TutorCourse | tutc_desc | tutc_desc | tutc_desc | TEXT | TextField(N=T; B=T) | - | - | — | - | ตรง | DD ทำเครื่องหมายเพิ่ม; ตรง | DD md:137; model:16 |
| 58 | Tutor Course | TutorCourse | tutc_img | tutc_img | tutc_img | VARCHAR(100) | ImageField(max_length=100; N=T; B=T; DB เป็น VARCHAR) | - | - | — | - | ตรง | DB Type/Size และความหมายตรง | DD md:138; model:17 |
| 59 | Tutor Course | TutorCourse | tutc_max_stu | tutc_max_stu | tutc_max_stu | INT | IntegerField(N=F; B=F) | - | - | — | - | ตรง | ตรง | DD md:139; model:18 |
| 60 | Tutor Course | TutorCourse | tutc_status | tutc_status | tutc_status | TINYINT(1) | IntegerField(N=F; B=F) | 0=ปิดรับสอน<br>1=เปิดรับสอน | 0=ปิดรับสอน<br>1=เปิดรับสอน | 1 | - | ไม่ตรง | choices ตรง แต่ field type ไม่ตรง | DD md:140; `apps/tutoring/models.py:9-12,19`; views:662,959-962 |
| 61 | Tutor Course | TutorCourse | tutc_rating | tutc_rating | tutc_rating | PDF ไม่ระบุ; Markdown เติม DECIMAL(3,2) จากระบบ | DecimalField(3,2; N=F; B=F) | - | - | 0 | - | กำกวม | PDF มีเพียง “รีวิวแยกตามรายวิชาที่เปิดสอน” ไม่มี Attribute/Type/Size; ค่าใน Markdown มาจาก Model จึงไม่ใช่ข้อกำหนด DD อิสระ | DD PDF หน้า 6; DD md:141; `apps/tutoring/models.py:20` |
| 62 | Tutor Course | TutorCourse | crs_id | crs_id | crs_id | VARCHAR(13) | ForeignKey(N=F; I=T*) | - | - | — | FK→Course; CASCADE; related_name=—; target PK=VARCHAR(13) | ตรง | ตรง | DD md:142; model:21-26; `apps/courses/models.py:55` |
| 63 | Tutor Course | TutorCourse | tut_id | tut_id | tut_id | VARCHAR(13) | ForeignKey(N=F; I=T*) | - | - | — | FK→Tutor; CASCADE; related_name=—; target PK=INT | ไม่ตรง | DD ระบุ VARCHAR(13) แต่ Tutor PK จริงเป็น O2O ไป Member.id แบบ INT | DD md:143; `apps/tutoring/models.py:27-32`; `apps/accounts/models.py:52-58` |
| 64 | Tutor Rate | TutorRate | tut_rate_id | tut_rate_id | tut_rate_id | INT | AutoField(PK=T; U=T; I=T*) | - | - | auto | PK | ตรง | ตรง | DD md:151; `apps/tutoring/models.py:44` |
| 65 | Tutor Rate | TutorRate | tut_rate_per_person | tut_rate_per_person | tut_rate_per_person | INT | IntegerField(N=F; B=F) | - | - | — | - | ตรง | ตรง | DD md:152; model:45 |
| 66 | Tutor Rate | TutorRate | tut_rate_stu_count | tut_rate_stu_count | tut_rate_stu_count | INT | IntegerField(N=F; B=F) | - | - | — | - | ตรง | ตรง | DD md:153; model:46 |
| 67 | Tutor Rate | TutorRate | tutc_id | tutc_id | tutc_id | VARCHAR(13) | ForeignKey(N=F; I=T*) | - | - | — | FK→TutorCourse; CASCADE; related_name=—; target PK=VARCHAR(13) | ตรง | ตรง | DD md:154; model:47-52 |
| 68 | ScheduleDate | ScheduleDate | sd_id | sd_id | sd_id | INT | AutoField(PK=T; U=T; I=T*) | - | - | auto | PK | ตรง | ตรง | DD md:164; `apps/tutoring/models.py:64` |
| 69 | ScheduleDate | ScheduleDate | sd_date | sd_date | sd_date | DATE | DateField(N=F; B=F) | - | - | — | - | ตรง | ตรง | DD md:165; model:65 |
| 70 | ScheduleDate | ScheduleDate | tutc_id | tutc_id | tutc_id | VARCHAR(13) | ForeignKey(N=F; I=T*) | - | - | — | FK→TutorCourse; CASCADE; related_name=`schedule_dates`; target PK=VARCHAR(13) | ตรง | DD ไม่ระบุ related_name แต่ relation/ชนิดตรง | DD md:166; model:66-72 |
| 71 | TimeSlot | TimeSlot | ts_id | ts_id | ts_id | INT | AutoField(PK=T; U=T; I=T*) | - | - | auto | PK | ตรง | Type/Key ตรง; DD description เขียน “รหัสวันที่เปิดสอน” ซึ่งซ้ำความหมาย `sd_id` และน่าจะเป็นข้อความผิด | DD md:174; `apps/tutoring/models.py:91,104` |
| 72 | TimeSlot | TimeSlot | ts_start_time | ts_start_time | ts_start_time | TIME | TimeField(N=F; B=F) | - | - | — | - | ตรง | ตรง | DD md:175; model:92 |
| 73 | TimeSlot | TimeSlot | ts_end_time | ts_end_time | ts_end_time | TIME | TimeField(N=F; B=F) | - | - | — | - | ตรง | ตรง | DD md:176; model:93 |
| 74 | TimeSlot | TimeSlot | ts_status | ts_status | ts_status | TINYINT(1) | IntegerField(N=F; B=F) | 0=ว่าง<br>1=จองแล้ว | 0=ว่าง<br>1=ล็อกแล้ว | 0 | - | ไม่ตรง | Type และ label ต่าง; logic ตั้ง 1 เมื่อติวเตอร์รับงานและใช้เป็น “ล็อก slot” ป้องกันจองซ้ำ จึงกว้าง/แม่นกว่า “จองแล้ว” และไม่เท่ากันด้านความหมาย | DD md:177; `apps/tutoring/models.py:83-98`; `apps/tutoring/views.py:271,290,628-644`; `apps/bookings/views.py:173-174` |
| 75 | TimeSlot | TimeSlot | sd_id | sd_id | sd_id | INT | ForeignKey(N=F; I=T*) | - | - | — | FK→ScheduleDate; CASCADE; related_name=`time_slots`; target PK=INT | ตรง | ตรง | DD md:178; model:99-105 |
| 76 | Refill | Refill | rf_id | rf_id | rf_id | INT | AutoField(PK=T; U=T; I=T*) | - | - | auto | PK | ตรง | ตรง | DD md:188; `apps/credits/models.py:14` |
| 77 | Refill | Refill | rf_date | rf_date | rf_date | DATETIME | DateTimeField(N=F; B=F) | - | - | — | - | ตรง | ตรง | DD md:189; model:15 |
| 78 | Refill | Refill | ไม่ระบุ (ธนาคารต้นทาง) | - | - | ไม่ระบุ | - | - | - | - | - | ไม่มีในระบบ | PDF ไม่ระบุ Attribute/Type/Size และ Django Refill ไม่มี field ความหมายนี้ | DD PDF หน้า 8; DD md:190,200; `apps/credits/models.py:7-27` |
| 79 | Refill | Refill | rf_money | rf_money | rf_money | DECIMAL(7,2) | DecimalField(7,2; N=F; B=F) | - | - | — | - | ตรง | ตรง | DD md:191; model:16 |
| 80 | Refill | Refill | rf_credit | rf_credit | rf_credit | INT | IntegerField(N=F; B=F) | - | - | — | - | ตรง | ตรง | DD md:192; model:17 |
| 81 | Refill | Refill | rf_slip | rf_slip | rf_slip | VARCHAR(255) | ImageField(max_length=100 โดย default; N=F; B=F; DB เป็น VARCHAR) | - | - | — | - | ไม่ตรง | Django field type เฉพาะไฟล์เหมาะกับความหมาย แต่ DB max_length 100 ไม่ตรง DD 255 | DD md:193; `apps/credits/models.py:18` |
| 82 | Refill | Refill | rf_qr_payload | rf_qr_payload | rf_qr_payload | VARCHAR(255) | CharField(max_length=255; N=T; B=T; U=T; I=T*) | - | - | — | UNIQUE | ตรง | Type/Size ตรง; DD ไม่ระบุ unique | DD md:194; model:19 |
| 83 | Refill | Refill | rf_confirm_date | rf_confirm_date | rf_confirm_date | DATETIME | DateTimeField(N=T; B=T) | - | - | — | - | ตรง | ตรงตามคุณสมบัติที่ DD ระบุ | DD md:195; model:20 |
| 84 | Refill | Refill | rf_status | rf_status | rf_status | TINYINT(1) | IntegerField(N=F; B=F) | 0=รอตรวจสอบ<br>1=ผ่านการตรวจสอบ<br>2=ไม่ผ่านการตรวจสอบ | 0=รอตรวจสอบ<br>1=ผ่านการตรวจสอบ<br>2=ไม่ผ่านการตรวจสอบ | 0 | - | ไม่ตรง | choices ตรง แต่ Type ไม่ตรง | DD md:196; `apps/credits/models.py:8-12,21`; `apps/admin_panel/views.py:327-363` |
| 85 | Refill | Refill | rf_cmt | rf_cmt | rf_cmt | TEXT | TextField(N=T; B=T) | - | - | — | - | ตรง | ตรง | DD md:197; model:22 |
| 86 | Refill | Refill | mb_id | member | member_id | VARCHAR(13) | ForeignKey(N=F; I=T*) | - | - | — | FK→Member; CASCADE; related_name=—; target PK=INT | ไม่ตรง | Python/DB column และชนิด FK ต่าง; DD เป็น `mb_id` VARCHAR(13), Django เป็น `member_id` INT | DD md:198; `apps/credits/models.py:23-27`; `apps/accounts/models.py:8,31-33` |
| 87 | Booking | Booking | bk_id | bk_id | bk_id | INT | AutoField(PK=T; U=T; I=T*) | - | - | auto | PK | ตรง | ตรง | DD md:210; `apps/bookings/models.py:19` |
| 88 | Booking | Booking | bk_desc | bk_desc | bk_desc | TEXT | TextField(N=T; B=T) | - | - | — | - | ตรง | ตรง | DD md:211; model:20 |
| 89 | Booking | Booking | bk_stu_datetime | bk_stu_datetime | bk_stu_datetime | DATETIME | DateTimeField(N=F; B=F) | - | - | — | - | ตรง | DD มีหมายเหตุ “รวม”; field ปัจจุบันรวมวันและเวลาใน DateTimeField | DD md:212 (PDF หน้า 9); model:21 |
| 90 | Booking | Booking | bk_stu_count | bk_stu_count | bk_stu_count | INT | IntegerField(N=F; B=F) | - | - | — | - | ตรง | ตรง | DD md:213; model:22 |
| 91 | Booking | Booking | bk_rate_per_person | bk_rate_per_person | bk_rate_per_person | INT | IntegerField(N=F; B=F) | - | - | — | - | ตรง | ตรง | DD md:214; model:23 |
| 92 | Booking | Booking | bk_date | bk_date | bk_date | DATETIME | DateTimeField(N=F; B=F) | - | - | — | - | ตรง | ตรง | DD md:215; model:24 |
| 93 | Booking | Booking | bk_accepted_date | bk_accepted_date | bk_accepted_date | DATETIME | DateTimeField(N=T; B=T) | - | - | — | - | ตรง | ตรง | DD md:216; model:25 |
| 94 | Booking | Booking | bk_status | bk_status | bk_status | TINYINT(1) | IntegerField(N=F; B=F) | 0=จอง<br>1=รับงานแล้ว<br>2=เรียนแล้ว<br>3=แจ้งจบงาน<br>4=ยืนยันการจบงาน<br>5=รีวิวแล้ว<br>6=ปฏิเสธ | 0=จอง<br>1=รับงานแล้ว<br>2=เรียนแล้ว<br>3=แจ้งจบงาน<br>4=ยืนยันการจบงาน<br>5=รีวิวแล้ว<br>6=ปฏิเสธ | 0 | - | ไม่ตรง | choices ตรงครบ แต่ Type ไม่ใช่ TINYINT(1); UI ใช้ label ตามบริบทบางค่าต่างจาก Model | DD md:217; `apps/bookings/models.py:9-17,26`; views:253-258; template `student_bookings.html:196-210` |
| 95 | Booking | Booking | bk_cmt | bk_cmt | bk_cmt | TEXT | TextField(N=T; B=T) | - | - | — | - | ตรง | ตรง | DD md:218; model:27 |
| 96 | Booking | Booking | bk_report_reason | bk_report_reason | bk_report_reason | VARCHAR(10) | CharField(max_length=10; N=T; B=T) | `'1'`=หลักฐานไม่ตรง<br>`'2'`=ไม่ได้สอน<br>`'3'`=เนื้อหาไม่ตรง<br>`'4'`=กดพลาด<br>`'other'`=อื่น ๆ | `'1'`=หลักฐานการสอนไม่ตรงความจริง<br>`'2'`=ไม่ได้สอนเลยแต่แจ้งจบงาน<br>`'3'`=เนื้อหาไม่ตรงที่ตกลงไว้<br>`'4'`=ผู้เรียนกดยืนยันโดยไม่ตั้งใจ<br>`'other'`=อื่นๆ | — | - | ไม่ตรง | Type/Size ตรงและความหมายหลักใกล้กัน แต่ label ไม่ตรงคำ; runtime ยังใช้ 5-8/alias/cancel นอก choices ทำให้ validation/display ไม่ครบ | DD md:219; `apps/bookings/models.py:28-35`; `apps/bookings/views.py:19-45,186-188,597-619,887-901`; templates `tutor_requests.html:1079-1091`, `student_bookings.html:942-954` |
| 97 | Booking | Booking | bk_report_desc | bk_report_desc | bk_report_desc | TEXT | TextField(N=T; B=T) | - | - | — | - | ตรง | ตรง | DD md:220; model:36 |
| 98 | Booking | Booking | bk_report_date | bk_report_date | bk_report_date | DATETIME | DateTimeField(N=T; B=T) | - | - | — | - | ตรง | ตรง | DD md:221; model:37 |
| 99 | Booking | Booking | bk_report_resolved_date | bk_report_resolved_date | bk_report_resolved_date | DATETIME | DateTimeField(N=T; B=T) | - | - | — | - | ตรง | ตรง | DD md:222; model:38 |
| 100 | Booking | Booking | mb_id | member | member_id | VARCHAR(13) | ForeignKey(N=F; I=T*) | - | - | — | FK→Member; CASCADE; related_name=—; target PK=INT | ไม่ตรง | ชื่อ/DB column/ชนิด FK ต่าง | DD md:223; `apps/bookings/models.py:39-43`; Member model:8,31-33 |
| 101 | Booking | Booking | tutc_id | tutc_id | tutc_id | VARCHAR(13) | ForeignKey(N=F; I=T*) | - | - | — | FK→TutorCourse; CASCADE; related_name=—; target PK=VARCHAR(13) | ตรง | ตรง | DD md:231; model:44-49 |
| 102 | Booking | Booking | ts_id | ts_id | ts_id | INT | ForeignKey(N=T; B=T; I=T*) | - | - | — | FK→TimeSlot; SET_NULL; related_name=—; target PK=INT | ตรง | ตรง; DD ไม่ระบุ nullable | DD md:232; model:50-57 |
| 103 | Inbox | Inbox | ib_id | ib_id | ib_id | INT | AutoField(PK=T; U=T; I=T*) | - | - | auto | PK | ตรง | ตรง | DD md:242; `apps/messaging/models.py:8` |
| 104 | Inbox | Inbox | ib_mb_id1 | member1 | member1_id | VARCHAR(13) | ForeignKey(N=F; I=T*) | - | - | — | FK→Member; CASCADE; related_name=`inbox_as_member1`; target PK=INT | ไม่ตรง | Attribute/DB column/ชนิด FK ไม่ตรง | DD md:243; model:9-14; Member model:8,31-33 |
| 105 | Inbox | Inbox | ib_mb_id2 | member2 | member2_id | VARCHAR(13) | ForeignKey(N=F; I=T*) | - | - | — | FK→Member; CASCADE; related_name=`inbox_as_member2`; target PK=INT | ไม่ตรง | Attribute/DB column/ชนิด FK ไม่ตรง; Django มี unique_together(member1,member2) ที่ DD ไม่ระบุ | DD md:244; `apps/messaging/models.py:15-25` |
| 106 | Message | Message | msg_id | msg_id | msg_id | INT | AutoField(PK=T; U=T; I=T*) | - | - | auto | PK | ตรง | ตรง | DD md:252; `apps/messaging/models.py:45` |
| 107 | Message | Message | msg_sent_time | msg_sent_time | msg_sent_time | DATETIME | DateTimeField(auto_now_add=T; N=F; B=T) | - | - | auto_now_add | - | ตรง | DD ไม่ระบุวิธีกำหนดเวลา | DD md:253; model:46 |
| 108 | Message | Message | msg | msg | msg | TEXT | TextField(N=F; B=T) | - | - | — | - | ตรง | ตรงตามคุณสมบัติที่ DD ระบุ | DD md:254; model:47 |
| 109 | Message | Message | msg_img | msg_img | msg_img | VARCHAR(255) | ImageField(max_length=100; N=T; B=T; DB เป็น VARCHAR) | - | - | — | - | ไม่ตรง | max_length 100 ไม่ตรง 255 | DD md:255; model:48-53 |
| 110 | Message | Message | msg_is_read | msg_is_read | msg_is_read | TINYINT(1) | IntegerField(N=F; B=F; ไม่มี choices) | 0=ยังไม่อ่าน<br>1=อ่านแล้ว | ไม่มี Model choices; verbose_name ระบุ 0=ยังไม่อ่าน, 1=อ่านแล้ว | 0 | - | ไม่ตรง | Type ไม่ตรงและ Django ไม่บังคับโดเมน 0/1 ด้วย choices/validator | DD md:256; `apps/messaging/models.py:54`; model method:36 |
| 111 | Message | Message | msg_sender_mb_id | sender | sender_id | VARCHAR(13) | ForeignKey(N=F; I=T*) | - | - | — | FK→Member; CASCADE; related_name=—; target PK=INT | ไม่ตรง | Attribute/DB column/ชนิด FK ไม่ตรง | DD md:257; model:55-59 |
| 112 | Message | Message | ib_id | inbox | inbox_id | INT | ForeignKey(N=F; I=T*) | - | - | — | FK→Inbox; CASCADE; related_name=—; target PK=INT | ไม่ตรง | Relation/ชนิดตรง แต่ Python field และ DB column ไม่ตรงชื่อ DD | DD md:258; model:60-64 |
| 113 | Tutoring Activity | TutoringActivity | bk_id | bk_id | bk_id | INT | OneToOneField(PK=T; U=T; I=T*) | - | - | — | PK/O2O→Booking; CASCADE; related_name=—; target PK=INT | ตรง | PK+FK สอดคล้อง; OneToOne บังคับหนึ่งกิจกรรมต่อ booking | DD md:268; `apps/bookings/models.py:106-112` |
| 114 | Tutoring Activity | TutoringActivity | ta_img1 | ta_img1 | ta_img1 | VARCHAR(255) | ImageField(max_length=100; N=T; B=T; DB เป็น VARCHAR) | - | - | — | - | ไม่ตรง | max_length 100 ไม่ตรง 255 | DD md:269; model:113 |
| 115 | Tutoring Activity | TutoringActivity | ta_img2 | ta_img2 | ta_img2 | VARCHAR(255) | ImageField(max_length=100; N=T; B=T; DB เป็น VARCHAR) | - | - | — | - | ไม่ตรง | max_length ไม่ตรง | DD md:270; model:114 |
| 116 | Tutoring Activity | TutoringActivity | ta_img3 | ta_img3 | ta_img3 | VARCHAR(255) | ImageField(max_length=100; N=T; B=T; DB เป็น VARCHAR) | - | - | — | - | ไม่ตรง | max_length ไม่ตรง | DD md:271; model:115 |
| 117 | Tutoring Activity | TutoringActivity | ta_desc | ta_desc | ta_desc | TEXT | TextField(N=T; B=T) | - | - | — | - | ตรง | ตรง | DD md:272; model:116 |
| 118 | Job Completion | JobCompletion | bk_id | bk_id | bk_id | INT | OneToOneField(PK=T; U=T; I=T*) | - | - | — | PK/O2O→Booking; CASCADE; related_name=—; target PK=INT | ตรง | ตรง | DD md:280; `apps/bookings/models.py:128-134` |
| 119 | Job Completion | JobCompletion | jc_complete_date | jc_complete_date | jc_complete_date | DATETIME | DateTimeField(N=F; B=F) | - | - | — | - | ตรง | ตรง | DD md:281; model:135 |
| 120 | Job Completion | JobCompletion | jc_confirm_date | jc_confirm_date | jc_confirm_date | DATETIME | DateTimeField(N=T; B=T) | - | - | — | - | ตรง | ตรง | DD md:282; model:136 |
| 121 | Review | Review | bk_id | bk_id | bk_id | INT | OneToOneField(PK=T; U=T; I=T*) | - | - | — | PK/O2O→Booking; CASCADE; related_name=—; target PK=INT | ตรง | ตรง | DD md:294; `apps/bookings/models.py:148-154` |
| 122 | Review | Review | rv_quality | rv_quality | rv_quality | TINYINT(1) | IntegerField(N=F; B=F; ไม่มี choices/validator) | - | - | — | - | ไม่ตรง | Type ไม่ตรงและ Django ไม่จำกัดช่วงคะแนน | DD md:295; model:155 |
| 123 | Review | Review | rv_knowledge | rv_knowledge | rv_knowledge | TINYINT(1) | IntegerField(N=F; B=F; ไม่มี choices/validator) | - | - | — | - | ไม่ตรง | Type ไม่ตรงและไม่จำกัดช่วง | DD md:296; model:156 |
| 124 | Review | Review | rv_communication | rv_communication | rv_communication | TINYINT(1) | IntegerField(N=F; B=F; ไม่มี choices/validator) | - | - | — | - | ไม่ตรง | Type ไม่ตรงและไม่จำกัดช่วง | DD md:297; model:157 |
| 125 | Review | Review | rv_punctuality | rv_punctuality | rv_punctuality | TINYINT(1) | IntegerField(N=F; B=F; ไม่มี choices/validator) | - | - | — | - | ไม่ตรง | Type ไม่ตรงและไม่จำกัดช่วง | DD md:298; model:158 |
| 126 | Review | Review | rv_satisfaction | rv_satisfaction | rv_satisfaction | TINYINT(1) | IntegerField(N=F; B=F; ไม่มี choices/validator) | - | - | — | - | ไม่ตรง | Type ไม่ตรงและไม่จำกัดช่วง | DD md:299; model:159 |
| 127 | Review | Review | rv_cmt | rv_cmt | rv_cmt | TEXT | TextField(N=T; B=T) | - | - | — | - | ตรง | ตรง | DD md:300; model:160 |
| 128 | Review | Review | rv_date | rv_date | rv_date | DATETIME | DateTimeField(N=F; B=F) | - | - | — | - | ตรง | ตรง | DD md:301; model:161 |
| 129 | Withdrawals | Withdrawals | wd_id | wd_id | wd_id | INT | AutoField(PK=T; U=T; I=T*) | - | - | auto | PK | ตรง | ตรง | DD md:311; `apps/credits/models.py:52` |
| 130 | Withdrawals | Withdrawals | wd_req_date | wd_req_date | wd_req_date | DATETIME | DateTimeField(N=F; B=F) | - | - | — | - | ตรง | ตรง | DD md:312; model:53 |
| 131 | Withdrawals | Withdrawals | wd_type | wd_type | wd_type | TINYINT(1) | IntegerField(N=F; B=F) | 0=นำฝาก<br>1=รายได้ | 0=นำฝาก<br>1=รายได้ | 0 | - | ไม่ตรง | choices ตรง แต่ Type ไม่ตรง | DD md:313; `apps/credits/models.py:40-43,55`; `apps/credits/views.py:406-451` |
| 132 | Withdrawals | Withdrawals | wd_credit | wd_credit | wd_credit | INT | IntegerField(N=F; B=F) | - | - | — | - | ตรง | ตรง | DD md:314; model:56 |
| 133 | Withdrawals | Withdrawals | wd_cash | wd_cash | wd_cash | DECIMAL(7,2) | DecimalField(7,2) | - | - | — | - | ตรง | ตรง | DD md:315; model:57 |
| 134 | Withdrawals | Withdrawals | wd_bank_name | wd_bank_name | wd_bank_name | VARCHAR(100) | CharField(max_length=100) | - | - | — | - | ตรง | ตรง | DD md:316; model:58 |
| 135 | Withdrawals | Withdrawals | wd_acc_name | wd_acc_name | wd_acc_name | VARCHAR(100) | CharField(max_length=100) | - | - | — | - | ตรง | ตรง | DD md:317; model:59 |
| 136 | Withdrawals | Withdrawals | wd_acc_no | wd_acc_no | wd_acc_no | VARCHAR(20) | CharField(max_length=20) | - | - | — | - | ตรง | ตรง | DD md:318; model:60 |
| 137 | Withdrawals | Withdrawals | wd_fee | wd_fee | wd_fee | DECIMAL(7,2) | DecimalField(7,2) | - | - | — | - | ตรง | ตรง | DD md:319; model:62 |
| 138 | Withdrawals | Withdrawals | wd_net_cash | wd_net_cash | wd_net_cash | DECIMAL(7,2) | DecimalField(7,2) | - | - | 0 | - | ตรง | DD ไม่ระบุ default | DD md:320; model:64 |
| 139 | Withdrawals | Withdrawals | wd_paid_date | wd_paid_date | wd_paid_date | DATETIME | DateTimeField(N=T; B=T) | - | - | — | - | ตรง | ตรง | DD md:321; model:65 |
| 140 | Withdrawals | Withdrawals | wd_status | wd_status | wd_status | TINYINT(1) | IntegerField(N=F; B=F) | 0=รอดำเนินการ<br>1=จ่ายแล้ว<br>2=ปฏิเสธการถอน<br>3=ยกเลิกการถอน | 0=รอดำเนินการ<br>1=จ่ายแล้ว<br>2=ปฏิเสธการถอน<br>3=ยกเลิกโดยผู้ใช้ | 0 | - | ไม่ตรง | Type ไม่ตรง; ค่า 3 workflow เดียวกันแต่ Django ระบุผู้กระทำชัดกว่า ทำให้ label ไม่ตรง | DD md:322; `apps/credits/models.py:45-50,66`; `apps/credits/views.py:214-220` |
| 141 | Withdrawals | Withdrawals | wd_cmt | wd_cmt | wd_cmt | TEXT | TextField(N=T; B=T) | - | - | — | - | ตรง | ตรง | DD md:323; model:67 |
| 142 | Withdrawals | Withdrawals | mb_id | member | member_id | VARCHAR(13) | ForeignKey(N=F; I=T*) | - | - | — | FK→Member; CASCADE; related_name=—; target PK=INT | ไม่ตรง | Attribute/DB column/ชนิด FK ไม่ตรง | DD md:324; model:68-72; Member model:8,31-33 |
| 143 | Withdrawals | Withdrawals | - | wd_promptpay_no | wd_promptpay_no | - | CharField(max_length=20; N=T; B=T) | - | - | — | - | ไม่มีใน Data Dictionary | Django รองรับหมายเลขพร้อมเพย์ในการถอน แต่ DD ไม่มี field | `apps/credits/models.py:61` |
| 144 | Booking Report Statement | BookingReportStatement | brs_id | brs_id | brs_id | INT | AutoField(PK=T; U=T; I=T*) | - | - | auto | PK | ตรง | ตรง | DD md:338; `apps/bookings/models.py:77` |
| 145 | Booking Report Statement | BookingReportStatement | brs_role | brs_role | brs_role | VARCHAR(10) | CharField(max_length=10; N=F; B=F) | ไม่แจกแจงค่า | `'student'`=Student<br>`'tutor'`=Tutor | — | - | กำกวม | Type/Size รองรับทั้งค่า (`student` 7, `tutor` 5 ตัวอักษร) แต่ DD กำหนดรายละเอียดไม่ครบ จึงยืนยัน choices ไม่ได้ | DD md:339; `apps/bookings/models.py:72-75,91`; templates `tutor_mgmt_detail.html:179` |
| 146 | Booking Report Statement | BookingReportStatement | brs_desc | brs_desc | brs_desc | TEXT | TextField(N=F; B=F) | - | - | — | - | ตรง | ตรง | DD md:340; model:92 |
| 147 | Booking Report Statement | BookingReportStatement | brs_date | brs_date | brs_date | DATETIME | DateTimeField(N=F; B=F) | - | - | — | - | ตรง | ตรง | DD md:341; model:93 |
| 148 | Booking Report Statement | BookingReportStatement | bk_id | bk_id | bk_id | INT | ForeignKey(N=F; I=T*) | - | - | — | FK→Booking; CASCADE; related_name=`report_statements`; target PK=INT | ตรง | ตรง | DD md:342; model:78-84 |
| 149 | Booking Report Statement | BookingReportStatement | mb_id | member | member_id | VARCHAR(13) | ForeignKey(N=F; I=T*) | - | - | — | FK→Member; CASCADE; related_name=—; target PK=INT | ไม่ตรง | Attribute/DB column/ชนิด FK ไม่ตรง | DD md:343; model:85-90; Member model:8,31-33 |
| 150 | Notification | Notification | id | id | id | INT | BigAutoField(PK=T; U=T; I=T*) | - | - | auto | PK | ไม่ตรง | DD ระบุ INT แต่ app กำหนด BigAutoField (64-bit) | DD md:351; `apps/notifications/apps.py:5`; model:7 |
| 151 | Notification | Notification | notif_type | notif_type | notif_type | VARCHAR(30) | CharField(max_length=30; N=F; B=F) | ไม่แจกแจงค่า | 17 ค่า: ดูตาราง choices ด้านล่าง | — | - | กำกวม | Type/Size ตรง แต่ DD ไม่ให้โดเมนค่า; runtime ยังสร้าง `booking_cancelled` นอก choices | DD md:352; `apps/notifications/models.py:9-27,45`; signals:108 |
| 152 | Notification | Notification | notif_text | notif_text | notif_text | VARCHAR(255) | CharField(max_length=255) | - | - | — | - | ตรง | ตรง | DD md:353; model:46 |
| 153 | Notification | Notification | notif_url | notif_url | notif_url | VARCHAR(255) | CharField(max_length=255; B=T) | - | - | `''` | - | ตรง | ตรง; DD ไม่ระบุ default | DD md:354; model:47 |
| 154 | Notification | Notification | notif_is_read | notif_is_read | notif_is_read | TINYINT(1) | BooleanField(N=F; B=F) | ไม่แจกแจงค่า | False=ยังไม่อ่าน<br>True=อ่านแล้ว (ตามการใช้งาน) | False | - | ไม่ตรง | DD ระบุ TINYINT(1) แต่ Django เป็น BooleanField; DD ไม่แจกแจงความหมาย | DD md:355; `apps/notifications/models.py:48`; `apps/notifications/views.py:16-24` |
| 155 | Notification | Notification | notif_created_at | notif_created_at | notif_created_at | DATETIME | DateTimeField(auto_now_add=T; N=F; B=T) | - | - | auto_now_add | - | ตรง | ตรง | DD md:356; model:49 |
| 156 | Notification | Notification | recipient_id | recipient | recipient_id | VARCHAR(13) | ForeignKey(N=T; B=T; I=T*) | - | - | — | FK→Member; CASCADE; related_name=`notifications`; target PK=INT | ไม่ตรง | DB column ตรงชื่อ DD แต่ชนิดจริงเป็น INT ตาม Member PK ไม่ใช่ VARCHAR(13) | DD md:357; model:30-36; Member model:8,31-33 |
| 157 | Notification | Notification | admin_recipient_id | admin_recipient | admin_recipient_id | INT | ForeignKey(N=T; B=T; I=T*) | - | - | — | FK→`auth.User`; CASCADE; related_name=`notifications`; target PK=INT | ตรง | Python field ไม่มี suffix `_id` แต่ DB column, target และชนิดตรง | DD md:358; model:38-44 |

## 3. ตาราง Choices ทั้งระบบ

| Model | Field | Data Dictionary Choices | Django Choices | ค่าที่ใช้จริงนอก Model | Default | สถานะ | รายละเอียด | หลักฐานไฟล์และบรรทัด |
|---|---|---|---|---|---|---|---|---|
| Member | mb_status | 0=ปิดการใช้งาน<br>1=ใช้งานปกติ<br>2=ระงับชั่วคราว | 0=ปิดการใช้งาน<br>1=ใช้งานปกติ<br>2=ระงับชั่วคราว | 0/1/2 ตามความหมายเดียวกัน | 1 | ตรง | Choices ตรงครบ; ความไม่ตรงของ field อยู่ที่ TINYINT เทียบ IntegerField | DD md:99; `apps/accounts/models.py:9-13,21`; `apps/admin_panel/views.py:47,420-425`; `templates/accounts/profile.html:34-44` |
| Tutor | tut_has_exp | 0=ไม่เคยสอน<br>1=เคยสอน | 0=ไม่เคยสอน<br>1=เคยสอน | 0/1 ตรง | 0 | ตรง | Choices ตรง | DD md:116; `apps/accounts/models.py:47-50,62`; `apps/tutoring/views.py:454,521`; `templates/tutoring/tutor_profile_edit.html:153-160` |
| Tutor | tut_status | 0=ยังไม่อนุมัติ<br>1=อนุมัติแล้ว<br>2=ปฏิเสธ<br>3=ระงับการสอน | 0=รอการตรวจสอบ<br>1=อนุมัติแล้ว<br>2=ปฏิเสธ<br>3=ระงับการสอน | 0/1/2/3 ตาม workflow เดียวกัน | 0 | ไม่ตรง | ค่า 0 มีเจตนาเดียวกันโดยอนุมานจาก workflow: ผู้สมัครยังไม่ได้รับอนุมัติและกำลังรอ Admin; แต่ข้อความ “ยังไม่อนุมัติ” กับ “รอการตรวจสอบ” ไม่เหมือนกัน จึงไม่ให้สถานะตรง | DD md:124; `apps/accounts/models.py:41-46,75`; `apps/admin_panel/views.py:210-269`; `templates/tutoring/register_tutor.html:91-106` |
| TutorCourse | tutc_status | 0=ปิดรับสอน<br>1=เปิดรับสอน | 0=ปิดรับสอน<br>1=เปิดรับสอน | 0/1 ตรง | 1 | ตรง | Choices ตรง | DD md:140; `apps/tutoring/models.py:9-12,19`; views:662,959-962 |
| TimeSlot | ts_status | 0=ว่าง<br>1=จองแล้ว | 0=ว่าง<br>1=ล็อกแล้ว | 0 ใช้เป็น slot ว่าง; 1 ตั้งเมื่อติวเตอร์รับงานและกันการจองซ้ำ; คืนเป็น 0 เมื่อปล่อย slot | 0 | ไม่ตรง | “ล็อกแล้ว” เป็นสถานะเชิงกลไกที่ครอบคลุมการกัน slot หลังรับงาน ไม่เท่ากับข้อความทั่วไป “จองแล้ว”; Type ยังต่าง | DD md:177; `apps/tutoring/models.py:83-98`; `apps/tutoring/views.py:185-197,271,290,628-644`; `apps/bookings/views.py:173-174,317` |
| Booking | bk_status | 0=จอง<br>1=รับงานแล้ว<br>2=เรียนแล้ว<br>3=แจ้งจบงาน<br>4=ยืนยันการจบงาน<br>5=รีวิวแล้ว<br>6=ปฏิเสธ | 0=จอง<br>1=รับงานแล้ว<br>2=เรียนแล้ว<br>3=แจ้งจบงาน<br>4=ยืนยันการจบงาน<br>5=รีวิวแล้ว<br>6=ปฏิเสธ | ใช้ครบ 0-6; UI นักเรียนแสดง 0=จองแล้ว, 1=อนุมัติแล้ว, 2=เรียนแล้ว, 3=ยืนยันจบงาน, 4=เสร็จสิ้น, 5=รีวิวแล้ว, 6=ติวเตอร์ปฏิเสธ | 0 | ตรง | Model choices ตรง DD ทุกค่า; UI label ต่างตามมุมมองแต่ workflow ค่าเดิม | DD md:217; `apps/bookings/models.py:9-17,26`; views:253-258; `templates/bookings/student_bookings.html:196-210` |
| Booking | bk_report_reason | `'1'`=หลักฐานไม่ตรง<br>`'2'`=ไม่ได้สอน<br>`'3'`=เนื้อหาไม่ตรง<br>`'4'`=กดพลาด<br>`'other'`=อื่น ๆ | `'1'`=หลักฐานการสอนไม่ตรงความจริง<br>`'2'`=ไม่ได้สอนเลยแต่แจ้งจบงาน<br>`'3'`=เนื้อหาไม่ตรงที่ตกลงไว้<br>`'4'`=ผู้เรียนกดยืนยันโดยไม่ตั้งใจ<br>`'other'`=อื่นๆ | รับเพิ่ม `'5'`=ผู้เรียนไม่เข้าเรียน, `'6'`=ติดต่อไม่ได้, `'7'`=ไม่สามารถตกลงกันได้, `'8'`=อื่นๆ, `'t_no_show'`→2, `'s_no_show'`→5, `'contact'`/`'cannot_contact'`→6, `'agree'`→7, `'other'`→8, `'cancel'`=ข้อพิพาทการยกเลิกจากติวเตอร์ | — | ไม่ตรง | ModelForm/full_clean จะปฏิเสธ 5-8 และ cancel เพราะไม่อยู่ choices; การ save ผ่าน view โดยไม่ full_clean ยังบันทึกได้; `get_bk_report_reason_display()` คืนค่าดิบสำหรับค่านอก choices ทำให้ label ไม่สม่ำเสมอ | DD md:219; `apps/bookings/models.py:28-35`; `apps/bookings/views.py:19-45,186-188,612,893`; `templates/admin_panel/report_mgmt.html:258-266`; templates report inputs:1079-1091,942-954 |
| BookingReportStatement | brs_role | ไม่แจกแจงค่า | `'student'`=Student<br>`'tutor'`=Tutor | templates ใช้ `'tutor'` มิฉะนั้นแสดงผู้เรียน; views ส่ง role ลง field | — | กำกวม | DD ระบุเพียง VARCHAR(10); ทั้ง `student` (7) และ `tutor` (5) ไม่เกิน 10 แต่ยืนยันโดเมนจาก DD ไม่ได้ | DD md:339; `apps/bookings/models.py:72-75,91`; `apps/bookings/views.py:224`; `templates/admin_panel/tutor_mgmt_detail.html:179` |
| Refill | rf_status | 0=รอตรวจสอบ<br>1=ผ่านการตรวจสอบ<br>2=ไม่ผ่านการตรวจสอบ | 0=รอตรวจสอบ<br>1=ผ่านการตรวจสอบ<br>2=ไม่ผ่านการตรวจสอบ | ใช้ 0→1/2 ตามความหมายเดียวกัน | 0 | ตรง | Choices ตรง | DD md:196; `apps/credits/models.py:8-12,21`; `apps/admin_panel/views.py:327-363`; `apps/notifications/signals.py:176-194` |
| Withdrawals | wd_type | 0=นำฝาก<br>1=รายได้ | 0=นำฝาก<br>1=รายได้ | views ใช้ 0 เลือกยอดนำฝากและ 1 เลือกยอดรายได้ | 0 | ตรง | Choices ตรง | DD md:313; `apps/credits/models.py:40-43,55`; `apps/credits/views.py:406-451` |
| Withdrawals | wd_status | 0=รอดำเนินการ<br>1=จ่ายแล้ว<br>2=ปฏิเสธการถอน<br>3=ยกเลิกการถอน | 0=รอดำเนินการ<br>1=จ่ายแล้ว<br>2=ปฏิเสธการถอน<br>3=ยกเลิกโดยผู้ใช้ | admin ใช้ 0→1/2; ผู้ใช้เปลี่ยน 0→3 | 0 | ไม่ตรง | ค่า 3 หมายถึงเหตุการณ์เดียวกัน แต่ Django ระบุ actor เพิ่ม จึง label ไม่ตรงข้อความ DD; Type ต่างด้วย | DD md:322; `apps/credits/models.py:45-50,66`; `apps/admin_panel/views.py:465-509`; `apps/credits/views.py:214-220` |
| Notification | notif_type | ไม่แจกแจงค่า | `'booking_new'`=มีการจองติวใหม่<br>`'booking_accepted'`=การจองได้รับการยืนยัน<br>`'booking_rejected'`=การจองถูกปฏิเสธ<br>`'booking_completed'`=มีการแจ้งจบงานที่ต้องยืนยัน<br>`'booking_credited'`=งานเสร็จสิ้น ได้รับเครดิตแล้ว<br>`'booking_reviewed'`=มีรีวิวใหม่<br>`'booking_reported'`=มีการรายงานปัญหา<br>`'tutor_approved'`=ติวเตอร์ได้รับการอนุมัติ<br>`'tutor_rejected'`=ติวเตอร์ถูกปฏิเสธ<br>`'tutor_suspended'`=บัญชีติวเตอร์ถูกระงับ<br>`'refill_approved'`=เติมเครดิตผ่านการตรวจสอบ<br>`'refill_rejected'`=เติมเครดิตไม่ผ่านการตรวจสอบ<br>`'withdraw_paid'`=ถอนเงินเข้าบัญชีเรียบร้อย<br>`'admin_refill'`=มีคำขอเติมเครดิต<br>`'admin_withdraw'`=มีคนขอถอนเครดิต<br>`'admin_tutor_new'`=มีติวเตอร์สมัครใหม่รอ approve<br>`'admin_reported'`=มีการรายงานปัญหา | `'booking_cancelled'`=ผู้เรียนยกเลิกการจองของคุณ ถูกสร้างนอก Model choices | — | ไม่ตรง | DD ไม่กำหนดโดเมน; `booking_cancelled` ไม่ผ่าน ModelForm/full_clean และ `get_notif_type_display()` จะคืน `'booking_cancelled'` แทน label ภาษาไทย; save โดยไม่ full_clean ยังบันทึกได้ จึงกระทบ validation/display/consistency | DD md:352; `apps/notifications/models.py:9-27,45`; `apps/notifications/signals.py:76-111` โดยค่าพิเศษอยู่บรรทัด 108 |

### Field เชิงสถานะที่ไม่มี Model choices

| Model | Field | Data Dictionary Values | Django/การใช้จริง | สถานะ | หลักฐาน |
|---|---|---|---|---|---|
| Message | msg_is_read | 0=ยังไม่อ่าน<br>1=อ่านแล้ว | IntegerField default=0; ไม่มี choices/validator; query ใช้ 0 และ flow เปลี่ยนเป็น 1 | ไม่ตรง | DD md:256; `apps/messaging/models.py:36,54`; `apps/messaging/views.py:102-103` |
| Notification | notif_is_read | DD ไม่แจกแจง | BooleanField: False=ยังไม่อ่าน, True=อ่านแล้ว | ไม่ตรง | DD md:355; `apps/notifications/models.py:48`; `apps/notifications/views.py:16-24` |

## 4. รายงานแยกตาม Model

### 4.1 System

- Source: `apps/admin_panel/models.py:7`; `db_table='system'` (`:27-29`); PK=`id` implicit AutoField
- ตรง: `uni_name`, `bank_name`, `acc_name`, `acc_no`, `promptpay_id`, `crd_val`, `deposit_withdraw_fee_pct`, `income_withdraw_fee_pct`, `email_domain`
- ไม่ตรง: `total_accumulated_fee` — DD DECIMAL(5,2), Django DecimalField(10,2) (`docs/...md:35`; model:25)
- ขาดใน Django table: `admin_pwd`, `admin_email`; ค่าจริงอยู่/คำนวณจาก `auth.User` (`docs/...md:36-37`; model:8-14,38-40)
- เกิน DD: `id`, `admin`; relation `admin` เป็น O2O→User, SET_NULL, related_name=`system`
- Choices/จุดกำกวม: ไม่มี

### 4.2 Faculty

- Source: `apps/courses/models.py:6`; `db_table='faculty'` (`:10-12`); PK=`fac_id` AutoField
- ตรง: `fac_id`, `fac_name`; ไม่ตรง/ขาด/เกิน/choices/relation กำกวม: ไม่มี

### 4.3 Major

- Source: `apps/courses/models.py:19`; `db_table='major'` (`:31-33`); PK=`mj_id` AutoField
- ตรง: `mj_id`, `mj_name`, `mj_desc`, `fac_id`; `fac_id` FK→Faculty/CASCADE/ไม่มี related_name (`:24-29`)
- กำกวม: `mj_abbr` โครงสร้างตรง VARCHAR(10) แต่ DD เขียน “ตัดออก” ขณะที่ Django ยังมี (`docs/...md:59`; model:22)
- ไม่ตรง/ขาด/เกิน/choices: ไม่มีรายการอื่น

### 4.4 CourseGroup

- Source: `apps/courses/models.py:40`; `db_table='course_group'` (`:45-47`); PK=`cg_id` AutoField
- ตรง: `cg_id`, `cg_name`, `cg_desc`; ไม่ตรง/ขาด/เกิน/choices/relation กำกวม: ไม่มี

### 4.5 Course

- Source: `apps/courses/models.py:54`; `db_table='course'` (`:65-67`); PK=`crs_id` CharField(13)
- ตรง: `crs_id`, `crs_name`, `crs_desc`, `cg_id`; `cg_id` FK→CourseGroup/CASCADE/ไม่มี related_name (`:58-63`)
- ไม่ตรง/ขาด/เกิน/choices/relation กำกวม: ไม่มี

### 4.6 Member

- Source: `apps/accounts/models.py:8`; `db_table='member'` (`:31-33`); PK=`id` implicit AutoField
- ตรง: `mb_full_name`, `mb_email`, `mb_img`, `mb_deposit_crd`, `mb_income_crd`, `mb_locked_crd`, `mj_id`
- ไม่ตรง: DD `mb_id` VARCHAR(13) เทียบ `id` INT; `mb_status` choices ตรงแต่ TINYINT เทียบ IntegerField (`docs/...md:92,99`; model:9-21)
- ขาด: `mb_pwd`; Django เก็บ password ใน User (`docs/...md:95`; model:15)
- เกิน: `user` O2O→User/CASCADE/related_name=`member` (`:15`)
- Relation ไม่ตรง: ตัวตนสมาชิกตาม DD เป็น VARCHAR PK แต่ Django ใช้ `Member.id` INT

### 4.7 Tutor

- Source: `apps/accounts/models.py:40`; `db_table='tutor'` (`:90-92`); PK=`tut_id` O2O→Member
- ตรง: `tut_desc`, `tut_skill`, `tut_gpax`, `tut_student_card`, `tut_exp_desc`, `tut_rating` และคะแนนแยก 5 ด้าน, `tut_reject_note`
- ไม่ตรง: `tut_id` เป็น INT ตาม Member PK ไม่ใช่ VARCHAR(13); `tut_has_exp`/`tut_status` ใช้ IntegerField ไม่ใช่ TINYINT(1)
- Choices ไม่ตรงข้อความ: `tut_status` ค่า 0 “ยังไม่อนุมัติ” เทียบ “รอการตรวจสอบ”; เจตนา workflow เดียวกันแต่ข้อความต่าง (`docs/...md:124`; model:41-46; admin views:210-269)
- ขาด/เกิน: ไม่มี

### 4.8 TutorCourse

- Source: `apps/tutoring/models.py:8`; `db_table='tutor_course'` (`:34-36`); PK=`tutc_id` CharField(13)
- ตรง: `tutc_id`, `tutc_name`, `tutc_desc`, `tutc_img`, `tutc_max_stu`, `crs_id`
- ไม่ตรง: `tutc_status` Type; `tut_id` FK target จริงเป็น INT ไม่ใช่ VARCHAR(13)
- กำกวม: `tutc_rating` มีใน Django เป็น DecimalField(3,2) แต่ PDF ไม่ให้ชื่อ/Type/Size (`docs/...md:141`; model:20)
- Relations: `crs_id` FK→Course/CASCADE ตรง; `tut_id` FK→Tutor/CASCADE ไม่ตรงชนิด

### 4.9 TutorRate

- Source: `apps/tutoring/models.py:43`; `db_table='tutor_rate'` (`:54-56`); PK=`tut_rate_id` AutoField
- ตรง: ทั้ง 4 field — `tut_rate_id`, `tut_rate_per_person`, `tut_rate_stu_count`, `tutc_id`
- Relation: `tutc_id` FK→TutorCourse/CASCADE/ไม่มี related_name ตรง (`:47-52`); ไม่ตรง/ขาด/เกิน/choices/กำกวม: ไม่มี

### 4.10 ScheduleDate

- Source: `apps/tutoring/models.py:63`; `db_table='schedule_date'` (`:74-76`); PK=`sd_id` AutoField
- ตรง: `sd_id`, `sd_date`, `tutc_id`; FK→TutorCourse/CASCADE/related_name=`schedule_dates` (`:66-72`)
- ไม่ตรง/ขาด/เกิน/choices/กำกวม: ไม่มี

### 4.11 TimeSlot

- Source: `apps/tutoring/models.py:85`; `db_table='time_slot'` (`:107-109`); PK=`ts_id` AutoField
- ตรง: `ts_id`, `ts_start_time`, `ts_end_time`, `sd_id`; FK→ScheduleDate/CASCADE/related_name=`time_slots`
- ไม่ตรง: `ts_status` TINYINT เทียบ IntegerField และค่า 1 “จองแล้ว” เทียบ “ล็อกแล้ว”; logic จริงล็อกเมื่อรับงาน (`apps/tutoring/views.py:271,290`) และปล่อยกลับ 0 เมื่อยกเลิก (`apps/bookings/views.py:173-174`)
- จุด DD: description `ts_id` เขียน “รหัสวันที่เปิดสอน” ซ้ำกับ `sd_id` (`docs/...md:174,178`)

### 4.12 Refill

- Source: `apps/credits/models.py:7`; `db_table='refill'` (`:29-31`); PK=`rf_id` AutoField
- ตรง: `rf_id`, `rf_date`, `rf_money`, `rf_credit`, `rf_qr_payload`, `rf_confirm_date`, `rf_cmt`
- ไม่ตรง: `rf_slip` max_length 100 เทียบ 255; `rf_status` IntegerField เทียบ TINYINT; DD `mb_id` VARCHAR(13) เทียบ `member_id` INT
- ไม่มีในระบบ: รายการ “ธนาคารต้นทาง”; PDF ไม่ให้ชื่อ/Type/Size (`docs/...md:190,200`; model:7-27)
- Relation: `member` FK→Member/CASCADE/ไม่มี related_name; ชนิดไม่ตรง DD

### 4.13 Booking

- Source: `apps/bookings/models.py:8`; `db_table='booking'` (`:59-61`); PK=`bk_id` AutoField
- ตรง: `bk_id`, `bk_desc`, `bk_stu_datetime`, `bk_stu_count`, `bk_rate_per_person`, `bk_date`, `bk_accepted_date`, `bk_cmt`, `bk_report_desc`, `bk_report_date`, `bk_report_resolved_date`, `tutc_id`, `ts_id`
- ไม่ตรง: `bk_status` Type; `bk_report_reason` choices/runtime; DD `mb_id` VARCHAR เทียบ `member_id` INT
- Choices: `bk_status` Model ตรง DDครบ 0-6; `bk_report_reason` ใช้ค่า 5-8/aliases/`cancel` นอก Model choices (`apps/bookings/views.py:19-45`)
- Relations: `tutc_id` FK→TutorCourse/CASCADE ตรง; `ts_id` FK→TimeSlot/SET_NULL ตรง; Member FK ไม่ตรงชนิด
- กำกวม: DD หมายเหตุ “รวม” ที่ `bk_stu_datetime`; โครงสร้างปัจจุบันเป็น DateTimeField เดียวจึงสอดคล้อง (`docs/...md:212`; model:21)

### 4.14 Inbox

- Source: `apps/messaging/models.py:7`; `db_table='inbox'` (`:22-25`); PK=`ib_id` AutoField
- ตรง: `ib_id`
- ไม่ตรง: DD `ib_mb_id1/ib_mb_id2` VARCHAR(13) เทียบ Python `member1/member2`, DB `member1_id/member2_id`, target Member PK INT
- Constraints เกิน DD: `unique_together(member1, member2)` (`:25`)
- Relations: ทั้งคู่ FK→Member/CASCADE; related_name=`inbox_as_member1`/`inbox_as_member2`

### 4.15 Message

- Source: `apps/messaging/models.py:44`; `db_table='message'` (`:66-69`); PK=`msg_id` AutoField
- ตรง: `msg_id`, `msg_sent_time`, `msg`
- ไม่ตรง: `msg_img` max_length 100 เทียบ 255; `msg_is_read` IntegerField ไม่มี choices/validatorเทียบ TINYINT(1); sender/member FK ชื่อและชนิดต่าง; inbox FK ชื่อ Python/DB column ต่าง
- Relations: `sender` FK→Member/CASCADE, `inbox` FK→Inbox/CASCADE, ไม่มี related_name (`:55-64`)

### 4.16 TutoringActivity

- Source: `apps/bookings/models.py:105`; `db_table='tutoring_activity'` (`:118-120`); PK=`bk_id` O2O→Booking/CASCADE
- ตรง: `bk_id`, `ta_desc`
- ไม่ตรง: `ta_img1`, `ta_img2`, `ta_img3` เป็น ImageField max_length 100 แต่ DD VARCHAR(255)
- ขาด/เกิน/choices/กำกวม: ไม่มี

### 4.17 JobCompletion

- Source: `apps/bookings/models.py:127`; `db_table='job_completion'` (`:138-140`); PK=`bk_id` O2O→Booking/CASCADE
- ตรง: `bk_id`, `jc_complete_date`, `jc_confirm_date`; ไม่ตรง/ขาด/เกิน/choices/กำกวม: ไม่มี

### 4.18 Review

- Source: `apps/bookings/models.py:147`; `db_table='review'` (`:163-165`); PK=`bk_id` O2O→Booking/CASCADE
- ตรง: `bk_id`, `rv_cmt`, `rv_date`
- ไม่ตรง: คะแนน 5 field (`rv_quality`, `rv_knowledge`, `rv_communication`, `rv_punctuality`, `rv_satisfaction`) เป็น IntegerField ไม่มี validator/choices ขณะที่ DD ระบุ TINYINT(1)
- ขาด/เกิน/choices/กำกวม: ไม่มี; DD เองไม่มีหัวข้อ 4.3.1.18 และข้ามไป 4.3.1.19 (`docs/...md:284-290`)

### 4.19 Withdrawals

- Source: `apps/credits/models.py:38`; `db_table='withdrawals'` (`:74-76`); PK=`wd_id` AutoField
- ตรง: `wd_id`, `wd_req_date`, `wd_credit`, `wd_cash`, `wd_bank_name`, `wd_acc_name`, `wd_acc_no`, `wd_fee`, `wd_net_cash`, `wd_paid_date`, `wd_cmt`
- ไม่ตรง: `wd_type` และ `wd_status` Type; `wd_status` label ค่า 3; DD `mb_id` VARCHAR เทียบ `member_id` INT
- เกิน DD: `wd_promptpay_no` CharField(20), nullable/blank (`:61`)
- Relation: member FK→Member/CASCADE ไม่ตรงชนิด DD

### 4.20 BookingReportStatement

- Source: `apps/bookings/models.py:71`; `db_table='booking_report_statement'` (`:95-98`); PK=`brs_id` AutoField
- ตรง: `brs_id`, `brs_desc`, `brs_date`, `bk_id`
- ไม่ตรง: DD `mb_id` VARCHAR เทียบ Python `member`, DB `member_id`, target PK INT
- กำกวม: `brs_role` DD ระบุ VARCHAR(10) แต่ไม่แจกแจง choices; Django `student`/`tutor` ความยาวไม่เกิน 10
- Relations: `bk_id` FK→Booking/CASCADE/related_name=`report_statements`; `member` FK→Member/CASCADE/ไม่มี related_name

### 4.21 Notification

- Source: `apps/notifications/models.py:7`; `db_table='notification'` (`:51-54`); PK=`id` implicit BigAutoField จาก `apps/notifications/apps.py:5`
- ตรง: `notif_text`, `notif_url`, `notif_created_at`, `admin_recipient_id`
- ไม่ตรง: `id` BigAutoField เทียบ INT; `notif_is_read` BooleanField เทียบ TINYINT(1); `recipient_id` target Member PK INT เทียบ VARCHAR(13)
- กำกวม/choices: DD ไม่แจกแจง `notif_type`; Django มี 17 choices แต่ signals สร้าง `booking_cancelled` นอก choices (`apps/notifications/signals.py:108`)
- Relations: `recipient` FK→Member/CASCADE และ `admin_recipient` FK→User/CASCADE; ทั้งคู่ nullable/blank และ related_name=`notifications`

## 5. ข้อผิดพลาดหรือความกำกวมใน Data Dictionary

| ประเด็น | ผลการตรวจ | หลักฐาน |
|---|---|---|
| จำนวนตาราง | เนื้อความ PDF ระบุ 19 ตาราง แต่รายการจริงมี 21 ตาราง/Model | PDF หน้า 2; `docs/Data Dictionary เพื่อนช่วยติว0608.md:17-358`; inventory `01_model_inventory.md:19-41` |
| ลำดับหัวข้อ | ไม่มีหัวข้อ 4.3.1.18; Review เริ่มที่ 4.3.1.19 | PDF หน้า 12; DD md:284-290 |
| หัวข้อซ้ำ | 4.3.1.20 ใช้ทั้ง Withdrawals และ Booking Report Statement | PDF หน้า 13-14; DD md:305,326-330 |
| เลขตารางซ้ำ | ตาราง 4.15 ใช้ทั้ง Message และ Booking Report Statement | PDF หน้า 10,14; DD md:248,332-334 |
| Refill ธนาคารต้นทาง | ไม่มี Attribute Name/Type/Size และไม่มี field ใน Django | PDF หน้า 8; DD md:190,200; `apps/credits/models.py:7-27` |
| Tutor Course rating | PDF มีข้อความ “รีวิวแยกตามรายวิชาที่เปิดสอน” แต่ไม่ให้ Attribute/Type/Size; Markdown เติม `tutc_rating` จาก Django | PDF หน้า 6; DD md:141; `apps/tutoring/models.py:20` |
| Major.mj_abbr | หมายเหตุ “ตัดออก” แต่ยังปรากฏเป็นแถวและยังมีใน Django | PDF หน้า 3; DD md:59; `apps/courses/models.py:22` |
| Booking.bk_stu_datetime | มีหมายเหตุ “รวม” แต่ไม่ระบุว่ารวมจาก field เดิมใด; Django ใช้ DateTimeField เดียว | PDF หน้า 9; DD md:212; `apps/bookings/models.py:21` |
| Booking ต่อหน้า | หน้า 10 มี `1 bk_id` ซ้ำและตำแหน่งแถว 15-16 เหลื่อม; Markdown จัดตามลำดับเชิงตรรกะ | PDF หน้า 10; DD md:226-234 |
| TimeSlot.ts_id | Description ระบุ “รหัสวันที่เปิดสอน” เหมือน `sd_id`; ไม่สอดคล้องชื่อ “รหัสช่วงเวลา” ใน Django | DD md:174,178; `apps/tutoring/models.py:91,104` |
| Choices ที่ DD ไม่ระบุ | `brs_role`, `notif_type`, `notif_is_read` ไม่แจกแจงโดเมนค่า | DD md:339,352,355; models `bookings:72-75`, `notifications:9-27,48` |
| Null/blank/default/index/constraints | DD ส่วนใหญ่ไม่กำหนด จึงไม่สามารถยืนยันคุณสมบัติเหล่านี้จาก DD ได้ | ตาราง DD ทุกหน้า; inventory `01_model_inventory.md:9-17,503-514` |

## 6. รายการที่ควรแก้ภายหลัง

> ส่วนนี้เป็นข้อเสนอจากผล audit เท่านั้น ยังไม่ได้แก้โค้ด เอกสาร migration หรือฐานข้อมูล

### A. ควรแก้ใน Django

1. ทำให้ `Booking.REPORT_REASON_CHOICES` ครอบคลุมค่าจริงที่อนุญาต หรือหยุดบันทึก 5-8/`cancel`/alias นอก choices; รวม mapping ไว้แหล่งเดียว เพื่อให้ ModelForm, `full_clean()` และ `get_bk_report_reason_display()` ทำงานตรงกัน (`apps/bookings/models.py:28-35`; `apps/bookings/views.py:19-45`)
2. เพิ่ม `'booking_cancelled'` พร้อม label ใน `Notification.TYPE_CHOICES` หรือเปลี่ยน signal ให้ใช้ชนิดที่ประกาศอยู่ (`apps/notifications/models.py:9-27`; `apps/notifications/signals.py:108`)
3. ตัดสินใจและทำให้ field ที่ DD กำหนด TINYINT(1) สอดคล้องกัน ได้แก่ status/type และคะแนน Review; หากคง IntegerField ควรมี validators/constraints จำกัดโดเมน โดยเฉพาะคะแนนและ `msg_is_read`
4. หาก DD VARCHAR(255) เป็นข้อกำหนดจริง ให้กำหนด `max_length=255` สำหรับ `rf_slip`, `msg_img`, `ta_img1-3`; ปัจจุบัน ImageField ใช้ 100
5. ทบทวน `System.total_accumulated_fee` ว่าต้องเป็น DecimalField(5,2) ตาม DD หรือคง 10,2 และแก้เอกสาร
6. ทบทวน schema ตัวตน Member/Tutor: ปัจจุบัน Member PK เป็น INT และ Tutor/FK ที่เกี่ยวข้องจึงเป็น INT แต่ DD วางโครงเป็น VARCHAR(13); การเปลี่ยนจุดนี้กระทบ relation จำนวนมากและต้องวางแผน migration แยกต่างหาก
7. หาก “ธนาคารต้นทาง” จำเป็นต่อธุรกิจ ให้กำหนดชื่อ field/Type/Size/validation ก่อนเพิ่มจริง; audit นี้ไม่เดาชื่อให้

### B. ควรแก้ใน Data Dictionary

1. แก้จำนวนตารางจาก 19 ให้ตรงรายการจริง 21 ตาราง และจัดเลขหัวข้อ/เลขตารางใหม่ไม่ให้ข้ามหรือซ้ำ
2. ระบุ schema บัญชีผู้ใช้จริง: `System.admin`, `Member.user`, implicit `id`, และการใช้ `auth.User` แทน `admin_pwd/admin_email/mb_pwd` โดยตรง
3. ระบุ PK ของ Member และ Tutor รวมถึง FK ทุกจุดให้ตรงชนิดจริง หรือประกาศชัดว่าจะปรับ Django ไปใช้ VARCHAR(13)
4. เติมรายละเอียด `tutc_rating` จากข้อกำหนดที่ได้รับอนุมัติ ไม่ใช่อ้างย้อนจาก Model; ใส่เลขลำดับ Attribute ให้ชัด
5. กำหนด Attribute Name/Type/Size ของ “ธนาคารต้นทาง” หรือเอารายการออกหากไม่ใช้
6. ตัดสินสถานะ `mj_abbr` ว่าจะ “ตัดออก” จริงหรือคง field แล้วลบหมายเหตุ
7. แจกแจง choices ของ `brs_role`, `notif_type`, `notif_is_read` ทุกค่า พร้อมความหมาย
8. ทำ label ให้ตรงกัน: `Tutor.tut_status=0`, `TimeSlot.ts_status=1`, `Withdrawals.wd_status=3` และ label ตามบริบทของ Booking
9. แก้ Description ของ `TimeSlot.ts_id` เป็นรหัสช่วงเวลา หากนั่นคือเจตนา
10. ระบุ `null`, `blank`, `default`, `unique`, index, validators, constraints, `on_delete` และ `related_name` ใน Data Dictionary ฉบับถัดไปเพื่อให้ตรวจ schema ได้ครบ

## 7. ข้อสรุป

จับคู่ได้ครบทั้ง 21 Model แต่มีเพียง 6 ตารางที่ตรงครบตามข้อมูลที่ DD ระบุ ปัญหาหลักไม่ใช่เพียงชื่อ field แต่รวมถึงชนิด PK/FK ของ Member/Tutor, TINYINT เทียบ Django Integer/Boolean, ความยาว ImageField, decimal precision และ choices ที่ runtime ใช้เกิน Model definition รายงานนี้หยุดที่การตรวจสอบและไม่ได้แก้ implementation ใด ๆ
