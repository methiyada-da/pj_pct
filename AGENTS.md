# โครงสร้างโปรเจค: Puean Chuay Tu (Django)

## Architecture

```
Request
→ config/urls.py
→ apps/<app>/urls.py
→ views.py
→ forms.py (ถ้ามี)
→ models.py
→ template
→ Response
```

## โครงสร้างโฟลเดอร์หลัก

```
pj_pct/
├── apps/
│   ├── __init__.py
│   ├── accounts/          ← Member, Tutor
│   │   ├── migrations/
│   │   ├── admin.py, apps.py, forms.py
│   │   ├── models.py, tests.py, urls.py, views.py
│   ├── admin_panel/       ← System config + reports
│   │   ├── management/commands/
│   │   │   └── set_email_domain.py
│   │   ├── migrations/
│   │   ├── admin.py, apps.py, context_processors.py, forms.py
│   │   ├── middleware.py, models.py, tests.py, urls.py, utils.py, views.py
│   ├── bookings/          ← Booking, TutoringActivity, JobCompletion, Review, BookingReportStatement
│   │   ├── migrations/
│   │   ├── admin.py, apps.py, forms.py
│   │   ├── models.py, tests.py, urls.py, views.py
│   ├── courses/           ← Faculty, Major, CourseGroup, Course
│   │   ├── migrations/
│   │   ├── admin.py, apps.py, forms.py
│   │   ├── models.py, tests.py, urls.py, views.py
│   ├── credits/           ← Refill, Withdrawals
│   │   ├── migrations/
│   │   ├── admin.py, apps.py, forms.py
│   │   ├── models.py, tests.py, urls.py, views.py
│   ├── messaging/         ← Inbox, Message
│   │   ├── migrations/
│   │   ├── admin.py, apps.py, context_processors.py
│   │   ├── forms.py, models.py, tests.py, urls.py, views.py
│   ├── notifications/     ← Notification + signals
│   │   ├── migrations/
│   │   ├── admin.py, apps.py, models.py
│   │   ├── signals.py, tests.py, urls.py, views.py
│   └── tutoring/          ← TutorCourse, TutorRate, ScheduleDate, TimeSlot
│       ├── migrations/
│       ├── admin.py, apps.py, forms.py, models.py, tests.py, urls.py, views.py
├── config/
│   ├── __init__.py
│   ├── asgi.py, settings.py, urls.py, wsgi.py
├── templates/
│   ├── accounts/
│   │   ├── auth_base.html, login.html, register.html, register_pending.html
│   │   ├── profile.html, email_verify.html
│   │   ├── password_reset*.html, verify_email_*.html
│   ├── admin_panel/
│   │   ├── base_admin.html, _sidebar.html, _topbar.html
│   │   ├── admin_setup.html, dashboard.html, member_mgmt.html
│   │   ├── tutor_mgmt_list.html, tutor_mgmt_detail.html, payment_mgmt.html
│   │   ├── refill_mgmt.html, report_mgmt.html, system_settings.html
│   ├── bookings/
│   │   ├── student_bookings.html, tutor_requests.html
│   │   ├── tutoring_activity.html, confirm_completion.html, review.html
│   ├── courses/
│   │   ├── faculty_list.html, major_list.html
│   │   ├── course_group_list.html, course_list.html
│   ├── credits/
│   │   ├── credit.html, topup.html, withdraw.html
│   ├── main/
│   │   ├── base.html, home.html, _header.html, _footer.html
│   ├── messaging/
│   │   ├── inbox.html, chat.html
│   └── tutoring/
│       ├── search.html, detail.html, register_tutor.html
│       ├── tutor_profile.html, tutor_profile_edit.html, tutor_manage.html
│       ├── tutor_course_list.html, manage_course.html, _course_options.html
├── static/
│   ├── btt5/              ← Bootstrap 5 (css/, js/) [library ไม่ต้องแก้]
│   ├── css/               ← admin.css, auth.css, detail.css, main.css, messaging.css, search.css
│   ├── faws6/              ← Font Awesome 6 (icon library ไม่ต้องแก้)
│   ├── images/             ← home.jpg, home1-3.jpg, login.jpg, register.jpg
│   └── js/
│       └── notifications.js
├── media/                  ← ไฟล์ที่ผู้ใช้อัปโหลด (รูปโปรไฟล์, สลิป, รูปกิจกรรม ฯลฯ) ไม่ใช่โค้ด
│   ├── accounts/member_profile/
│   ├── chat/
│   ├── member/
│   ├── Refill/
│   ├── tutor_cards/
│   ├── tutor_course/
│   └── tutoring/
│       ├── activity/
│       ├── tutor_img_course/
│       └── tutor_student_cards/
├── venv/                   ← Python virtual environment (ไม่เกี่ยวกับโค้ดโปรเจค)
├── AGENTS.md
├── .gitignore
├── manage.py
└── requirements.txt
```

