# รายงานตรวจสอบรายละเอียด Inbox และ Message

โครงการ “การพัฒนาระบบเว็บแอปพลิเคชันเพื่อนช่วยติว”  
DEVELOPMENT OF WEB APPLICATION SYSTEM FOR “PUEAN CHUAY TU”

วันที่ตรวจสอบ: 6 สิงหาคม 2026

## 1. ขอบเขตและวิธีตรวจสอบ

รายงานนี้ตรวจเฉพาะ Django Models `messaging.Inbox` และ `messaging.Message` โดยเทียบ 4 ชั้น ได้แก่ Data Dictionary, Model/logic, migration state ล่าสุด และ MySQL schema จริง ไม่แก้ application code, Model, migration, schema หรือข้อมูลฐานข้อมูล

แหล่งหลัก:

- `docs/Data Dictionary เพื่อนช่วยติว0608.pdf` หน้า 10 และไฟล์ Markdown ที่ถอดจาก PDF บรรทัด 236-258
- `docs/data_dictionary_audit/01_model_inventory.md`, `02_field_comparison.md`, `03_final_audit_report.md`
- `apps/messaging/models.py`, `forms.py`, `views.py`, `context_processors.py`, `tests.py`
- `templates/messaging/inbox.html`, `templates/messaging/chat.html` และจุดเชื่อมไปหน้าแชทที่ค้นพบ
- `apps/messaging/migrations/0001_initial.py` และ `0002_message_msg_img_alter_message_msg_and_more.py`
- MySQL `information_schema.COLUMNS`, `TABLE_CONSTRAINTS`, `KEY_COLUMN_USAGE`, `STATISTICS`, `REFERENTIAL_CONSTRAINTS`, `django_migrations` และ query ตรวจข้อมูล ทั้งหมดเป็น `SELECT`

เครื่องมืออ่านข้อความ PDF โดยตรง (`pdftotext`) ไม่มีใน environment นี้ จึงยืนยันข้อความหน้า 10 ผ่าน Markdown ที่ถอดครบหน้าและรายงาน audit ก่อนหน้า ไม่ได้แก้หรือแปลง PDF

## 2. สรุป Schema และข้อมูลจริง

| รายการ | Inbox | Message |
|---|---|---|
| Django Model | `messaging.Inbox` | `messaging.Message` |
| Model source | `apps/messaging/models.py:7-40` | `apps/messaging/models.py:44-72` |
| ตารางจริง | `inbox` | `message` |
| จำนวน field/column | 3 | 7 |
| Primary key | `ib_id` AutoField / DB `int auto_increment` | `msg_id` AutoField / DB `int auto_increment` |
| Migration สร้าง | `messaging.0001_initial` บรรทัด 16-28 | `messaging.0001_initial` บรรทัด 29-44 |
| Migration ภายหลัง | ไม่มี | `0002_message_msg_img_alter_message_msg_and_more`: เพิ่ม `msg_img`, เปลี่ยน `msg` และ `msg_sent_time` บรรทัด 13-27 |
| Applied migration | `0001` เวลา 2026-03-29 12:54:18; `0002` เวลา 2026-04-17 19:54:28 | เช่นเดียวกัน |
| จำนวนแถวขณะตรวจ | 10 | 45 |

ผล query ตรวจข้อมูล ณ เวลาตรวจ:

- Inbox ที่ `member1_id = member2_id`: 0
- คู่ห้องกลับด้านซ้ำ: 0
- Message ที่ `msg_is_read` อยู่นอก 0/1: 0
- Message ที่ไม่มีทั้งข้อความและรูป: 0
- Message ที่ sender ไม่ใช่ member1/member2 ของ Inbox: 0
- ความยาว path `msg_img` สูงสุดที่พบ: 31 ตัวอักษร จากเพดาน schema 100

ผลข้างต้นบอกสถานะข้อมูลปัจจุบัน ไม่ได้แปลว่า schema ป้องกันเหตุการณ์เหล่านี้ทั้งหมด

## 3. รายละเอียด Inbox

### 3.1 Model และ Meta

- Model: `Inbox` (`apps/messaging/models.py:7`)
- `Meta.db_table = 'inbox'` (`:22-25`)
- Primary key: `ib_id` (`:8`)
- จำนวน field: 3 ได้แก่ `ib_id`, `member1`, `member2`
- `Meta.ordering`: ไม่กำหนด
- `Meta.unique_together = [['member1', 'member2']]` (`:25`)
- `Meta.constraints`: ไม่มี
- `Meta.indexes`: ไม่มี index ที่ประกาศเอง
- Django สร้าง unique composite index สำหรับ `(member1_id, member2_id)` และ FK index; schema จริงมี primary index, composite unique index และ index ของ `member2_id`

