# เลือกโค้ดหลักสำหรับบท 4.4

> ฉันกำลังทำบทที่ 4.4 ผลการพัฒนาระบบ สำหรับปริญญานิพนธ์ระบบ “เพื่อนช่วยติว”
>
> ช่วยตรวจสอบ Source Code ในโปรเจกต์ และเลือก **เฉพาะโค้ดส่วนหลักและสำคัญของแต่ละ Process** ที่เหมาะสำหรับนำไปใส่ในเล่ม เช่น Logic การตรวจสอบเงื่อนไข การบันทึก/แก้ไขข้อมูล การเปลี่ยนสถานะ การคำนวณ หรือการทำงานหลักของ Process
>
> **ไม่ต้องเอาโค้ดมาละเอียดมาก** ไม่ต้องเอา CSS, HTML ตกแต่ง, import หรือโค้ดทั่วไปที่ไม่ได้แสดงการทำงานสำคัญ
>
> โค้ดที่เลือก **ไม่จำเป็นต้องเป็นบรรทัดติดกันทั้งหมด** หาก Logic สำคัญอยู่คนละช่วง สามารถเลือกหลายช่วงได้ เช่น บรรทัด 35–45 และ 60–70
>
> ในแต่ละ Process ให้บอกเพียง:
>
> - &#x20;ชื่อ Process&#x20;
> - &#x20;ชื่อไฟล์&#x20;
> - &#x20;ช่วงบรรทัดที่ควรนำไปใส่&#x20;
> - &#x20;โค้ดส่วนที่เลือก&#x20;
> - &#x20;อธิบายสั้น ๆ 1–2 ประโยคว่าโค้ดส่วนนี้ทำอะไร&#x20;
>
> **เลือกเฉพาะส่วนหลักจริง ๆ เพื่อไม่ให้เนื้อหาในเล่มยาวเกินไป และห้ามเขียนโค้ดใหม่ ให้ใช้เฉพาะโค้ดที่มีอยู่จริงในโปรเจกต์**

<details><summary>1 previous message</summary>

> ผมจะไล่จาก URL ไปยัง view/form/model ของแต่ละแอป เพื่อระบุ Process ที่ระบบมีจริง แล้วคัดเฉพาะช่วงโค้ดที่เป็นแกนของเงื่อนไข การบันทึก การเปลี่ยนสถานะ และการคำนวณ โดยจะไม่แก้ไขไฟล์ใด ๆ ครับ
</details>

จากเส้นทางของระบบ พบ Process หลักครอบคลุมสมาชิก ติวเตอร์ การค้นหาและจอง งานสอน/รีวิว เครดิต การสนทนา และงานผู้ดูแลระบบ ต่อไปผมกำลังตรวจบรรทัดจริงในฟังก์ชันที่รับผิดชอบแต่ละ Process เพื่อให้ช่วงบรรทัดที่อ้างอิงตรงกับ Source Code ปัจจุบันครับ

> เริ่มตรวจสอบจาก Process **การตรวจสอบสิทธิ์การใช้งาน** ก่อน

<details><summary>1 previous message</summary>

> ได้ครับ ผมจะจำกัดเฉพาะ Process “การตรวจสอบสิทธิ์การใช้งาน” โดยตรวจทั้งการยืนยันตัวตนตอนเข้าสู่ระบบ และเงื่อนไขจำกัดสิทธิ์ของสมาชิก ติวเตอร์ และผู้ดูแลระบบ แล้วคัดเฉพาะแกนสำคัญที่สุดสำหรับใส่เล่มครับ
</details>

ชื่อ Process: การตรวจสอบสิทธิ์การใช้งาน

ชื่อไฟล์: `apps/accounts/views.py`

ช่วงบรรทัดที่ควรนำไปใส่: 63–92

```python
if request.user.is_authenticated:
    return redirect('home')

if request.method == 'POST':
    email    = request.POST.get('username', '').strip()
    password = request.POST.get('password', '')
    next_url = request.POST.get('next', '')

    from django.contrib.auth.models import User as AuthUser
    try:
        user_obj = AuthUser.objects.get(email=email)
        username = user_obj.username
    except AuthUser.DoesNotExist:
        username = email

    user = authenticate(request, username=username, password=password)
    if user is not None:
        login(request, user)
        if request.POST.get('remember_me'):
            request.session.set_expiry(60 * 60 * 24 * 7)
        else:
            request.session.set_expiry(0)

        if user.is_staff:
            return redirect('admin_panel:dashboard')
        return redirect(next_url or 'home')
    else:
        login_error = 'อีเมลหรือรหัสผ่านไม่ถูกต้อง กรุณาลองใหม่อีกครั้ง'
```

