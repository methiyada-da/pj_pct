# รายงานตรวจสอบ Data Dictionary, Django Model, Migration และ Schema จริง

## โครงการ

**การพัฒนาระบบเว็บแอปพลิเคชันเพื่อนช่วยติว**  
**DEVELOPMENT OF WEB APPLICATION SYSTEM FOR “PUEAN CHUAY TU”**

## 1. ขอบเขตการตรวจสอบ

รายงานนี้ตรวจความสอดคล้อง 4 ชั้นแบบ read-only:

1. Data Dictionary จาก PDF หน้า 1-14 และ Markdown
2. Django Model ปัจจุบัน 21 Model / 153 field
3. Migration state จาก migration ของ local apps 33 ไฟล์ (ไม่นับ `__init__.py`)
4. Schema จริงใน MySQL ฐานข้อมูล `pj_pct`: 21 ตารางโครงการ / 153 column

ตรวจชื่อ table/column, data type, size/precision/scale, nullable/default, PK/FK/O2O, target, `on_delete`, `related_name`, unique/index/constraints, migration history, choices และค่าที่ใช้ใน views/forms/templates/JavaScript/signals/constants โดยไม่ได้แก้ application code, migration, settings หรือข้อมูลในฐานข้อมูล

## 2. เอกสารและไฟล์ที่ใช้

| แหล่ง | ขอบเขต | หลักฐาน |
|---|---|---|
| ข้อกำหนดโครงการ | โครงสร้างและข้อห้าม | `AGENTS.md:1-ท้ายไฟล์` |
| Data Dictionary ต้นฉบับ | หน้า 1-14 | `docs/Data Dictionary เพื่อนช่วยติว0608.pdf` |
| Data Dictionary Markdown | ตาราง 4.1-4.21 และ field 153 รายการ | `docs/Data Dictionary เพื่อนช่วยติว0608.md:1-358` |
| Model inventory | Model/field/options/choices | `docs/data_dictionary_audit/01_model_inventory.md:1-525` |
| Field comparison | เปรียบเทียบ DD↔Model 157 แถวแบบ union | `docs/data_dictionary_audit/02_field_comparison.md:1-ท้ายไฟล์` |
| Django Models | 8 ไฟล์ / 21 Model | `apps/*/models.py` ตาม path ในรายงาน 01 และ 02 |
| Migrations | 33 migration ของ 8 local apps | `apps/*/migrations/*.py` |
| Runtime usage | forms/views/templates/JS/signals/constants/tests | หลักฐานราย field ในหัวข้อ choices และตารางปัญหา |
| Schema จริง | `information_schema` และ `django_migrations` | MySQL `localhost:3306`, database `pj_pct`; ตรวจด้วย SELECT เท่านั้น |

## 3. คำสั่งที่รัน

| ลำดับ | คำสั่ง/การตรวจ | Exit code/ผล | Output สำคัญ | Warning/Error |
|---:|---|---|---|---|
| 1 | `python manage.py makemigrations --check --dry-run` | ไม่มี child-process exit code เพราะ `python.exe` เริ่มทำงานไม่ได้ | ไม่มีผลตรวจ pending changes | PowerShell `ResourceUnavailable`: “The file cannot be accessed by the system” |
| 2 | `py -0p` | ไม่สำเร็จ | `No installed Pythons found!` | Python launcher ไม่พบ runtime ที่ใช้ได้ |
| 3 | `Test-NetConnection localhost -Port 3306` | สำเร็จ | `TcpTestSucceeded: True` | ไม่มี |
| 4 | MySQL `SELECT` จาก `information_schema.COLUMNS` | 0 | พบ schema 21 ตาราง/153 column พร้อม type/length/precision/nullable/default/key | ไม่มี |
| 5 | MySQL `SELECT` จาก `TABLE_CONSTRAINTS`, `KEY_COLUMN_USAGE`, `STATISTICS`, `REFERENTIAL_CONSTRAINTS` | 0 | ตรวจ PK/FK/unique/index และ referential rules สำเร็จ | ไม่มี |
| 6 | MySQL `SELECT` จาก `django_migrations` | 0 | พบ local migration applied 33 รายการ | ไม่มี |
| 7 | Static scan `rg`/PowerShell ของ migration ทุกไฟล์ | 0 | CreateModel=21, AddField=23, AlterField=16, RemoveField=1, RenameField=0, RenameModel=0, Add/RemoveConstraint=0, Add/RemoveIndex=0 | ไม่มี |

### สถานะคำสั่งตรวจ pending migration

ไม่สามารถใช้ผลจาก `makemigrations --check --dry-run` ยืนยัน pending model changes ได้ เพราะคำสั่งไม่เริ่มทำงาน จึง **ไม่ควรรายงานว่า exit code 0 หรือ “No changes detected”** อย่างไรก็ตาม การเปรียบเทียบ static ระหว่าง Model กับ leaf migration state ทุก app และการตรวจ schema จริงไม่พบ field/option เชิงโครงสร้างที่ต่างกัน

## 4. สถานะการเชื่อมต่อฐานข้อมูล

- สถานะ: **เชื่อมต่อและตรวจ schema จริงสำเร็จ**
- Backend: MySQL (`config/settings.py:74-83`)
- Server: `localhost:3306`; TCP เปิดใช้งาน
- Database: `pj_pct`
- Engine ของ 21 ตารางโครงการ: InnoDB
- ตรวจด้วยบัญชีที่ตั้งค่าในโปรเจกต์ โดยไม่แสดงรหัสผ่านในรายงาน
- ใช้เฉพาะ `SELECT`; ไม่ได้ใช้ CREATE/ALTER/DROP/INSERT/UPDATE/DELETE/TRUNCATE
- พบตารางโครงการครบ 21 ตารางและ column รวม 153 column
- พบ migration history ของ local apps ครบ 33 รายการ และทุกรายการในไฟล์มี record ว่า applied

## 5. สรุปผลรวม

| รายการ | ผล |
|---|---|
| DD กล่าวอ้างจำนวนตาราง | 19 |
| ตาราง/Model ที่ปรากฏจริง | 21 |
| Model ↔ Migration state ล่าสุด | ตรงจาก static comparison ทั้ง 21 Model |
| Migration history ↔ Schema | migration local 33 รายการ applied ครบ; table/column/PK/FK/unique/index ตรงกับ state ล่าสุด |
| Model ↔ Schema | table/column/type/size/nullability/key ตรง; Django `on_delete` ส่วนใหญ่ทำงานระดับ ORM ขณะที่ MySQL FK แสดง `NO ACTION` |
| DD ↔ Model | ตรง 109, ไม่ตรง 36, ไม่มีในระบบ 4, ไม่มีใน DD 4, กำกวม 4 (union 157 แถว) |
| DD ↔ Schema | ความไม่ตรงหลักเหมือน DD↔Model และยืนยันชนิดจริงได้ เช่น Member/Tutor/FK เป็น BIGINT, รูปหลาย field เป็น VARCHAR(100), total fee DECIMAL(10,2) |
| Pending model changes | ตรวจด้วยคำสั่ง Django ไม่ได้; static Model↔migration ไม่พบ pending state |
| RenameField / RenameModel | ไม่พบ |
| AlterField | 16 operations |
| AddField | 23 operations; ทุก field ยังใช้ใน Model ปัจจุบัน ยกเว้น `bk_report_type` ซึ่งถูก RemoveField แล้ว |
| RemoveField | 1: `Booking.bk_report_type` |
| Constraints/indexes | ไม่พบ Add/RemoveConstraint หรือ Add/RemoveIndex; `Inbox.unique_together`, unique O2O/`rf_qr_payload` และ FK indexes อยู่ใน state/schema |

> การแก้ไขข้อมูลจากรายงาน 01/02: `Member.id` และ `System.id` เป็น **BigAutoField/BIGINT** ตาม migration ล่าสุดและ schema จริง ไม่ใช่ AutoField/INT (`accounts/0003:13-16`, `admin_panel/0004:13-16`, schema `member.id`/`system.id` เป็น `bigint`).

## 6. สรุป Data Dictionary ↔ Model

- จับคู่ครบ 21 Model แต่ตรงทั้งหมดเพียง 6 ตาราง: Faculty, CourseGroup, Course, TutorRate, ScheduleDate, JobCompletion (`02_field_comparison.md` หัวข้อ 1)
- PK/FK กลุ่ม Member/Tutor ไม่ตรงอย่างมีนัยสำคัญ: DD วาง `mb_id`/`tut_id` เป็น VARCHAR(13) แต่ Model ใช้ implicit BigAutoField ของ Member และ Tutor เป็น O2O PK ไป Member; FK ที่อ้างสอง Model จึงเป็น BIGINT (`apps/accounts/models.py:8,15,31-33,52-58`)
- DD ระบุ TINYINT(1) หลาย field แต่ Model ใช้ IntegerField; `Notification.notif_is_read` เป็น BooleanField
- ImageField ที่ไม่กำหนด `max_length` ใช้ 100; จึงไม่ตรง DD VARCHAR(255) ใน Refill, Message และ TutoringActivity
- Choices ที่เสี่ยง runtime: `Booking.bk_report_reason` และ `Notification.notif_type` มีค่าที่ถูกใช้นอก Model choices
- รายละเอียดราย field ทั้ง 157 แถวอยู่ `02_field_comparison.md` หัวข้อ 2

