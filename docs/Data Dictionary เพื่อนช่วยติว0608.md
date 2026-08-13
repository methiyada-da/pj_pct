# Data Dictionary ระบบเพื่อนช่วยติว

> ถอดข้อมูลจากไฟล์ `Data Dictionary เพื่อนช่วยติว0608.pdf` ครบหน้า 1–14 โดยรักษาลำดับหัวข้อ เลขตาราง ชื่อ Attribute และหมายเหตุจากต้นฉบับ

## หน้า 1

### Data Dictionary “ระบบเพื่อนช่วยติว”

หน้าปกเอกสาร ไม่มีตารางข้อมูล

## หน้า 2

### 4.3 การออกแบบระบบ

> หมายเหตุในต้นฉบับ: “*ฟิลที่เพิ่มมาใหม่ ให้ไปเช็ค Type Size ในระบบใหม่”รายการที่ไม่สามารถระบุ Attribute Name, Type หรือ Sizeได้คือดูจากในระบบว่าชื่อหรือรายละเอียดในระบบเป็นอะไร

### 4.3.1 การออกแบบฐานข้อมูล

ผู้พัฒนาได้ใช้พจนานุกรมข้อมูล (Data Dictionary) มาเป็นเครื่องมือช่วยในการกำหนดรายละเอียดต่าง ๆ เกี่ยวกับข้อมูล ผลการออกแบบฐานข้อมูลประกอบด้วย 21 ตาราง ดังนี้

### 4.3.1.1 ข้อมูลระบบ

#### ตาราง 4.1 ตารางข้อมูลระบบ (System)

| No. | Attribute Name | Type | Size | Description | Key |
|---:|---|---|---|---|---|
| 1 | uni_name | VARCHAR | 100 | ชื่อมหาวิทยาลัย | |
| 2 | bank_name | VARCHAR | 100 | ชื่อธนาคาร | |
| 3 | acc_name | VARCHAR | 100 | ชื่อบัญชี | |
| 4 | acc_no | VARCHAR | 20 | เลขที่บัญชีธนาคาร | |
| 5 | promptpay_id | VARCHAR | 20 | หมายเลขพร้อมเพย์ | หมายเหตุสีแดง: เพิ่ม |
| 6 | crd_val | DECIMAL | 5,2 | มูลค่าเครดิต | |
| 7 | deposit_withdraw_fee_pct | DECIMAL | 5,2 | อัตราร้อยละค่าธรรมเนียมการถอนยอดเครดิตนำฝาก | |
| 8 | income_withdraw_fee_pct | DECIMAL | 5,2 | อัตราร้อยละค่าธรรมเนียมการถอนยอดเครดิตรายได้ | |
| 9 | total_accumulated_fee | DECIMAL | 5,2 | ค่าธรรมเนียมสะสมทั้งหมด | หมายเหตุสีแดง: เพิ่ม |
| 10 | admin_pwd | VARCHAR | 255 | รหัสผ่านผู้ดูแลระบบ | |
| 11 | admin_email | VARCHAR | 255 | อีเมลผู้ดูแลระบบ | |
| 12 | email_domain | VARCHAR | 100 | โดเมนอีเมลมหาวิทยาลัย | หมายเหตุสีแดง: เพิ่ม |

### 4.3.1.2 ข้อมูลคณะ

#### ตาราง 4.2 ตารางข้อมูลคณะ (Faculty)

| No. | Attribute Name | Type | Size | Description | Key |
|---:|---|---|---|---|---|
| 1 | fac_id | INT | - | รหัสคณะ | PK |
| 2 | fac_name | VARCHAR | 100 | ชื่อคณะ | |

## หน้า 3

### 4.3.1.3 ข้อมูลสาขา

#### ตาราง 4.3 ตารางข้อมูลสาขา (Major)

| No. | Attribute Name | Type | Size | Description | Key |
|---:|---|---|---|---|---|
| 1 | mj_id | INT | - | รหัสสาขา | PK |
| 2 | mj_name | VARCHAR | 100 | ชื่อสาขา | |
| 3 | mj_abbr | VARCHAR | 10 | ชื่อย่อสาขา | หมายเหตุสีแดง: ตัดออก |
| 4 | mj_desc | TEXT | - | รายละเอียด | |
| 5 | fac_id | INT | - | รหัสคณะ | FK(Faculty) |

