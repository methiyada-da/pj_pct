from datetime import date, datetime
from io import BytesIO
from tempfile import TemporaryDirectory

from django.contrib.auth.models import AnonymousUser, User
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.utils import timezone
from PIL import Image

from apps.accounts.models import Member, Tutor, TutorExperienceImage

from .views import (
    _is_future_schedule_start, calculate_bayesian_rating, register_tutor,
    tutor_profile_edit, tutor_profile_view,
)


class BayesianRatingTests(SimpleTestCase):
    def test_uses_configured_weight(self):
        self.assertEqual(
            calculate_bayesian_rating(5.0, 1, 4.0, minimum_reviews=5),
            4.17,
        )

    def test_many_reviews_approach_raw_rating(self):
        rating = calculate_bayesian_rating(4.8, 30, 4.0, minimum_reviews=5)
        self.assertEqual(rating, 4.69)

    def test_course_without_reviews_has_no_rating(self):
        self.assertEqual(calculate_bayesian_rating(0, 0, 4.0), 0.0)

    def test_system_without_reviews_has_no_rating(self):
        self.assertEqual(calculate_bayesian_rating(0, 0, 0), 0.0)


class ManageCourseScheduleTimeTests(SimpleTestCase):
    def setUp(self):
        self.current_time = timezone.make_aware(
            datetime(2026, 9, 11, 11, 0), timezone.get_current_timezone()
        )

    def test_past_date_is_not_available(self):
        self.assertFalse(_is_future_schedule_start(date(2026, 9, 10), '13:00', self.current_time))

    def test_start_time_inside_booking_window_is_not_available(self):
        today = date(2026, 9, 11)
        self.assertFalse(_is_future_schedule_start(today, '09:00', self.current_time))
        self.assertFalse(_is_future_schedule_start(today, '11:00', self.current_time))
        self.assertFalse(_is_future_schedule_start(today, '12:59', self.current_time))

    def test_start_time_at_booking_window_boundary_is_available(self):
        self.assertTrue(_is_future_schedule_start(date(2026, 9, 11), '13:00', self.current_time))

    def test_same_time_on_future_date_is_available(self):
        self.assertTrue(_is_future_schedule_start(date(2026, 9, 18), '09:00', self.current_time))


class TutorExperienceImageTests(TestCase):
    def setUp(self):
        self.media_dir = TemporaryDirectory()
        self.addCleanup(self.media_dir.cleanup)
        media_settings = override_settings(MEDIA_ROOT=self.media_dir.name)
        media_settings.enable()
        self.addCleanup(media_settings.disable)
        self.factory = RequestFactory()
        user = User.objects.create_user(username='tutor_images', password='test-password')
        self.member = Member.objects.create(
            user=user, mb_full_name='ติวเตอร์ทดสอบ', mb_email='tutor@example.com',
            mb_img='accounts/member_profile/existing.png',
        )

    def make_image(self, name):
        output = BytesIO()
        Image.new('RGB', (2, 2), color='blue').save(output, format='PNG')
        return SimpleUploadedFile(name, output.getvalue(), content_type='image/png')

    def post_request(self, path, data):
        request = self.factory.post(path, data)
        request.user = self.member.user
        request.session = {}
        request._messages = FallbackStorage(request)
        return request

    def test_registration_saves_multiple_images_and_profile_shows_them(self):
        request = self.post_request('/tutoring/register/', {
            'gpa': '3.50', 'teaching_skills': 'คณิตศาสตร์',
            'has_experience': '1', 'experience_detail': 'เคยสอนคณิตศาสตร์',
            'experience_images': [self.make_image('one.png'), self.make_image('two.png')],
        })
        response = register_tutor(request)

        self.assertEqual(response.status_code, 302)
        tutor = Tutor.objects.get(tut_id=self.member)
        self.assertEqual(tutor.experience_images.count(), 2)
        profile_request = self.factory.get('/tutoring/profile/')
        profile_request.user = AnonymousUser()
        profile = tutor_profile_view(profile_request, self.member.pk)
        self.assertContains(profile, 'เคยสอนคณิตศาสตร์')
        self.assertContains(profile, '/media/tutoring/experience/one.png')

    def test_edit_can_enable_experience_and_add_image_later(self):
        registration = self.post_request('/tutoring/register/', {
            'gpa': '3.50', 'teaching_skills': 'คณิตศาสตร์',
            'has_experience': '0', 'experience_detail': '',
        })
        self.assertEqual(register_tutor(registration).status_code, 302)
        tutor = Tutor.objects.get(tut_id=self.member)
        self.assertEqual(tutor.tut_has_exp, 0)
        self.assertFalse(tutor.experience_images.exists())
        request = self.post_request('/tutoring/profile/edit/', {
            'tut_desc': '', 'tut_skill': '', 'tut_has_exp': '1',
            'tut_exp_desc': 'เคยเป็นผู้ช่วยสอน',
            'experience_images': self.make_image('certificate.png'),
        })
        response = tutor_profile_edit(request)

        self.assertEqual(response.status_code, 302)
        tutor.refresh_from_db()
        self.assertEqual(tutor.tut_has_exp, 1)
        self.assertEqual(TutorExperienceImage.objects.filter(tutor=tutor).count(), 1)

    def test_invalid_image_does_not_save_profile_changes(self):
        tutor = Tutor.objects.create(tut_id=self.member, tut_gpax='3.50', tut_has_exp=0)
        request = self.post_request('/tutoring/profile/edit/', {
            'tut_has_exp': '1',
            'experience_images': SimpleUploadedFile('invalid.png', b'not an image', content_type='image/png'),
        })
        tutor_profile_edit(request)

        tutor.refresh_from_db()
        self.assertEqual(tutor.tut_has_exp, 0)
        self.assertFalse(tutor.experience_images.exists())