## 7. สรุป Model ↔ Migration

### 7.1 Matrix ราย Model

| App.Model | Initial migration / field แรก | Migration ล่าสุดที่กระทบ Model | State ล่าสุดเทียบ Model | หลักฐาน |
|---|---|---|---|---|
| accounts.Member | `0001_initial` สร้าง 10 field | `0003` เปลี่ยน `id` เป็น BigAutoField; `0006` เปลี่ยน `mb_img.upload_to` | ตรง | `accounts/migrations/0001_initial.py:18-33`; `0003:13-16`; `0006:13-16`; model `accounts/models.py:8-33` |
| accounts.Tutor | `0001_initial` สร้างฐาน 10 field | `0002` choices status; `0004` เพิ่ม rating 5 ด้าน; `0005` เพิ่ม note/card; `0006` เปลี่ยน upload path | ตรง | `accounts/0001:37-51`; `0002:18-21`; `0004:13-36`; `0005:13-21`; `0006:18-21`; model:40-92 |
| admin_panel.System | `0001_initial` สร้าง 9 field | `0002` crd_val(5,2); `0004` id BigAuto; `0005-0007` เพิ่ม promptpay/fee/email_domain | ตรง | `admin_panel/0001:17-34`; `0002:13-20`; `0004:13-16`; `0005:13-16`; `0006:13-16`; `0007:13-16`; model:7-29 |
| courses.Faculty | `0001_initial` | ไม่มีภายหลัง | ตรง | `courses/0001_initial.py:27-35`; model `courses/models.py:6-12` |
| courses.Major | `0001_initial` | ไม่มีภายหลัง | ตรง | `courses/0001:51-62`; model:19-33 |
| courses.CourseGroup | `0001_initial` | ไม่มีภายหลัง | ตรง | `courses/0001:15-25`; model:40-47 |
| courses.Course | `0001_initial` | ไม่มีภายหลัง | ตรง | `courses/0001:38-49`; model:54-67 |
| tutoring.TutorCourse | `0001_initial` | `0003` upload path; `0004` เพิ่ม `tutc_rating` | ตรง | `tutoring/0001:41-55`; `0003:13-16`; `0004:13-16`; model:8-36 |
| tutoring.TutorRate | `0001_initial` | ไม่มีภายหลัง | ตรง | `tutoring/0001:63-73`; model:43-56 |
| tutoring.ScheduleDate | `0001_initial` (CreateModel + AddField FK) | ไม่มีภายหลัง | ตรง | `tutoring/0001:17-25,58-61`; model:63-76 |
| tutoring.TimeSlot | `0001_initial` | `0002` เพิ่ม `ts_status` | ตรง | `tutoring/0001:28-38`; `0002:13-16`; model:85-109 |
| bookings.Booking | `0001_initial` | `0002` เพิ่ม report fields/type; `0003` ลบ type เพิ่ม reason; `0004` เพิ่ม resolved date | ตรง | `bookings/0001:17-35`; `0002:13-26`; `0003:13-20`; `0004:13-16`; model:8-61 |
| bookings.BookingReportStatement | `0006` สร้างครบ 6 field | ไม่มีภายหลัง | ตรง | `bookings/0006:15-30`; model:71-98 |
| bookings.TutoringActivity | `0001_initial` | `0005` เปลี่ยน upload path รูป 3 field | ตรง | `bookings/0001:67-78`; `0005:13-26`; model:105-120 |
| bookings.JobCompletion | `0001_initial` | ไม่มีภายหลัง | ตรง | `bookings/0001:38-48`; model:127-140 |
| bookings.Review | `0001_initial` | ไม่มีภายหลัง | ตรง | `bookings/0001:50-65`; model:147-165 |
| messaging.Inbox | `0001_initial` | ไม่มีภายหลัง | ตรง รวม unique_together | `messaging/0001:16-26`; model:7-25 |
| messaging.Message | `0001_initial` | `0002` เพิ่ม `msg_img`, เปลี่ยน `msg`, `msg_sent_time` | ตรง | `messaging/0001:29-42`; `0002:13-26`; model:44-69 |
| credits.Refill | `0001_initial` | `0005` เพิ่ม `rf_qr_payload` unique | ตรง | `credits/0001:16-33`; `0005:13-16`; model:7-31 |
| credits.Withdrawals | `0001_initial` | `0002` เพิ่ม type/net; `0003` เปลี่ยน net default; `0004` เพิ่ม promptpay; `0006` เพิ่ม status 3 | ตรง | `credits/0001:34-54`; `0002:18-37`; `0003:13-16`; `0004:13-16`; `0006:13-16`; model:38-76 |
| notifications.Notification | `0001_initial` สร้างครบ 8 field | ไม่มีภายหลัง | ตรง | `notifications/0001:18-35`; model `notifications/models.py:7-54` |

### 7.2 สรุป operation พิเศษ

- `CreateModel`: 21; ครบทุก Model
- `AddField`: 23; field ที่เพิ่มและยังใช้: ratings 5 ด้าน, tutor note/card, System promptpay/fee/email domain, TimeSlot status, ScheduleDate FK, Withdrawals type/net/promptpay, Refill QR, Booking report fields/reason/resolved, Message image, TutorCourse rating
- `AlterField`: 16; ครอบคลุม PK BigAuto, choices, decimal precision, upload paths, message properties, withdrawal status/default
- `RemoveField`: `Booking.bk_report_type` เพียงรายการเดียว (`apps/bookings/migrations/0003_remove_booking_bk_report_type_and_more.py:13-15`); ไม่มีใน Model/schema ปัจจุบัน จึงสอดคล้อง
- ไม่พบ RenameField, RenameModel, Add/RemoveConstraint หรือ Add/RemoveIndex
- ไม่พบ field ใน current Model ที่ไม่มี migration state หรือ field ค้างใน latest migration state ที่ไม่มีใน Model จาก static comparison

## 8. สรุป Migration ↔ Schema

### 8.1 ผลการยืนยัน

- ตาราง migration history แสดง local migration 33 รายการ applied ครบ ตั้งแต่ initial ถึง leaf: accounts `0006`, admin_panel `0007`, bookings `0006`, courses `0001`, credits `0006`, messaging `0002`, notifications `0001`, tutoring `0004`
- Schema มีครบ 21 project tables/153 columns และตรงกับ latest migration state ด้านชื่อ column, MySQL type/length/precision/scale, nullable, PK, FK, unique และ indexes
- ตัวอย่างการยืนยัน: `system.crd_val=decimal(5,2)`, `system.total_accumulated_fee=decimal(10,2)`, `member.id=bigint`, `tutor.tut_id=bigint`, `refill.rf_slip=varchar(100)`, `notification.id=bigint`, `notification.notif_is_read=tinyint(1)`
- unique constraints จริง: `system.admin_id`, `member.user_id`, `refill.rf_qr_payload`, `inbox(member1_id,member2_id)`; ตรง migration/Model
- FK และ index จริงมีครบทุก relation ที่ Model ประกาศ

### 8.2 `on_delete` ระดับ ORM กับฐานข้อมูล

`on_delete` ใน Model/migration ส่วนใหญ่เป็น CASCADE/SET_NULL แต่ `information_schema.REFERENTIAL_CONSTRAINTS` ของ MySQL แสดง `DELETE_RULE=NO ACTION` เกือบทุก FK; `time_slot.sd_id` แสดง CASCADE ข้อยกเว้น (`apps/tutoring/migrations/0001_initial.py:34`). Django ดำเนินพฤติกรรม `on_delete` ผ่าน ORM Collector จึงไม่ถือเป็น migration drift โดยอัตโนมัติ แต่การลบด้วย SQL ตรงอาจมีพฤติกรรมต่างจากการลบผ่าน ORM และควรจัดเป็นข้อควรระวังระดับกลาง

## 9. ตารางปัญหาทั้งหมด