### 4.3.1.4 ข้อมูลกลุ่มรายวิชา

#### ตาราง 4.4 ตารางข้อมูลกลุ่มรายวิชา (Course Group)

| No. | Attribute Name | Type | Size | Description | Key |
|---:|---|---|---|---|---|
| 1 | cg_id | INT | - | รหัสกลุ่มรายวิชา | PK |
| 2 | cg_name | VARCHAR | 100 | ชื่อกลุ่มรายวิชา | |
| 3 | cg_desc | TEXT | - | รายละเอียด | |

### 4.3.1.5 ข้อมูลรายวิชา

#### ตาราง 4.5 ตารางข้อมูลรายวิชา (Course)

| No. | Attribute Name | Type | Size | Description | Key |
|---:|---|---|---|---|---|
| 1 | crs_id | VARCHAR | 13 | รหัสรายวิชา | PK |
| 2 | crs_name | VARCHAR | 150 | ชื่อรายวิชา | |
| 3 | crs_desc | TEXT | - | รายละเอียด | |
| 4 | cg_id | INT | - | รหัสกลุ่มรายวิชา | FK(Course Group) |

## หน้า 4

### 4.3.1.6 ข้อมูลสมาชิก

#### ตาราง 4.6 ตารางข้อมูลสมาชิก (Member)

| No. | Attribute Name | Type | Size | Description | Key |
|---:|---|---|---|---|---|
| 1 | mb_id | VARCHAR | 13 | รหัสสมาชิก | PK |
| 2 | mb_full_name | VARCHAR | 100 | ชื่อและนามสกุล | |
| 3 | mb_email | VARCHAR | 50 | อีเมลมหาวิทยาลัย | |
| 4 | mb_pwd | VARCHAR | 255 | รหัสผ่าน | |
| 5 | mb_img | VARCHAR | 100 | ชื่อไฟล์รูปโปรไฟล์ | |
| 6 | mb_deposit_crd | INT | - | เครดิตนำฝาก (สำหรับเรียน) | |
| 7 | mb_income_crd | INT | - | เครดิตรายได้ (จากการสอน) | |
| 8 | mb_status | TINYINT | 1 | สถานะ:<br>0 = ปิดการใช้งาน<br>1 = ใช้งานปกติ<br>2 = ระงับชั่วคราว | |
| 9 | mb_locked_crd | INT | - | เครดิตที่ล็อกไว้ | |
| 10 | mj_id | INT | - | รหัสสาขา | FK(Major) |

## หน้า 5

### 4.3.1.7 ข้อมูลติวเตอร์

#### ตาราง 4.7 ตารางข้อมูลติวเตอร์ (Tutor)

| No. | Attribute Name | Type | Size | Description | Key |
|---:|---|---|---|---|---|
| 1 | tut_id | VARCHAR | 13 | รหัสติวเตอร์ | PK, FK(Member) |
| 2 | tut_desc | TEXT | - | ข้อมูลแนะนำตัว | |
| 3 | tut_skill | TEXT | - | ความถนัด | |
| 4 | tut_gpax | DECIMAL | 3,2 | เกรดเฉลี่ย | |
| 5 | tut_student_card | VARCHAR | 100 | ชื่อไฟล์บัตรนักศึกษา | หมายเหตุสีแดง: เพิ่ม |
| 6 | tut_has_exp | TINYINT | 1 | ประสบการณ์สอน:<br>0 = ไม่เคยสอน<br>1 = เคยสอน | |
| 7 | tut_exp_desc | TEXT | - | รายละเอียดประสบการณ์สอน | |
| 8 | tut_rating | DECIMAL | 3,2 | คะแนนรีวิวเฉลี่ยรวม | |
| 9 | tut_rating_quality | DECIMAL | 3,2 | คะแนนคุณภาพการสอน | |
| 10 | tut_rating_knowledge | DECIMAL | 3,2 | คะแนนความรู้ความสามารถ | |
| 11 | tut_rating_communication | DECIMAL | 3,2 | คะแนนการสื่อสารและการอธิบาย | |
| 12 | tut_rating_punctuality | DECIMAL | 3,2 | คะแนนความตรงต่อเวลา | |
| 13 | tut_rating_satisfaction | DECIMAL | 3,2 | คะแนนความพึงพอใจ | |
| 14 | tut_status | TINYINT | 1 | สถานะ:<br>0 = ยังไม่อนุมัติ<br>1 = อนุมัติแล้ว<br>2 = ปฏิเสธ<br>3 = ระงับการสอน | |
| 15 | tut_reject_note | TEXT | - | หมายเหตุการปฏิเสธ/ระงับ | หมายเหตุสีแดง: เพิ่ม |

