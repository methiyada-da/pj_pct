from django.contrib import admin

from .models import ScheduleDate, TimeSlot, TutorCourse, TutorRate


class TutorRateInline(admin.TabularInline):
    model = TutorRate
    extra = 0


class ScheduleDateInline(admin.TabularInline):
    model = ScheduleDate
    extra = 0


class TimeSlotInline(admin.TabularInline):
    model = TimeSlot
    extra = 0


@admin.register(TutorCourse)
class TutorCourseAdmin(admin.ModelAdmin):
    list_display = ('tutc_id', 'tutc_name', 'tut_id', 'crs_id', 'tutc_max_stu', 'tutc_status')
    list_filter = ('tutc_status', 'crs_id')
    search_fields = ('tutc_id', 'tutc_name', 'tutc_desc', 'tut_id__tut_id__mb_full_name', 'crs_id__crs_name')
    ordering = ('tutc_name',)
    inlines = (TutorRateInline, ScheduleDateInline)


@admin.register(TutorRate)
class TutorRateAdmin(admin.ModelAdmin):
    list_display = ('tut_rate_id', 'tutc_id', 'tut_rate_stu_count', 'tut_rate_per_person')
    list_filter = ('tutc_id',)
    search_fields = ('tutc_id__tutc_id', 'tutc_id__tutc_name')
    ordering = ('tutc_id', 'tut_rate_stu_count')


@admin.register(ScheduleDate)
class ScheduleDateAdmin(admin.ModelAdmin):
    list_display = ('sd_id', 'tutc_id', 'sd_date')
    list_filter = ('sd_date',)
    search_fields = ('tutc_id__tutc_id', 'tutc_id__tutc_name')
    ordering = ('-sd_date',)
    inlines = (TimeSlotInline,)


@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    list_display = ('ts_id', 'sd_id', 'ts_start_time', 'ts_end_time', 'ts_status')
    list_filter = ('ts_status', 'sd_id__sd_date')
    search_fields = ('sd_id__tutc_id__tutc_id', 'sd_id__tutc_id__tutc_name')
    ordering = ('-sd_id__sd_date', 'ts_start_time')
