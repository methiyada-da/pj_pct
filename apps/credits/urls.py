from django.urls import path
from . import views

app_name = 'credits'

urlpatterns = [
    path('',       views.credit_view,  name='credit'),
    path('topup/', views.topup_view,   name='topup'),
    path('qr/',    views.promptpay_qr, name='promptpay_qr'),
]
