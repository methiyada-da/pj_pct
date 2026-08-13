from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Avg

from apps.accounts.models import Tutor
from apps.tutoring.models import TutorCourse
from apps.bookings.models import Review


RATING_FIELDS = (
    'rv_quality',
    'rv_knowledge',
    'rv_communication',
    'rv_punctuality',
    'rv_satisfaction',
)


class Command(BaseCommand):
    help = 'คำนวณคะแนนเฉลี่ยของคอร์สและติวเตอร์ใหม่จากรีวิวทั้งหมด'

    @transaction.atomic
    def handle(self, *args, **options):
        courses = list(TutorCourse.objects.all())
        tutors = list(Tutor.objects.all())

        for course in courses:
            values = Review.objects.filter(
                bk_id__tutc_id=course
            ).aggregate(**{
                field: Avg(field) for field in RATING_FIELDS
            })
            course.tutc_rating = round(
                sum(float(value or 0) for value in values.values()) / 5,
                2,
            )

        if courses:
            TutorCourse.objects.bulk_update(courses, ['tutc_rating'])

        tutor_update_fields = [
            'tut_rating',
            'tut_rating_quality',
            'tut_rating_knowledge',
            'tut_rating_communication',
            'tut_rating_punctuality',
            'tut_rating_satisfaction',
        ]
        for tutor in tutors:
            values = Review.objects.filter(
                bk_id__tutc_id__tut_id=tutor
            ).aggregate(**{
                field: Avg(field) for field in RATING_FIELDS
            })
            quality = round(values['rv_quality'] or 0, 2)
            knowledge = round(values['rv_knowledge'] or 0, 2)
            communication = round(values['rv_communication'] or 0, 2)
            punctuality = round(values['rv_punctuality'] or 0, 2)
            satisfaction = round(values['rv_satisfaction'] or 0, 2)

            tutor.tut_rating_quality = quality
            tutor.tut_rating_knowledge = knowledge
            tutor.tut_rating_communication = communication
            tutor.tut_rating_punctuality = punctuality
            tutor.tut_rating_satisfaction = satisfaction
            tutor.tut_rating = round(
                (quality + knowledge + communication + punctuality + satisfaction) / 5,
                2,
            )

        if tutors:
            Tutor.objects.bulk_update(tutors, tutor_update_fields)

        self.stdout.write(self.style.SUCCESS(
            f'คำนวณคะแนนใหม่สำเร็จ: {len(courses)} คอร์ส, {len(tutors)} ติวเตอร์'
        ))