อธิบาย: ระบบค้นหาบัญชีจากอีเมลและตรวจสอบรหัสผ่านด้วย Django Authentication หากข้อมูลถูกต้องจะสร้าง Session และแยกเส้นทางเข้าใช้งานระหว่างผู้ดูแลระบบกับสมาชิกทั่วไป หากไม่ถูกต้องจะแจ้งข้อผิดพลาดและไม่อนุญาตให้เข้าสู่ระบบ

ไม่มีการแก้ไข Source Code และไม่ต้องรันคำสั่งหรือ Migration ครับ

> ฉันกำลังจัดทำปริญญานิพนธ์ บทที่ 4 หัวข้อ 4.4 ผลการพัฒนาระบบ
> ของระบบเว็บแอปพลิเคชัน “เพื่อนช่วยติว”
>
> ช่วยตรวจสอบ Source Code ในโปรเจกต์ และเลือกเฉพาะ Source Code ส่วนหลักและสำคัญ
> ของแต่ละ Process เพื่อนำไปใส่ในหัวข้อ 4.4 ผลการพัฒนาระบบ
>
> หลักในการเลือก Source Code:
>
> - เลือกเฉพาะ Logic หลักที่แสดงการทำงานของ Process นั้น
> - ไม่ต้องเอาโค้ดมาละเอียดหรือยาวเกินไป
> - เน้นส่วนสำคัญ เช่น การตรวจสอบเงื่อนไข การค้นหาข้อมูล การบันทึก/แก้ไขข้อมูล
>   การเปลี่ยนสถานะ การคำนวณ หรือการทำงานหลักของ Process
> - ไม่ต้องนำ CSS, HTML สำหรับตกแต่ง, import, layout, navbar, footer
>   หรือโค้ดทั่วไปที่ไม่สำคัญมาใส่
> - หาก HTML หรือ JavaScript เป็นส่วนสำคัญต่อ Logic ของ Process จึงค่อยเลือกมา
> - Source Code ที่เลือกไม่จำเป็นต้องเป็นบรรทัดต่อเนื่องกันทั้งหมด
>   หาก Logic สำคัญอยู่คนละช่วง สามารถเลือกหลายช่วงได้
>   เช่น บรรทัด 35–45 และ 60–70
> - หาก Logic สำคัญอยู่คนละไฟล์ สามารถเลือกจากหลายไฟล์ได้
> - เลือกให้น้อยที่สุดเท่าที่จำเป็น แต่ต้องยังมองเห็นการทำงานหลักของ Process
> - ห้ามเขียน Source Code ใหม่ ห้ามปรับแก้ Source Code
>   ให้ใช้เฉพาะโค้ดที่มีอยู่จริงในโปรเจกต์เท่านั้น
>
> สำหรับแต่ละ Process ให้เขียนคำอธิบายสั้น ๆ ใต้ชื่อหัวข้อก่อนแสดง Source Code
> โดยเขียนเพียง 1 ประโยคสั้น ๆ แบบภาษาปริญญานิพนธ์
> ไม่ต้องอธิบายรายละเอียดเยอะ
>
> ตัวอย่างรูปแบบคำอธิบาย:
>
> 4.4.1 ตรวจสอบสิทธิ์การใช้งาน
> เป็นระบบที่ใช้ในการตรวจสอบสิทธิ์เข้าใช้งานของผู้ใช้งาน โดยรับข้อมูลสำหรับเข้าสู่ระบบและตรวจสอบข้อมูลก่อนอนุญาตให้เข้าใช้งาน โดยมีคำสั่ง ดังนี้
>
> ให้เขียนคำอธิบายในลักษณะเดียวกันให้เหมาะกับการทำงานจริงของแต่ละ Process
>
> รูปแบบผลลัพธ์ที่ต้องการ:
>
> 4.4.x [ชื่อ Process]
>
> [คำอธิบายสั้น ๆ 1 ประโยค] โดยมีคำสั่ง ดังนี้
>
> ชื่อไฟล์: [ชื่อและ path ของไฟล์]
> ช่วงบรรทัด: [บรรทัด xx–xx]
>
> [แสดง Source Code เฉพาะส่วนหลักที่เลือก]
>
> หากต้องใช้มากกว่า 1 ช่วง ให้ระบุ:
> ช่วงที่ 1: บรรทัด xx–xx
> ช่วงที่ 2: บรรทัด xx–xx
>
> และแสดงโค้ดของแต่ละช่วง
>
> ไม่ต้องเขียนคำอธิบาย Source Code แบบยาวหลังโค้ด
> ไม่ต้องอธิบายทีละบรรทัด
> ไม่ต้องเสนอการแก้ไขโค้ด
> ไม่ต้องรันคำสั่ง ไม่ต้อง Migration และไม่ต้องแก้ไขไฟล์ใด ๆ
>
> ให้ตรวจสอบจาก Source Code จริงในโปรเจกต์ก่อนเลือกทุกครั้ง
> และเน้นให้ผลลัพธ์พร้อมนำไปจัดทำหัวข้อ 4.4 ในเล่มปริญญานิพนธ์ได้ทันที
>
> เริ่มจาก Process: จัดการข้อมูลพื้นฐาน

