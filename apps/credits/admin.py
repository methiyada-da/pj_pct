from django.contrib import admin

from .models import Refill, Withdrawals


@admin.register(Refill)
class RefillAdmin(admin.ModelAdmin):
    list_display = ('rf_id', 'member', 'rf_credit', 'rf_money', 'rf_status', 'rf_date', 'rf_confirm_date')
    list_filter = ('rf_status', 'rf_date', 'rf_confirm_date')
    search_fields = ('rf_id', 'member__mb_full_name', 'member__mb_email', 'rf_qr_payload', 'rf_cmt')
    ordering = ('-rf_date',)


@admin.register(Withdrawals)
class WithdrawalsAdmin(admin.ModelAdmin):
    list_display = ('wd_id', 'member', 'wd_type', 'wd_credit', 'wd_cash', 'wd_net_cash', 'wd_status', 'wd_req_date')
    list_filter = ('wd_type', 'wd_status', 'wd_req_date', 'wd_paid_date')
    search_fields = ('wd_id', 'member__mb_full_name', 'member__mb_email', 'wd_bank_name', 'wd_acc_name', 'wd_acc_no', 'wd_promptpay_no')
    ordering = ('-wd_req_date',)
