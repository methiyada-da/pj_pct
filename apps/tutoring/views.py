from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse

from apps.accounts.models import Tutor
from apps.courses.models import CourseGroup, Course
from .forms import TutorRegisterForm
import re
from .models import TutorCourse, TutorRate, ScheduleDate, TimeSlot


def _member_context(member):
    return {
        'member'      : member,
        'faculty_name': member.mj_id.fac_id.fac_name if member.mj_id else '',
        'major_name'  : member.mj_id.mj_name          if member.mj_id else '',
    }


# ─── สมัครเป็นติวเตอร์ ────────────────────────────────────────────────────────

@login_required
def register_tutor(request):
    member = request.user.member

    # ── ตรวจสอบรูปโปรไฟล์ก่อนเข้าหน้าสมัครติวเตอร์ ──
    if not member.mb_img:
        messages.warning(
            request,
            'คุณยังไม่มีรูปโปรไฟล์ กรุณาอัปโหลดรูปโปรไฟล์ก่อนสมัครเป็นติวเตอร์ เพื่อความน่าเชื่อถือของคุณ'
        )
        return redirect('accounts:profile')

    tutor  = Tutor.objects.filter(tut_id=member).first()

    initial = {}
    if tutor:
        initial = {
            'gpa'              : tutor.tut_gpax,
            'teaching_skills'  : tutor.tut_skill,
            'has_experience'   : str(tutor.tut_has_exp),
            'experience_detail': tutor.tut_exp_desc,
        }

    form = TutorRegisterForm(request.POST or None, initial=initial)

    if request.method == 'POST' and form.is_valid():
        if tutor:
            old_status         = tutor.tut_status
            tutor.tut_gpax     = form.cleaned_data['gpa']
            tutor.tut_skill    = form.cleaned_data['teaching_skills']
            tutor.tut_has_exp  = int(form.cleaned_data['has_experience'])
            tutor.tut_exp_desc = form.cleaned_data['experience_detail'] or ''
            if old_status == 2:
                tutor.tut_status = 0
                tutor.save()
                messages.success(request, 'ส่งคำขอใหม่เรียบร้อยแล้ว ทีมงานจะตรวจสอบและแจ้งผลภายใน 2-3 วันทำการ')
            else:
                tutor.save()
                messages.success(request, 'อัปเดตข้อมูลติวเตอร์เรียบร้อยแล้ว')
        else:
            tutor = Tutor.objects.create(
                tut_id       = member,
                tut_gpax     = form.cleaned_data['gpa'],
                tut_skill    = form.cleaned_data['teaching_skills'],
                tut_has_exp  = int(form.cleaned_data['has_experience']),
                tut_exp_desc = form.cleaned_data['experience_detail'] or '',
                tut_status   = 0,
            )
            messages.success(
                request,
                'ส่งคำขอสมัครเป็นติวเตอร์เรียบร้อยแล้ว ทีมงานจะตรวจสอบและแจ้งผลภายใน 2-3 วันทำการ'
            )
        return redirect('tutoring:register_tutor')

    return render(request, 'tutoring/register_tutor.html', {
        **_member_context(member),
        'form'         : form,
        'tutor'        : tutor,
        'is_view_only' : tutor is not None and tutor.tut_status in (0, 3),
    })


# ─── หน้าเมนูหลัก จัดการข้อมูลติวเตอร์ ──────────────────────────────────────

@login_required
def tutor_manage(request):
    member = request.user.member
    tutor  = Tutor.objects.filter(tut_id=member).first()

    course_count         = 0
    pending_booking_count = 0
    total_student_count  = 0

    if tutor and tutor.tut_status == 1:
        courses = TutorCourse.objects.filter(tut_id=tutor)
        course_count = courses.count()
        # TODO: ใส่ logic booking count เมื่อมี booking model

    return render(request, 'tutoring/tutor_manage.html', {
        **_member_context(member),
        'tutor'               : tutor,
        'course_count'        : course_count,
        'pending_booking_count': pending_booking_count,
        'total_student_count' : total_student_count,
    })