### 3.2 Field ทุกตัว

| DD Attribute | Python field | db_column | DB column | Django type | Schema type | max_length | null / blank / default | PK / unique / db_index | Relation | Migration | การใช้จริง |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `ib_id` | `ib_id` | ไม่กำหนดเอง | `ib_id` | AutoField | `int`, precision 10, auto_increment | - | False / True โดยคุณสมบัติ non-editable / ไม่มี | PK=True; unique/index โดย PK | - | `0001:19` | URL polling ใช้ `inbox.ib_id` (`chat.html:213-217`); view รับ `ib_id` แล้วค้นด้วย `pk` (`views.py:161-175`) |
| `ib_mb_id1` | `member1` | ไม่กำหนดเอง | `member1_id` | ForeignKey | `bigint`, precision 19, NOT NULL | - | False / False / ไม่มี | ไม่ unique; indexed ผ่าน composite unique | FK -> `accounts.Member.id`; target PK BigAutoField; ORM `CASCADE`; `related_name='inbox_as_member1'` | `0001:20` | filter ห้องที่ผู้ใช้เป็นฝั่งใดฝั่งหนึ่ง (`views.py:55-63`); สร้างเป็นสมาชิก PK ที่น้อยกว่า (`:113-119`) |
| `ib_mb_id2` | `member2` | ไม่กำหนดเอง | `member2_id` | ForeignKey | `bigint`, precision 19, NOT NULL | - | False / False / ไม่มี | ไม่ unique; มี FK index | FK -> `accounts.Member.id`; target PK BigAutoField; ORM `CASCADE`; `related_name='inbox_as_member2'` | `0001:21` | ใช้ร่วมกับ member1 ใน filter, permission และหาสมาชิกอีกฝั่ง (`models.py:30-32`; `views.py:55-79,173-175`) |

หมายเหตุ: FK ไม่มี `db_column` กำหนดเอง Django จึงสร้างชื่อ `<python_field>_id` โดยอัตโนมัติ ไม่ได้ใช้ชื่อ Attribute จาก DD

### 3.3 Constraints และ indexes จริง

| ชนิด | ชื่อใน schema | Column | รายละเอียด |
|---|---|---|---|
| Primary key | `PRIMARY` | `ib_id` | unique BTREE |
| Unique | `inbox_member1_id_member2_id_3570a3e9_uniq` | `member1_id`, `member2_id` | ป้องกันเฉพาะ ordered pair เดิม |
| Foreign key | `inbox_member1_id_e8e49cf7_fk` | `member1_id` -> `member.id` | MySQL DELETE/UPDATE `NO ACTION` |
| Foreign key | `inbox_member2_id_05b050a0_fk` | `member2_id` -> `member.id` | MySQL DELETE/UPDATE `NO ACTION` |
| Non-unique index | `inbox_member2_id_05b050a0_fk` | `member2_id` | BTREE; ฝั่ง member1 ใช้ prefix ของ composite unique indexได้ |

### 3.4 การป้องกันห้องซ้ำและห้องคุยกับตัวเอง

- View `chat_with` ป้องกันคุยกับตัวเองที่ `apps/messaging/views.py:109-111`
- View เรียงสมาชิกด้วย PK ให้น้อยกว่าอยู่ `member1` เสมอ แล้วใช้ `get_or_create(member1=m1, member2=m2)` ที่ `:113-119` จึงลดคู่กลับด้านซ้ำเมื่อสร้างผ่าน flow นี้
- Unique constraint ป้องกันเพียง `(A,B)` ซ้ำกับ `(A,B)` แต่ไม่ป้องกัน `(B,A)` และไม่มี check constraint บังคับ `member1_id < member2_id`
- Model ไม่มี `clean()` หรือ constraint ป้องกัน `member1 == member2`
- การสร้างผ่าน admin, shell, fixture หรือโค้ดอื่นสามารถสร้าง self-inbox หรือ reverse pair ได้ หากไม่ใช้ view นี้
- ขณะตรวจไม่พบ self-inbox หรือ reverse duplicate แต่ความเสี่ยงเชิงโครงสร้างยังมี

### 3.5 Query และลำดับ Inbox

- รายการห้องค้นด้วย `Q(member1=me) | Q(member2=me)` และ preload สมาชิก/ข้อความ (`views.py:55-63`)
- `get_other_member()` คืน member อีกฝั่ง (`models.py:30-32`)
- `last_message()` เรียง `-msg_sent_time` เพื่อเลือกข้อความล่าสุด (`models.py:38-40`)
- Sidebar นำห้องมา sort ตามเวลาข้อความล่าสุดแบบใหม่ไปเก่าใน Python (`views.py:64-79`)
- context processor และ unread endpoint ใช้ filter คู่เดียวกัน (`context_processors.py:13-18`; `views.py:199-211`)

