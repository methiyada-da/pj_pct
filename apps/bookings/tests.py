from datetime import time, timedelta
import tempfile

from django.contrib.auth.models import User
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Member, Tutor
from apps.courses.models import Course, CourseGroup
from apps.tutoring.models import ScheduleDate, TimeSlot, TutorCourse, TutorRate

from .models import Booking
from .services import get_remaining_seats


TEST_MIDDLEWARE = [
    middleware
    for middleware in settings.MIDDLEWARE
    if middleware != 'apps.admin_panel.middleware.AdminSetupMiddleware'
]


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
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


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class GroupBookingFlowTests(TestCase):
    def setUp(self):
        self.student_user = User.objects.create_user(username='group-student')
        self.student = Member.objects.create(
            user=self.student_user,
            mb_full_name='ผู้เรียนกลุ่มหนึ่ง',
            mb_email='group-student@test.local',
            mb_deposit_crd=100,
        )
        self.second_user = User.objects.create_user(username='group-student-two')
        self.second_student = Member.objects.create(
            user=self.second_user,
            mb_full_name='ผู้เรียนกลุ่มสอง',
            mb_email='group-student-two@test.local',
            mb_deposit_crd=100,
        )
        self.tutor_user = User.objects.create_user(username='group-tutor')
        tutor_member = Member.objects.create(
            user=self.tutor_user,
            mb_full_name='ติวเตอร์กลุ่ม',
            mb_email='group-tutor@test.local',
        )
        self.tutor = Tutor.objects.create(
            tut_id=tutor_member,
            tut_gpax=3.00,
            tut_status=1,
        )
        course_group = CourseGroup.objects.create(cg_name='กลุ่มทดสอบการจองร่วม')
        course = Course.objects.create(
            crs_id='CRSGROUP00001',
            crs_name='วิชาทดสอบการจองร่วม',
            cg_id=course_group,
        )
        self.tutor_course = TutorCourse.objects.create(
            tutc_id='TUTCGROUP0001',
            tutc_name='คอร์สจองร่วม',
            tutc_meeting_detail='อาคารทดสอบ ชั้น 2',
            tutc_max_stu=5,
            crs_id=course,
            tut_id=self.tutor,
        )
        TutorRate.objects.create(
            tutc_id=self.tutor_course,
            tut_rate_stu_count=1,
            tut_rate_per_person=10,
        )
        schedule = ScheduleDate.objects.create(
            tutc_id=self.tutor_course,
            sd_date=timezone.localdate() + timedelta(days=2),
        )
        self.slot = TimeSlot.objects.create(
            sd_id=schedule,
            ts_start_time=time(10, 0),
            ts_end_time=time(11, 0),
        )

    def _book(self, user, seats):
        self.client.force_login(user)
        return self.client.post(
            reverse('tutoring:booking_create', args=[self.tutor_course.pk]),
            {'ts_id': self.slot.pk, 'stu_count': seats},
        )

    def test_multiple_accounts_share_slot_until_capacity_is_full(self):
        self._book(self.student_user, 3)
        self._book(self.second_user, 2)

        self.slot.refresh_from_db()
        self.assertEqual(self.slot.ts_status, 0)
        self.assertEqual(Booking.objects.filter(ts_id=self.slot).count(), 2)
        self.assertEqual(get_remaining_seats(self.slot), 0)

    def test_same_account_cannot_create_second_active_booking_in_slot(self):
        self._book(self.student_user, 2)
        self._book(self.student_user, 1)

        self.assertEqual(
            Booking.objects.filter(ts_id=self.slot, member=self.student).count(),
            1,
        )
        self.assertEqual(get_remaining_seats(self.slot), 3)

    def test_accept_all_accepts_current_pending_bookings_and_saves_meeting(self):
        self._book(self.student_user, 2)
        self._book(self.second_user, 1)
        self.client.force_login(self.tutor_user)

        response = self.client.post(
            reverse('bookings:booking_accept_all', args=[self.slot.pk]),
            {
                'meeting_detail': 'อาคารทดสอบ ห้อง 201',
                'meeting_confirmed': '1',
            },
        )

        self.slot.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.slot.ts_meeting_detail, 'อาคารทดสอบ ห้อง 201')
        self.assertEqual(
            Booking.objects.filter(ts_id=self.slot, bk_status=1).count(),
            2,
        )

    def test_accept_all_can_close_slot_immediately(self):
        self._book(self.student_user, 2)
        self.client.force_login(self.tutor_user)

        response = self.client.post(
            reverse('bookings:booking_accept_all', args=[self.slot.pk]),
            {
                'meeting_detail': 'อาคารทดสอบ ห้อง 201',
                'meeting_confirmed': '1',
                'close_slot': '1',
            },
        )

        self.slot.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.slot.ts_status, 2)
        self.assertEqual(
            Booking.objects.filter(ts_id=self.slot, bk_status=1).count(),
            1,
        )

    def test_deadline_command_rejects_pending_and_unlocks_credit(self):
        self._book(self.student_user, 2)
        booking = Booking.objects.get(ts_id=self.slot, member=self.student)
        self.slot.sd_id.sd_date = timezone.localdate() - timedelta(days=1)
        self.slot.sd_id.save(update_fields=['sd_date'])

        call_command('process_booking_deadlines')

        booking.refresh_from_db()
        self.student.refresh_from_db()
        self.assertEqual(booking.bk_status, 6)
        self.assertTrue(booking.bk_cmt.startswith('[เลยกำหนดตอบรับ]'))
        self.assertEqual(self.student.mb_locked_crd, 0)

    def test_group_completion_records_attended_and_absent_separately(self):
        self.slot.sd_id.sd_date = timezone.localdate() - timedelta(days=1)
        self.slot.sd_id.save(update_fields=['sd_date'])
        lesson_datetime = timezone.now() - timedelta(days=1)
        attended_booking = Booking.objects.create(
            member=self.student,
            tutc_id=self.tutor_course,
            ts_id=self.slot,
            bk_stu_datetime=lesson_datetime,
            bk_stu_count=2,
            bk_rate_per_person=10,
            bk_date=lesson_datetime,
            bk_status=1,
        )
        absent_booking = Booking.objects.create(
            member=self.second_student,
            tutc_id=self.tutor_course,
            ts_id=self.slot,
            bk_stu_datetime=lesson_datetime,
            bk_stu_count=1,
            bk_rate_per_person=10,
            bk_date=lesson_datetime,
            bk_status=1,
        )
        self.client.force_login(self.tutor_user)

        with tempfile.TemporaryDirectory() as media_root:
            with self.settings(MEDIA_ROOT=media_root):
                response = self.client.post(
                    reverse('bookings:tutoring_activity_group', args=[self.slot.pk]),
                    {
                        f'attendance_{attended_booking.pk}': 'attended',
                        f'attendance_{absent_booking.pk}': 'absent',
                        'ta_desc': 'ทบทวนบทเรียนร่วมกัน',
                        'absent_desc': 'ติดต่อแล้วแต่ผู้เรียนไม่เข้าร่วม',
                        'ta_img1': SimpleUploadedFile('proof.jpg', b'group-proof', content_type='image/jpeg'),
                    },
                )

        attended_booking.refresh_from_db()
        absent_booking.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(attended_booking.bk_status, 3)
        self.assertTrue(hasattr(attended_booking, 'tutoringactivity'))
        self.assertTrue(hasattr(attended_booking, 'jobcompletion'))
        self.assertEqual(absent_booking.bk_status, 1)
        self.assertEqual(absent_booking.bk_report_reason, '5')
        self.assertIsNotNone(absent_booking.bk_report_date)
