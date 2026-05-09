# admin_panel/urls.py - URL routing ของ admin_panel
from django.urls import path
from . import views

app_name = 'admin_panel'

urlpatterns = [
    path('',                         views.dashboard,          name='dashboard'),
    path('settings/',                views.system_settings,    name='system_settings'),
    path('tutor-mgmt/',              views.tutor_mgmt_list,    name='tutor_mgmt_list'),
    path('tutor-mgmt/<int:pk>/',     views.tutor_mgmt_detail,  name='tutor_mgmt_detail'),
    path('refill-mgmt/',             views.refill_mgmt,        name='refill_mgmt'),
    path('member-mgmt/',             views.member_mgmt,        name='member_mgmt'),
    path('payment-mgmt/',            views.payment_mgmt,       name='payment_mgmt'),
    path('report-mgmt/',             views.report_mgmt,        name='report_mgmt'),
    path('setup/', views.admin_setup, name='admin_setup'),
]