### 3.6 ผลของการลบ

- ใน Model/migration, การลบ Member ผ่าน Django ORM ใช้ `on_delete=CASCADE` กับ Inbox ทั้งสองฝั่ง (`models.py:9-20`; migration `0001:20-21`) ทำให้ Inbox ที่เกี่ยวข้องถูกลบ และ Message ใต้ Inbox ถูก Django Collector ลบต่อ
- การลบ Inbox ผ่าน Django ORM ลบ Message ที่อ้าง Inbox เพราะ `Message.inbox` เป็น CASCADE (`models.py:60-63`)
- Schema MySQL จริงกำหนด FK เหล่านี้เป็น `NO ACTION` ไม่ใช่ database-level CASCADE การลบด้วย SQL ตรงจึงถูก FK ปฏิเสธหากยังมีลูก ไม่ได้ cascade เหมือน Django ORM

## 4. รายละเอียด Message

### 4.1 Model และ Meta

- Model: `Message` (`apps/messaging/models.py:44`)
- `Meta.db_table = 'message'` (`:66-69`)
- Primary key: `msg_id` (`:45`)
- จำนวน field: 7 ได้แก่ `msg_id`, `msg_sent_time`, `msg`, `msg_img`, `msg_is_read`, `sender`, `inbox`
- `Meta.ordering = ['msg_sent_time']` (`:69`) หมายถึงเก่าไปใหม่โดยปริยาย
- `Meta.constraints`: ไม่มี
- `Meta.indexes`: ไม่มี index ที่ประกาศเอง; Django สร้าง index สำหรับ Foreign Key

### 4.2 Field ทุกตัว

| DD Attribute | Python field | db_column | DB column | Django type | Schema type | max_length | null / blank / default | auto_now / auto_now_add | PK / unique / db_index | Relation / validators / choices | Migration และการใช้จริง |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `msg_id` | `msg_id` | ไม่กำหนดเอง | `msg_id` | AutoField | `int`, precision 10, auto_increment | - | False / True โดยคุณสมบัติ non-editable / ไม่มี | False / False | PK=True; unique/index โดย PK | ไม่มี validator/choices | `0001:32`; ใช้เป็น DOM/poll cursor (`chat.html:127-129,308-313`; `views.py:180-196`) |
| `msg_sent_time` | `msg_sent_time` | ไม่กำหนดเอง | `msg_sent_time` | DateTimeField | `datetime(6)`, NOT NULL | - | False / True / ไม่มี | False / True | ไม่ unique/index | ไม่มี validator/choices | `0001:33` เดิมไม่มี auto_now_add; `0002:23-26` เปลี่ยนเป็น auto_now_add; view/template เรียงและแสดงเวลา (`views.py:138-146,181`; `chat.html:123,150`) |
| `msg` | `msg` | ไม่กำหนดเอง | `msg` | TextField | `longtext`, NOT NULL | ไม่จำกัดแบบ CharField | False / True / ไม่มี | False / False | ไม่ unique/index | ไม่มี field validator/choices; form clean บังคับร่วมกับรูป | `0001:34` เดิม blank=False; `0002:18-21` เปลี่ยน blank=True; แสดงด้วย urlize/linebreaks (`chat.html:146-148`) |
| `msg_img` | `msg_img` | ไม่กำหนดเอง | `msg_img` | ImageField | `varchar(100)`, NULL | 100 โดย default | True / True / ไม่มี | False / False | ไม่ unique/index | `upload_to='chat/'`; ImageField; form จำกัด 5 MB แต่ Model ไม่มี size validator; ไม่มี choices | เพิ่มใน `0002:13-16`; form `forms.py:19-23,35-41`; preview JS `chat.html:251-268`; แสดงรูป `:140-145,328-334` |
| `msg_is_read` | `msg_is_read` | ไม่กำหนดเอง | `msg_is_read` | IntegerField | `int`, precision 10, NOT NULL | - | False / False / Django default=0; DB default ไม่มี | False / False | ไม่ unique/index | ไม่มี validators, choices หรือ check constraint; convention 0=ยังไม่อ่าน, 1=อ่านแล้ว | `0001:35`; เปลี่ยน 0 -> 1 ที่ `views.py:134-135,177-178`; template/JS แสดง receipt ที่ `chat.html:151-155,349-368` |
| `msg_sender_mb_id` | `sender` | ไม่กำหนดเอง | `sender_id` | ForeignKey | `bigint`, precision 19, NOT NULL | - | False / False / ไม่มี | False / False | ไม่ unique; FK index | FK -> `Member.id` BigAutoField; ORM CASCADE; ไม่มี related_name จึงใช้ reverse default `message_set`; ไม่มี validator/choices | `0001:37`; view กำหนด sender จาก current member (`views.py:125-129`) |
| `ib_id` | `inbox` | ไม่กำหนดเอง | `inbox_id` | ForeignKey | `int`, precision 10, NOT NULL | - | False / False / ไม่มี | False / False | ไม่ unique; FK index | FK -> `Inbox.ib_id` AutoField; ORM CASCADE; ไม่มี related_name จึงใช้ reverse default `message_set`; ไม่มี validator/choices | `0001:36`; view กำหนด Inbox จากห้อง canonical (`views.py:119,125-129`) |