| ลำดับ | Model/Table | Field | ปัญหา | DD | Model | Migration | Schema | ประเภทความไม่ตรง | ระดับ | ผลกระทบ | แนวทางแก้ | ต้อง Migration หรือไม่ | หลักฐานไฟล์และบรรทัด |
|---:|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | System | total_accumulated_fee | Precision ต่าง | DECIMAL(5,2) | DecimalField(10,2) | `0006` Decimal(10,2) | decimal(10,2) | DD↔Model/Migration/Schema | กลาง | เอกสารจำกัดยอดต่ำกว่าระบบ; ไม่ทำให้ข้อมูลในระบบสูญหาย | ตัดสิน requirement แล้วแก้ DD เป็น 10,2 หรือ Model เป็น 5,2 | ถ้าแก้ Django: ต้อง | DD md:35; `admin_panel/models.py:25`; `migrations/0006:13-16` |
| 2 | System | admin_pwd | DD มี field แต่ table ไม่มี | VARCHAR(255) | ไม่มี; ใช้ User.password | ไม่มีใน system state | ไม่มี column; `auth_user.password` varchar(128) | DD↔Model/Migration/Schema | กลาง | ผู้อ่าน DD เข้าใจผิดเรื่องตำแหน่ง credential | แก้ DD ให้อ้าง `auth.User`; ไม่ควรเพิ่ม password ซ้ำ | ไม่ต้อง | DD md:36; `admin_panel/models.py:8-14`; schema `auth_user.password` |
| 3 | System | admin_email | DD มี field แต่ table ไม่มี | VARCHAR(255) | property จาก User.email | ไม่มี DB field | ไม่มี system column; auth_user.email varchar(254) | DD↔สามชั้น | กลาง | เอกสารชื่อ/size ผิด | แก้ DD เป็น relation/property และ VARCHAR(254) ของ auth_user | ไม่ต้อง | DD md:37; `admin_panel/models.py:38-40`; schema query |
| 4 | System | id/admin | Django มีแต่ DD ไม่มี | ไม่ระบุ | BigAuto PK + O2O User | `0001`, `0004` | id bigint, admin_id int UNIQUE/FK | DD ขาด field/relation | กลาง | DD ไม่สะท้อน PK/relation จริง | เพิ่มใน DD | ไม่ต้อง | `admin_panel/0001:20,28`; `0004:13-16`; schema query |
| 5 | Major | mj_abbr | DD ทำเครื่องหมายตัดออกแต่ยังใช้อยู่ | VARCHAR(10), “ตัดออก” | CharField(10) | `courses 0001` | varchar(10) | DD กำกวม | กลาง | ไม่ทราบเจตนาว่าควรคงหรือลบ | ตัดสิน requirement ก่อน | ถ้าลบ Django: ต้อง | DD md:59; `courses/models.py:22`; `courses/0001:56` |
| 6 | Member | mb_id/id | PK ชนิดต่าง | VARCHAR(13) PK | implicit BigAutoField | `accounts 0003` BigAutoField | bigint auto_increment | DD↔สามชั้น | สูง | PK/FK หลายตารางไม่ตรงแบบข้อมูล | เลือก canonical ID; วิเคราะห์ข้อมูล/relations ก่อนเปลี่ยน | ถ้าแก้ Django: ต้อง | DD md:92; `accounts/models.py:8,31-33`; `accounts/0003:13-16`; schema member.id |
| 7 | Member | mb_pwd | DD มีแต่ Model ไม่มี | VARCHAR(255) | ใช้ User relation | ไม่มี member field | auth_user.password varchar(128) | DD↔สามชั้น | กลาง | เอกสาร authentication ผิด | แก้ DD ให้อ้าง User.password | ไม่ต้อง | DD md:95; `accounts/models.py:15`; `accounts/0001:30` |
| 8 | Member | user | ระบบมีแต่ DD ไม่มี | ไม่ระบุ | O2O→User/CASCADE | `accounts 0001` | user_id int UNIQUE/FK | DD ขาด relation | กลาง | DD ไม่อธิบาย account identity | เพิ่ม relation ใน DD | ไม่ต้อง | `accounts/models.py:15`; `accounts/0001:30`; schema constraints |
| 9 | Member | mb_status | Type ต่าง | TINYINT(1), choices 0/1/2 | IntegerField, choicesตรง | `0001` IntegerField | int | DD↔สามชั้น | กลาง | DB รองรับค่านอกโดเมน; Model validationไม่เกิดเมื่อ save ตรง | กำหนด canonical type/constraint | ถ้าแก้ schema: ต้อง | DD md:99; `accounts/models.py:9-21`; `accounts/0001:27` |
| 10 | Tutor | tut_id | PK/FK ชนิดต่าง | VARCHAR(13) PK/FK Member | O2O PK→Member BigAuto | `accounts 0001` | bigint PK/FK | DD↔สามชั้น | สูง | กระทบ Tutor และ FK ต่อเนื่อง | แก้ DD ตาม schema หรือวาง migration ID ครั้งใหญ่ | ถ้าแก้ Django: ต้อง | DD md:111; `accounts/models.py:52-58`; `accounts/0001:40`; schema tutor.tut_id |
| 11 | Tutor | tut_has_exp | Type ต่าง | TINYINT(1) | IntegerField choices 0/1 | `0001` IntegerField | int | DD↔สามชั้น | กลาง | DB ไม่จำกัด 0/1 | ใช้ validator/check หรือแก้ DD | ถ้าแก้ schema: ต้อง |
| 12 | Tutor | tut_status | Type/label ค่า 0 ต่าง | 0=ยังไม่อนุมัติ; 1=อนุมัติ; 2=ปฏิเสธ; 3=ระงับ | 0=รอการตรวจสอบ; ค่าอื่นตรง | `0002` เหมือน Model | int | DD↔สามชั้น | กลาง | ความหมายใกล้กันแต่รายงาน/UI อาจใช้คำต่าง | กำหนด label กลาง; พิจารณา constraint | เฉพาะ labelไม่ต้อง; type/constraintต้อง | DD md:124; `accounts/models.py:41-46`; `accounts/0002:18-21` |
| 13 | TutorCourse | tutc_status | Type ต่าง | TINYINT(1) | IntegerField | `tutoring 0001` | int | DD↔สามชั้น | กลาง | DB ไม่จำกัด 0/1 | แก้ DD หรือเพิ่ม constraint | ถ้าแก้ schema: ต้อง |
| 14 | TutorCourse | tutc_rating | DD ต้นฉบับไม่ให้ schema | มีแต่ข้อความรีวิว | DecimalField(3,2) | `0004` AddField | decimal(3,2) | DD ไม่ครบ | กลาง | ไม่สามารถยืนยัน requirement อิสระ | อนุมัติชื่อ/Type/Size แล้วเติม DD | ไม่ต้องหากยอมรับปัจจุบัน | PDF หน้า 6; DD md:141; `tutoring/0004:13-16` |
| 15 | TutorCourse | tut_id | FK ชนิดต่าง | VARCHAR(13) | FK→Tutor BigAuto | `0001` | bigint FK | DD↔สามชั้น | สูง | relation schema ไม่ตรงเอกสาร | แก้พร้อมกลยุทธ์ Member/Tutor ID | ถ้าแก้ Django: ต้อง |
| 16 | TimeSlot | ts_status | Type และความหมายค่า 1 ต่าง | 0=ว่าง, 1=จองแล้ว | 0=ว่าง, 1=ล็อกแล้ว | `0002` เหมือน Model | int | DD↔สามชั้น + semantic | สูง | workflow เข้าใจผิด; “ล็อก” เกิดเมื่อรับงาน ไม่ใช่ทุกการจอง | กำหนดสถานะตาม logic จริงและทำเอกสาร/โค้ดให้ตรง | label/DD อาจไม่ต้อง; schema typeต้อง | DD md:177; `tutoring/models.py:83-98`; `tutoring/0002:13-16`; views:271,290 |
| 17 | Refill | ธนาคารต้นทาง | DD ไม่ให้ชื่อ/Type/Sizeและระบบไม่มี | รายการกำกวม | ไม่มี | ไม่มี | ไม่มี | DD↔สามชั้น | กลาง | Requirement ขาด/เก็บข้อมูลไม่ได้ถ้าจำเป็น | ระบุ requirement ก่อนเพิ่มหรือลบจาก DD | ถ้าเพิ่ม: ต้อง | PDF หน้า 8; DD md:190,200; `credits/models.py:7-27` |
| 18 | Refill | rf_slip | Size ต่าง | VARCHAR(255) | ImageField max_length=100 | `0001` max default100 | varchar(100) | DD↔สามชั้น | สูง | path >100 อาจบันทึกไม่ได้/ถูกตัดตาม backend | เพิ่ม max_length=255 หรือแก้ DDเป็น100หลังตรวจ path จริง | ถ้าเปลี่ยน: ต้อง | DD md:193; `credits/models.py:18`; `credits/0001:23`; schema |
| 19 | Refill | rf_status | Type ต่าง | TINYINT(1) choices 0/1/2 | IntegerField choicesตรง | `0001` | int | DD↔สามชั้น | กลาง | DB ไม่จำกัดโดเมน | เพิ่ม constraint/แก้ DD | ถ้าเปลี่ยน schema: ต้อง |
| 20 | Refill | mb_id/member_id | FK ชื่อ/ชนิดต่าง | VARCHAR(13) | FK→Member BigAuto | `0001` | member_id bigint | DD↔สามชั้น | สูง | relation documentation ผิด | แก้พร้อม Member ID | ถ้าแก้ Django: ต้อง |
| 21 | Booking | bk_status | Type ต่าง | TINYINT(1), 0-6 | IntegerField, choicesตรง | `0001` | int | DD↔สามชั้น | กลาง | DB ไม่จำกัด 0-6 | เพิ่ม constraintหรือแก้ DD | ถ้าเปลี่ยน schema: ต้อง |
| 22 | Booking | bk_report_reason | Runtime ใช้ค่านอก choices | 1/2/3/4/other | choices 1/2/3/4/other | `0003` เหมือน Model | varchar(10), DBไม่บังคับ choices | Model/Migration↔runtime และ DD↔runtime | สูง | ModelForm/full_clean ปฏิเสธ; save ตรงบันทึกได้; display คืนค่าดิบ | รวม canonical choices/normalize ให้แหล่งเดียวและตรวจข้อมูลเดิม | Choices change: ต้อง migration state; DB typeไม่เปลี่ยน | DD md:219; `bookings/models.py:28-35`; `bookings/0003:17-20`; views:19-45; templates linesในหัวข้อ 10 |
| 23 | Booking | mb_id/member_id | FK ชนิดต่าง | VARCHAR(13) | FK→Member BigAuto | `0001` | bigint | DD↔สามชั้น | สูง | relation ไม่ตรง | แก้พร้อม Member ID | ถ้าแก้ Django: ต้อง |
| 24 | Inbox | ib_mb_id1/member1_id | ชื่อ/ชนิด FK ต่าง | VARCHAR(13) | FK→Member BigAuto | `0001` | bigint | DD↔สามชั้น | สูง | schema integration ตาม DD ใช้ไม่ได้ | แก้ DDหรือ redesign ID | ถ้าแก้ Django: ต้อง |
| 25 | Inbox | ib_mb_id2/member2_id | ชื่อ/ชนิด FK ต่าง | VARCHAR(13) | FK→Member BigAuto | `0001` | bigint | DD↔สามชั้น | สูง | เช่นเดียวกับข้อ 24 | เช่นเดียวกับข้อ 24 | ถ้าแก้ Django: ต้อง |
| 26 | Inbox | unique pair | DD ไม่ระบุ unique_together | ไม่ระบุ | unique_together | `0001 options` | UNIQUE(member1_id,member2_id) | DD ขาด constraint | กลาง | เอกสารไม่บอก duplicate policy; กลับลำดับคู่ยังสร้างซ้ำได้ | ระบุ constraint และพิจารณาคู่แบบไม่เรียงลำดับ | ถ้าเปลี่ยน constraint: ต้อง |
| 27 | Message | msg_img | Size ต่าง | VARCHAR(255) | ImageField max100 | `0002` max default100 | varchar(100) | DD↔สามชั้น | สูง | path ยาวอาจเก็บไม่ได้ | max_length255หรือแก้ DD | ถ้าเปลี่ยน: ต้อง |
| 28 | Message | msg_is_read | Type/validation ต่าง | TINYINT(1), 0/1 | IntegerField ไม่มี choices/validator | `0001` | int | DD↔สามชั้น | กลาง | เก็บค่านอก 0/1 ได้ | BooleanFieldหรือ constraint/choices | ถ้าเปลี่ยน field/constraint: ต้อง |
| 29 | Message | msg_sender_mb_id/sender_id | ชื่อ/ชนิด FK ต่าง | VARCHAR(13) | FK→Member BigAuto | `0001` | bigint | DD↔สามชั้น | สูง | relation ไม่ตรง | แก้พร้อม Member ID | ถ้าแก้ Django: ต้อง |
| 30 | Message | ib_id/inbox_id | ชื่อ column ต่าง | ib_id INT | Python `inbox`; column `inbox_id` | `0001` | inbox_id int | DD↔สามชั้น | ต่ำ | integration ที่อิงชื่อ DD ผิด | แก้ DD เป็น inbox_id หรือกำหนด db_column | ถ้าแก้ column: ต้อง |
| 31 | TutoringActivity | ta_img1-3 | Size ต่าง 3 field | VARCHAR(255) | ImageField max100 | `0005` max default100 | varchar(100) | DD↔สามชั้น | สูง | path ยาวอาจเก็บไม่ได้ | ตั้ง max_length255หรือแก้ DD | ถ้าเปลี่ยน: ต้อง | DD md:269-271; `bookings/models.py:113-115`; `bookings/0005:13-26` |
| 32 | Review | คะแนน 5 field | Type/validatorต่าง | TINYINT(1) | IntegerField ไม่มี validator | `0001` | int | DD↔สามชั้น | สูง | บันทึกคะแนนนอกช่วงที่ UIคาดได้ กระทบค่าเฉลี่ย | กำหนด Min/MaxValidator และ DB CheckConstraint ตามช่วงที่อนุมัติ | ต้อง | DD md:295-299; `bookings/models.py:155-159`; `bookings/0001:54-58` |
| 33 | Withdrawals | wd_type | Type ต่าง | TINYINT(1), 0/1 | IntegerField choicesตรง | `0002` | int | DD↔สามชั้น | กลาง | DB เก็บค่านอกโดเมนได้ | constraintหรือแก้ DD | ถ้าเปลี่ยน schema: ต้อง |
| 34 | Withdrawals | wd_status | Type/labelค่า3ต่าง | 3=ยกเลิกการถอน | 3=ยกเลิกโดยผู้ใช้ | `0006` เหมือน Model | int | DD↔สามชั้น | กลาง | รายงาน/ความหมาย actor ต่าง | กำหนด labelกลางและ constraint | labelอย่างเดียวไม่ต้อง; constraintต้อง |
| 35 | Withdrawals | mb_id/member_id | FK ชนิดต่าง | VARCHAR(13) | FK→Member BigAuto | `0001` | bigint | DD↔สามชั้น | สูง | relation ไม่ตรง | แก้พร้อม Member ID | ถ้าแก้ Django: ต้อง |
| 36 | Withdrawals | wd_promptpay_no | Djangoมีแต่ DDไม่มี | ไม่ระบุ | CharField(20), nullable | `0004` AddField | varchar(20) nullable | DD ขาด field | กลาง | DD ไม่ครอบคลุมช่องทางจ่าย | เพิ่มใน DD | ไม่ต้อง |
| 37 | BookingReportStatement | brs_role | DD ไม่แจกแจง choices | VARCHAR(10) | student/tutor | `0006` เหมือน Model | varchar(10) | DD ไม่ครบ | กลาง | integrationไม่รู้โดเมน | เพิ่ม choices ใน DD | ไม่ต้อง |
| 38 | BookingReportStatement | mb_id/member_id | ชื่อ/ชนิด FK ต่าง | VARCHAR(13) | FK→Member BigAuto | `0006` | bigint | DD↔สามชั้น | สูง | relation ไม่ตรง | แก้พร้อม Member ID | ถ้าแก้ Django: ต้อง |
| 39 | Notification | id | PK width ต่าง | INT | BigAutoField | `0001` BigAuto | bigint | DD↔สามชั้น | ต่ำ | schemaรองรับช่วงมากกว่า DD; integration 32-bitอาจผิด | แก้ DDเป็น BIGINT | ไม่ต้อง |
| 40 | Notification | notif_type | DDไม่แจกแจงและ runtimeมีค่านอก choices | VARCHAR(30) ไม่มีค่า | 17 choices | `0001` 17 choices | varchar(30), ไม่บังคับโดเมน | DD↔Model + Model/Migration↔runtime | สูง | `booking_cancelled` ไม่ผ่าน form/full_clean; display คืน code ดิบ; consistency เสีย | เพิ่ม canonical choice และแก้ DD; ตรวจข้อมูลเดิม | Choices change: ต้อง migration state | DD md:352; `notifications/models.py:9-27`; `notifications/0001:22`; `signals.py:108` |
| 41 | Notification | notif_is_read | Model typeต่าง แต่ schemaตรง DD storage | TINYINT(1), ไม่แจกแจงค่า | BooleanField False/True | `0001` Boolean | tinyint(1) | DD↔Model semantics/detail | ต่ำ | DD ไม่บอกความหมาย; DB storageตรง | เติม False/Trueหรือ0/1ใน DD | ไม่ต้อง |
| 42 | Notification | recipient_id | FK widthต่าง | VARCHAR(13) | FK→Member BigAuto | `0001` | bigint | DD↔สามชั้น | สูง | relation ไม่ตรง | แก้พร้อม Member ID | ถ้าแก้ Django: ต้อง |
| 43 | ทุก relation | on_delete | DB rule ส่วนใหญ่ NO ACTION | DDไม่ระบุ | CASCADE/SET_NULL | state เหมือน Model | MySQL ส่วนใหญ่ NO ACTION | Model/Migration semantics↔DB DDL | กลาง | ลบผ่าน SQLตรงต่างจาก ORM; อาจติด constraint/ไม่ cascade | ใช้ ORMเป็นหลักและเอกสาร; หากต้อง DB-level cascade ให้ออกแบบเฉพาะ | อาจต้อง migration/RunSQL หากเลือกแก้ |
| 44 | โครงการ | dry-run check | ตรวจ pending ด้วย Djangoไม่ได้ | - | - | static ตรง | schemaตรง | ข้อจำกัดการตรวจ | กลาง | ยังไม่มี machine-generated “No changes detected” | ซ่อม Python runtimeแล้วรันคำสั่งเดิม | ไม่ใช่ migrationเอง |
| 45 | Data Dictionary | จำนวน/เลขหัวข้อ | จำนวน 19 แต่จริง21; เลขข้าม/ซ้ำ | ผิด/ซ้ำ | 21 Model | 21 CreateModel | 21 tables | DD metadata | ต่ำ | อ้างอิงเอกสารสับสน | แก้เลข/จำนวน | ไม่ต้อง |
| 46 | TimeSlot | ts_id description | คำอธิบายซ้ำ sd_id | “รหัสวันที่เปิดสอน” | “รหัสช่วงเวลา” | `0001` รหัสช่วงเวลา | int PK | DD description | ต่ำ | เข้าใจ semantic ผิด | แก้ description DD | ไม่ต้อง |
| 47 | Booking | bk_stu_datetime | หมายเหตุ “รวม” ไม่บอกที่มา | DATETIME/รวม | DateTimeField | `0001` | datetime(6) | DD กำกวม | ต่ำ | trace requirement เดิมไม่ได้ | ระบุว่ารวมวัน+เวลาใด | ไม่ต้อง |

