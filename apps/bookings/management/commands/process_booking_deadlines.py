from django.core.management.base import BaseCommand
from django.db.models import Count

from apps.bookings.services import (
    process_overdue_completions,
    process_overdue_pending_bookings,
)
from apps.tutoring.models import TutorCourse

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
        return process_overdue_pending_bookings()

    def _confirm_overdue_completion(self):
        return process_overdue_completions()