`msg_sent_time` ไม่ใช้ default และไม่ได้ให้ผู้ใช้กำหนดเอง ปัจจุบัน Django กำหนดครั้งแรกตอนสร้างด้วย `auto_now_add=True` ส่วน database column ไม่มี server-side default

### 4.3 Constraints และ indexes จริง

| ชนิด | ชื่อใน schema | Column | รายละเอียด |
|---|---|---|---|
| Primary key | `PRIMARY` | `msg_id` | unique BTREE |
| Foreign key/index | `message_inbox_id_b8d74f22_fk_inbox_ib_id` | `inbox_id` -> `inbox.ib_id` | index BTREE; MySQL DELETE/UPDATE `NO ACTION` |
| Foreign key/index | `message_sender_id_a2a2e825_fk` | `sender_id` -> `member.id` | index BTREE; MySQL DELETE/UPDATE `NO ACTION` |
| Check constraint | ไม่มี | - | ไม่บังคับ `msg_is_read IN (0,1)`, sender เป็นสมาชิกห้อง หรือมีข้อความ/รูปอย่างน้อยหนึ่งอย่าง |

### 4.4 การส่งข้อความและ validation

- `MessageForm` เปิดรับเฉพาะ `msg` และ `msg_img`; sender/inbox ถูกกำหนดฝั่ง server (`forms.py:6-24`; `views.py:121-130`)
- Form `clean()` อนุญาตข้อความอย่างเดียว รูปอย่างเดียว หรือทั้งสองอย่าง และปฏิเสธกรณีไม่มีทั้งคู่ (`forms.py:26-33`)
- `clean_msg_img()` จำกัดไฟล์ 5 MB (`forms.py:35-41`) และ widget/JavaScript ใช้ `accept='image/*'` พร้อมตรวจ 5 MB ฝั่ง client (`forms.py:19-23`; `chat.html:251-268`)
- ImageField/Form จะตรวจว่าเป็นรูปเมื่อผ่าน ModelForm แต่ไม่มี validator ระบุ MIME/นามสกุลที่อนุญาตเป็นรายการ และการสร้างผ่าน ORM โดยไม่ใช้ form สามารถข้าม form size/empty validation
- DB ไม่บังคับว่าต้องมีข้อความหรือรูป จึงมีความเสี่ยง empty message จาก admin/direct ORM แม้ข้อมูลปัจจุบันไม่พบ
- DB ไม่บังคับว่า sender ต้องเป็น member1/member2 ของ Inbox; view ปกติกำหนด sender จากผู้ใช้ในห้อง แต่ admin/direct ORM อาจสร้าง sender นอกห้องได้ ข้อมูลปัจจุบันไม่พบ

### 4.5 สถานะอ่านและ ordering

- ความหมายที่ระบบใช้จริง: 0 = ยังไม่อ่าน, 1 = อ่านแล้ว
- เมื่อเปิดหน้า chat ระบบ update ข้อความของอีกฝ่ายจาก 0 เป็น 1 (`views.py:134-135`)
- AJAX polling ทำการ update แบบเดียวกัน (`views.py:177-178`)
- ผู้ส่งเห็น check เดี่ยวเมื่อไม่ใช่ 1 และ check คู่เมื่อเป็น 1 ทั้ง server-rendered template และ JavaScript (`chat.html:151-155,349-368`)
- Model เป็น IntegerField ไม่มี choices/validator และ schema ไม่มี check constraint จึงเก็บค่าอื่นได้; UI จะตีความทุกค่าที่ไม่ใช่ 1 ว่า “ยังไม่อ่าน”
- Meta ordering และ query หน้า chat/poll เรียง `msg_sent_time` จากเก่าไปใหม่ (`models.py:66-69`; `views.py:138,181`); เฉพาะ `last_message()` เรียงใหม่ไปเก่าเพื่อหยิบรายการล่าสุด (`models.py:38-40`)

### 4.6 รูปภาพและ orphan risk

