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
]
