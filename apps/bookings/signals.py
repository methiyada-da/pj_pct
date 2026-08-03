from django.db.models import Avg
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Review


def _update_tutorcourse_rating(review):
    """คำนวณและบันทึกคะแนนรีวิวเฉลี่ยของคอร์สที่เกี่ยวข้อง"""
    tutorcourse = review.bk_id.tutc_id
    averages = Review.objects.filter(
        bk_id__tutc_id=tutorcourse
    ).aggregate(
        avg_quality=Avg('rv_quality'),
        avg_knowledge=Avg('rv_knowledge'),
        avg_communication=Avg('rv_communication'),
        avg_punctuality=Avg('rv_punctuality'),
        avg_satisfaction=Avg('rv_satisfaction'),
    )

    rating_values = [value or 0 for value in averages.values()]
    tutorcourse.tutc_rating = round(sum(rating_values) / 5, 2)
    tutorcourse.save(update_fields=['tutc_rating'])


def _update_tutor_rating(review):
    """คำนวณและบันทึกคะแนนรีวิวเฉลี่ยของติวเตอร์ที่เกี่ยวข้อง"""
    tutor = review.bk_id.tutc_id.tut_id
    averages = Review.objects.filter(
        bk_id__tutc_id__tut_id=tutor
    ).aggregate(
        avg_quality=Avg('rv_quality'),
        avg_knowledge=Avg('rv_knowledge'),
        avg_communication=Avg('rv_communication'),
        avg_punctuality=Avg('rv_punctuality'),
        avg_satisfaction=Avg('rv_satisfaction'),
    )

    quality = round(averages['avg_quality'] or 0, 2)
    knowledge = round(averages['avg_knowledge'] or 0, 2)
    communication = round(averages['avg_communication'] or 0, 2)
    punctuality = round(averages['avg_punctuality'] or 0, 2)
    satisfaction = round(averages['avg_satisfaction'] or 0, 2)

    tutor.tut_rating_quality = quality
    tutor.tut_rating_knowledge = knowledge
    tutor.tut_rating_communication = communication
    tutor.tut_rating_punctuality = punctuality
    tutor.tut_rating_satisfaction = satisfaction
    tutor.tut_rating = round(
        (quality + knowledge + communication + punctuality + satisfaction) / 5,
        2,
    )
    tutor.save(update_fields=[
        'tut_rating',
        'tut_rating_quality',
        'tut_rating_knowledge',
        'tut_rating_communication',
        'tut_rating_punctuality',
        'tut_rating_satisfaction',
    ])


@receiver(post_save, sender=Review)
def update_tutorcourse_rating_after_save(sender, instance, **kwargs):
    """อัปเดตคะแนนรายคอร์สเมื่อสร้างหรือแก้ไขรีวิว"""
    _update_tutorcourse_rating(instance)
    _update_tutor_rating(instance)


@receiver(post_delete, sender=Review)
def update_tutorcourse_rating_after_delete(sender, instance, **kwargs):
    """อัปเดตคะแนนรายคอร์สเมื่อลบรีวิว"""
    _update_tutorcourse_rating(instance)
    _update_tutor_rating(instance)