- `msg_img` เป็น ImageField ไม่ใช่ FileField, path ขึ้นต้น `chat/`, ความยาว database สูงสุด 100
- DD ระบุ VARCHAR(255) จึงไม่ตรง Model/migration/schema
- path ที่ยาวเกิน 100 อาจถูก database ปฏิเสธหรือ truncate ตาม SQL mode; path ยาวสุดที่พบจริง 31 จึงยังไม่เกิดปัญหาในข้อมูลปัจจุบัน
- Foreign Key NOT NULL และ constraint ป้องกัน orphan row ของ Message ที่ไม่มี Inbox/Member ใน schema
- อย่างไรก็ตาม Django `ImageField` ไม่ลบไฟล์จาก storage โดยอัตโนมัติเมื่อ Message ถูกลบ จึงมีความเสี่ยง orphan file แม้ไม่มี orphan database row
- การลบ Member/Inbox ผ่าน ORM cascade ลบ Message; SQL ตรงเจอ `NO ACTION` และจะถูกปฏิเสธเมื่อยังมี Message

## 5. เปรียบเทียบ Data Dictionary กับระบบจริง: Inbox

| DD Attribute | Django Field | DB Column | DD Type/Size | Django Type | Schema Type | Key/Relation | Null/Blank/Default | สถานะ | รายละเอียด | หลักฐาน |
|---|---|---|---|---|---|---|---|---|---|---|
| `ib_id` | `ib_id` | `ib_id` | INT/- | AutoField | int auto_increment | PK | False/True/ไม่มี | ตรง | ชื่อและชนิดฐานข้อมูลตรง | DD md:242; model:8; migration `0001:19`; schema SELECT |
| `ib_mb_id1` | `member1` | `member1_id` | VARCHAR/13 | ForeignKey -> Member | bigint | FK -> `member.id`; ORM CASCADE | False/False/ไม่มี | ไม่ตรง | ความหมาย relation ตรง แต่ชื่อ Python/DB และชนิดไม่ตรง DD; ไม่มี custom db_column | DD md:243; model:9-14; migration `0001:20`; schema SELECT |
| `ib_mb_id2` | `member2` | `member2_id` | VARCHAR/13 | ForeignKey -> Member | bigint | FK -> `member.id`; ORM CASCADE | False/False/ไม่มี | ไม่ตรง | เช่นเดียวกับ member1 | DD md:244; model:15-20; migration `0001:21`; schema SELECT |
| ไม่มี | `Meta.unique_together` | composite unique index | ไม่ระบุ | unique_together | UNIQUE(member1_id,member2_id) | ordered pair unique | - | ไม่มีใน Data Dictionary | DD ไม่บันทึกข้อจำกัดห้องซ้ำแบบ ordered pair | model:22-25; migration `0001:23-27`; schema SELECT |

## 6. เปรียบเทียบ Data Dictionary กับระบบจริง: Message

| DD Attribute | Django Field | DB Column | DD Type/Size | Django Type | Schema Type | Key/Relation | Null/Blank/Default | Choices/Validator | สถานะ | รายละเอียด | หลักฐาน |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `msg_id` | `msg_id` | `msg_id` | INT/- | AutoField | int auto_increment | PK | False/True/ไม่มี | ไม่มี | ตรง | ชื่อ/type/key ตรง | DD md:252; model:45; migration `0001:32`; schema |
| `msg_sent_time` | `msg_sent_time` | `msg_sent_time` | DATETIME/- | DateTimeField(auto_now_add=True) | datetime(6) | - | False/True/ไม่มี | ไม่มี | ตรง | DD ไม่ระบุวิธีกำหนดเวลา; migration ล่าสุดใช้ auto_now_add | DD md:253; model:46; `0002:23-26`; schema |
| `msg` | `msg` | `msg` | TEXT/- | TextField(blank=True) | longtext | - | False/True/ไม่มี | Form บังคับร่วมกับรูป | ตรง | ชนิดเชิงข้อความตรง; DD ไม่ระบุ blank behavior | DD md:254; model:47; `0002:18-21`; forms:26-33; schema |
| `msg_img` | `msg_img` | `msg_img` | VARCHAR/255 | ImageField(max_length=100) | varchar(100) | - | True/True/ไม่มี | Form ตรวจรูปและ 5 MB | ไม่ตรง | ความยาว 100 ไม่ใช่ 255; upload_to=`chat/` | DD md:255; model:48-53; `0002:13-16`; forms:35-41; schema |
| `msg_is_read` | `msg_is_read` | `msg_is_read` | TINYINT/1; 0=ยังไม่อ่าน, 1=อ่านแล้ว | IntegerField(default=0) | int; ไม่มี DB default/check | - | False/False/Django=0 | ไม่มี choices/validator/constraint | ไม่ตรง | ความหมาย runtime ตรง แต่ชนิด/การบังคับโดเมนไม่ตรง | DD md:256; model:54; migration `0001:35`; views:134-135,177-178; schema |
| `msg_sender_mb_id` | `sender` | `sender_id` | VARCHAR/13 | ForeignKey -> Member | bigint | FK -> `member.id`; ORM CASCADE | False/False/ไม่มี | ไม่มี | ไม่ตรง | ความหมาย relation ตรง แต่ชื่อและชนิดต่าง; ไม่มี related_name | DD md:257; model:55-59; migration `0001:37`; schema |
| `ib_id` | `inbox` | `inbox_id` | INT/- | ForeignKey -> Inbox | int | FK -> `inbox.ib_id`; ORM CASCADE | False/False/ไม่มี | ไม่มี | ไม่ตรง | Type/relation ตรง แต่ Python field/DB column ไม่ใช้ชื่อ `ib_id`; ไม่มี related_name | DD md:258; model:60-64; migration `0001:36`; schema |