## 10. ตาราง Choices ทั้งระบบ

| Model.Field | Data Dictionary choices | Model choices | Migration choices | ค่าที่ใช้จริงนอก Model/หมายเหตุ | Default | ปัญหา | หลักฐาน |
|---|---|---|---|---|---|---|---|
| Member.mb_status | 0=ปิดการใช้งาน<br>1=ใช้งานปกติ<br>2=ระงับชั่วคราว | 0=ปิดการใช้งาน<br>1=ใช้งานปกติ<br>2=ระงับชั่วคราว | เหมือน Model | ใช้ 0/1/2 ตรง | 1 | choices ตรง; DD TINYINT แต่สามชั้นจริง INT | DD md:99; `accounts/models.py:9-21`; `accounts/0001:27`; admin views:47,420-425 |
| Tutor.tut_has_exp | 0=ไม่เคยสอน<br>1=เคยสอน | 0=ไม่เคยสอน<br>1=เคยสอน | เหมือน Model | ใช้ 0/1 ตรง | 0 | choicesตรง; Typeต่าง | DD md:116; `accounts/models.py:47-62`; `accounts/0001:44`; tutoring views:454,521 |
| Tutor.tut_status | 0=ยังไม่อนุมัติ<br>1=อนุมัติแล้ว<br>2=ปฏิเสธ<br>3=ระงับการสอน | 0=รอการตรวจสอบ<br>1=อนุมัติแล้ว<br>2=ปฏิเสธ<br>3=ระงับการสอน | `0001` เดิม: 0=ยังไม่อนุมัติ,1=อนุมัติแล้ว,2=ระงับการสอน; `0002` ล่าสุดเหมือน Model 4 ค่า | ใช้ครบ0-3ตาม Model | 0 | ค่า0 labelต่าง DD; migrationแก้ประวัติค่า2และเพิ่ม3 | DD md:124; `accounts/models.py:41-46`; `accounts/0001:47`; `accounts/0002:18-21`; admin views:210-269 |
| TutorCourse.tutc_status | 0=ปิดรับสอน<br>1=เปิดรับสอน | 0=ปิดรับสอน<br>1=เปิดรับสอน | เหมือน Model | ใช้ 0/1 ตรง | 1 | choicesตรง; Typeต่าง | DD md:140; `tutoring/models.py:9-19`; `tutoring/0001:49`; views:662,959-962 |
| TimeSlot.ts_status | 0=ว่าง<br>1=จองแล้ว | 0=ว่าง<br>1=ล็อกแล้ว | เหมือน Model (`0002`) | 1 ตั้งเมื่อติวเตอร์รับงาน/ล็อก slot; 0 เมื่อว่างหรือปล่อย slot | 0 | ค่า1 ความหมายไม่ตรง DD; Typeต่าง | DD md:177; `tutoring/models.py:86-98`; `tutoring/0002:13-16`; tutoring views:271,290; bookings views:173-174 |
| Booking.bk_status | 0=จอง<br>1=รับงานแล้ว<br>2=เรียนแล้ว<br>3=แจ้งจบงาน<br>4=ยืนยันการจบงาน<br>5=รีวิวแล้ว<br>6=ปฏิเสธ | เหมือน DDครบทุกค่า | เหมือน Model (`0001`) | ใช้ครบ0-6; UIใช้ labelตามมุมมองบางค่า | 0 | choicesตรง; DD TINYINT แต่สามชั้นจริง INT | DD md:217; `bookings/models.py:9-26`; `bookings/0001:27`; bookings views:253-258 |
| Booking.bk_report_reason | `'1'`=หลักฐานไม่ตรง<br>`'2'`=ไม่ได้สอน<br>`'3'`=เนื้อหาไม่ตรง<br>`'4'`=กดพลาด<br>`'other'`=อื่นๆ | `'1'`=หลักฐานการสอนไม่ตรงความจริง<br>`'2'`=ไม่ได้สอนเลยแต่แจ้งจบงาน<br>`'3'`=เนื้อหาไม่ตรงที่ตกลงไว้<br>`'4'`=ผู้เรียนกดยืนยันโดยไม่ตั้งใจ<br>`'other'`=อื่นๆ | เหมือน Model (`0003`) | เพิ่ม `'5'`=ผู้เรียนไม่เข้าเรียน, `'6'`=ติดต่อไม่ได้, `'7'`=ไม่สามารถตกลงกันได้, `'8'`=อื่นๆ, `'t_no_show'`→2, `'s_no_show'`→5, `'contact'`/`'cannot_contact'`→6, `'agree'`→7, `'other'`→8, `'cancel'`=ข้อพิพาทยกเลิกจากติวเตอร์ | ไม่มี | ค่านอก choicesกระทบ validationและ `get_*_display()` | DD md:219; `bookings/models.py:28-35`; `bookings/0003:17-20`; `bookings/views.py:19-45,186-188,612,893`; templates `tutor_requests.html:1079-1091`, `student_bookings.html:942-954` |
| BookingReportStatement.brs_role | ไม่แจกแจง | `'student'`=Student<br>`'tutor'`=Tutor | เหมือน Model (`0006`) | ใช้ student/tutor; UIแปลเป็นผู้เรียน/ติวเตอร์ | ไม่มี | DDรายละเอียดไม่ครบ; ทั้งสองค่าไม่เกิน VARCHAR(10) | DD md:339; `bookings/models.py:72-91`; `bookings/0006:19`; bookings views:224 |
| Refill.rf_status | 0=รอตรวจสอบ<br>1=ผ่านการตรวจสอบ<br>2=ไม่ผ่านการตรวจสอบ | เหมือน DD | เหมือน Model (`0001`) | ใช้0→1/2ตรง | 0 | choicesตรง; Typeต่าง | DD md:196; `credits/models.py:8-21`; `credits/0001:25`; admin views:327-363 |
| Withdrawals.wd_type | 0=นำฝาก<br>1=รายได้ | เหมือน DD | เหมือน Model (`0002`) | ใช้0เลือกเครดิตนำฝาก,1เครดิตรายได้ | 0 | choicesตรง; Typeต่าง | DD md:313; `credits/models.py:40-55`; `credits/0002:18-25`; credits views:406-451 |
| Withdrawals.wd_status | 0=รอดำเนินการ<br>1=จ่ายแล้ว<br>2=ปฏิเสธการถอน<br>3=ยกเลิกการถอน | 0=รอดำเนินการ<br>1=จ่ายแล้ว<br>2=ปฏิเสธการถอน<br>3=ยกเลิกโดยผู้ใช้ | `0001` มี0-2; `0006` ล่าสุดเหมือน Model 0-3 | adminใช้0→1/2; ผู้ใช้ใช้0→3 | 0 | ค่า3 labelต่าง; Typeต่าง | DD md:322; `credits/models.py:45-66`; `credits/0001:46`; `credits/0006:13-16`; credits views:214-220 |
| Notification.notif_type | ไม่แจกแจง | `'booking_new'`=มีการจองติวใหม่<br>`'booking_accepted'`=การจองได้รับการยืนยัน<br>`'booking_rejected'`=การจองถูกปฏิเสธ<br>`'booking_completed'`=มีการแจ้งจบงานที่ต้องยืนยัน<br>`'booking_credited'`=งานเสร็จสิ้น ได้รับเครดิตแล้ว<br>`'booking_reviewed'`=มีรีวิวใหม่<br>`'booking_reported'`=มีการรายงานปัญหา<br>`'tutor_approved'`=ติวเตอร์ได้รับการอนุมัติ<br>`'tutor_rejected'`=ติวเตอร์ถูกปฏิเสธ<br>`'tutor_suspended'`=บัญชีติวเตอร์ถูกระงับ<br>`'refill_approved'`=เติมเครดิตผ่านการตรวจสอบ<br>`'refill_rejected'`=เติมเครดิตไม่ผ่านการตรวจสอบ<br>`'withdraw_paid'`=ถอนเงินเข้าบัญชีเรียบร้อย<br>`'admin_refill'`=มีคำขอเติมเครดิต<br>`'admin_withdraw'`=มีคนขอถอนเครดิต<br>`'admin_tutor_new'`=มีติวเตอร์สมัครใหม่รอ approve<br>`'admin_reported'`=มีการรายงานปัญหา | เหมือน Modelครบ17ค่า (`0001`) | `'booking_cancelled'`=ผู้เรียนยกเลิกการจองของคุณ ถูกสร้างจริงแต่ไม่มีใน choices | ไม่มี | DDขาดโดเมน; runtime value นอก choicesกระทบ form/full_clean/display consistency | DD md:352; `notifications/models.py:9-27,45`; `notifications/0001:22`; `notifications/signals.py:76-111` โดยค่าพิเศษบรรทัด108 |

