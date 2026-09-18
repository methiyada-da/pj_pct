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
from apps.notifications.models import Notification
from apps.tutoring.models import ScheduleDate, TimeSlot, TutorCourse, TutorRate

from .models import Booking
from .services import BOOKING_CLOSED_AT_MARKER, get_booking_closed_at, get_remaining_seats


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

    def _book(self, user, seats=1):
        self.client.force_login(user)
        return self.client.post(
            reverse('tutoring:booking_create', args=[self.tutor_course.pk]),
            {'ts_id': self.slot.pk, 'stu_count': seats},
        )

    def _create_accepted_booking(self, hours_until_lesson):
        self._book(self.student_user)
        booking = Booking.objects.get(ts_id=self.slot, member=self.student)
        booking.bk_status = 1
        booking.bk_stu_datetime = timezone.now() + timedelta(hours=hours_until_lesson)
        booking.save(update_fields=['bk_status', 'bk_stu_datetime'])
        return booking

    def test_posted_seat_count_is_ignored_and_booking_uses_one_seat(self):
        self._book(self.student_user, 3)

        booking = Booking.objects.get(ts_id=self.slot, member=self.student)
        self.student.refresh_from_db()
        self.assertEqual(booking.bk_stu_count, 1)
        self.assertEqual(booking.total_credit, 10)
        self.assertEqual(self.student.mb_locked_crd, 10)
        self.assertEqual(get_remaining_seats(self.slot), 4)

    def test_multiple_accounts_reserve_one_seat_each(self):
        self._book(self.student_user, 3)
        self._book(self.second_user, 2)

        self.slot.refresh_from_db()
        self.assertEqual(self.slot.ts_status, 0)
        self.assertEqual(Booking.objects.filter(ts_id=self.slot).count(), 2)
        self.assertTrue(
            all(
                booking.bk_stu_count == 1
                for booking in Booking.objects.filter(ts_id=self.slot)
            )
        )
        self.assertEqual(get_remaining_seats(self.slot), 3)

    def test_same_account_cannot_create_second_active_booking_in_slot(self):
        self._book(self.student_user, 2)
        self._book(self.student_user, 1)

        self.assertEqual(
            Booking.objects.filter(ts_id=self.slot, member=self.student).count(),
            1,
        )
        self.assertEqual(get_remaining_seats(self.slot), 4)

    def test_student_cancels_accepted_booking_immediately_when_more_than_24_hours_remain(self):
        booking = self._create_accepted_booking(25)
        self.client.force_login(self.student_user)

        response = self.client.post(
            reverse('bookings:student_request_cancel_booking', args=[booking.pk])
        )

        booking.refresh_from_db()
        self.student.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(booking.bk_status, 6)
        self.assertTrue(
            booking.bk_cmt.startswith(
                'ผู้เรียนยกเลิกหลังรับงานล่วงหน้ามากกว่า 24 ชั่วโมง'
            )
        )
        self.assertIn(BOOKING_CLOSED_AT_MARKER, booking.bk_cmt)
        self.assertIsNotNone(get_booking_closed_at(booking.bk_cmt))
        self.assertEqual(self.student.mb_locked_crd, 0)
        self.assertTrue(Notification.objects.filter(
            recipient=self.tutor.tut_id,
            notif_type='booking_cancelled',
        ).exists())

    def test_student_cannot_cancel_accepted_booking_within_24_hours(self):
        booking = self._create_accepted_booking(23)
        self.client.force_login(self.student_user)

        response = self.client.post(
            reverse('bookings:student_request_cancel_booking', args=[booking.pk])
        )

        booking.refresh_from_db()
        self.student.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(booking.bk_status, 1)
        self.assertEqual(self.student.mb_locked_crd, 10)
        self.assertFalse(Notification.objects.filter(
            recipient=self.tutor.tut_id,
            notif_type='booking_cancelled',
        ).exists())

    def test_tutor_can_cancel_for_student_within_24_hours(self):
        booking = self._create_accepted_booking(23)
        booking.bk_cmt = 'หมายเหตุเดิมต้องไม่หาย'
        booking.save(update_fields=['bk_cmt'])
        self.client.force_login(self.tutor_user)

        response = self.client.post(
            reverse('bookings:tutor_cancel_for_student_booking', args=[booking.pk])
        )

        booking.refresh_from_db()
        self.student.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(booking.bk_status, 6)
        self.assertTrue(booking.bk_cmt.startswith('หมายเหตุเดิมต้องไม่หาย'))
        self.assertIn('ติวเตอร์ยกเลิกการเรียน', booking.bk_cmt)
        self.assertIn(BOOKING_CLOSED_AT_MARKER, booking.bk_cmt)
        self.assertEqual(self.student.mb_locked_crd, 0)
        self.assertTrue(Notification.objects.filter(
            recipient=self.student,
            notif_type='booking_cancelled',
        ).exists())

    def test_tutor_cannot_cancel_for_student_when_more_than_24_hours_remain(self):
        booking = self._create_accepted_booking(25)
        self.client.force_login(self.tutor_user)

        response = self.client.post(
            reverse('bookings:tutor_cancel_for_student_booking', args=[booking.pk])
        )

        booking.refresh_from_db()
        self.student.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(booking.bk_status, 1)
        self.assertEqual(self.student.mb_locked_crd, 10)

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

    def test_accepted_group_badge_changes_after_lesson_start_without_status_change(self):
        now = timezone.now()
        booking = Booking.objects.create(
            member=self.student,
            tutc_id=self.tutor_course,
            ts_id=self.slot,
            bk_stu_datetime=now + timedelta(hours=1),
            bk_stu_count=2,
            bk_rate_per_person=10,
            bk_date=now,
            bk_status=1,
        )
        self.client.force_login(self.tutor_user)

        before = self.client.get(reverse('bookings:tutor_requests'))
        self.assertEqual(before.status_code, 200)
        self.assertFalse(before.context['accepted_groups'][0].has_started)
        self.assertContains(before, 'data-phase="accepted"')
        self.assertContains(before, 'id="acceptedGroupFilter"')

        booking.bk_stu_datetime = now - timedelta(hours=1)
        booking.save(update_fields=['bk_stu_datetime'])
        after = self.client.get(reverse('bookings:tutor_requests'))
        self.assertEqual(after.status_code, 200)
        self.assertTrue(after.context['accepted_groups'][0].has_started)
        self.assertContains(after, 'data-phase="studying"')
        booking.refresh_from_db()
        self.assertEqual(booking.bk_status, 1)

    def test_ended_status_one_group_moves_to_completion_and_changes_on_finish(self):
        now = timezone.now()
        self.slot.sd_id.sd_date = timezone.localdate() - timedelta(days=1)
        self.slot.sd_id.save(update_fields=['sd_date'])
        booking = Booking.objects.create(
            member=self.student,
            tutc_id=self.tutor_course,
            ts_id=self.slot,
            bk_stu_datetime=now - timedelta(days=1),
            bk_stu_count=1,
            bk_rate_per_person=10,
            bk_date=now - timedelta(days=1),
            bk_status=1,
        )
        self.client.force_login(self.tutor_user)

        response = self.client.get(reverse('bookings:tutor_requests'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['accepted_groups'], [])
        self.assertEqual(len(response.context['completion_pending_groups']), 1)
        self.assertEqual(response.context['accepted_count'], 0)
        self.assertEqual(response.context['completion_count'], 1)
        self.assertContains(response, 'สิ้นสุดเวลาเรียน — รอแจ้งจบงาน')
        self.assertContains(response, 'data-completion-phase="pending"')
        self.assertContains(
            response,
            reverse('bookings:tutoring_activity_group', args=[self.slot.pk]),
        )

        finish_response = self.client.post(
            reverse('bookings:tutoring_activity_group', args=[self.slot.pk]),
            {'action': 'start_completion'},
        )
        self.assertEqual(finish_response.status_code, 302)
        booking.refresh_from_db()
        self.assertEqual(booking.bk_status, 2)

        activity_response = self.client.get(
            reverse('bookings:tutoring_activity_group', args=[self.slot.pk])
        )
        self.assertEqual(activity_response.status_code, 200)
        booking.refresh_from_db()
        self.assertEqual(booking.bk_status, 2)

    def test_completion_tab_combines_pending_and_submitted_activity(self):
        now = timezone.now()
        for student, status in ((self.student, 2), (self.second_student, 3)):
            Booking.objects.create(
                member=student,
                tutc_id=self.tutor_course,
                ts_id=self.slot,
                bk_stu_datetime=now - timedelta(hours=2),
                bk_stu_count=1,
                bk_rate_per_person=10,
                bk_date=now,
                bk_status=status,
            )
        self.client.force_login(self.tutor_user)

        response = self.client.get(reverse('bookings:tutor_requests'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['completion_bookings']), 1)
        self.assertEqual(len(response.context['completion_pending_groups']), 1)
        self.assertEqual(response.context['completion_count'], 2)
        self.assertContains(response, 'data-tab="completion"')
        self.assertContains(response, 'data-completion-phase="pending"')
        self.assertContains(response, 'data-completion-phase="submitted"')
        self.assertContains(response, 'เรียนแล้ว — รอบันทึกกิจกรรม')
        self.assertContains(response, 'id="completionFilter"')
        self.assertNotContains(response, 'id="tab-studying"')
        self.assertNotContains(response, 'id="tab-notified"')

    def test_completion_filter_is_visible_when_there_are_no_bookings(self):
        self.client.force_login(self.tutor_user)

        response = self.client.get(reverse('bookings:tutor_requests'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="completionFilter"')
        self.assertContains(response, 'ยังไม่มีรายการแจ้งจบงาน')

    def test_student_waiting_tab_has_time_based_badges_and_no_all_tab(self):
        self.client.force_login(self.student_user)
        empty = self.client.get(reverse('bookings:student_bookings'))
        self.assertEqual(empty.status_code, 200)
        self.assertContains(empty, 'id="studentLessonFilter"')
        self.assertContains(empty, 'รอเรียน/กำลังเรียน')
        self.assertContains(empty, 'การจบงาน')
        self.assertNotContains(empty, 'data-filter="all"')

        now = timezone.now()
        booking = Booking.objects.create(
            member=self.student,
            tutc_id=self.tutor_course,
            ts_id=self.slot,
            bk_stu_datetime=now + timedelta(hours=1),
            bk_stu_count=1,
            bk_rate_per_person=10,
            bk_date=now,
            bk_status=1,
        )
        before = self.client.get(reverse('bookings:student_bookings'))
        self.assertEqual(before.status_code, 200)
        self.assertContains(before, 'data-lesson-phase="waiting"')

        booking.bk_stu_datetime = now - timedelta(hours=1)
        booking.save(update_fields=['bk_stu_datetime'])
        after = self.client.get(reverse('bookings:student_bookings'))
        self.assertEqual(after.status_code, 200)
        self.assertContains(after, 'data-lesson-phase="studying"')
        booking.refresh_from_db()
        self.assertEqual(booking.bk_status, 1)

    def test_student_completion_tab_combines_ended_status_one_and_status_two(self):
        now = timezone.now()
        self.slot.sd_id.sd_date = timezone.localdate() - timedelta(days=1)
        self.slot.sd_id.save(update_fields=['sd_date'])
        booking = Booking.objects.create(
            member=self.student,
            tutc_id=self.tutor_course,
            ts_id=self.slot,
            bk_stu_datetime=now - timedelta(days=1),
            bk_stu_count=1,
            bk_rate_per_person=10,
            bk_date=now - timedelta(days=1),
            bk_status=1,
        )
        self.client.force_login(self.student_user)

        ended_response = self.client.get(reverse('bookings:student_bookings'))

        self.assertEqual(ended_response.status_code, 200)
        self.assertContains(ended_response, 'data-lesson-phase="finished"')
        self.assertContains(
            ended_response,
            'สิ้นสุดเวลาเรียน — รอติวเตอร์แจ้งจบงาน',
        )
        self.assertContains(ended_response, 'id="studentCompletionFilter"')
        booking.refresh_from_db()
        self.assertEqual(booking.bk_status, 1)

        booking.bk_status = 2
        booking.save(update_fields=['bk_status'])
        status_two_response = self.client.get(reverse('bookings:student_bookings'))

        self.assertEqual(status_two_response.status_code, 200)
        self.assertContains(
            status_two_response,
            'สิ้นสุดเวลาเรียน — รอติวเตอร์แจ้งจบงาน',
        )
        booking.refresh_from_db()
        self.assertEqual(booking.bk_status, 2)

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

    def test_notification_poll_processes_overdue_booking_and_notifies_both_sides(self):
        self._book(self.student_user, 1)
        booking = Booking.objects.get(ts_id=self.slot, member=self.student)
        self.slot.sd_id.sd_date = timezone.localdate() - timedelta(days=1)
        self.slot.sd_id.save(update_fields=['sd_date'])
        self.client.force_login(self.tutor_user)

        response = self.client.get(reverse('notifications:api_list'))

        booking.refresh_from_db()
        self.student.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(booking.bk_status, 6)
        self.assertEqual(self.student.mb_locked_crd, 0)
        self.assertTrue(response.json()['booking_state_token'])
        self.assertTrue(Notification.objects.filter(
            recipient=self.student,
            notif_type='booking_rejected',
        ).exists())
        self.assertTrue(Notification.objects.filter(
            recipient=self.tutor.tut_id,
            notif_type='booking_cancelled',
        ).exists())

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

        finish_response = self.client.post(
            reverse('bookings:tutoring_activity_group', args=[self.slot.pk]),
            {'action': 'start_completion'},
        )
        self.assertEqual(finish_response.status_code, 302)
        attended_booking.refresh_from_db()
        absent_booking.refresh_from_db()
        self.assertEqual(attended_booking.bk_status, 2)
        self.assertEqual(absent_booking.bk_status, 2)

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
