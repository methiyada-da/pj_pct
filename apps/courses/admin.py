from django.contrib import admin

from .models import Course, CourseGroup, Faculty, Major


@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_display = ('fac_id', 'fac_name')
    search_fields = ('fac_name',)
    ordering = ('fac_name',)


@admin.register(Major)
class MajorAdmin(admin.ModelAdmin):
    list_display = ('mj_id', 'mj_name', 'mj_abbr', 'fac_id')
    list_filter = ('fac_id',)
    search_fields = ('mj_name', 'mj_abbr', 'fac_id__fac_name')
    ordering = ('fac_id__fac_name', 'mj_name')


@admin.register(CourseGroup)
class CourseGroupAdmin(admin.ModelAdmin):
    list_display = ('cg_id', 'cg_name')
    search_fields = ('cg_name', 'cg_desc')
    ordering = ('cg_name',)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('crs_id', 'crs_name', 'cg_id')
    list_filter = ('cg_id',)
    search_fields = ('crs_id', 'crs_name', 'crs_desc', 'cg_id__cg_name')
    ordering = ('crs_id',)