### Status fields ที่ไม่มี Model choices

- `Message.msg_is_read`: DD 0=ยังไม่อ่าน, 1=อ่านแล้ว; Model/migration IntegerField default=0 ไม่มี choices/validator; schema `int` (`docs/...md:256`; `apps/messaging/models.py:54`; `messaging/0001:35`).
- `Notification.notif_is_read`: DD ไม่แจกแจง; Model/migration BooleanField default=False; schema `tinyint(1)`; การใช้จริง False=ยังไม่อ่าน, True=อ่านแล้ว (`docs/...md:355`; `apps/notifications/models.py:48`; `notifications/0001:25`; `apps/notifications/views.py:16-24`).

## 11. ปัญหาระดับสูง

1. กลุ่มรหัส Member/Tutor และ Foreign Key ที่เกี่ยวข้อง: Data Dictionary กำหนด `VARCHAR(13)` แต่ระบบจริงใช้ `BigAutoField`/`BIGINT` ส่งผลต่อการออกแบบ interface, การนำเข้าข้อมูล และระบบภายนอกที่ยึดเอกสารเป็นสัญญาข้อมูล
2. `TimeSlot.ts_status`: ค่า 1 ในเอกสารหมายถึง “จองแล้ว” แต่ระบบหมายถึง “ล็อกแล้ว” และถูกตั้งเมื่อ Tutor รับงาน ความต่างนี้กระทบความเข้าใจ workflow โดยตรง
3. ฟิลด์ไฟล์หลายรายการกำหนด `VARCHAR(255)` ในเอกสาร แต่ Model และ schema จำกัด 100 ตัวอักษร เช่น `rf_slip` จึงมีความเสี่ยงเมื่อ path ยาว
4. `Booking.bk_report_reason`: views/templates ใช้ค่าเพิ่มเติมนอก Model choices ทำให้ validation และ `get_bk_report_reason_display()` ไม่สอดคล้องกัน
5. `Notification.notif_type`: signal สร้างค่า `booking_cancelled` ซึ่งไม่มีใน Model choices
6. `Review` ไม่มี validator หรือ database constraint บังคับช่วงคะแนน แม้ความหมายทางธุรกิจเป็นคะแนนแบบมีขอบเขต