## หน้า 6

### 4.3.1.8 ข้อมูลรายวิชาที่รับสอน

#### ตาราง 4.8 ตารางข้อมูลรายวิชาที่รับสอน (Tutor Course)

| No. | Attribute Name | Type | Size | Description | Key |
|---:|---|---|---|---|---|
| 1 | tutc_id | VARCHAR | 13 | รหัสรายวิชาที่รับสอน | PK |
| 2 | tutc_name | VARCHAR | 150 | ชื่อรายวิชาเพื่อโฆษณา | |
| 3 | tutc_desc | TEXT | - | รายละเอียดเนื้อหา | หมายเหตุสีแดง: เพิ่ม |
| 4 | tutc_img | VARCHAR | 100 | ชื่อไฟล์รูปปก | |
| 5 | tutc_max_stu | INT | - | จำนวนรับสูงสุด (คน) | |
| 6 | tutc_status | TINYINT | 1 | สถานะการเปิดสอน:<br>0 = ปิดรับสอน<br>1 = เปิดรับสอน | |
|  | tutc_rating | DECIMAL | 3,2 | คะแนนรีวิวเฉลี่ยรายคอร์ส (ตรงกับข้อความใน PDF ว่า “รีวิวแยกตามรายวิชาที่เปิดสอน”) | ตรวจสอบจากฟิลด์ในระบบ: `TutorCourse.tutc_rating` |
| 7 | crs_id | VARCHAR | 13 | รหัสรายวิชา | FK(Course) |
| 8 | tut_id | VARCHAR | 13 | รหัสติวเตอร์ | FK(Tutor) |

### 4.3.1.9 ข้อมูลอัตราค่าติว

#### ตาราง 4.9 ตารางข้อมูลอัตราค่าติว (Tutor Rate)

| No. | Attribute Name | Type | Size | Description | Key |
|---:|---|---|---|---|---|
| 1 | tut_rate_id | INT | - | รหัสค่าติว | PK |
| 2 | tut_rate_per_person | INT | - | อัตราค่าติว (เครดิต) ต่อคน | |
| 3 | tut_rate_stu_count | INT | - | เรทตามจำนวนคน | |
| 4 | tutc_id | VARCHAR | 13 | รหัสรายวิชาที่รับสอน | FK(Tutor Course) |

## หน้า 7

### 4.3.1.10 ข้อมูลวันที่เปิดสอน

#### ตาราง 4.10 ตารางข้อมูลวันที่เปิดสอน (ScheduleDate)

| No. | Attribute Name | Type | Size | Description | Key |
|---:|---|---|---|---|---|
| 1 | sd_id | INT | - | รหัสวันที่เปิดสอน | PK |
| 2 | sd_date | DATE | - | วันที่เปิดสอน | |
| 3 | tutc_id | VARCHAR | 13 | รหัสรายวิชาที่รับสอน | FK(Tutor Course) |

### 4.3.1.11 ข้อมูลช่วงเวลาที่เปิดสอน

#### ตาราง 4.11 ตารางข้อมูลช่วงเวลาที่เปิดสอน (TimeSlot)