<details><summary>1 previous message</summary>

> กำลังตรวจสอบ Process “จัดการข้อมูลพื้นฐาน” ในแอป `courses` ซึ่งครอบคลุมข้อมูลคณะ สาขาวิชา กลุ่มวิชา และรายวิชา โดยจะคัดเฉพาะ Logic การค้นหา เพิ่ม แก้ไข และลบที่เป็นตัวแทนการทำงานหลักของ Process ครับ
</details>

### 4.4.2 จัดการข้อมูลพื้นฐาน

เป็นระบบที่ใช้สำหรับค้นหา เพิ่ม แก้ไข และลบข้อมูลคณะ สาขาวิชา กลุ่มรายวิชา และรายวิชา พร้อมตรวจสอบข้อมูลที่เกี่ยวข้องก่อนดำเนินการ โดยมีคำสั่ง ดังนี้

ชื่อไฟล์: `apps/courses/views.py`

ช่วงที่ 1: บรรทัด 244–255

```python
def course_list(request):
    qs = Course.objects.select_related('cg_id').annotate(
    tutorcourse_count=Count('tutorcourse')
    ).order_by('crs_id')
    q         = request.GET.get('q',  '').strip()
    cg_filter = request.GET.get('cg', '')
    if q:
        qs = qs.filter(Q(crs_id__icontains=q) | Q(crs_name__icontains=q))
    if cg_filter:
        qs = qs.filter(cg_id=cg_filter)
    paginator     = Paginator(qs, 10)
    page          = paginator.get_page(request.GET.get('page', 1))
```

ช่วงที่ 2: บรรทัด 273–279

```python
if request.method == 'POST':
    data = request.POST.copy()
    data['crs_id'] = Course.generate_id()
    form = CourseForm(data)
    if form.is_valid():
        form.save()
        messages.success(request, 'เพิ่มรายวิชาเรียบร้อยแล้ว')
```

ช่วงที่ 3: บรรทัด 288–295

```python
obj = get_object_or_404(Course, pk=pk)
if request.method == 'POST':
    data = request.POST.copy()
    data['crs_id'] = pk  # ใส่ crs_id กลับเข้าไปเพราะ modal ไม่ส่งมา
    form = CourseForm(data, instance=obj)
    if form.is_valid():
        form.save()
        messages.success(request, 'แก้ไขรายวิชาเรียบร้อยแล้ว')
```

ช่วงที่ 4: บรรทัด 304–305 และ 308–314

```python
obj = get_object_or_404(Course, pk=pk)
if request.method == 'POST':
    tutor_course_count = TutorCourse.objects.filter(crs_id=obj).count()
    if tutor_course_count > 0:
        messages.error(request, f'ไม่สามารถลบรายวิชา "{obj.crs_name}" ได้ เนื่องจากมีติวเตอร์ใช้งานอยู่ ({tutor_course_count} คอร์ส)')
    else:
        try:
            obj.delete()
            messages.success(request, f'ลบรายวิชา "{obj.crs_name}" เรียบร้อยแล้ว')
```