> หมายเหตุ: ตัดรายละเอียดปลีกย่อยของไฟล์ static ของ library ภายนอก (เช่น รายชื่อไอคอน SVG ทั้งหมดใน `faws6/`, ไฟล์ CSS/JS ย่อยของ Bootstrap) และรายชื่อไฟล์ใน `media/` ออก เพราะเป็น asset/library ที่ไม่ต้องแก้ไขหรืออ้างอิงตอนพัฒนาโค้ด — ไม่จำเป็นต่อ context ของ AI

## ไฟล์มาตรฐานภายในแต่ละ App

ตัวอย่างจาก `accounts/` (ใช้เป็น pattern สำหรับทุก app):

| ไฟล์ | หน้าที่ |
|------|---------|
| `models.py` | Model definitions |
| `views.py` | View functions / class-based views |
| `urls.py` | URL routing |
| `forms.py` | Django forms |
| `admin.py` | Django admin registration |
| `apps.py` | App config |
| `migrations/` | Database migrations |
| `tests.py` | Unit tests |
| `serializers.py` | สำหรับ API (REST Framework) — ยังไม่มีใช้จริงในทุก app |
| `signals.py` | Django signals (เช่น auto-create Tutor record) — มีเฉพาะ `notifications/` |
| `permissions.py` | Custom permissions (IsTutor, IsMember) — ยังไม่มีไฟล์นี้จริงในโปรเจค |

App พิเศษที่มีไฟล์เพิ่มนอกเหนือ pattern มาตรฐาน:
- `admin_panel/` มี `context_processors.py`, `middleware.py`, `utils.py`, และ `management/commands/set_email_domain.py`
- `messaging/` มี `context_processors.py`

## Models แยกตาม App

| App | Models |
|-----|--------|
| `accounts` | Member, Tutor |
| `courses` | Faculty, Major, CourseGroup, Course |
| `tutoring` | TutorCourse, TutorRate, ScheduleDate, TimeSlot |
| `bookings` | Booking, TutoringActivity, JobCompletion, Review, BookingReportStatement |
| `messaging` | Inbox, Message |
| `credits` | Refill, Withdrawals |
| `notifications` | Notification |
| `admin_panel` | System config, Reports |

## App Relationship

```
accounts
├── Member
└── Tutor

tutoring
├── TutorCourse
├── TimeSlot
└── ScheduleDate

bookings
└── Booking
    ├── Member
    ├── TutorCourse
    └── TutoringActivity

messaging
└── Inbox
    └── Message

credits
├── Refill
└── Withdrawals

notifications
└── Notification
```

> หมายเหตุ: นี่คือความสัมพันธ์เชิงแนวคิดคร่าวๆ เท่านั้น หากไม่แน่ใจ FK จริงในโค้ด ให้เปิด `models.py` ของ app นั้นตรวจสอบก่อนเสมอ ห้ามอนุมานเองจากผังนี้เพียงอย่างเดียว

## Business Workflow

