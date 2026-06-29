from django.contrib import admin

from .models import System


@admin.register(System)
class SystemAdmin(admin.ModelAdmin):
    list_display = ('uni_name', 'email_domain', 'bank_name', 'acc_name', 'crd_val', 'total_accumulated_fee')
    search_fields = ('uni_name', 'email_domain', 'bank_name', 'acc_name', 'acc_no', 'promptpay_id')