ชื่อไฟล์: `apps/courses/models.py`

ช่วงบรรทัด: 71–78

```python
@classmethod
def generate_id(cls):
    last = cls.objects.order_by('-crs_id').first()
    if last:
        num = int(last.crs_id[3:]) + 1
    else:
        num = 1
    return f'CRS{num:04d}'
```

> ถ้ามีหลายข่วงให้บอหด้วยว่าช่วงนั้นๆคืออะไรเช่น ช่วงบรรทัด: 71–78   : \<!-- ฟอร์มเลือกการประมูล -->

รับทราบครับ หากมีหลายช่วง ผมจะระบุหน้าที่ของแต่ละช่วงต่อท้ายเลขบรรทัดให้ชัดเจน เช่น

### 4.4.2 จัดการข้อมูลพื้นฐาน

เป็นระบบที่ใช้สำหรับค้นหา เพิ่ม แก้ไข และลบข้อมูลคณะ สาขาวิชา กลุ่มรายวิชา และรายวิชา พร้อมตรวจสอบข้อมูลที่เกี่ยวข้องก่อนดำเนินการ โดยมีคำสั่ง ดังนี้

ชื่อไฟล์: `apps/courses/views.py`

ช่วงที่ 1 — บรรทัด 244–255: การค้นหา กรอง และแบ่งหน้าข้อมูลรายวิชา

```python
def course_list(request):
    qs = Course.objects.select_related('cg_id').annotate(
    tutorcourse_count=Count('tutorcourse')
    ).order_by('crs_id')
    q         = request.GET.get('q',  '').strip()
    cg_filter = request.GET.get('cg', '')
    if q:
        qs = qs.filter(Q(crs_id__icontains=q) | Q(crs_name__icontains=q))
    if cg_filter:
        qs = qs.filter(cg_id=cg_filter)
    paginator     = Paginator(qs, 10)
    page          = paginator.get_page(request.GET.get('page', 1))
```

ช่วงที่ 2 — บรรทัด 273–279: การตรวจสอบและบันทึกข้อมูลรายวิชาใหม่

```python
if request.method == 'POST':
    data = request.POST.copy()
    data['crs_id'] = Course.generate_id()
    form = CourseForm(data)
    if form.is_valid():
        form.save()
        messages.success(request, 'เพิ่มรายวิชาเรียบร้อยแล้ว')
```

ช่วงที่ 3 — บรรทัด 288–295: การค้นหาและแก้ไขข้อมูลรายวิชาเดิม

```python
obj = get_object_or_404(Course, pk=pk)
if request.method == 'POST':
    data = request.POST.copy()
    data['crs_id'] = pk  # ใส่ crs_id กลับเข้าไปเพราะ modal ไม่ส่งมา
    form = CourseForm(data, instance=obj)
    if form.is_valid():
        form.save()
        messages.success(request, 'แก้ไขรายวิชาเรียบร้อยแล้ว')
```

ช่วงที่ 4 — บรรทัด 304–305: การค้นหารายวิชาที่ต้องการลบ

```python
obj = get_object_or_404(Course, pk=pk)
if request.method == 'POST':
```

ช่วงที่ 5 — บรรทัด 308–316: การตรวจสอบข้อมูลคอร์สที่เกี่ยวข้องก่อนลบรายวิชา

```python
tutor_course_count = TutorCourse.objects.filter(crs_id=obj).count()
if tutor_course_count > 0:
    messages.error(request, f'ไม่สามารถลบรายวิชา "{obj.crs_name}" ได้ เนื่องจากมีติวเตอร์ใช้งานอยู่ ({tutor_course_count} คอร์ส)')
else:
    try:
        obj.delete()
        messages.success(request, f'ลบรายวิชา "{obj.crs_name}" เรียบร้อยแล้ว')
    except Exception:
        messages.error(request, 'ไม่สามารถลบได้ เนื่องจากมีข้อมูลที่เกี่ยวข้อง')
```

ชื่อไฟล์: `apps/courses/models.py`

ช่วงที่ 1 — บรรทัด 71–78: การสร้างรหัสรายวิชาใหม่โดยอัตโนมัติ

```python
@classmethod
def generate_id(cls):
    last = cls.objects.order_by('-crs_id').first()
    if last:
        num = int(last.crs_id[3:]) + 1
    else:
        num = 1
    return f'CRS{num:04d}'
```

