from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.http import JsonResponse

from .models import Faculty, Major, CourseGroup, Course
from .forms import FacultyForm, MajorForm, CourseGroupForm, CourseForm


def is_admin(user):
    return user.is_authenticated and user.is_staff


# ─── Faculty ────────────────────────────────────────────────────────────────

@login_required
@user_passes_test(is_admin)
def faculty_list(request):
    qs = Faculty.objects.annotate(major_count=Count('major')).order_by('fac_id')
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(Q(fac_name__icontains=q))
    paginator = Paginator(qs, 10)
    page = paginator.get_page(request.GET.get('page', 1))
    form = FacultyForm()
    return render(request, 'courses/faculty_list.html', {
        'page_obj'          : page,
        'form'              : form,
        'q'                 : q,
        'total'             : qs.count(),
        'active_menu'       : 'faculty',
        'topbar_breadcrumb' : 'การจัดการข้อมูลพื้นฐาน › คณะ',
    })


@login_required
@user_passes_test(is_admin)
def faculty_create(request):
    if request.method == 'POST':
        form = FacultyForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'เพิ่มคณะเรียบร้อยแล้ว')
        else:
            messages.error(request, 'ข้อมูลไม่ถูกต้อง กรุณาตรวจสอบอีกครั้ง')
    return redirect('courses:faculty_list')


@login_required
@user_passes_test(is_admin)
def faculty_edit(request, pk):
    obj = get_object_or_404(Faculty, pk=pk)
    if request.method == 'POST':
        form = FacultyForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'แก้ไขคณะเรียบร้อยแล้ว')
        else:
            messages.error(request, 'ข้อมูลไม่ถูกต้อง กรุณาตรวจสอบอีกครั้ง')
    return redirect('courses:faculty_list')


@login_required
@user_passes_test(is_admin)
def faculty_delete(request, pk):
    obj = get_object_or_404(Faculty, pk=pk)
    if request.method == 'POST':
        try:
            obj.delete()
            messages.success(request, f'ลบคณะ "{obj.fac_name}" เรียบร้อยแล้ว')
        except Exception:
            messages.error(request, 'ไม่สามารถลบได้ เนื่องจากมีข้อมูลที่เกี่ยวข้อง')
    return redirect('courses:faculty_list')


def faculty_json(request, pk):
    obj = get_object_or_404(Faculty, pk=pk)
    return JsonResponse({'fac_id': obj.fac_id, 'fac_name': obj.fac_name})


# ─── Major ───────────────────────────────────────────────────────────────────

@login_required
@user_passes_test(is_admin)
def major_list(request):
    qs = Major.objects.select_related('fac_id').order_by('mj_id')
    q          = request.GET.get('q',   '').strip()
    fac_filter = request.GET.get('fac', '')
    if q:
        qs = qs.filter(Q(mj_name__icontains=q) | Q(mj_abbr__icontains=q))
    if fac_filter:
        qs = qs.filter(fac_id=fac_filter)
    paginator = Paginator(qs, 10)
    page      = paginator.get_page(request.GET.get('page', 1))
    form      = MajorForm()
    faculties = Faculty.objects.all().order_by('fac_name')
    return render(request, 'courses/major_list.html', {
        'page_obj'          : page,
        'form'              : form,
        'q'                 : q,
        'faculties'         : faculties,
        'fac_filter'        : fac_filter,
        'total'             : qs.count(),
        'active_menu'       : 'major',
        'topbar_breadcrumb' : 'การจัดการข้อมูลพื้นฐาน › สาขา',
    })


@login_required
@user_passes_test(is_admin)
def major_create(request):
    if request.method == 'POST':
        form = MajorForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'เพิ่มสาขาเรียบร้อยแล้ว')
        else:
            messages.error(request, 'ข้อมูลไม่ถูกต้อง กรุณาตรวจสอบอีกครั้ง')
    return redirect('courses:major_list')


@login_required
@user_passes_test(is_admin)
def major_edit(request, pk):
    obj = get_object_or_404(Major, pk=pk)
    if request.method == 'POST':
        form = MajorForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'แก้ไขสาขาเรียบร้อยแล้ว')
        else:
            messages.error(request, 'ข้อมูลไม่ถูกต้อง กรุณาตรวจสอบอีกครั้ง')
    return redirect('courses:major_list')


@login_required
@user_passes_test(is_admin)
def major_delete(request, pk):
    obj = get_object_or_404(Major, pk=pk)
    if request.method == 'POST':
        try:
            obj.delete()
            messages.success(request, f'ลบสาขา "{obj.mj_name}" เรียบร้อยแล้ว')
        except Exception:
            messages.error(request, 'ไม่สามารถลบได้ เนื่องจากมีข้อมูลที่เกี่ยวข้อง')
    return redirect('courses:major_list')


def major_json(request, pk):
    obj = get_object_or_404(Major, pk=pk)
    return JsonResponse({
        'mj_id'  : obj.mj_id,
        'mj_name': obj.mj_name,
        'mj_abbr': obj.mj_abbr,
        'mj_desc': obj.mj_desc or '',
        'fac_id' : obj.fac_id_id,
    })


# ─── CourseGroup ─────────────────────────────────────────────────────────────