## 7. สรุปชื่อ Field ที่ถูกต้อง

| ตาราง | ความหมาย | ชื่อใน DD | Django Field | DB Column จริง | อ้างอิง |
|---|---|---|---|---|---|
| Inbox | Primary Key | `ib_id` | `ib_id` | `ib_id` | model:8; schema |
| Inbox | สมาชิกคนที่ 1 | `ib_mb_id1` | `member1` | `member1_id` | model:9-14; schema |
| Inbox | สมาชิกคนที่ 2 | `ib_mb_id2` | `member2` | `member2_id` | model:15-20; schema |
| Message | Primary Key | `msg_id` | `msg_id` | `msg_id` | model:45; schema |
| Message | เวลาส่ง | `msg_sent_time` | `msg_sent_time` | `msg_sent_time` | model:46; schema |
| Message | ข้อความ | `msg` | `msg` | `msg` | model:47; schema |
| Message | รูปภาพ | `msg_img` | `msg_img` | `msg_img` | model:48-53; schema |
| Message | สถานะอ่าน | `msg_is_read` | `msg_is_read` | `msg_is_read` | model:54; schema |
| Message | ผู้ส่ง | `msg_sender_mb_id` | `sender` | `sender_id` | model:55-59; schema |
| Message | กล่องข้อความ | `ib_id` | `inbox` | `inbox_id` | model:60-64; schema |

## 8. สรุปปัญหาและข้อเสนอแนะ

### A. ปัญหาใน Django / Model / logic

| ตาราง | Field | ปัญหา | DD | Model | Schema | ผลกระทบ | แนวทางแก้ | ต้อง migration | หลักฐาน |
|---|---|---|---|---|---|---|---|---|---|
| Inbox | `member1`,`member2` | unique ป้องกันเฉพาะ ordered pair; ไม่มี constraint บังคับลำดับหรือห้ามคนเดียวกัน | ไม่ระบุ | View ป้องกัน/เรียง แต่ Model ไม่บังคับ | UNIQUE(A,B) เท่านั้น; ไม่มี CHECK | admin/direct ORM อาจสร้าง (B,A) หรือ (A,A) | ยืนยัน requirement แล้วเพิ่ม Model validation; หากต้องบังคับ DB ใช้ CheckConstraint/ออกแบบ canonical pair พร้อมตรวจข้อมูลเดิม | ต้อง หากเพิ่ม constraint | model:22-25; views:109-119; schema; data check ปัจจุบันเป็น 0 |
| Message | `msg_is_read` | IntegerField ไม่มี choices/validator/check | TINYINT(1), 0/1 | IntegerField default=0 | int ไม่มี DB default/check | ค่าอื่นถูกเก็บได้และ UI ตีความเป็นยังไม่อ่าน | ใช้ BooleanField หรือคง IntegerFieldแล้วเพิ่ม choices/validator/check ตาม requirement | ต้อง | model:54; views:134-135,177-178; chat:151-155,349-368; schema |
| Message | `sender`,`inbox` | ไม่มี constraint ว่า sender เป็นสมาชิกของ Inbox | relation แยกกัน | View ปกติกำหนดถูก แต่ Model ไม่ validate | FK แยกสองตัว | admin/direct ORM สร้างข้อความจากคนนอกห้องได้ | เพิ่ม `clean()`/service validation และจำกัด admin; DB constraintข้ามตารางทำไม่ได้ด้วย CHECK ปกติ | validation อย่างเดียวอาจมี state migration; schema constraintต้องออกแบบเพิ่ม | model:55-64; views:125-129,173-175; data check ปัจจุบันเป็น 0 |
| Message | `msg`,`msg_img` | กฎต้องมีอย่างน้อยหนึ่งอย่างอยู่เฉพาะ Form | DD ไม่ระบุ | Form clean บังคับ; Model ไม่บังคับ | ไม่มี CHECK | direct ORM/admin อาจสร้างข้อความว่าง | ย้าย invariant ไป validation ระดับ Model/service; พิจารณา DB checkตามความเข้ากันได้ของ field path | อาจต้อง | forms:26-33; model:47-53; schema; data checkปัจจุบัน 0 |
| Message | `msg_img` | ขนาด 5 MB ตรวจเฉพาะ form; ไม่มี Model validator ที่ใช้ทุก flow | VARCHAR(255) | ImageField 100; form 5 MB | varchar(100) | direct save ข้ามเพดานไฟล์; path อาจเกิน 100 | ยืนยันเพดาน path/ไฟล์ แล้วเพิ่ม reusable validators; หากขยาย max_length เป็น 255 ให้สร้าง migration | ต้องเมื่อเปลี่ยน max_length/field state | model:48-53; forms:35-41; chat:251-268; schema |
| Inbox/Message | FK deletion | ORM CASCADE แต่ MySQL `NO ACTION` | ไม่ระบุ | CASCADE | NO ACTION | SQL ตรงไม่ทำเหมือน ORM | ใช้ ORM เป็นหลักและบันทึกข้อจำกัด; เปลี่ยน DB rule เฉพาะเมื่อมี requirement ชัด | อาจต้อง | model:9-20,55-64; migration `0001:20-21,36-37`; schema |
| Message | `msg_img` storage | ลบ row ไม่ลบไฟล์โดยอัตโนมัติ | ไม่ระบุ | ไม่มี cleanup signal/storage policy | DB ไม่ติดตามไฟล์ | เกิด orphan file | กำหนด retention/cleanup policy แล้วทดสอบก่อนเพิ่ม signal/job | ไม่จำเป็นหากแก้ logic เท่านั้น | model:48-53; ไม่มี signal ที่เกี่ยวข้องจากการค้นหา |
| Messaging | tests | ไม่มี test กรณี canonical pair, self-chat, read domain, empty/image validation และ authorization | ไม่ระบุ | `tests.py` ว่าง | - | regression ไม่ถูกจับ | เพิ่ม tests ครอบคลุม invariant และ deletion behavior | ไม่ต้อง | `apps/messaging/tests.py:1-3` |

