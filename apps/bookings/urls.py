# bookings/urls.py - URL routing ของ bookings
from django.urls import path
from . import views

app_name = 'bookings'

urlpatterns = [
    # ─── ฝั่งติวเตอร์ ───────────────────────────────────────────────────────
    path('tutor/',                             views.tutor_requests,    name='tutor_requests'),
    path('tutor/<int:bk_id>/accept/',          views.booking_accept,    name='booking_accept'),
    path('tutor/<int:bk_id>/reject/',          views.booking_reject,    name='booking_reject'),
    path('tutor/<int:bk_id>/studying/',        views.mark_studying,     name='mark_studying'),   # 1→2
    path('tutor/<int:bk_id>/activity/',        views.tutoring_activity, name='tutoring_activity'), # 2→3

    # ─── ฝั่งนักเรียน ───────────────────────────────────────────────────────
    path('my/',                                views.student_bookings,   name='student_bookings'),
    path('my/<int:bk_id>/confirm-completion/', views.confirm_completion, name='confirm_completion'), # 3→4
    path('my/<int:bk_id>/review/',             views.review,             name='review'),              # 4→5
    path('my/<int:bk_id>/report/',             views.report_problem,     name='report_problem'),
]