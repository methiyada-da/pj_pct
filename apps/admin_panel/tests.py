import json

from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Member, Tutor, TutorExperienceImage
from apps.bookings.models import Booking
from apps.credits.models import Withdrawals
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
        self.tutor = tutor
        course_group = CourseGroup.objects.create(cg_name='กลุ่มวิชาทดสอบ')
        course = Course.objects.create(
            crs_id='CRSTEST000001',
            crs_name='รายวิชาทดสอบ',
            cg_id=course_group,
        )
        self.course = course
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

    def test_report_center_lists_exactly_seven_report_types(self):
        response = self.client.get(reverse('admin_reports'))

        self.assertEqual(response.status_code, 200)
        for report_type in (
            'members', 'tutors', 'courses', 'bookings', 'refills',
            'withdrawals', 'reviews',
        ):
            self.assertContains(response, f'report_type={report_type}')
        self.assertNotContains(response, 'report_type=tutor_income')
        self.assertNotContains(response, 'report_type=summary')
        self.assertNotContains(response, 'report_type=booking_reports')

    def test_every_report_preview_loads(self):
        for report_type in (
            'members', 'tutors', 'courses', 'bookings', 'refills',
            'withdrawals', 'reviews',
        ):
            with self.subTest(report_type=report_type):
                response = self.client.get(reverse('admin_reports'), {'report_type': report_type})
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context['report_selected'])

    def test_invalid_date_range_does_not_raise_error(self):
        response = self.client.get(reverse('admin_reports'), {
            'report_type': 'bookings',
            'date_from': '2026-09-30',
            'date_to': '2026-09-01',
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_rows'], 0)
        self.assertContains(response, 'วันที่จองเริ่มต้นต้องไม่มากกว่าวันสิ้นสุด')

    def test_course_report_counts_each_tutor_once(self):
        TutorCourse.objects.create(
            tutc_id='TUTCTEST00002',
            tutc_name='คอร์สทดสอบลำดับที่สอง',
            tutc_max_stu=1,
            crs_id=self.course,
            tut_id=self.tutor,
        )

        response = self.client.get(reverse('admin_reports'), {'report_type': 'courses'})

        self.assertEqual(response.status_code, 200)
        row_values = [cell['value'] for cell in response.context['rows'][0]['cells']]
        self.assertEqual(row_values[-1], 1)

    def test_report_export_returns_pdf_file(self):
        response = self.client.get(reverse('admin_reports'), {
            'report_type': 'courses',
            'print': '1',
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response.content.startswith(b'%PDF'))

    def test_report_codes_match_management_pages(self):
        member_response = self.client.get(reverse('admin_reports'), {'report_type': 'members'})
        tutor_response = self.client.get(reverse('admin_reports'), {'report_type': 'tutors'})

        member_codes = {
            row['cells'][2]['value'] for row in member_response.context['rows']
        }
        tutor_code = tutor_response.context['rows'][0]['cells'][2]['value']
        tutor_year = self.tutor.tut_id.user.date_joined.year

        self.assertIn(f'M{self.student.pk:03d}', member_codes)
        self.assertEqual(tutor_code, f'TR-{tutor_year}-{self.tutor.pk:04d}')

    def test_member_report_can_filter_user_type(self):
        response = self.client.get(reverse('admin_reports'), {
            'report_type': 'members',
            'user_type': 'tutor',
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_rows'], 1)
        self.assertIn('ประเภทผู้ใช้งาน', response.context['headers'])

    def test_tutor_detail_displays_experience_images(self):
        TutorExperienceImage.objects.create(
            tutor=self.tutor,
            image='tutoring/experience/teaching-proof.jpg',
        )

        response = self.client.get(
            reverse('admin_panel:tutor_mgmt_detail', args=[self.tutor.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'รูปผลงานหรือหลักฐานประสบการณ์')
        self.assertContains(response, '/media/tutoring/experience/teaching-proof.jpg')

    def test_admin_can_update_member_status_from_detail_modal(self):
        response = self.client.post(reverse('admin_panel:member_mgmt'), {
            'action': 'update_status',
            'member_id': self.student.pk,
            'member_status': '2',
        })

        self.assertRedirects(response, reverse('admin_panel:member_mgmt'))
        self.student.refresh_from_db()
        self.assertEqual(self.student.mb_status, 2)

    def test_member_status_rejects_invalid_value(self):
        response = self.client.post(reverse('admin_panel:member_mgmt'), {
            'action': 'update_status',
            'member_id': self.student.pk,
            'member_status': '99',
        })

        self.assertRedirects(response, reverse('admin_panel:member_mgmt'))
        self.student.refresh_from_db()
        self.assertEqual(self.student.mb_status, 1)

    def test_admin_payment_is_idempotent_for_one_withdrawal(self):
        self.student.mb_deposit_crd = 100
        self.student.mb_locked_crd = 10
        self.student.save(update_fields=['mb_deposit_crd', 'mb_locked_crd'])
        withdrawal = Withdrawals.objects.create(
            wd_req_date=timezone.now(),
            wd_type=0,
            wd_credit=10,
            wd_cash=Decimal('100.00'),
            wd_bank_name='ธนาคารทดสอบ',
            wd_acc_name='สมาชิกทดสอบ',
            wd_acc_no='1234567890',
            wd_promptpay_no='0812345678',
            wd_fee=Decimal('0.00'),
            wd_net_cash=Decimal('100.00'),
            wd_status=0,
            member=self.student,
        )

        first_response = self.client.post(reverse('admin_panel:payment_mgmt'), {
            'action': 'pay',
            'wd_id': withdrawal.pk,
        })
        second_response = self.client.post(reverse('admin_panel:payment_mgmt'), {
            'action': 'pay',
            'wd_id': withdrawal.pk,
        })

        self.assertRedirects(first_response, reverse('admin_panel:payment_mgmt'))
        self.assertRedirects(second_response, reverse('admin_panel:payment_mgmt'))
        withdrawal.refresh_from_db()
        self.student.refresh_from_db()
        self.assertEqual(withdrawal.wd_status, 1)
        self.assertEqual(self.student.mb_deposit_crd, 90)
        self.assertEqual(self.student.mb_locked_crd, 0)

    def test_course_report_filter_can_select_group_and_course_together(self):
        response = self.client.get(reverse('admin_reports'), {
            'report_type': 'courses',
            'course_group': self.course.cg_id_id,
            'course': self.course.crs_id,
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_rows'], 1)

    def test_booking_report_contains_only_reviewed_bookings_and_starts_with_date(self):
        for status in (4, 5, 6, 5):
            Booking.objects.create(
                member=self.student,
                tutc_id=self.tutor_course,
                bk_stu_datetime=timezone.now(),
                bk_stu_count=1,
                bk_rate_per_person=10,
                bk_date=timezone.now(),
                bk_status=status,
            )

        response = self.client.get(reverse('admin_reports'), {
            'report_type': 'bookings',
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_rows'], 2)
        self.assertEqual(response.context['headers'][0], 'วันที่จอง')
        self.assertEqual(response.context['rows'][0]['cells'][0]['rowspan'], 2)

    def test_booking_report_searches_tutor_by_name_without_member_filter(self):
        Booking.objects.create(
            member=self.student,
            tutc_id=self.tutor_course,
            bk_stu_datetime=timezone.now(),
            bk_stu_count=1,
            bk_rate_per_person=10,
            bk_date=timezone.now(),
            bk_status=5,
        )

        response = self.client.get(reverse('admin_reports'), {
            'report_type': 'bookings',
            'tutor': self.tutor.tut_id.mb_full_name[:4],
        })

        filter_names = {field['name']: field for field in response.context['filter_fields']}
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_rows'], 1)
        self.assertEqual(filter_names['tutor']['type'], 'search')
        self.assertIn(
            self.tutor.tut_id.mb_full_name,
            filter_names['tutor']['options'],
        )
        self.assertNotIn('member', filter_names)

    def test_dashboard_chart_uses_selected_metric_metadata(self):
        response = self.client.get(reverse('admin_panel:dashboard'), {
            'chart_metric': 'topups',
            'chart_range': '30d',
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['chart_metric_label'], 'ยอดเติมเครดิต')
        self.assertEqual(response.context['chart_range_label'], '30 วันล่าสุด')
        self.assertEqual(response.context['chart_unit'], 'บาท')
        self.assertEqual(response.context['chart_type'], 'bar')
        self.assertContains(response, 'ยอดเติมเครดิต — 30 วันล่าสุด')
        self.assertNotContains(response, 'สมาชิกใหม่ 7 เดือนล่าสุด')

    def test_dashboard_booking_chart_counts_only_closed_bookings(self):
        for status in (4, 6):
            Booking.objects.create(
                member=self.student,
                tutc_id=self.tutor_course,
                bk_stu_datetime=timezone.now(),
                bk_stu_count=1,
                bk_rate_per_person=10,
                bk_date=timezone.now(),
                bk_status=status,
            )

        response = self.client.get(reverse('admin_panel:dashboard'), {
            'chart_metric': 'bookings',
            'chart_range': '30d',
        })

        chart_data = json.loads(response.context['chart_data'])
        self.assertEqual(sum(chart_data), 1)
        self.assertEqual(response.context['total_bookings'], 1)

    def test_dashboard_year_chart_starts_in_january(self):
        response = self.client.get(reverse('admin_panel:dashboard'), {
            'chart_metric': 'members',
            'chart_range': 'year',
        })

        labels = json.loads(response.context['chart_labels'])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(labels), timezone.localdate().month)
        self.assertTrue(labels[0].startswith('ม.ค.'))
        self.assertEqual(
            response.context['chart_range_label'],
            f'ปี {timezone.localdate().year + 543}',
        )
