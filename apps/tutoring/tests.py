from django.test import SimpleTestCase

from .views import calculate_bayesian_rating


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
