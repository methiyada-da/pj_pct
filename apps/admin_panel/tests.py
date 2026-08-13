from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Member, Tutor
from apps.bookings.models import Booking
from apps.courses.models import Course, CourseGroup
from apps.tutoring.models import TutorCourse

from .models import System


class AdminReportStatusTransitionTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username='admin-test', password='test-pass', is_staff=True
        )
        System.objects.create(
            admin=self.admin_user,
            uni_name='มหาวิทยาลัยทดสอบ',
            bank_name='ธนาคารทดสอบ',
            acc_name='บัญชีทดสอบ',
            acc_no='1234567890',
            crd_val=1,
            deposit_withdraw_fee_pct=0,
            income_withdraw_fee_pct=0,
        )
        self.student_user = User.objects.create_user(username='student-test')
        self.student = Member.objects.create(
            user=self.student_user,
            mb_full_name='ผู้เรียนทดสอบ',
            mb_email='student@test.local',
            mb_deposit_crd=100,
            mb_locked_crd=10,
        )
        tutor_user = User.objects.create_user(username='tutor-test')
        tutor_member = Member.objects.create(
            user=tutor_user,
            mb_full_name='ติวเตอร์ทดสอบ',
            mb_email='tutor@test.local',
        )
        tutor = Tutor.objects.create(
            tut_id=tutor_member,
            tut_gpax=3.00,
            tut_status=1,
        )
        course_group = CourseGroup.objects.create(cg_name='กลุ่มวิชาทดสอบ')
        course = Course.objects.create(
            crs_id='CRSTEST000001',
            crs_name='รายวิชาทดสอบ',
            cg_id=course_group,
        )
        self.tutor_course = TutorCourse.objects.create(
            tutc_id='TUTCTEST00001',
            tutc_name='คอร์สทดสอบ',
            tutc_max_stu=1,
            crs_id=course,
            tut_id=tutor,
        )
        self.client.force_login(self.admin_user)

    def create_reported_booking(self, status):
        return Booking.objects.create(
            member=self.student,
            tutc_id=self.tutor_course,
            bk_stu_datetime=timezone.now(),
            bk_stu_count=1,
            bk_rate_per_person=10,
            bk_date=timezone.now(),
            bk_status=status,
            bk_report_reason='8',
            bk_report_desc='รายละเอียดทดสอบ',
            bk_report_date=timezone.now(),
        )

    def resolve(self, booking, action):
        return self.client.post(
            reverse('admin_panel:report_mgmt'),
            {'bk_id': booking.pk, 'action': action, 'note': 'ผลทดสอบ'},
        )

    def test_admin_cannot_resolve_report_after_status_changed(self):
        for status in (0, 2, 4, 5, 6):
            for action in ('refund', 'no_refund'):
                with self.subTest(status=status, action=action):
                    booking = self.create_reported_booking(status)
                    self.resolve(booking, action)
                    booking.refresh_from_db()
                    self.assertEqual(booking.bk_status, status)
                    self.assertIsNone(booking.bk_report_resolved_date)

    def test_admin_can_refund_report_at_status_one(self):
        booking = self.create_reported_booking(1)
        self.resolve(booking, 'refund')
        booking.refresh_from_db()
        self.assertEqual(booking.bk_status, 6)
        self.assertIsNotNone(booking.bk_report_resolved_date)

    def test_admin_can_reject_refund_report_at_status_three(self):
        booking = self.create_reported_booking(3)
        self.resolve(booking, 'no_refund')
        booking.refresh_from_db()
        self.assertEqual(booking.bk_status, 4)
        self.assertIsNotNone(booking.bk_report_resolved_date)