### Member (ผู้เรียน)
```
สมัครสมาชิก / เข้าสู่ระบบ
→ ค้นหาติวเตอร์
→ ดูรายละเอียดคอร์ส
→ เติมเครดิต
→ จองเรียน
→ ใช้เครดิตชำระเงิน
→ เรียนตามเวลาที่จอง
→ ยืนยันการเรียนเสร็จ
→ รีวิวติวเตอร์
→ ถอนเครดิตคงเหลือ (หากมี)
```

### Tutor (ผู้สอน)
```
สมัครสมาชิก / เข้าสู่ระบบ
→ สมัครเป็นติวเตอร์
→ รอแอดมินอนุมัติ
→ เพิ่มคอร์สที่สอน
→ ตั้งวันและเวลาเรียน
→ รับรายการจอง
→ สอนนักเรียน
→ ยืนยันงานเสร็จ
→ ได้รับเครดิตจากการสอน
→ ถอนเครดิต
```

### Admin
```
จัดการสมาชิก
→ อนุมัติ / ปฏิเสธติวเตอร์
→ ตรวจสอบการเติมเครดิต
→ ตรวจสอบการถอนเครดิต
→ จัดการรายงาน
→ ตั้งค่าระบบ
```

## Tech Stack

- **Framework:** Django (Python)
- **Structure:** Multi-app Django project
- **Template Engine:** Django Templates (HTML)
- **Static Files:** CSS, JS, Bootstrap (btt5), Font Awesome (faws6)
- **Environment:** venv (Python virtual environment)

## Coding Convention

- ใช้ Function Based Views
- ใช้ Django Forms
- ไม่ใช้ Django REST Framework
- ใช้ Django Template
- CSS อยู่ที่ `static/css`
- JavaScript อยู่ที่ `static/js`
- แต่ละ app มี template ของตัวเอง (แยกตามชื่อ app ใน `templates/<app>/`)

## Commands

```bash
python manage.py runserver
python manage.py makemigrations
python manage.py migrate
python manage.py test
```

---

## คำสั่งสำหรับ AI ที่รับไฟล์นี้

### Workflow เมื่อได้รับคำสั่ง
1. อ่าน requirement
2. ระบุไฟล์ที่จะต้องแก้
3. ถ้าข้อมูลไม่ครบ ให้ถามก่อน
4. อธิบายแนวทางสั้น ๆ
5. จึงเริ่มเขียนโค้ด
6. หลังเขียนเสร็จ สรุปไฟล์ที่ถูกแก้
7. แจ้งว่าต้อง migrate หรือไม่

### การสร้างไฟล์ใหม่
- **ถามความต้องการให้ครบก่อนเสมอ** ได้แก่ logic, field, ความสัมพันธ์, ลักษณะ UI ฯลฯ
- เริ่มสร้างได้ต่อเมื่อผู้ใช้ยืนยันแล้วเท่านั้น

### การแก้ไขไฟล์
- ถ้าแก้ **ไม่เกิน 2 จุด** → **ห้ามส่งไฟล์ทั้งหมด** ให้บอกตำแหน่งที่แก้แทน เช่น:
  - "บรรทัดที่ 42 — เปลี่ยน `X` เป็น `Y`"
  - "แทรกโค้ดนี้หลังบรรทัดที่ 55 (หลัง `def save():`):"
  - "ลบบรรทัดที่ 30–33 ออก"
- ถ้าแก้ **3 จุดขึ้นไป** → **ส่งโค้ดไฟล์ทั้งหมดมาเลย ห้ามบอกเป็นตำแหน่ง**
- **ระบุตำแหน่งให้ชัดเจน** โดยอ้างเลขบรรทัด + context รอบข้าง (ชื่อ function / block) เสมอ

### บอก Context ก่อนเริ่มเสมอ
- ก่อนสร้างหรือแก้ไขทุกครั้ง ให้ระบุให้ชัดว่ากำลังทำงานกับไฟล์ไหน ใน app ไหน เช่น "กำลังแก้ `bookings/views.py`"