# ─── รายการคอร์สของติวเตอร์ ──────────────────────────────────────────────────

@login_required
def tutor_course_list(request):
    member = request.user.member
    tutor  = get_object_or_404(Tutor, tut_id=member, tut_status=1)
    courses = TutorCourse.objects.filter(tut_id=tutor).select_related('crs_id', 'crs_id__cg_id').order_by('-tutc_id')

    return render(request, 'tutoring/tutor_course_list.html', {
        **_member_context(member),
        'tutor'  : tutor,
        'courses': courses,
    })


# ─── เพิ่ม / แก้ไขคอร์ส ──────────────────────────────────────────────────────

@login_required
def manage_course(request, tutc_id=None):
    member = request.user.member
    tutor  = get_object_or_404(Tutor, tut_id=member, tut_status=1)

    tutc  = None
    rates = []
    schedule_dates_with_slots = []

    if tutc_id:
        tutc  = get_object_or_404(TutorCourse, tutc_id=tutc_id, tut_id=tutor)
        rates = TutorRate.objects.filter(tutc_id=tutc).order_by('tut_rate_stu_count')
        _sds  = list(
            ScheduleDate.objects.filter(tutc_id=tutc)
            .prefetch_related('time_slots')
            .order_by('sd_date')
        )
        # แนบ weekday (0=จ … 6=อา) ให้แต่ละ sd
        for sd in _sds:
            sd.weekday = sd.sd_date.weekday()
        schedule_dates_with_slots = _sds
        # จัดกลุ่มตาม weekday โดยใช้ dict (ไม่ขึ้นกับลำดับ)
        _wd_map = {}
        for sd in _sds:
            _wd_map.setdefault(sd.weekday, []).append(sd)
        # เรียงกลุ่มตามลำดับวันในสัปดาห์ (จ→อา)
        grouped_schedule = sorted(_wd_map.items(), key=lambda x: x[0])

    course_groups = CourseGroup.objects.all().order_by('cg_name')

    if request.method == 'POST':
        # ── ข้อมูลพื้นฐาน ──
        tutc_name    = request.POST.get('tutc_name', '').strip()
        tutc_desc    = request.POST.get('tutc_desc', '').strip()
        tutc_max_stu = request.POST.get('tutc_max_stu', '').strip()
        tutc_status  = 1 if request.POST.get('tutc_status') == '1' else 0
        crs_id_val   = request.POST.get('crs_id', '').strip()

        # ── ตรวจ new_dates + existing_sd ──
        new_dates        = [d for d in request.POST.getlist('new_date[]') if d.strip()]
        existing_sd_ids  = [
            key.split('ts_start_')[1].rstrip('[]').split('[')[0]
            for key in request.POST
            if key.startswith('ts_start_') and not key.startswith('ts_start_new_')
        ]
        has_any_date = len(new_dates) > 0 or len(existing_sd_ids) > 0

        # ── ตรวจ rate (tiered pricing) ──
        stu_counts  = request.POST.getlist('rate_stu_count[]')
        per_persons = request.POST.getlist('rate_per_person[]')

        # parse เรทที่กรอกครบถ้วน
        valid_rates = []
        for sc, pp in zip(stu_counts, per_persons):
            sc_s, pp_s = sc.strip(), pp.strip()
            if sc_s and pp_s and int(sc_s) >= 1 and int(pp_s) >= 0:
                valid_rates.append((int(sc_s), int(pp_s)))

        # validate tiered pricing logic
        rate_errors = []
        if not valid_rates:
            rate_errors.append('กรุณากรอกอัตราค่าติวอย่างน้อย 1 เรท')
        else:
            max_stu_int = int(tutc_max_stu) if tutc_max_stu and tutc_max_stu.isdigit() and int(tutc_max_stu) >= 1 else 0
            first_price = valid_rates[0][1]

            for i, (stu, price) in enumerate(valid_rates):
                # จำนวนคนต้องมากกว่าแถวก่อนหน้า
                if i > 0 and stu <= valid_rates[i - 1][0]:
                    rate_errors.append(f'เรทที่ {i+1}: จำนวนคนต้องมากกว่าเรทก่อนหน้า ({valid_rates[i-1][0]} คน)')
                    break

                # จำนวนคนต้องไม่เกิน max
                if max_stu_int > 0 and stu > max_stu_int:
                    rate_errors.append(f'เรทที่ {i+1}: จำนวนคนต้องไม่เกิน {max_stu_int} คน (จำนวนรับสูงสุด)')
                    break

                # เครดิต: ถ้าเรทแรก=0(ฟรี) เรทที่2 เป็นอะไรก็ได้ แต่เรทที่3+ ต้อง < ก่อนหน้า
                # ถ้าเรทแรก>=1 ทุกเรทถัดไปต้อง < ก่อนหน้า
                if i > 0:
                    prev_price = valid_rates[i - 1][1]
                    if first_price == 0 and i == 1:
                        pass  # เรทที่ 2 หลังจากฟรี → ใส่อะไรก็ได้
                    else:
                        if price >= prev_price:
                            rate_errors.append(
                                f'เรทที่ {i+1}: เครดิตต้องต่ำกว่าเรทก่อนหน้า ({prev_price} เครดิต)'
                            )
                            break

        # ── ตรวจ time slots อย่างน้อย 1 ช่วงในแต่ละวัน และทุก slot ต้องกรอกครบคู่ ──
        has_all_slots   = True
        slot_error_msg  = ''

        # ── compile regex เวลา HH:MM ครั้งเดียว ──
        time_re = re.compile(r'^([01][0-9]|2[0-3]):[0-5][0-9]$')

        # วันใหม่ — key รูปแบบ ts_start_new_XXXX[]
        seen_new_suffixes = set()
        for key in request.POST:
            if key.startswith('ts_start_new_'):
                suffix = key[len('ts_start_new_'):].rstrip('[]')
                if suffix in seen_new_suffixes:
                    continue
                seen_new_suffixes.add(suffix)

                starts = [s.strip() for s in request.POST.getlist(key)                       if s.strip()]
                ends   = [e.strip() for e in request.POST.getlist(f'ts_end_new_{suffix}[]')  if e.strip()]

                if len(starts) == 0:
                    has_all_slots  = False
                    slot_error_msg = 'แต่ละวันต้องมีช่วงเวลาอย่างน้อย 1 ช่วง'
                    break
                if len(starts) != len(ends):
                    has_all_slots  = False
                    slot_error_msg = 'กรุณากรอกเวลาเริ่มและเวลาสิ้นสุดให้ครบทุกช่วง'
                    break
                # ตรวจ format HH:MM และ end > start
                for s, e in zip(starts, ends):
                    if not time_re.match(s) or not time_re.match(e):
                        has_all_slots  = False
                        slot_error_msg = 'รูปแบบเวลาไม่ถูกต้อง กรุณาใช้รูปแบบ HH:MM (เช่น 09:00)'
                        break
                    if e <= s:
                        has_all_slots  = False
                        slot_error_msg = 'เวลาสิ้นสุดต้องมากกว่าเวลาเริ่มต้น'
                        break
                if not has_all_slots:
                    break

        # วันเก่า — key รูปแบบ ts_start_SDID[]
        if has_all_slots:
            for sd_id_str in existing_sd_ids:
                starts = [s.strip() for s in request.POST.getlist(f'ts_start_{sd_id_str}[]') if s.strip()]
                ends   = [e.strip() for e in request.POST.getlist(f'ts_end_{sd_id_str}[]')   if e.strip()]

                if len(starts) == 0:
                    has_all_slots  = False
                    slot_error_msg = 'แต่ละวันต้องมีช่วงเวลาอย่างน้อย 1 ช่วง'
                    break
                if len(starts) != len(ends):
                    has_all_slots  = False
                    slot_error_msg = 'กรุณากรอกเวลาเริ่มและเวลาสิ้นสุดให้ครบทุกช่วง'
                    break
                for s, e in zip(starts, ends):
                    if not time_re.match(s) or not time_re.match(e):
                        has_all_slots  = False
                        slot_error_msg = 'รูปแบบเวลาไม่ถูกต้อง กรุณาใช้รูปแบบ HH:MM (เช่น 09:00)'
                        break
                    if e <= s:
                        has_all_slots  = False
                        slot_error_msg = 'เวลาสิ้นสุดต้องมากกว่าเวลาเริ่มต้น'
                        break
                if not has_all_slots:
                    break

        # ── รวม error ──
        errors = []
        if not tutc_name:
            errors.append('กรุณากรอกชื่อรายวิชา')
        if not crs_id_val:
            errors.append('กรุณาเลือกรายวิชา')
        if not tutc_max_stu or not tutc_max_stu.isdigit() or int(tutc_max_stu) < 1:
            errors.append('กรุณาระบุจำนวนรับสูงสุด')
        if not has_any_date:
            errors.append('กรุณาเพิ่มวันที่อย่างน้อย 1 วัน')
        elif not has_all_slots:
            errors.append(slot_error_msg or 'แต่ละวันต้องมีช่วงเวลาอย่างน้อย 1 ช่วง')
        if not valid_rates:
            errors.append('กรุณากรอกอัตราค่าติวอย่างน้อย 1 เรท')
        elif rate_errors:
            errors.extend(rate_errors)

        if errors:
            for err in errors:
                messages.error(request, err)
            return render(request, 'tutoring/manage_course.html', {
                **_member_context(member),
                'tutor'                    : tutor,
                'tutc'                     : tutc,
                'rates'                    : rates,
                'course_groups'            : course_groups,
                'schedule_dates_with_slots': schedule_dates_with_slots,
                'grouped_schedule'         : grouped_schedule if tutc_id else [],
                'weekday_labels'           : ['จ','อ','พ','พฤ','ศ','ส','อา'],
            })

        course = get_object_or_404(Course, crs_id=crs_id_val)

        # ── สร้าง / อัปเดต TutorCourse ──
        if tutc:
            tutc.tutc_name    = tutc_name
            tutc.tutc_desc    = tutc_desc or None
            tutc.tutc_max_stu = int(tutc_max_stu)
            tutc.tutc_status  = tutc_status
            tutc.crs_id       = course
            if 'tutc_img' in request.FILES:
                tutc.tutc_img = request.FILES['tutc_img']
            tutc.save()
            messages.success(request, 'อัปเดตคอร์สเรียบร้อยแล้ว')
        else:
            # สร้าง tutc_id แบบ TUTC001, TUTC002, ...
            last = TutorCourse.objects.order_by('-tutc_id').first()
            if last and re.match(r'TUTC\d+', last.tutc_id):
                last_num = int(last.tutc_id[4:])
            else:
                last_num = 0
            new_id = f"TUTC{last_num + 1:03d}"
            tutc = TutorCourse.objects.create(
                tutc_id      = new_id,
                tutc_name    = tutc_name,
                tutc_desc    = tutc_desc or None,
                tutc_max_stu = int(tutc_max_stu),
                tutc_status  = tutc_status,
                crs_id       = course,
                tut_id       = tutor,
                tutc_img     = request.FILES.get('tutc_img'),
            )
            messages.success(request, 'เพิ่มคอร์สเรียบร้อยแล้ว')

        # ── อัปเดต Rates (เรียงตามจำนวนคน) ──
        TutorRate.objects.filter(tutc_id=tutc).delete()
        for stu, price in sorted(valid_rates, key=lambda x: x[0]):
            TutorRate.objects.create(
                tutc_id             = tutc,
                tut_rate_stu_count  = stu,
                tut_rate_per_person = price,
            )

        # ── อัปเดต Schedule Dates + Time Slots ──
        # วันที่มีอยู่แล้ว (sd_id ที่ส่งมาจาก POST)
        existing_sd_ids = [
            key.split('ts_start_')[1].rstrip('[]').split('[')[0]
            for key in request.POST
            if key.startswith('ts_start_') and not key.startswith('ts_start_new_')
        ]
        # ลบ sd เก่าที่ไม่ได้ส่งมา
        ScheduleDate.objects.filter(tutc_id=tutc).exclude(sd_id__in=[
            int(i) for i in existing_sd_ids if i.isdigit()
        ]).delete()

        # อัปเดต time slots ของวันที่มีอยู่
        for sd_id_str in existing_sd_ids:
            if not sd_id_str.isdigit():
                continue
            sd = ScheduleDate.objects.filter(sd_id=int(sd_id_str), tutc_id=tutc).first()
            if not sd:
                continue
            TimeSlot.objects.filter(sd_id=sd, ts_status=0).delete()
            starts = request.POST.getlist(f'ts_start_{sd_id_str}[]')
            ends   = request.POST.getlist(f'ts_end_{sd_id_str}[]')
            for s, e in zip(starts, ends):
                if s and e:
                    TimeSlot.objects.create(sd_id=sd, ts_start_time=s, ts_end_time=e)

        # วันที่ใหม่ — จับคู่ new_date[] กับ ts_start_new_XXXX[] ตามลำดับ
        new_dates = request.POST.getlist('new_date[]')

        # รวบรวม suffix ทั้งหมดของ new dates (เรียงตามลำดับที่ปรากฏใน POST)
        new_suffixes = []
        seen_suffixes = set()
        for key in sorted(request.POST.keys()):
            if key.startswith('ts_start_new_'):
                suffix = key[len('ts_start_new_'):].rstrip('[]')
                if suffix not in seen_suffixes:
                    seen_suffixes.add(suffix)
                    new_suffixes.append(suffix)

        # จับคู่ new_date[i] กับ suffix[i]
        for i, date_str in enumerate(new_dates):
            if not date_str:
                continue
            sd = ScheduleDate.objects.create(sd_date=date_str, tutc_id=tutc)
            if i < len(new_suffixes):
                suffix = new_suffixes[i]
                starts = request.POST.getlist(f'ts_start_new_{suffix}[]')
                ends   = request.POST.getlist(f'ts_end_new_{suffix}[]')
                for s, e in zip(starts, ends):
                    if s and e:
                        TimeSlot.objects.create(sd_id=sd, ts_start_time=s, ts_end_time=e)

        return redirect('tutoring:tutor_course_list')

    return render(request, 'tutoring/manage_course.html', {
        **_member_context(member),
        'tutor'                   : tutor,
        'tutc'                    : tutc,
        'rates'                   : rates,
        'course_groups'           : course_groups,
        'schedule_dates_with_slots': schedule_dates_with_slots,
        'grouped_schedule'        : grouped_schedule if tutc_id else [],
        'weekday_labels'          : ['จ','อ','พ','พฤ','ศ','ส','อา'],
    })


