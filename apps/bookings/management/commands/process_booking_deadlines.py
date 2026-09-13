from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from apps.accounts.models import Member
from apps.bookings.models import Booking, JobCompletion
from apps.bookings.services import get_tutor_response_deadline_at
from apps.tutoring.models import TutorCourse


BOOKING_TIMEOUT_MARKER = '[เลยกำหนดตอบรับ]'


def notify_member(member, notif_type, message, url):
    try:
        from apps.notifications.signals import _notif_member
        _notif_member(member, notif_type, message, url)
    except Exception:
        # การประมวลผลหลักต้องดำเนินต่อได้ แม้สร้างการแจ้งเตือนไม่สำเร็จ
        return


class Command(BaseCommand):
    help = 'ปิดรายการที่เลยกำหนดตอบรับ และยืนยันจบงานที่ครบกำหนดอัตโนมัติ'

    def handle(self, *args, **options):
        legacy_courses = self._close_courses_without_single_rate()
        timed_out = self._reject_overdue_pending()
        completed = self._confirm_overdue_completion()
        self.stdout.write(
            self.style.SUCCESS(
                f'closed legacy courses: {legacy_courses}, '
                f'timed-out bookings: {timed_out}, '
                f'auto-confirmed completions: {completed}'
            )
        )

    def _close_courses_without_single_rate(self):
        course_ids = list(
            TutorCourse.objects.annotate(rate_count=Count('tutorrate'))
            .exclude(rate_count=1)
            .filter(tutc_status=1)
            .values_list('pk', flat=True)
        )
        return TutorCourse.objects.filter(pk__in=course_ids).update(tutc_status=0)

    def _reject_overdue_pending(self):
        now = timezone.now()
        booking_ids = []
        pending = (
            Booking.objects.filter(bk_status=0, ts_id__isnull=False)
            .select_related('ts_id__sd_id')
        )
        for booking in pending:
            if now >= get_tutor_response_deadline_at(booking.ts_id):
                booking_ids.append(booking.pk)

        processed = 0
        for booking_id in booking_ids:
            with transaction.atomic():
                booking = (
                    Booking.objects.select_for_update()
                    .select_related('member', 'ts_id__sd_id')
                    .filter(pk=booking_id, bk_status=0)
                    .first()
                )
                if not booking or now < get_tutor_response_deadline_at(booking.ts_id):
                    continue

                student = Member.objects.select_for_update().get(pk=booking.member_id)
                student.mb_locked_crd = max(
                    0,
                    student.mb_locked_crd - booking.total_credit,
                )
                student.save(update_fields=['mb_locked_crd'])
                booking.bk_status = 6
                booking.bk_cmt = f'{BOOKING_TIMEOUT_MARKER} ระบบปิดรายการอัตโนมัติ'
                booking.save(update_fields=['bk_status', 'bk_cmt'])

            notify_member(
                booking.member,
                'booking_rejected',
                f'การจอง BK{booking.bk_id:05d} เลยกำหนดตอบรับ เครดิตได้รับการปลดล็อกแล้ว',
                '/bookings/my/?tab=6',
            )
            processed += 1
        return processed

    def _confirm_overdue_completion(self):
        cutoff = timezone.now() - timezone.timedelta(
            hours=settings.COMPLETION_AUTO_CONFIRM_HOURS,
        )
        booking_ids = list(
            Booking.objects.filter(
                bk_status=3,
                jobcompletion__jc_complete_date__lte=cutoff,
            ).values_list('pk', flat=True)
        )

        processed = 0
        for booking_id in booking_ids:
            with transaction.atomic():
                booking = (
                    Booking.objects.select_for_update()
                    .select_related('tutc_id__tut_id__tut_id')
                    .filter(pk=booking_id, bk_status=3)
                    .first()
                )
                if not booking:
                    continue
                completion = JobCompletion.objects.select_for_update().get(bk_id=booking)
                if completion.jc_complete_date > cutoff:
                    continue

                student = Member.objects.select_for_update().get(pk=booking.member_id)
                tutor_member = Member.objects.select_for_update().get(
                    pk=booking.tutc_id.tut_id.tut_id_id,
                )
                total_credit = booking.total_credit
                deposit_deduct = min(student.mb_deposit_crd, total_credit)
                income_deduct = total_credit - deposit_deduct
                student.mb_deposit_crd = max(0, student.mb_deposit_crd - deposit_deduct)
                student.mb_income_crd = max(0, student.mb_income_crd - income_deduct)
                student.mb_locked_crd = max(0, student.mb_locked_crd - total_credit)
                student.save(update_fields=['mb_deposit_crd', 'mb_income_crd', 'mb_locked_crd'])
                tutor_member.mb_income_crd += total_credit
                tutor_member.save(update_fields=['mb_income_crd'])

                completion.jc_confirm_date = timezone.now()
                completion.save(update_fields=['jc_confirm_date'])
                booking.bk_status = 4
                booking.save(update_fields=['bk_status'])
                processed += 1
        return processed
