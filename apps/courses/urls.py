from django.urls import path
from . import views

app_name = 'courses'

urlpatterns = [
    # Faculty
    path('faculty/',                        views.faculty_list,    name='faculty_list'),
    path('faculty/create/',                 views.faculty_create,  name='faculty_create'),
    path('faculty/<int:pk>/edit/',          views.faculty_edit,    name='faculty_edit'),
    path('faculty/<int:pk>/delete/',        views.faculty_delete,  name='faculty_delete'),
    path('faculty/<int:pk>/json/',          views.faculty_json,    name='faculty_json'),

    # Major
    path('major/',                          views.major_list,      name='major_list'),
    path('major/create/',                   views.major_create,    name='major_create'),
    path('major/<int:pk>/edit/',            views.major_edit,      name='major_edit'),
    path('major/<int:pk>/delete/',          views.major_delete,    name='major_delete'),
    path('major/<int:pk>/json/',            views.major_json,      name='major_json'),

    # CourseGroup
    path('course-group/',                   views.course_group_list,   name='course_group_list'),
    path('course-group/create/',            views.course_group_create, name='course_group_create'),
    path('course-group/<int:pk>/edit/',     views.course_group_edit,   name='course_group_edit'),
    path('course-group/<int:pk>/delete/',   views.course_group_delete, name='course_group_delete'),
    path('course-group/<int:pk>/json/',     views.course_group_json,   name='course_group_json'),

    # Course
    path('course/',                         views.course_list,     name='course_list'),
    path('course/create/',                  views.course_create,   name='course_create'),
    path('course/<str:pk>/edit/',           views.course_edit,     name='course_edit'),
    path('course/<str:pk>/delete/',         views.course_delete,   name='course_delete'),
    path('course/<str:pk>/json/',           views.course_json,     name='course_json'),
]