> ใส่ไปให้เลยเช่น    \<!-- การสร้างรหัสรายวิชาใหม่โดยอัตโนมัติ --> @classmethod&#x20;
> def generate\_id(cls):
> &#x20;   last = cls.objects.order\_by('-crs\_id').first()
> &#x20;   if last:
> &#x20;       num = int(last.crs\_id[3:]) + 1
> &#x20;   else:
> &#x20;       num = 1
> &#x20;   return f'CRS{num:04d}'

เข้าใจแล้วครับ ต่อไปจะใส่คำอธิบายช่วงไว้ในกล่อง Source Code โดยตรง ดังนี้

### 4.4.2 จัดการข้อมูลพื้นฐาน

เป็นระบบที่ใช้สำหรับค้นหา เพิ่ม แก้ไข และลบข้อมูลคณะ สาขาวิชา กลุ่มรายวิชา และรายวิชา พร้อมตรวจสอบข้อมูลที่เกี่ยวข้องก่อนดำเนินการ โดยมีคำสั่ง ดังนี้

ชื่อไฟล์: `apps/courses/views.py`
ช่วงบรรทัด: 244–255, 273–279, 288–295, 304–305 และ 308–316

```python
<!-- การค้นหา กรอง และแบ่งหน้าข้อมูลรายวิชา -->
def course_list(request):
    qs = Course.objects.select_related('cg_id').annotate(
    tutorcourse_count=Count('tutorcourse')
    ).order_by('crs_id')
    q         = request.GET.get('q',  '').strip()
    cg_filter = request.GET.get('cg', '')
    if q:
        qs = qs.filter(Q(crs_id__icontains=q) | Q(crs_name__icontains=q))
    if cg_filter:
        qs = qs.filter(cg_id=cg_filter)
    paginator = Paginator(qs, 10)
    page = paginator.get_page(request.GET.get('page', 1))

<!-- การตรวจสอบและบันทึกข้อมูลรายวิชาใหม่ -->
if request.method == 'POST':
    data = request.POST.copy()
    data['crs_id'] = Course.generate_id()
    form = CourseForm(data)
    if form.is_valid():
        form.save()
        messages.success(request, 'เพิ่มรายวิชาเรียบร้อยแล้ว')

<!-- การค้นหาและแก้ไขข้อมูลรายวิชาเดิม -->
obj = get_object_or_404(Course, pk=pk)
if request.method == 'POST':
    data = request.POST.copy()
    data['crs_id'] = pk  # ใส่ crs_id กลับเข้าไปเพราะ modal ไม่ส่งมา
    form = CourseForm(data, instance=obj)
    if form.is_valid():
        form.save()
        messages.success(request, 'แก้ไขรายวิชาเรียบร้อยแล้ว')

<!-- การค้นหารายวิชาและตรวจสอบข้อมูลที่เกี่ยวข้องก่อนลบ -->
obj = get_object_or_404(Course, pk=pk)
if request.method == 'POST':
    tutor_course_count = TutorCourse.objects.filter(crs_id=obj).count()
    if tutor_course_count > 0:
        messages.error(request, f'ไม่สามารถลบรายวิชา "{obj.crs_name}" ได้ เนื่องจากมีติวเตอร์ใช้งานอยู่ ({tutor_course_count} คอร์ส)')
    else:
        try:
            obj.delete()
            messages.success(request, f'ลบรายวิชา "{obj.crs_name}" เรียบร้อยแล้ว')
        except Exception:
            messages.error(request, 'ไม่สามารถลบได้ เนื่องจากมีข้อมูลที่เกี่ยวข้อง')
```

ชื่อไฟล์: `apps/courses/models.py`
ช่วงบรรทัด: 71–78

```python
<!-- การสร้างรหัสรายวิชาใหม่โดยอัตโนมัติ -->
@classmethod
def generate_id(cls):
    last = cls.objects.order_by('-crs_id').first()
    if last:
        num = int(last.crs_id[3:]) + 1
    else:
        num = 1
    return f'CRS{num:04d}'
```

> ต่อไป Process: สมัครสมาชิก

<details><summary>1 previous message</summary>

