# credits/urls.py - URL routing ของ credits
from django.urls import path
from . import views

app_name = 'credits'

urlpatterns = [
    path('',         views.credit_view,   name='credit'),
    path('topup/',   views.topup_view,    name='topup'),
    path('withdraw/',views.withdraw_view, name='withdraw'),
    path('qr/',      views.promptpay_qr,  name='promptpay_qr'),
]