| No. | Attribute Name | Type | Size | Description | Key |
|---:|---|---|---|---|---|
| 1 | ts_id | INT | - | รหัสวันที่เปิดสอน | PK |
| 2 | ts_start_time | TIME | - | เวลาเริ่ม | |
| 3 | ts_end_time | TIME | - | เวลาจบ | |
| 4 | ts_status | TINYINT | 1 | สถานะ:<br>0 = ว่าง<br>1 = จองแล้ว | |
| 5 | sd_id | INT | - | รหัสวันที่เปิดสอน | FK(ScheduleDate) |

## หน้า 8

### 4.3.1.12 ข้อมูลการเติมเครดิต

#### ตาราง 4.12 ตารางข้อมูลการเติมเครดิต (Refill)

| No. | Attribute Name | Type | Size | Description | Key |
|---:|---|---|---|---|---|
| 1 | rf_id | INT | - | รหัสการเติมเครดิต | PK |
| 2 | rf_date | DATETIME | - | วันเวลาที่แจ้งเติม | |
| 3 | [ไม่พบฟิลด์ในระบบ หน้า 8] | [ไม่พบ Type ในระบบ หน้า 8] | [ไม่พบ Size ในระบบ หน้า 8] | ธนาคารต้นทาง | หมายเหตุสีแดง: เพิ่ม |
| 4 | rf_money | DECIMAL | 7,2 | จำนวนเงินที่เติม | |
| 5 | rf_credit | INT | - | จำนวนเครดิตที่ได้รับ | |
| 6 | rf_slip | VARCHAR | 255 | ชื่อไฟล์สลิปการโอนเงิน | |
| 7 | rf_qr_payload | VARCHAR | 255 | ข้อมูล QR จากสลิป | |
| 8 | rf_confirm_date | DATETIME | - | วันเวลาที่ยืนยันการเติม | |
| 9 | rf_status | TINYINT | 1 | สถานะการตรวจสอบ:<br>0 = รอตรวจสอบ<br>1 = ผ่านการตรวจสอบ<br>2 = ไม่ผ่านการตรวจสอบ | |
| 10 | rf_cmt | TEXT | - | หมายเหตุ | |
| 11 | mb_id | VARCHAR | 13 | รหัสสมาชิก | FK(Member) |

> หมายเหตุ: ตรวจสอบโมเดล `Refill` และ migration ที่เกี่ยวข้องแล้ว ไม่พบฟิลด์สำหรับ “ธนาคารต้นทาง” ในระบบปัจจุบัน จึงไม่กำหนด Attribute Name, Type หรือ Size ขึ้นเอง

## หน้า 9

### 4.3.1.13 ข้อมูลการจองเรียน

#### ตาราง 4.13 ตารางข้อมูลการจองเรียน (Booking) — ส่วนที่ 1

| No. | Attribute Name | Type | Size | Description | Key |
|---:|---|---|---|---|---|
| 1 | bk_id | INT | - | รหัสการจองเรียน | PK |
| 2 | bk_desc | TEXT | - | รายละเอียด | |
| 3 | bk_stu_datetime | DATETIME | - | วันเวลาที่นัดเรียน | หมายเหตุสีแดง: รวม |
| 4 | bk_stu_count | INT | - | จำนวนผู้เรียน | |
| 5 | bk_rate_per_person | INT | - | อัตราค่าติว (เครดิต) ต่อคน | |
| 6 | bk_date | DATETIME | - | วันเวลาที่จอง | |
| 7 | bk_accepted_date | DATETIME | - | วันเวลาที่รับงาน | |
| 8 | bk_status | TINYINT | 1 | สถานะ:<br>0 = จอง<br>1 = รับงานแล้ว<br>2 = เรียนแล้ว<br>3 = แจ้งจบงาน<br>4 = ยืนยันการจบงาน<br>5 = รีวิวแล้ว<br>6 = ปฏิเสธ | |
| 9 | bk_cmt | TEXT | - | หมายเหตุ | |
| 10 | bk_report_reason | VARCHAR | 10 | สาเหตุการรายงานปัญหา:<br>1 = หลักฐานการสอนไม่ตรงความจริง<br>2 = ติวเตอร์ไม่เข้าสอน<br>3 = เนื้อหาไม่ตรงที่ตกลงไว้<br>5 = ผู้เรียนไม่เข้าเรียน<br>6 = ติดต่ออีกฝ่ายไม่ได้<br>7 = ไม่สามารถตกลงกันได้<br>8 = อื่น ๆ | |
| 11 | bk_report_desc | TEXT | - | รายละเอียดการรายงานปัญหา | |
| 12 | bk_report_date | DATETIME | - | วันเวลาที่รายงาน | |
| 13 | bk_report_resolved_date | DATETIME | - | วันเวลาที่จัดการรายงาน | |
| 14 | mb_id | VARCHAR | 13 | รหัสสมาชิก | FK(Member) |

