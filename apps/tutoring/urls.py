from django.urls import path
from . import views


app_name = 'tutoring'

urlpatterns = [
    # สมัครเป็นติวเตอร์ (เดิม)
    path('register/', views.register_tutor, name='register_tutor'),

    # หน้าเมนูหลักจัดการข้อมูลติวเตอร์
    path('manage/', views.tutor_manage, name='tutor_manage'),

    # รายการคอร์สของติวเตอร์
    path('manage/courses/', views.tutor_course_list, name='tutor_course_list'),

    # เพิ่มคอร์สใหม่
    path('manage/courses/add/', views.manage_course, name='manage_course'),

    # แก้ไขคอร์ส (ใช้ tutc_id เป็น str ตาม model)
    path('manage/courses/<str:tutc_id>/edit/', views.manage_course, name='manage_course_edit'),

    path('course/<str:tutc_id>/toggle/', views.toggle_course_status, name='toggle_course_status'),

    path('course/<str:tutc_id>/delete/', views.delete_course,        name='delete_course'),
]