## 12. ปัญหาระดับกลาง

- ความกว้าง/ชนิดข้อมูลใน Data Dictionary ต่างจากระบบจริงหลายจุด โดยเฉพาะ `TINYINT` เทียบกับ `IntegerField`/`INT`, decimal precision และชื่อ Foreign Key
- Data Dictionary แสดง password/email เป็นคอลัมน์ของ `System` หรือ `Member` ทั้งที่ระบบอ้าง `django.contrib.auth.models.User`
- `Major.mj_abbr` มีหมายเหตุ “ตัดออก” แต่ยังมีอยู่ครบใน Model, migration และ schema จึงต้องตัดสิน requirement ก่อนดำเนินการ
- `TutorCourse.tutc_rating` มีในระบบ แต่เอกสารหน้า 6 ให้เพียงข้อความ “รีวิวแยกตามรายวิชาที่เปิดสอน” โดยไม่ระบุ Attribute Name, Type หรือ Size
- รายการ “ธนาคารต้นทาง” ของ Refill ไม่มีชื่อ Attribute/Type/Size และไม่มี field รองรับในระบบ ต้องยืนยันว่าต้องจัดเก็บจริงหรือเป็นเพียงข้อความประกอบ
- MySQL แสดง `DELETE_RULE=NO ACTION` สำหรับ Foreign Key ส่วนใหญ่ ขณะที่ Django ประกาศ `CASCADE`/`SET_NULL`; การลบผ่าน ORM ยังใช้ Collector แต่การลบด้วย SQL ตรงมีพฤติกรรมต่างกัน
- ไม่สามารถรับรองสถานะ pending migration ด้วยคำสั่ง Django ได้ เพราะ Python runtime เริ่มทำงานไม่ได้ แม้การเทียบแบบ static และ schema จริงจะตรงกัน

## 13. ปัญหาระดับต่ำ

- Data Dictionary ระบุจำนวนตาราง/ลำดับหัวข้อไม่สอดคล้องกับเนื้อหาจริง
- ไม่มีหัวข้อ 4.3.1.18, หัวข้อ 4.3.1.20 ซ้ำ และเลขตาราง 4.15 ถูกใช้ทั้ง Message และ Booking Report Statement
- คำอธิบาย `TimeSlot.ts_id` ซ้ำความหมายของ `sd_id`
- หมายเหตุ “รวม” ของ `Booking.bk_stu_datetime` ไม่อธิบายว่านำวันและเวลาใดมารวม
- ค่า label บางสถานะต่างกันเล็กน้อย เช่น Tutor ค่า 0 และ Withdrawals ค่า 3 แม้ค่าตัวเลขและ workflow หลักยังสอดคล้อง

## 14. ความกำกวมและข้อผิดพลาดใน Data Dictionary

| หน้า | รายการ | ผลการตรวจสอบ |
|---:|---|---|
| 2 | ระบุจำนวนตาราง 19 ตาราง | ระบบและ migration มี 21 project models/tables; เนื้อหาเอกสารเองมีรายการมากกว่า 19 |
| 3 | `mj_abbr` หมายเหตุ “ตัดออก” | ยังมี field จริงเป็น `CharField(max_length=10)` และ schema `varchar(10)` |
| 6 | “รีวิวแยกตามรายวิชาที่เปิดสอน” | สอดคล้องเชิงแนวคิดกับ `TutorCourse.tutc_rating` แต่ต้นฉบับไม่ระบุ Attribute Name, Type หรือ Size จึงไม่ควรถือว่าเอกสารกำหนด schema แล้ว |
| 8 | “ธนาคารต้นทาง” | ไม่พบ Attribute Name, Type หรือ Size และไม่พบ field ตรงกันใน `Refill`; ต้องเก็บ requirement เพิ่มเติมก่อนออกแบบ |
| 9–10 | Booking ต่อเนื่องข้ามหน้า | รวมเป็นตารางเดียวในการเปรียบเทียบแล้ว; ไม่ถือเป็นสองตาราง |
| 12 | ไม่มีหัวข้อ 4.3.1.18 | เป็นช่องว่างของเลขหัวข้อในต้นฉบับ ห้ามสร้างหัวข้อสมมติ |
| 14 | หัวข้อ 4.3.1.20 ซ้ำ | ต้องแก้เลขหัวข้อในเอกสารโดยไม่เปลี่ยนชื่อ table/model |
| 14 | Booking Report Statement ใช้เลขตาราง 4.15 ซ้ำกับ Message | ต้องกำหนดเลขตารางใหม่ในเอกสาร |
| 7 | `TimeSlot.ts_id` | Description ระบุเป็นรหัสวันที่เปิดสอน ซึ่งซ้ำกับ `sd_id`; ระบบใช้เป็นรหัสช่วงเวลา |
| 9 | `Booking.bk_stu_datetime` หมายเหตุ “รวม” | ไม่ชัดว่ารวม field ใดจากแบบเดิม |

## 15. ข้อเสนอแนะการแก้ไข

### 15.1 ฝั่ง Django / Model / Migration

ตารางนี้เป็นข้อเสนอเท่านั้น ยังไม่ได้แก้ไฟล์ใด:

