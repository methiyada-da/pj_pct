from django.urls import path
from . import views

app_name = 'bookings'

urlpatterns = [
    path('tutor/',                    views.tutor_requests,  name='tutor_requests'),
    path('tutor/<int:bk_id>/accept/', views.booking_accept,  name='booking_accept'),
    path('tutor/<int:bk_id>/reject/', views.booking_reject,  name='booking_reject'),
    path('my/',                       views.student_bookings, name='student_bookings'),
]
