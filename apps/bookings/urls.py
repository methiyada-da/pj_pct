# bookings/urls.py - URL routing ของ bookings
from django.urls import path
from . import views

app_name = 'bookings'

urlpatterns = [
    # ─── ฝั่งติวเตอร์ ───────────────────────────────────────────────────────
    path('tutor/',                             views.tutor_requests,    name='tutor_requests'),
    path('tutor/<int:bk_id>/accept/',          views.booking_accept,    name='booking_accept'),
    path('tutor/slot/<int:ts_id>/accept-all/', views.booking_accept_all, name='booking_accept_all'),
    path('tutor/slot/<int:ts_id>/complete/',   views.tutoring_activity_group, name='tutoring_activity_group'),
    path('tutor/<int:bk_id>/reject/',          views.booking_reject,    name='booking_reject'),
    path('tutor/<int:bk_id>/studying/',        views.mark_studying,     name='mark_studying'),   # 1→2
    path('tutor/<int:bk_id>/activity/',        views.tutoring_activity, name='tutoring_activity'), # 2→3
    path('tutor/<int:bk_id>/approve-cancel/',  views.tutor_approve_cancel_booking, name='tutor_approve_cancel_booking'),
    path('tutor/<int:bk_id>/reject-cancel/',   views.tutor_reject_cancel_booking,  name='tutor_reject_cancel_booking'),
    path('tutor/<int:bk_id>/cancel-for-student/', views.tutor_cancel_for_student_booking, name='tutor_cancel_for_student_booking'),
    path('tutor/<int:bk_id>/escalate-cancel-dispute/', views.tutor_escalate_cancel_dispute, name='tutor_escalate_cancel_dispute'),
    path('<int:bk_id>/report-statement/',        views.submit_report_statement, name='submit_report_statement'),

    # ─── ฝั่งนักเรียน ───────────────────────────────────────────────────────
    path('my/',                                views.student_bookings,   name='student_bookings'),
    path('my/<int:bk_id>/confirm-completion/', views.confirm_completion, name='confirm_completion'), # 3→4
    path('my/<int:bk_id>/review/',             views.review,             name='review'),              # 4→5
    path('my/<int:bk_id>/report/',             views.report_problem,     name='report_problem'),
    path('my/<int:bk_id>/cancel/',             views.student_cancel_booking, name='student_cancel_booking'),
    path('my/<int:bk_id>/request-cancel/',     views.student_request_cancel_booking, name='student_request_cancel_booking'),
]