| Model | Field | ค่าปัจจุบัน | ค่าที่ควรเป็น | ไฟล์ที่ต้องแก้หากอนุมัติ | ผลกระทบ | ต้องสร้าง migration | ต้องตรวจข้อมูลเดิม | ความเร่งด่วน | หลักฐาน |
|---|---|---|---|---|---|---|---|---|---|
| Booking | `bk_report_reason` | Model: `'1'`,`'2'`,`'3'`,`'4'`,`'other'`; runtime ยังใช้ `'5'`,`'6'`,`'7'`,`'8'`,`'cancel'` และ alias หลายค่า | กำหนด canonical choices ชุดเดียวจาก requirement แล้วให้ทุกชั้นอ้างชุดนั้น; ห้ามเลือกชุดค่าแทนเจ้าของระบบ | `apps/bookings/models.py`, `apps/bookings/views.py`, templates ที่ส่ง/แสดงเหตุผล | แก้ validation และ display label ที่ไม่สอดคล้อง | ต้องสร้าง migration state เมื่อแก้ choices | ต้องตรวจ distinct values และแผน normalize | สูง | `apps/bookings/models.py:28-35`; `views.py:19-45,186-188,612,893`; `bookings/migrations/0003:17-20`; templates `tutor_requests.html:1079-1091`, `student_bookings.html:942-954` |
| Notification | `notif_type` | choices 17 ค่า แต่ signal บันทึก `'booking_cancelled'` นอก choices | เพิ่มค่าดังกล่าวพร้อม label ที่อนุมัติ หรือเปลี่ยน signal ไปใช้ค่ามาตรฐานที่มีอยู่ | `apps/notifications/models.py`, `apps/notifications/signals.py` | ทำให้ form/full_clean/display ใช้โดเมนเดียวกัน | ต้อง เมื่อแก้ choices | ต้องตรวจ distinct values โดยเฉพาะ `booking_cancelled` | สูง | `apps/notifications/models.py:9-27,45`; `signals.py:76-111`; `notifications/migrations/0001:22` |
| TimeSlot | `ts_status` | 0=ว่าง, 1=ล็อกแล้ว; DD ระบุ 1=จองแล้ว | ให้เจ้าของ workflow ยืนยันว่า 1 หมายถึง “ล็อกเมื่อ Tutor รับงาน” หรือ “ถูกจอง” แล้วใช้ความหมายเดียว | `apps/tutoring/models.py`, views ที่เปลี่ยนสถานะ และ UI ที่แสดงผล | ป้องกัน workflow/รายงานตีความสถานะผิด | ต้องเมื่อแก้ field choices; logic อย่างเดียวอาจไม่ต้อง | ต้องตรวจค่าปัจจุบันและ Booking ที่เชื่อมโยง | สูง | `apps/tutoring/models.py:83-98`; `tutoring/migrations/0002:13-16`; tutoring views:271,290; bookings views:173-174 |
| Review | `rev_rating_*` | PositiveIntegerField ไม่มี Min/Max validator หรือ CheckConstraint | ช่วงคะแนนต้องยืนยันจาก requirement ก่อน แล้วเพิ่ม validators; พิจารณา CheckConstraint หากต้องบังคับที่ DB | `apps/bookings/models.py` และ form ที่รับคะแนน | ป้องกันคะแนนนอกช่วงและค่าเฉลี่ยผิด | validators อาจมี migration state; constraint ต้องมี | ต้องตรวจ min/max และค่าผิดช่วง | สูง | `apps/bookings/models.py:144-159`; `bookings/migrations/0001:69-78`; schema ไม่มี check constraint |
| Refill และกลุ่มไฟล์อัปโหลด | `rf_slip` และ field path ที่ DD กำหนด 255 | Model/schema ส่วนที่พบใช้ความยาว 100 แต่ DD ระบุ 255 | หาก path จริงต้องรองรับ 255 ให้ใช้ `max_length=255`; หากไม่จำเป็นให้คง Model และแก้ DD | Model ที่ประกาศ FileField/ImageField ที่เกี่ยวข้อง | path ยาวอาจบันทึกไม่ได้; การขยายโดยทั่วไปไม่ทำข้อมูลเดิมสูญหาย | ต้อง หากเปลี่ยน max_length | ต้องตรวจความยาวสูงสุดและ storage path | สูง | `apps/credits/models.py:18`; `credits/migrations/0001:23`; DD md:193; schema `refill.rf_slip varchar(100)` |
| Member/Tutor และ relation ต่อเนื่อง | PK/FK ID | Model/migration/schema ใช้ BIGINT; DD ใช้ VARCHAR(13) | แนะนำให้คง BIGINT และแก้ DD เว้นแต่ requirement ภายนอกบังคับ VARCHAR; หากบังคับต้องออกแบบ migration ใหญ่แยกต่างหาก | Models/migrations ของ accounts และทุก app ที่อ้าง Member/Tutor | กระทบ PK/FK และข้อมูลหลายตาราง มีความเสี่ยงสูงมาก | ต้อง หากเปลี่ยน Django/schema | ต้องตรวจทุก relation, external ID และ rollback | สูง | `accounts/models.py:8,52-58`; `accounts/migrations/0003:13-16`; schema `member.id`/`tutor.tut_id` bigint |
| System | `total_accumulated_fee` | Decimal(10,2); DD Decimal(5,2) | ยืนยันเพดานยอดเงิน; แนะนำให้คง 10,2 หากรองรับยอดสะสมจริง แล้วแก้ DD | `apps/admin_panel/models.py` เฉพาะกรณีเลือก 5,2 | ลด precision อาจทำข้อมูลเกินช่วงและ migration ล้มเหลว | ต้อง หากเปลี่ยน Model | ต้องตรวจค่าสูงสุด | กลาง | `apps/admin_panel/models.py:25`; `admin_panel/migrations/0006:13-16`; DD md:35; schema decimal(10,2) |
| Foreign Key ทุก relation | `on_delete`/DB rule | Django state เป็น CASCADE/SET_NULL; MySQL ส่วนใหญ่เป็น NO ACTION | ใช้ ORM เป็นหลักและบันทึกข้อจำกัด; หากต้องการ DB-level cascade ให้ทบทวนทีละ relation | Models/migrations เฉพาะ relation ที่อนุมัติ; อาจต้อง migration/RunSQL | SQL ตรงอาจลบไม่ได้หรือไม่ cascade เหมือน ORM | อาจต้อง หากเปลี่ยน DB rule | ต้องทดสอบข้อมูลลูกและ deletion paths | กลาง | Model/migration relations; `information_schema.REFERENTIAL_CONSTRAINTS`; ข้อยกเว้น `time_slot.sd_id` ที่ `tutoring/migrations/0001:34` |

### 15.2 ฝั่ง Data Dictionary

| ตาราง | Attribute | ข้อมูลที่กำกวม/ไม่ตรง | ข้อเสนอข้อความใหม่ | Type/Size/Choices ที่ควรระบุให้ครบ | เหตุผล | หลักฐาน |
|---|---|---|---|---|---|---|
| Member/Tutor และตารางที่อ้างอิง | PK/FK IDs | DD ใช้ VARCHAR(13), ระบบใช้ BIGINT | “รหัสภายในระบบ เป็นเลขจำนวนเต็มขนาดใหญ่และเพิ่มอัตโนมัติ; FK ใช้ชนิดเดียวกับ PK ปลายทาง” | PK `BIGINT`; FK `BIGINT`; ระบุ Python field และ `db_column` แยกกัน | ให้เอกสารใช้สร้าง integration/schema ได้ตรงระบบ | DD md:92,111 และ FK ที่เกี่ยวข้อง; `accounts/migrations/0003:13-16`; schema query |
| System/Member | `admin_pwd`, `admin_email`, `mb_pwd` | เอกสารทำให้เข้าใจว่าเป็นคอลัมน์ใน project table | “ข้อมูลยืนยันตัวตนและอีเมลอ้างอิงจาก Django User ผ่าน relation” | `auth_user.password VARCHAR(128)`; `auth_user.email VARCHAR(254)`; ระบุว่าไม่ใช่ column ของ System/Member | ป้องกันการออกแบบ credential ซ้ำ | DD md:36-37,95; `admin_panel/models.py:8-14,38-40`; `accounts/models.py:15`; schema `auth_user` |
| Major | `mj_abbr` | มีหมายเหตุ “ตัดออก” แต่ระบบยังใช้ | หลังอนุมัติให้เลือกอย่างใดอย่างหนึ่ง: “คงใช้—ชื่อย่อสาขา” หรือเอาแถวออกพร้อมแผนแก้ระบบ | ปัจจุบัน `VARCHAR(10)`; ห้ามเสนอ Type ใหม่ก่อนตัดสิน requirement | หมายเหตุปัจจุบันขัดกับ schema | PDF หน้า 3; DD md:59; `courses/models.py:22`; `courses/migrations/0001:56` |
| TutorCourse | `[ไม่ระบุชื่อในต้นฉบับ]` | หน้า 6 เขียน “รีวิวแยกตามรายวิชาที่เปิดสอน” แต่ไม่มี Attribute/Type/Size | หากยืนยันว่าหมายถึง field ปัจจุบัน ให้เพิ่มแถว “`tutc_rating` — คะแนนเฉลี่ยรีวิวแยกตามรายวิชา” | ปัจจุบัน `DECIMAL(3,2)`, null=True, blank=True; ต้องให้เจ้าของเอกสารอนุมัติก่อน | เชื่อมข้อความกำกวมกับระบบโดยไม่อ้างว่า PDF ระบุชื่อไว้แล้ว | PDF หน้า 6; DD md:141; `tutoring/migrations/0004:13-16`; schema `tutor_course.tutc_rating` |
| Refill | `[ธนาคารต้นทาง—ไม่ระบุ Attribute]` | ไม่มีชื่อ Attribute, Type, Size และไม่มี field ในระบบ | “รายการนี้ยังเป็น requirement ที่ต้องยืนยัน ไม่ใช่ field ใน schema ปัจจุบัน” จนกว่าจะระบุว่าจะเก็บหรือไม่ | `[กำกวมจากต้นฉบับ หน้า 8]`; ห้ามกำหนด Type/Size/choices เอง | ปฏิบัติตามข้อห้ามเดา schema | PDF หน้า 8; DD md:190,200; `apps/credits/models.py:7-27` |
| TimeSlot | `ts_id`, `ts_status` | Description ของ `ts_id` ซ้ำ `sd_id`; ค่า 1 ของ status ต่างจากระบบ | `ts_id`: “รหัสช่วงเวลา”; `ts_status`: ใช้ข้อความตามผลยืนยัน workflow | `ts_id INT PK`; `ts_status` แจกแจง 0=ว่าง, 1=ล็อกแล้ว หากยืนยันตามระบบ | แก้ semantic ที่อาจทำให้ workflow ผิด | DD md:174-178; `tutoring/models.py:83-98`; `tutoring/migrations/0002:13-16` |
| Booking | `bk_report_reason` | DD/Model ไม่รวม runtime values | หลังยืนยัน canonical set ให้แจกแจงรหัสและความหมายทุกค่า รวม mapping legacy | ปัจจุบัน column `VARCHAR(10)`; choices ต้องระบุทีละค่าตามชุดที่อนุมัติ ไม่เขียนเป็นช่วง | ป้องกัน validation/display ต่างกัน | DD md:219; `bookings/models.py:28-35`; `bookings/views.py:19-45` |
| Notification | `notif_type` | DD ไม่แจกแจงโดเมน; runtime มี `booking_cancelled` นอก Model | เพิ่มรายการ choices ครบทุกค่าตามตารางหัวข้อ 10 หลังแก้ canonical choices | `VARCHAR(30)`; ระบุรหัสและความหมายทีละค่า รวม `booking_cancelled` หากอนุมัติ | เอกสารต้องสะท้อน event ที่ระบบสร้างจริง | DD md:352; `notifications/models.py:9-27`; `signals.py:108`; schema varchar(30) |
| Data Dictionary metadata | เลขหัวข้อ/เลขตาราง/จำนวน | จำนวน 19 ไม่ตรง, ข้าม 4.3.1.18, 4.3.1.20 ซ้ำ, ตาราง 4.15 ซ้ำ | นับตารางใหม่และกำหนดเลขหัวข้อ/เลขตารางไม่ซ้ำ โดยคงชื่อ table เดิม | ไม่เกี่ยวกับ Type/Size/Choices | ทำให้การอ้างอิงหลักฐานไม่กำกวม | PDF หน้า 2,12,14; DD md:17,284-290,305,326-334 |
| Booking | `bk_stu_datetime` | หมายเหตุ “รวม” ไม่บอกต้นทาง | “วันและเวลาที่ผู้เรียนเลือกสำหรับการเรียน” หรือข้อความอื่นตาม requirement ที่ยืนยันแล้ว | `DATETIME`; null=True; ไม่ควรระบุที่มาของการรวมโดยเดา | ทำให้ความหมาย field ตรวจสอบย้อนกลับได้ | DD md:212; `bookings/models.py:48`; `bookings/migrations/0001:34` |

