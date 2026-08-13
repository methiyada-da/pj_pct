from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Member, Tutor
from apps.courses.models import Course, CourseGroup
from apps.tutoring.models import TutorCourse

from .models import Booking


class BookingStateTransitionTests(TestCase):
    def setUp(self):
        self.student_user = User.objects.create_user(username='student-flow')
        self.student = Member.objects.create(
            user=self.student_user,
            mb_full_name='ผู้เรียนทดสอบ',
            mb_email='student-flow@test.local',
        )
        self.tutor_user = User.objects.create_user(username='tutor-flow')
        tutor_member = Member.objects.create(
            user=self.tutor_user,
            mb_full_name='ติวเตอร์ทดสอบ',
            mb_email='tutor-flow@test.local',
        )
        tutor = Tutor.objects.create(
            tut_id=tutor_member,
            tut_gpax=3.00,
            tut_status=1,
        )
        course_group = CourseGroup.objects.create(cg_name='กลุ่มวิชาทดสอบ')
        course = Course.objects.create(
            crs_id='CRSTEST000002',
            crs_name='รายวิชาทดสอบ',
            cg_id=course_group,
        )
        self.tutor_course = TutorCourse.objects.create(
            tutc_id='TUTCTEST00002',
            tutc_name='คอร์สทดสอบ',
            tutc_max_stu=1,
            crs_id=course,
            tut_id=tutor,
        )

    def create_booking(self, status):
        return Booking.objects.create(
            member=self.student,
            tutc_id=self.tutor_course,
            bk_stu_datetime=timezone.now(),
            bk_stu_count=1,
            bk_rate_per_person=10,
            bk_date=timezone.now(),
            bk_status=status,
        )

    def test_accept_changes_only_status_zero_to_one(self):
        booking = self.create_booking(0)
        self.client.force_login(self.tutor_user)
        response = self.client.post(
            reverse('bookings:booking_accept', args=[booking.pk])
        )
        booking.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(booking.bk_status, 1)

    def test_tutor_cannot_skip_to_status_two_from_status_zero(self):
        booking = self.create_booking(0)
        self.client.force_login(self.tutor_user)
        response = self.client.post(
            reverse('bookings:mark_studying', args=[booking.pk])
        )
        booking.refresh_from_db()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(booking.bk_status, 0)

    def test_student_cannot_confirm_before_status_three(self):
        booking = self.create_booking(1)
        self.client.force_login(self.student_user)
        response = self.client.post(
            reverse('bookings:confirm_completion', args=[booking.pk])
        )
        booking.refresh_from_db()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(booking.bk_status, 1)

    def test_student_cannot_review_before_status_four(self):
        booking = self.create_booking(3)
        self.client.force_login(self.student_user)
        response = self.client.get(reverse('bookings:review', args=[booking.pk]))
        booking.refresh_from_db()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(booking.bk_status, 3)

    def test_tutor_cannot_submit_activity_after_status_four(self):
        booking = self.create_booking(4)
        self.client.force_login(self.tutor_user)
        response = self.client.post(
            reverse('bookings:tutoring_activity', args=[booking.pk]),
            {'action': 'submit', 'ta_desc': 'รายละเอียด'},
        )
        booking.refresh_from_db()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(booking.bk_status, 4)