## หน้า 10

### ตาราง 4.13 ตารางข้อมูลการจองเรียน (Booking) — ส่วนที่ 2 (ต่อจากหน้า 9)

| No. | Attribute Name | Type | Size | Description | Key |
|---:|---|---|---|---|---|
| 15 | tutc_id | VARCHAR | 13 | รหัสรายวิชาที่รับสอน | FK(Tutor Course) |
| 16 | ts_id | INT | - | รหัสวันที่เปิดสอน | FK(TimeSlot) |

> หมายเหตุ: ต้นหน้าที่ 10 แสดงข้อความ `1 bk_id` ซ้ำในส่วนหัวของตารางต่อเนื่อง และตำแหน่งข้อความของแถว 15–16 เหลื่อมกัน จึงจัดแถวตามลำดับข้อมูลต่อเนื่องจากหน้า 9; จุดนี้เป็น [กำกวมจากต้นฉบับ หน้า 10]

### 4.3.1.14 ข้อมูลกล่องข้อความ

#### ตาราง 4.14 กล่องข้อความ (Inbox)

| No. | Attribute Name | Type | Size | Description | Key |
|---:|---|---|---|---|---|
| 1 | ib_id | INT | - | รหัสกล่องข้อความ | PK |
| 2 | ib_mb_id1 | VARCHAR | 13 | รหัสสมาชิก คนที่ 1 | FK(Member) |
| 3 | ib_mb_id2 | VARCHAR | 13 | รหัสสมาชิก คนที่ 2 | FK(Member) |

### 4.3.1.15 ข้อมูลรายการข้อความ

#### ตาราง 4.15 ตารางข้อมูลรายการข้อความ (Message)

| No. | Attribute Name | Type | Size | Description | Key |
|---:|---|---|---|---|---|
| 1 | msg_id | INT | - | ลำดับข้อความ | PK |
| 2 | msg_sent_time | DATETIME | - | วันเวลาที่ส่ง | |
| 3 | msg | TEXT | - | ข้อความ | |
| 4 | msg_img | VARCHAR | 255 | ชื่อไฟล์รูปภาพในข้อความ | |
| 5 | msg_is_read | TINYINT | 1 | สถานะการอ่าน:<br>0 = ยังไม่อ่าน<br>1 = อ่านแล้ว | |
| 6 | msg_sender_mb_id | VARCHAR | 13 | มาจาก (รหัสผู้ส่ง) | FK(Member) |
| 7 | ib_id | INT | - | รหัสกล่องข้อความ | FK(Inbox) |

## หน้า 11

### 4.3.1.16 ข้อมูลกิจกรรมการติว

#### ตาราง 4.16 ตารางข้อมูลกิจกรรมการติว (Tutoring Activity)

| No. | Attribute Name | Type | Size | Description | Key |
|---:|---|---|---|---|---|
| 1 | bk_id | int | - | รหัสการจองเรียน | PK, FK(Booking) |
| 2 | ta_img1 | varchar | 255 | ชื่อไฟล์รูปภาพการสอน 1 | |
| 3 | ta_img2 | varchar | 255 | ชื่อไฟล์รูปภาพการสอน 2 | |
| 4 | ta_img3 | varchar | 255 | ชื่อไฟล์รูปภาพการสอน 3 | |
| 5 | ta_desc | text | - | รายละเอียดเพิ่มเติม | |

### 4.3.1.17 ข้อมูลการแจ้งจบงาน

#### ตาราง 4.17 ตารางข้อมูลการแจ้งจบงาน (Job Completion)

