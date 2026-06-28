from django.contrib import admin

from .models import Member, Tutor


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ('id', 'mb_full_name', 'mb_email', 'mj_id', 'mb_status', 'mb_deposit_crd', 'mb_income_crd')
    list_filter = ('mb_status', 'mj_id')
    search_fields = ('mb_full_name', 'mb_email', 'user__username')
    ordering = ('mb_full_name',)


@admin.register(Tutor)
class TutorAdmin(admin.ModelAdmin):
    list_display = ('tut_id', 'tut_status', 'tut_gpax', 'tut_has_exp', 'tut_rating')
    list_filter = ('tut_status', 'tut_has_exp')
    search_fields = ('tut_id__mb_full_name', 'tut_id__mb_email')
    ordering = ('tut_status', 'tut_id__mb_full_name')
