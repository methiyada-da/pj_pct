from django.contrib import admin

from .models import Booking, BookingReportStatement, JobCompletion, Review, TutoringActivity


class BookingReportStatementInline(admin.TabularInline):
    model = BookingReportStatement
    extra = 0


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('bk_id', 'member', 'tutc_id', 'bk_stu_datetime', 'bk_stu_count', 'bk_status', 'bk_date')
    list_filter = ('bk_status', 'bk_stu_datetime', 'bk_date')
    search_fields = ('bk_id', 'member__mb_full_name', 'tutc_id__tutc_name', 'bk_desc', 'bk_cmt')
    ordering = ('-bk_date',)
    inlines = (BookingReportStatementInline,)


@admin.register(BookingReportStatement)
class BookingReportStatementAdmin(admin.ModelAdmin):
    list_display = ('brs_id', 'bk_id', 'member', 'brs_role', 'brs_date')
    list_filter = ('brs_role', 'brs_date')
    search_fields = ('bk_id__bk_id', 'member__mb_full_name', 'brs_desc')
    ordering = ('-brs_date',)


@admin.register(TutoringActivity)
class TutoringActivityAdmin(admin.ModelAdmin):
    list_display = ('bk_id', 'ta_desc')
    search_fields = ('bk_id__bk_id', 'bk_id__member__mb_full_name', 'ta_desc')


@admin.register(JobCompletion)
class JobCompletionAdmin(admin.ModelAdmin):
    list_display = ('bk_id', 'jc_complete_date', 'jc_confirm_date')
    list_filter = ('jc_complete_date', 'jc_confirm_date')
    search_fields = ('bk_id__bk_id', 'bk_id__member__mb_full_name')
    ordering = ('-jc_complete_date',)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('bk_id', 'rv_quality', 'rv_knowledge', 'rv_communication', 'rv_punctuality', 'rv_satisfaction', 'rv_date')
    list_filter = ('rv_date',)
    search_fields = ('bk_id__bk_id', 'bk_id__member__mb_full_name', 'rv_cmt')
    ordering = ('-rv_date',)