### B. ปัญหาใน Data Dictionary

| ตาราง | Field | ปัญหา | DD | Model | Schema | ผลกระทบ | แนวทางแก้ DD | ต้อง migration | หลักฐาน |
|---|---|---|---|---|---|---|---|---|---|
| Inbox | `ib_mb_id1`,`ib_mb_id2` | ชื่อและชนิดไม่ตรงระบบ | VARCHAR(13) | `member1`,`member2` FK -> Member.id | `member1_id`,`member2_id` BIGINT | ผู้นำเอกสารไปสร้าง query/schema ใช้ชื่อและ type ผิด | ระบุแยก DD logical name, Django field และ DB column; ใช้ BIGINT หากยึดระบบปัจจุบัน | ไม่ต้อง หากแก้ DD | DD md:243-244; model:9-20; schema |
| Inbox | unique pair | DD ไม่ระบุ unique constraint | ไม่มี | unique_together | composite UNIQUE | เอกสารไม่บอกกติกาห้องซ้ำ | เพิ่มข้อจำกัด UNIQUE(`member1_id`,`member2_id`) พร้อมระบุว่ายังไม่ป้องกันคู่กลับด้าน | ไม่ต้อง | model:22-25; migration `0001:23-27`; schema |
| Message | `msg_img` | Size ไม่ตรง | VARCHAR(255) | ImageField default 100 | varchar(100) | เอกสารให้ความสามารถเกินระบบ | หากยึดระบบปัจจุบันแก้เป็น VARCHAR(100), path `chat/`; หาก 255 เป็น requirement ให้แก้ระบบภายหลัง | ไม่ต้องหากแก้ DD | DD md:255; model:48-53; `0002:13-16`; schema |
| Message | `msg_is_read` | Type/constraint ใน DD ไม่ตรง implementation | TINYINT(1), 0/1 | IntegerField ไม่มี choices | int ไม่มี check | DD ทำให้เข้าใจว่าฐานข้อมูลจำกัด 0/1 | ระบุ `INT`, Django default 0 และ “ค่าที่ระบบใช้ 0/1 แต่ยังไม่มี constraint” จนกว่าระบบแก้ | ไม่ต้องหากแก้ DD | DD md:256; model:54; schema |
| Message | `msg_sender_mb_id` | ชื่อและชนิดไม่ตรง | VARCHAR(13) | `sender` FK -> Member.id | `sender_id` BIGINT | query/integration ผิด | ระบุ Django field `sender`, DB `sender_id`, BIGINT FK -> `member.id` | ไม่ต้อง | DD md:257; model:55-59; schema |
| Message | `ib_id` relation | DD ใช้ชื่อ PK เป็นชื่อ FK แต่ Django/DB เติม suffix | INT | `inbox` | `inbox_id` INT | ชื่อจริงกำกวม | ระบุ Django field `inbox`, DB column `inbox_id`, FK -> `inbox.ib_id` | ไม่ต้อง | DD md:258; model:60-64; schema |
| Message | เวลา/เนื้อหา/รูป | DD ไม่บันทึก null, blank, default, upload และ validation | รายละเอียดไม่ครบ | ตามหัวข้อ 4.2 | ตาม schema | ไม่สามารถสร้าง schema/validation จาก DD ได้ครบ | เติม `auto_now_add`, null/blank, Django default, upload_to และ form rule โดยแยก Model rule กับ UI rule | ไม่ต้อง | DD md:253-256; model:46-54; forms:26-41 |