> กำลังตรวจสอบ Process “สมัครสมาชิก” ใน `accounts/forms.py` และ `accounts/views.py` โดยจะคัดเฉพาะการตรวจสอบอีเมล การสร้างลิงก์ยืนยัน และการสร้างบัญชีสมาชิกหลังยืนยันสำเร็จครับ
</details>

### 4.4.3 สมัครสมาชิก

เป็นระบบที่ใช้สำหรับตรวจสอบข้อมูลการสมัคร ส่งอีเมลยืนยันตัวตน และสร้างบัญชีสมาชิกเมื่อผู้ใช้งานยืนยันอีเมลสำเร็จ โดยมีคำสั่ง ดังนี้

ชื่อไฟล์: `apps/accounts/forms.py`
ช่วงบรรทัด: 87–94

```python
<!-- การตรวจสอบรูปแบบและความซ้ำซ้อนของอีเมลมหาวิทยาลัย -->
def clean_mb_email(self):
    email = self.cleaned_data.get('mb_email')
    email_suffix = get_system_email_suffix()
    if not email.lower().endswith(email_suffix):
        raise forms.ValidationError(f'กรุณาใช้อีเมลมหาวิทยาลัย ({email_suffix}) เท่านั้น')
    if Member.objects.filter(mb_email=email).exists():
        raise forms.ValidationError('อีเมลนี้ถูกใช้งานแล้ว')
    return email
```

ชื่อไฟล์: `apps/accounts/views.py`
ช่วงบรรทัด: 140–153, 198–201, 210–222, 430–446, 464–480 และ 486–488

```python
<!-- การตรวจสอบฟอร์มและเตรียมข้อมูลสำหรับสมัครสมาชิก -->
if form.is_valid():
    from django.core.signing import dumps
    from django.contrib.auth.hashers import make_password
    from django.conf import settings as conf_settings
    from django.contrib.auth.models import User as AuthUser
    from django.db import transaction

    data = {
        'first_name': form.cleaned_data['first_name'],
        'last_name':  form.cleaned_data['last_name'],
        'mj_id':      form.cleaned_data['mj_id'].pk,
        'email':      form.cleaned_data['mb_email'],
        'password':   make_password(form.cleaned_data['password1']),
    }

<!-- การสร้าง Token และลิงก์สำหรับยืนยันอีเมล -->
token      = dumps(data, salt='email-verify')
verify_url = request.build_absolute_uri(
    f"/accounts/verify-email/?token={token}"
)

<!-- การส่งอีเมลยืนยันการสมัครสมาชิก -->
try:
    send_mail(
        subject='[เพื่อนช่วยติว] ยืนยันอีเมลของคุณ',
        message=(
            f'สวัสดี {data["first_name"]},\n\n'
            f'คลิกลิงก์เพื่อยืนยันการสมัครสมาชิก:\n{verify_url}\n\n'
            f'ลิงก์นี้จะหมดอายุใน 24 ชั่วโมง'
        ),
        html_message=html_message,
        from_email=conf_settings.DEFAULT_FROM_EMAIL,
        recipient_list=[data['email']],
        fail_silently=False,
    )

<!-- การตรวจสอบความถูกต้องและอายุของ Token -->
try:
    data = loads(token, max_age=86400, salt='email-verify')
except SignatureExpired:
    return render(request, 'accounts/verify_email_error.html', {
        'error': 'ลิงก์ยืนยันหมดอายุแล้ว (24 ชั่วโมง) กรุณาสมัครสมาชิกใหม่อีกครั้ง'
    })
except (BadSignature, Exception):
    return render(request, 'accounts/verify_email_error.html', {
        'error': 'ลิงก์ยืนยันไม่ถูกต้อง กรุณาสมัครสมาชิกใหม่อีกครั้ง'
    })

email_addr = data['email']

<!-- การตรวจสอบอีเมลที่ยืนยันและสมัครสมาชิกแล้ว -->
if Member.objects.filter(mb_email__iexact=email_addr).exists():
    messages.info(request, 'อีเมลนี้ยืนยันแล้ว กรุณาเข้าสู่ระบบ')
    return redirect('accounts:login')

<!-- การสร้างบัญชีผู้ใช้และข้อมูลสมาชิกภายใน Transaction เดียวกัน -->
try:
    with transaction.atomic():
        user = AuthUser(
            username=username,
            email=email_addr,
            first_name=data['first_name'],
            last_name=data['last_name'],
            password=data['password'],  # hashed แล้วตั้งแต่ตอน sign
        )
        user.save()
        Member.objects.create(
            user=user,
            mb_full_name=f"{data['first_name']} {data['last_name']}".strip(),
            mb_email=email_addr,
            mb_img=None,
            mj_id=major,
        )

<!-- การเข้าสู่ระบบหลังยืนยันอีเมลสำเร็จ -->
login(request, user)
messages.success(request, f'ยืนยันอีเมลเรียบร้อย ยินดีต้อนรับสู่เพื่อนช่วยติว, {user.first_name}!')
return redirect('home')
```