| No. | Attribute Name | Type | Size | Description | Key |
|---:|---|---|---|---|---|
| 1 | bk_id | INT | - | รหัสการจองเรียน | PK, FK(Booking) |
| 2 | jc_complete_date | DATETIME | - | วันเวลาที่แจ้งจบงาน | |
| 3 | jc_confirm_date | DATETIME | - | วันเวลาที่ยืนยัน | |

## หน้า 12

> หมายเหตุ: เอกสารต้นฉบับไม่มีหัวข้อ 4.3.1.18

### 4.3.1.19 ข้อมูลการรีวิว

#### ตาราง 4.19 ตารางข้อมูลการรีวิว (Review)

| No. | Attribute Name | Type | Size | Description | Key |
|---:|---|---|---|---|---|
| 1 | bk_id | INT | - | รหัสการจองเรียน | PK, FK(Booking) |
| 2 | rv_quality | TINYINT | 1 | คะแนนคุณภาพการสอน | |
| 3 | rv_knowledge | TINYINT | 1 | คะแนนความรู้ความสามารถ | |
| 4 | rv_communication | TINYINT | 1 | คะแนนการสื่อสารและการอธิบาย | |
| 5 | rv_punctuality | TINYINT | 1 | คะแนนความตรงต่อเวลา | |
| 6 | rv_satisfaction | TINYINT | 1 | คะแนนความพึงพอใจ | |
| 7 | rv_cmt | TEXT | - | ข้อความรีวิว | |
| 8 | rv_date | DATETIME | - | วันเวลาที่บันทึก | |

## หน้า 13

### 4.3.1.20 ข้อมูลการขอถอนเครดิต

#### ตาราง 4.20 ตารางข้อมูลการขอถอนเครดิต (Withdrawals)

| No. | Attribute Name | Type | Size | Description | Key |
|---:|---|---|---|---|---|
| 1 | wd_id | INT | - | รหัสการขอถอนเครดิต | PK |
| 2 | wd_req_date | DATETIME | - | วันเวลาที่ขอถอนเครดิต | |
| 3 | wd_type | TINYINT | 1 | ประเภทเครดิต:<br>0 = นำฝาก<br>1 = รายได้ | |
| 4 | wd_credit | INT | - | จำนวนเครดิตที่ถอน | |
| 5 | wd_cash | DECIMAL | 7,2 | จำนวนเงิน (บาท) | |
| 6 | wd_bank_name | VARCHAR | 100 | ชื่อธนาคาร | |
| 7 | wd_acc_name | VARCHAR | 100 | ชื่อบัญชี | |
| 8 | wd_acc_no | VARCHAR | 20 | เลขที่บัญชีธนาคาร | |
| 9 | wd_fee | DECIMAL | 7,2 | ค่าธรรมเนียมการถอน | |
| 10 | wd_net_cash | DECIMAL | 7,2 | ยอดสุทธิที่จ่ายจริง | |
| 11 | wd_paid_date | DATETIME | - | วันเวลาที่จ่าย | |
| 12 | wd_status | TINYINT | 1 | สถานะการจ่าย:<br>0 = รอดำเนินการ<br>1 = จ่ายแล้ว<br>2 = ปฏิเสธการถอน<br>3 = ยกเลิกการถอน | |
| 13 | wd_cmt | TEXT | - | หมายเหตุ | |
| 14 | mb_id | VARCHAR | 13 | รหัสสมาชิก | FK(Member) |

## หน้า 14

> หมายเหตุ: หมายเลขหัวข้อ 4.3.1.20 ปรากฏซ้ำจากหน้า 13 ในเอกสารต้นฉบับ

### 4.3.1.20 ข้อมูลคำชี้แจงรายงานปัญหา

#### ตาราง 4.15 ตารางข้อมูลคำชี้แจงรายงานปัญหา (booking report statement)

> หมายเหตุ: เลขตาราง 4.15 ซ้ำกับตารางข้อมูลรายการข้อความ (Message) ในหน้า 10 ตามต้นฉบับ

