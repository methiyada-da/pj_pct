from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from apps.accounts.models import Tutor
from .forms import TutorRegisterForm


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
    tutor  = Tutor.objects.filter(tut_id=member).first()

    # เติมฟอร์มจากข้อมูลที่มีอยู่ (กรณีสมัครแล้ว)
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