> Process: ลงทะเบียนติวเตอร์

<details><summary>1 previous message</summary>

> กำลังตรวจสอบ Process “ลงทะเบียนติวเตอร์” จากฟอร์มและ View ที่ใช้จริง โดยจะคัดเฉพาะการตรวจสอบข้อมูลหลัก การสร้างคำขอใหม่ และการส่งคำขอซ้ำหลังถูกปฏิเสธครับ
</details>

### 4.4.4 ลงทะเบียนติวเตอร์

เป็นระบบที่ใช้สำหรับตรวจสอบคุณสมบัติเบื้องต้น บันทึกคำขอลงทะเบียนติวเตอร์ และส่งคำขอใหม่เมื่อคำขอเดิมถูกปฏิเสธ โดยมีคำสั่ง ดังนี้

ชื่อไฟล์: `apps/tutoring/views.py`
ช่วงบรรทัด: 594–604, 617–637 และ 638–655

```python
<!-- การตรวจสอบการเข้าสู่ระบบและรูปโปรไฟล์ก่อนสมัครเป็นติวเตอร์ -->
@login_required
def register_tutor(request):
    member = request.user.member

    if not member.mb_img:
        messages.warning(
            request,
            'คุณยังไม่มีรูปโปรไฟล์ กรุณาอัปโหลดรูปโปรไฟล์ก่อนสมัครเป็นติวเตอร์ เพื่อความน่าเชื่อถือของคุณ'
        )
        return redirect('accounts:profile')

<!-- การตรวจสอบฟอร์มและปรับปรุงคำขอลงทะเบียนติวเตอร์เดิม -->
form = TutorRegisterForm(request.POST or None, request.FILES or None, initial=initial)

if request.method == 'POST' and form.is_valid():
    if tutor:
        old_status         = tutor.tut_status
        tutor.tut_gpax     = form.cleaned_data['gpa']
        tutor.tut_skill    = form.cleaned_data['teaching_skills']
        tutor.tut_has_exp  = int(form.cleaned_data['has_experience'])
        tutor.tut_exp_desc = form.cleaned_data['experience_detail'] or ''

        if form.cleaned_data.get('student_card'):
            card = _rename_student_card(form.cleaned_data['student_card'], member.pk)
            tutor.tut_student_card = card

        if old_status == 2:
            tutor.tut_status      = 0
            tutor.tut_reject_note = None
            tutor.save()
            messages.success(request, 'ส่งคำขอใหม่เรียบร้อยแล้ว Admin จะตรวจสอบและแจ้งผลภายใน 1-3 วันทำการ')
        else:
            tutor.save()
            messages.success(request, 'อัปเดตข้อมูลติวเตอร์เรียบร้อยแล้ว')

<!-- การบันทึกคำขอลงทะเบียนติวเตอร์ใหม่ในสถานะรอตรวจสอบ -->
    else:
        card = None
        if form.cleaned_data.get('student_card'):
            card = _rename_student_card(form.cleaned_data['student_card'], member.pk)

        tutor = Tutor.objects.create(
            tut_id           = member,
            tut_gpax         = form.cleaned_data['gpa'],
            tut_skill        = form.cleaned_data['teaching_skills'],
            tut_has_exp      = int(form.cleaned_data['has_experience']),
            tut_exp_desc     = form.cleaned_data['experience_detail'] or '',
            tut_student_card = card,
            tut_status       = 0,
        )
        messages.success(
            request,
            'ส่งคำขอสมัครเป็นติวเตอร์เรียบร้อยแล้ว Adminจะตรวจสอบและแจ้งผลภายใน 1-3 วันทำการ'
        )
    return redirect('tutoring:register_tutor')
```
