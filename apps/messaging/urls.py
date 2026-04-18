from django.urls import path
from . import views

app_name = 'messaging'

urlpatterns = [
    # หน้ารายการแชททั้งหมด
    path('', views.inbox_list, name='inbox'),

    # หน้าแชทกับ member คนใดคนหนึ่ง
    path('with/<int:mb_id>/', views.chat_with, name='chat_with'),

    # AJAX polling
    path('poll/<int:ib_id>/', views.poll_messages, name='poll'),
]