# notifications/urls.py - URL routing ของ notifications
from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('api/', views.api_list, name='api_list'),
    path('api/read-all/', views.api_mark_all_read, name='api_mark_all_read'),
    path('api/<int:notif_id>/read/', views.api_mark_read, name='api_mark_read'),
]