# ─── เปิด / ปิด รับนักเรียน ──────────────────────────────────────────────────

@login_required
def toggle_course_status(request, tutc_id):
    if request.method != 'POST':
        return redirect('tutoring:tutor_course_list')

    member = request.user.member
    tutor  = get_object_or_404(Tutor, tut_id=member, tut_status=1)
    tutc   = get_object_or_404(TutorCourse, tutc_id=tutc_id, tut_id=tutor)

    tutc.tutc_status = 0 if tutc.tutc_status == 1 else 1
    tutc.save()

    label = 'เปิดรับสอน' if tutc.tutc_status == 1 else 'ปิดรับสอน'
    messages.success(request, f'เปลี่ยนสถานะคอร์ส "{tutc.tutc_name}" เป็น {label} แล้ว')
    return redirect('tutoring:tutor_course_list')


# ─── ลบคอร์ส ─────────────────────────────────────────────────────────────────

@login_required
def delete_course(request, tutc_id):
    if request.method != 'POST':
        return redirect('tutoring:tutor_course_list')

    member = request.user.member
    tutor  = get_object_or_404(Tutor, tut_id=member, tut_status=1)
    tutc   = get_object_or_404(TutorCourse, tutc_id=tutc_id, tut_id=tutor)

    name = tutc.tutc_name
    tutc.delete()
    messages.success(request, f'ลบคอร์ส "{name}" เรียบร้อยแล้ว')
    return redirect('tutoring:tutor_course_list')