| No. | Attribute Name | Type | Size | Description | Key |
|---:|---|---|---|---|---|
| 1 | brs_id | INT | - | รหัสคำชี้แจงรายงานปัญหา | PK |
| 2 | brs_role | VARCHAR | 10 | บทบาทผู้ชี้แจง | |
| 3 | brs_desc | TEXT | - | รายละเอียดคำชี้แจง | |
| 4 | brs_date | DATETIME | - | วันเวลาที่ส่งคำชี้แจง | |
| 5 | bk_id | INT | - | รหัสการจองที่ถูกรายงานปัญหา | FK(Booking) |
| 6 | mb_id | VARCHAR | 13 | รหัสสมาชิกเจ้าของคำชี้แจง | FK(Member) |

### 4.3.1.21 ข้อมูลการแจ้งเตือน

#### ตาราง 4.21 ตารางข้อมูลการการแจ้งเตือน (Notification)

| No. | Attribute Name | Type | Size | Description | Key |
|---:|---|---|---|---|---|
| 1 | notif_id | BIGINT | - | รหัสรายการแจ้งเตือน สร้างอัตโนมัติ | PK, Auto Increment |
| 2 | notif_type | VARCHAR | 30 | ประเภทการแจ้งเตือน | |
| 3 | notif_text | VARCHAR | 255 | ข้อความแจ้งเตือน | |
| 4 | notif_url | VARCHAR | 255 | ลิงก์ปลายทางเมื่อกดแจ้งเตือน | |
| 5 | notif_is_read | BOOLEAN | 1 | สถานะการอ่านแจ้งเตือน: 0/False = ยังไม่อ่าน, 1/True = อ่านแล้ว; ค่าเริ่มต้น 0/False | |
| 6 | notif_created_at | DATETIME | - | วันเวลาที่สร้างแจ้งเตือน กำหนดอัตโนมัติเมื่อสร้างรายการ | |
| 7 | recipient_id | BIGINT | - | อ้างอิง Member.id ของสมาชิกผู้รับแจ้งเตือน; อนุญาต NULL กรณีผู้รับเป็นผู้ดูแลระบบ | FK(Member.id) |
| 8 | admin_recipient_id | INT | - | อ้างอิง auth_user.id ของผู้ดูแลระบบผู้รับแจ้งเตือน; อนุญาต NULL กรณีผู้รับเป็นสมาชิก | FK(auth_user.id) |

ค่า `notif_type` ที่ระบบรองรับ:

- `booking_new` = มีการจองติวใหม่
- `booking_accepted` = การจองได้รับการยืนยัน
- `booking_rejected` = การจองถูกปฏิเสธ
- `booking_completed` = มีการแจ้งจบงานที่ต้องยืนยัน
- `booking_credited` = งานเสร็จสิ้น ได้รับเครดิตแล้ว
- `booking_reviewed` = มีรีวิวใหม่
- `booking_reported` = มีการรายงานปัญหา
- `booking_cancel_requested` = มีคำขอยกเลิกการเรียน
- `booking_cancel_rejected` = คำขอยกเลิกไม่ได้รับการอนุมัติ
- `booking_cancelled` = การจองหรือการเรียนถูกยกเลิก
- `booking_report_statement` = มีคำชี้แจงเพิ่มเติมในรายงาน
- `booking_report_resolved` = รายงานได้รับการพิจารณาแล้ว
- `tutor_approved` = ติวเตอร์ได้รับการอนุมัติ
- `tutor_rejected` = ติวเตอร์ถูกปฏิเสธ
- `tutor_suspended` = บัญชีติวเตอร์ถูกระงับ
- `refill_approved` = เติมเครดิตผ่านการตรวจสอบ
- `refill_rejected` = เติมเครดิตไม่ผ่านการตรวจสอบ
- `withdraw_paid` = ถอนเงินเข้าบัญชีเรียบร้อย
- `admin_refill` = มีคำขอเติมเครดิต
- `admin_withdraw` = มีคนขอถอนเครดิต
- `admin_tutor_new` = มีติวเตอร์สมัครใหม่รออนุมัติ
- `admin_reported` = มีการรายงานปัญหา