### ห้ามสมมติ
- ถ้าไม่แน่ใจว่า field, model, หรือ function มีอยู่จริงในโปรเจคไหม → **ถามก่อนเสมอ ห้ามเดาแล้วเขียนเลย**

### บอก Dependency ทุกครั้ง
- ถ้าโค้ดที่สร้างหรือแก้ต้องพึ่ง import, package, หรือ setting อื่น → แจ้งด้วยว่าต้องเพิ่มอะไร ที่ไหน

### ภาษาในโค้ด
- **Comment ใช้ภาษาไทย**
- ชื่อตัวแปร, function, class ใช้ภาษาอังกฤษตาม Django convention

### แจ้งเตือน Migration
- ถ้ามีการแก้ไข `models.py` ทุกครั้ง → ต้องแจ้งเตือนท้ายคำตอบว่า:
  "⚠️ อย่าลืมรัน `python manage.py makemigrations` และ `python manage.py migrate`"

### ข้อห้าม
- **ห้ามแก้ `models.py` โดยไม่จำเป็น** — ถ้างานที่ขอไม่ได้ต้องการ field/relation ใหม่ ห้ามแตะ models เด็ดขาด ถ้าไม่แน่ใจว่าจำเป็นหรือไม่ ให้ถามก่อน
- **ห้ามเปลี่ยน URL เดิม** — ห้ามแก้ไข เปลี่ยนชื่อ หรือย้าย path/name ของ URL pattern ที่มีอยู่แล้วใน `urls.py` ของทุก app หากต้องเพิ่มหน้าใหม่ ให้เพิ่ม URL ใหม่แทนการแก้ของเดิม
- **หน้าเว็บต้องใช้ภาษาไทยเสมอ** — ข้อความที่แสดงผลใน template (HTML), label, ปุ่ม, ข้อความแจ้งเตือน (messages/alerts), placeholder ในฟอร์ม ฯลฯ ที่ผู้ใช้เห็น ต้องเป็นภาษาไทยทั้งหมด (comment ในโค้ดเป็นภาษาไทยตามที่กำหนดไว้ด้านบนอยู่แล้ว ส่วนชื่อตัวแปร/ฟังก์ชัน/คลาสยังคงเป็นภาษาอังกฤษตาม Django convention)

### ห้ามแก้ (โฟลเดอร์/ไฟล์)
- `static/btt5/` (Bootstrap 5 library)
- `static/faws6/` (Font Awesome 6 library)
- `media/` (ไฟล์ที่ผู้ใช้อัปโหลด)
- `migrations/` ของทุก app (ห้ามแก้ไขไฟล์ migration ที่มีอยู่แล้วด้วยมือ ให้ใช้คำสั่ง `makemigrations` สร้างใหม่แทนเสมอ)
- `venv/` (Python virtual environment)

### เมื่อส่งโค้ด
- ถ้าเป็นไฟล์ใหม่ → ส่งทั้งไฟล์
- ถ้าเป็นการแก้เล็กน้อย (ไม่เกิน 2 จุดตามกฎด้านบน) → บอกตำแหน่งที่แก้แทนการส่งทั้งไฟล์
- ห้ามตัดโค้ดส่วนอื่นออกเมื่อส่งทั้งไฟล์
- ห้ามใช้ `...` หรือคอมเมนต์ลักษณะ "โค้ดเดิม" แทนโค้ดจริง
- โค้ดที่ส่งต้องสมบูรณ์และคัดลอกไปใช้ได้ทันที

## Final Response Format

- ตอบเป็นภาษาไทย
- สรุปว่าทำอะไรไป
- ระบุไฟล์ที่แก้
- แจ้งว่าต้องรันคำสั่งอะไรต่อ
- ถ้าแก้ `models.py` ต้องแจ้งให้รัน:
  - `python manage.py makemigrations`
  - `python manage.py migrate`