## 16. ลำดับการแก้ไขที่แนะนำ

1. แก้ความไม่สอดคล้องของ runtime choices: `Booking.bk_report_reason` และ `Notification.notif_type`
2. ยืนยัน semantics ของ `TimeSlot.ts_status` และช่วงคะแนน Review แล้วเพิ่ม validation/constraint ตามที่อนุมัติ
3. ตัดสิน canonical ID และความยาว path; แนะนำให้ยึด BIGINT/schema ปัจจุบันและแก้เอกสาร เว้นแต่มีข้อกำหนดภายนอกบังคับ
4. ตัดสินรายการกำกวม `mj_abbr`, `TutorCourse.tutc_rating` และ “ธนาคารต้นทาง”
5. ปรับ Data Dictionary ราย field ให้ตรง Model/schema พร้อมแก้เลขหัวข้อและเลขตาราง
6. หลังมีการแก้ Model ให้สร้าง migration ใหม่ ตรวจ migration plan และทดสอบกับสำเนาฐานข้อมูลก่อน deploy

## 17. รายการที่ต้องสร้าง Migration

รายการต่อไปนี้ “ต้องสร้าง migration หากเลือกแก้ฝั่ง Django”:

- เปลี่ยนชนิด/ความยาว/precision ของ field เช่น ID, `total_accumulated_fee`, FileField/ImageField หรือ Integer/TinyInt
- เพิ่ม ลบ หรือเปลี่ยนชื่อ field เช่น `mj_abbr` หรือ field ธนาคารต้นทาง
- เพิ่ม/แก้ Model choices ของ `Booking.bk_report_reason`, `Notification.notif_type`, `TimeSlot.ts_status` หรือ field choices อื่น เพื่อให้ migration state ตรง Model
- เพิ่ม validators อย่างเดียวอาจไม่เปลี่ยน schema แต่ Django มักบันทึก state ใน migration; หากเพิ่ม `CheckConstraint`, unique หรือ index ต้องมี migration แน่นอน
- เปลี่ยน Foreign Key, `on_delete` ใน migration state หรือ DB constraint/rule

รายงานนี้ไม่ได้อนุมัติให้ดำเนินการรายการข้างต้น และไม่ได้สร้าง migration ใด ๆ

## 18. รายการที่ไม่ต้องสร้าง Migration

- แก้ Data Dictionary, เลขหัวข้อ, เลขตาราง, Description และข้อความหมายเหตุเท่านั้น
- แก้คำอธิบายว่า password/email อยู่ใน Django User โดยไม่เปลี่ยน Model
- แก้ข้อความ UI หรือ constants ให้ใช้ค่าที่มีอยู่แล้ว โดยไม่เปลี่ยน field definition (แต่ต้องทดสอบพฤติกรรม)
- เพิ่มเอกสารอธิบาย ORM `on_delete` เทียบกับ DB `DELETE_RULE`
- รันคำสั่งตรวจสอบแบบ read-only หลังซ่อม Python runtime

## 19. ข้อจำกัดของการตรวจสอบ

- `python manage.py makemigrations --check --dry-run` เริ่มทำงานไม่ได้ เนื่องจาก executable Python ในสภาพแวดล้อมนี้รายงานว่าไม่สามารถเข้าถึงไฟล์ได้ และ `py -0p` ไม่พบ Python ที่ติดตั้ง จึงไม่มี exit code จาก Django และห้ามสรุปว่า “No changes detected”
- การยืนยันว่าไม่มี pending migration อาศัยการเทียบ Model กับ migration ล่าสุดแบบ static, การตรวจ `django_migrations` และ schema จริง ซึ่งทั้งสามส่วนสอดคล้องกัน แต่ไม่ทดแทน Django autodetector ได้สมบูรณ์
- การตรวจฐานข้อมูลเป็นคำสั่ง `SELECT` เท่านั้น ไม่ได้เรียก `migrate`, `makemigrations` หรือคำสั่งเขียนข้อมูล
- choices เป็นข้อจำกัดระดับ Model ไม่ใช่ database constraint โดยอัตโนมัติ ดังนั้น schema อาจเก็บค่านอก choices ได้
- ผล `on_delete` ของ Django เป็นพฤติกรรม ORM; ค่า `NO ACTION` ที่พบใน MySQL ไม่ได้พิสูจน์ว่า migration ผิด แต่เป็นข้อควรระวังสำหรับ SQL ตรง
- รายงานอิงสถานะไฟล์และฐานข้อมูล ณ วันที่ 6 สิงหาคม 2026 หากไฟล์หรือ schema เปลี่ยนต้องตรวจใหม่

## 20. ข้อสรุปสุดท้าย

พบ 21 Models, 21 project tables, 153 project columns และ migration files 33 รายการที่มีประวัติ applied ครบใน `django_migrations` โครงสร้าง Model ↔ migration ล่าสุด ↔ schema จริงตรงกันในระดับ table, column, type, nullability, primary key, unique, index และ Foreign Key ที่ตรวจได้ ไม่พบ migration/schema drift จากการเปรียบเทียบดังกล่าว

อย่างไรก็ตาม Data Dictionary ยังไม่ตรงระบบจริงหลายจุด โดยรายงานก่อนหน้าจัดหมวดได้เป็นตรง 109 field, ไม่ตรง 36 field, มีในระบบแต่ไม่มีในเอกสาร 4 field, มีในเอกสารแต่ไม่มีในระบบ 4 รายการ และกำกวม 4 รายการ ประเด็นเร่งด่วนที่สุดคือชนิด Member/Tutor ID, ความหมาย `TimeSlot.ts_status`, ความยาว field ไฟล์, runtime values นอก choices ของ Booking/Notification และการไม่มีข้อบังคับช่วงคะแนน Review

สถานะสุดท้ายของ audit นี้คือ “โครงสร้างสามชั้น Model–Migration–Schema สอดคล้องกันตามหลักฐานที่ตรวจได้ แต่เอกสารและ runtime choices ยังต้องปรับให้มี canonical definition เดียว” โดยยังไม่ควรแก้ schema จนกว่าจะยืนยัน requirement ของรายการกำกวมและวางแผนผลกระทบต่อข้อมูลเดิม