@login_required
@user_passes_test(is_admin)
def course_group_list(request):
    qs = CourseGroup.objects.annotate(course_count=Count('course')).order_by('cg_id')
    q  = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(Q(cg_name__icontains=q))
    paginator = Paginator(qs, 10)
    page      = paginator.get_page(request.GET.get('page', 1))
    form      = CourseGroupForm()
    return render(request, 'courses/course_group_list.html', {
        'page_obj'          : page,
        'form'              : form,
        'q'                 : q,
        'total'             : qs.count(),
        'active_menu'       : 'course_group',
        'topbar_breadcrumb' : 'การจัดการข้อมูลพื้นฐาน › กลุ่มรายวิชา',
    })


@login_required
@user_passes_test(is_admin)
def course_group_create(request):
    if request.method == 'POST':
        form = CourseGroupForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'เพิ่มกลุ่มรายวิชาเรียบร้อยแล้ว')
        else:
            messages.error(request, 'ข้อมูลไม่ถูกต้อง กรุณาตรวจสอบอีกครั้ง')
    return redirect('courses:course_group_list')


@login_required
@user_passes_test(is_admin)
def course_group_edit(request, pk):
    obj = get_object_or_404(CourseGroup, pk=pk)
    if request.method == 'POST':
        form = CourseGroupForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'แก้ไขกลุ่มรายวิชาเรียบร้อยแล้ว')
        else:
            messages.error(request, 'ข้อมูลไม่ถูกต้อง กรุณาตรวจสอบอีกครั้ง')
    return redirect('courses:course_group_list')


@login_required
@user_passes_test(is_admin)
def course_group_delete(request, pk):
    obj = get_object_or_404(CourseGroup, pk=pk)
    if request.method == 'POST':
        try:
            obj.delete()
            messages.success(request, f'ลบกลุ่มรายวิชา "{obj.cg_name}" เรียบร้อยแล้ว')
        except Exception:
            messages.error(request, 'ไม่สามารถลบได้ เนื่องจากมีข้อมูลที่เกี่ยวข้อง')
    return redirect('courses:course_group_list')


def course_group_json(request, pk):
    obj = get_object_or_404(CourseGroup, pk=pk)
    return JsonResponse({'cg_id': obj.cg_id, 'cg_name': obj.cg_name, 'cg_desc': obj.cg_desc or ''})


# ─── Course ───────────────────────────────────────────────────────────────────

@login_required
@user_passes_test(is_admin)
def course_list(request):
    qs        = Course.objects.select_related('cg_id').order_by('crs_id')
    q         = request.GET.get('q',  '').strip()
    cg_filter = request.GET.get('cg', '')
    if q:
        qs = qs.filter(Q(crs_id__icontains=q) | Q(crs_name__icontains=q))
    if cg_filter:
        qs = qs.filter(cg_id=cg_filter)
    paginator     = Paginator(qs, 10)
    page          = paginator.get_page(request.GET.get('page', 1))
    form          = CourseForm()
    course_groups = CourseGroup.objects.all().order_by('cg_name')
    return render(request, 'courses/course_list.html', {
        'page_obj'          : page,
        'form'              : form,
        'q'                 : q,
        'course_groups'     : course_groups,
        'cg_filter'         : cg_filter,
        'total'             : qs.count(),
        'active_menu'       : 'course',
        'topbar_breadcrumb' : 'การจัดการข้อมูลพื้นฐาน › รายวิชา',
    })


@login_required
@user_passes_test(is_admin)
def course_create(request):
    if request.method == 'POST':
        data = request.POST.copy()
        data['crs_id'] = Course.generate_id()
        form = CourseForm(data)
        if form.is_valid():
            form.save()
            messages.success(request, 'เพิ่มรายวิชาเรียบร้อยแล้ว')
        else:
            messages.error(request, 'ข้อมูลไม่ถูกต้อง กรุณาตรวจสอบอีกครั้ง')
    return redirect('courses:course_list')


@login_required
@user_passes_test(is_admin)
def course_edit(request, pk):
    obj = get_object_or_404(Course, pk=pk)
    if request.method == 'POST':
        form = CourseForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'แก้ไขรายวิชาเรียบร้อยแล้ว')
        else:
            messages.error(request, 'ข้อมูลไม่ถูกต้อง กรุณาตรวจสอบอีกครั้ง')
    return redirect('courses:course_list')


@login_required
@user_passes_test(is_admin)
def course_delete(request, pk):
    obj = get_object_or_404(Course, pk=pk)
    if request.method == 'POST':
        try:
            obj.delete()
            messages.success(request, f'ลบรายวิชา "{obj.crs_name}" เรียบร้อยแล้ว')
        except Exception:
            messages.error(request, 'ไม่สามารถลบได้ เนื่องจากมีข้อมูลที่เกี่ยวข้อง')
    return redirect('courses:course_list')


def course_json(request, pk):
    obj = get_object_or_404(Course, pk=pk)
    return JsonResponse({
        'crs_id'  : obj.crs_id,
        'crs_name': obj.crs_name,
        'crs_desc': obj.crs_desc or '',
        'cg_id'   : obj.cg_id_id,
    })