### C. จุดที่ต้องตัดสินใจ Requirement ก่อน

1. ห้องสนทนาหนึ่งคู่ต้องมีได้เพียงห้องเดียวโดยไม่สนลำดับหรือไม่ และต้องห้าม self-inbox ที่ Model/DB ด้วยหรือให้ view ป้องกันเพียงพอ
2. `msg_is_read` ควรเป็น BooleanField หรือ IntegerField ที่จำกัด 0/1 และต้องการ DB CheckConstraint หรือไม่
3. `msg_img` ต้องรองรับ path 100 หรือ 255 ตัวอักษร และต้องจำกัดชนิดไฟล์/MIME/ขนาดที่ Model layer ด้วยหรือไม่
4. กฎ “ต้องมีข้อความหรือรูปอย่างน้อยหนึ่งอย่าง” และ “sender ต้องเป็นสมาชิกใน Inbox” ต้องบังคับสำหรับ admin/import/direct ORM ด้วยหรือเฉพาะหน้า chat
5. ต้องการให้ database FK cascade เองเมื่อใช้ SQL ตรง หรือยอมรับ Django ORM CASCADE + MySQL NO ACTION
6. นโยบายลบไฟล์รูปเมื่อ Message ถูกลบและระยะเวลาเก็บไฟล์ต้องเป็นอย่างไร

### D. จุดที่ตรงอยู่แล้ว ไม่ควรแก้

- ชื่อตารางจริง `inbox` และ `message` ตรง `Meta.db_table` และ DD
- `Inbox.ib_id` และ `Message.msg_id` เป็น INT auto-increment primary key ตรง DD
- `msg_sent_time` เป็น DATETIME และปัจจุบันกำหนดครั้งเดียวด้วย `auto_now_add=True`
- `msg` เป็น TextField/ฐานข้อมูล LONGTEXT และรองรับข้อความอย่างเดียว
- `sender` อ้าง `Member.id`; `inbox` อ้าง `Inbox.ib_id`; FK ทั้งหมด NOT NULL และมี index
- Message เรียงเก่าไปใหม่ในหน้า chat; sidebar เรียงห้องจากข้อความล่าสุดใหม่ไปเก่า เป็นพฤติกรรมสอดคล้องกับ UI
- Form รองรับข้อความอย่างเดียว รูปอย่างเดียว หรือทั้งสองอย่าง และข้อมูลปัจจุบันไม่พบข้อความว่าง
- ข้อมูลปัจจุบันไม่พบ self-inbox, reverse duplicate, read status ผิดโดเมน หรือ sender นอกห้อง

## 9. ข้อสรุป

Model, migration state ล่าสุด และ schema จริงของ Inbox/Message ตรงกันทุก field ที่ตรวจ พบความต่างหลักกับ Data Dictionary ที่ชื่อ FK และชนิด Member FK (`VARCHAR(13)` ใน DD เทียบ `BIGINT` จริง), `msg_img` (255 เทียบ 100) และ `msg_is_read` (DD สื่อ TINYINT 0/1 แต่ระบบเป็น INT ไม่มีตัวบังคับโดเมน)

ความเสี่ยงสำคัญของระบบอยู่ที่ invariant ซึ่งบังคับเฉพาะ view/form ได้แก่ canonical member pair, ห้าม self-chat, sender ต้องอยู่ในห้อง, ต้องมีข้อความหรือรูป และขนาดรูป 5 MB ส่วนฐานข้อมูลปัจจุบันยังสะอาดตาม query read-only ที่ตรวจ แต่ควรตัดสิน requirement ก่อนเพิ่ม validation/constraint ใด ๆ

รายงานนี้ไม่ได้สร้าง migration ไม่ได้รัน migrate และไม่ได้แก้ข้อมูลหรือ schema ฐานข้อมูล
